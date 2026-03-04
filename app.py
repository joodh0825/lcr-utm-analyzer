import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Flexible Pressure Sensor: Precision Analyzer (kgf to kPa)")

# 데이터 업로드
utm_file = st.file_uploader("Upload UTM File (.xlsx)", type=["xlsx"])
lcr_file = st.file_uploader("Upload LCR File (.csv)", type=["csv"])

# [수정] 샘플 형상 및 파라미터 설정
st.divider()
st.subheader("Sample Geometry & Stress Parameters")
shape = st.radio("Select Sample Shape", ["Circular", "Rectangular"], horizontal=True)

area_m2 = 0.0
if shape == "Circular":
    diameter = st.number_input("Sample Diameter (mm)", value=20.0)
    radius_m = (diameter / 2) * 1e-3
    area_m2 = np.pi * (radius_m ** 2)
    st.caption(f"Target: Circular sample with Ø {diameter} mm")
else:
    width = st.number_input("Width (mm)", value=20.0)
    height = st.number_input("Height (mm)", value=20.0)
    area_m2 = (width * 1e-3) * (height * 1e-3)
    st.caption(f"Target: Rectangular sample ({width} mm x {height} mm)")

baseline_kpa = st.number_input("Baseline Stress Shift (kPa)", value=0.0)

def load_file(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        import io
        string_data = file.getvalue().decode("cp949").splitlines()
        cols = [c.strip() for c in string_data[3].split(',')]
        cp_idx = next((i for i, c in enumerate(cols) if "Cp [F]" in c), 4)
        time_idx = next((i for i, c in enumerate(cols) if "Time" in c), 0)
        
        data_rows = [line.split(',') for line in string_data[5:] if line.strip()]
        df = pd.DataFrame(data_rows).iloc[:, :len(cols)]
        df.columns = cols
        df = df.iloc[:, [time_idx, cp_idx]].apply(pd.to_numeric, errors="coerce").dropna()
        df.columns = ["Time", "Cap"]
        # [수정] pF 단위를 기본으로 계산 (10^-12)
        df["Cap"] = df["Cap"] * 1e-12
    else:
        df = pd.read_excel(file, usecols=[1, 2])
        df.columns = ["Time", "Load"]
    return df

if utm_file and lcr_file:
    utm = load_file(utm_file)
    lcr = load_file(lcr_file)

    # [수정] 압력 환산 (kgf -> N -> kPa)
    # 1 kgf = 9.80665 N, 1 kPa = 1000 N/m^2
    u_raw_time = utm["Time"] - utm["Time"].iloc[0]
    utm["Stress_kPa"] = ((utm["Load"] * 9.80665) / area_m2) / 1000 - baseline_kpa
    
    l_raw_time = lcr["Time"] - lcr["Time"].iloc[0]

    # --- 이후 Manual Alignment & Zoom 로직 (동일) ---
    st.subheader("Fine-Tuning: Manual Alignment & Zoom")
    # =========================
    # Fine-Tuning: Alignment & Zoom (Slider + Input)
    # =========================
    st.divider()
    st.subheader("Fine-Tuning: Manual Alignment & Zoom View")
    
    col_off, col_zoom = st.columns(2)
    
    with col_off:
        st.write("Step 1: Time Offset (s)")
        inner_col1, inner_col2 = st.columns([3, 1])
        with inner_col1:
            s_offset = st.slider("Offset Slider", -10.0, 10.0, 0.0, 0.01, key="s_off")
        with inner_col2:
            i_offset = st.number_input("Input (s)", value=s_offset, step=0.001, key="i_off")
        final_offset = i_offset

    with col_zoom:
        st.write("Step 2: Time Zoom (s)")
        max_t = float(u_raw_time.max())
        z_range = st.slider("Zoom Slider", 0.0, max_t, (0.0, max_t), key="s_zoom")
        z_min = st.number_input("Start (s)", value=z_range[0], step=0.1, key="i_zmin")
        z_max = st.number_input("End (s)", value=z_range[1], step=0.1, key="i_zmax")
        final_zoom = (z_min, z_max)

    # 데이터 실시간 재계산
    l_adj_time = l_raw_time + final_offset
    cap_interp = np.interp(u_raw_time, l_adj_time, lcr["Cap"], left=np.nan, right=np.nan)
    df_sync = pd.DataFrame({
        "Time": u_raw_time, 
        "Stress_kPa": utm["Stress_kPa"], 
        "Cap": cap_interp
    }).dropna()

    # 결과 그래프 (수정된 파라미터 즉시 반영)
    fig_adj, ax_adj1 = plt.subplots(figsize=(12, 5))
    ax_adj1.plot(df_sync['Time'], df_sync['Stress_kPa'], color='tab:blue', label='Stress (kPa)', linewidth=1.5)
    ax_adj1.set_ylabel('Stress (kPa)', color='tab:blue')
    
    ax_adj2 = ax_adj1.twinx()
    # Capacitance 단위 가독성을 위해 pF로 다시 표시하거나 F로 유지
    ax_adj2.plot(df_sync['Time'], df_sync['Cap'], color='tab:red', label='Capacitance (F)', linewidth=1.5)
    ax_adj2.set_ylabel('Capacitance (F)', color='tab:red')
    
    ax_adj1.set_xlim(final_zoom[0], final_zoom[1])
    ax_adj1.set_xlabel('Time (s)')
    ax_adj1.grid(True, which='both', linestyle='--', alpha=0.5)
    fig_adj.tight_layout()
    st.pyplot(fig_adj)

    l_adj_time = l_raw_time + time_offset
    cap_interp = np.interp(u_raw_time, l_adj_time, lcr["Cap"], left=np.nan, right=np.nan)
    
    df_sync = pd.DataFrame({"Time": u_raw_time, "Stress_kPa": utm["Stress_kPa"], "Cap": cap_interp}).dropna()

    # 하단 확대 그래프 (Stress vs Cap)
    fig_adj, ax_adj1 = plt.subplots(figsize=(12, 5))
    ax_adj1.plot(df_sync['Time'], df_sync['Stress_kPa'], color='tab:blue', label='Stress (kPa)', linewidth=2)
    ax_adj1.set_ylabel('Stress (kPa)', color='tab:blue')
    ax_adj2 = ax_adj1.twinx()
    ax_adj2.plot(df_sync['Time'], df_sync['Cap'], color='tab:red', label='Capacitance (F)', linewidth=2)
    ax_adj2.set_ylabel('Capacitance (F)', color='tab:red')
    ax_adj1.set_xlim(zoom_range[0], zoom_range[1])
    fig_adj.tight_layout()
    st.pyplot(fig_adj)

    # 3. 데이터 프리뷰 및 다운로드
    st.divider()
    st.subheader("Synchronized Data Preview & Export")
    st.dataframe(df_sync, use_container_width=True)

    csv_data = df_sync.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Synchronized Data as CSV",
        data=csv_data,
        file_name='synchronized_sensor_data.csv',
        mime='text/csv',
    )
