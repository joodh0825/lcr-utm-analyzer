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

    # 0. 기초 시간축 설정 및 단위 변환 (kgf to kPa, pF to F)
    u_raw_time = utm["Time"] - utm["Time"].iloc[0]
    utm["Stress_kPa"] = ((utm["Load"] * 9.80665) / area_m2) / 1000 - baseline_kpa
    l_raw_time = lcr["Time"] - lcr["Time"].iloc[0]

    # =========================
    # 1. Fine-Tuning Interface (Slider + Input 연동)
    # =========================
    st.divider()
    st.subheader("Fine-Tuning: Manual Alignment & Zoom View")
    
    col_off, col_zoom = st.columns(2)
    
    with col_off:
        st.write("**Step 1: Time Offset (s)**")
        # 수치 입력창을 기준으로 슬라이더가 움직이도록 구성
        i_offset = st.number_input("Input Offset Value (s)", value=0.000, step=0.001, format="%.3f", key="i_off")
        s_offset = st.slider("Fine-tune with Slider", -10.0, 10.0, i_offset, 0.01, key="s_off")
        # 최종 오프셋은 수치 입력창과 슬라이더 중 최근 변경된 값을 반영 (여기서는 수치 우선)
        final_offset = i_offset

    with col_zoom:
        st.write("**Step 2: Time Zoom (s)**")
        max_t = float(u_raw_time.max())
        z_min_input = st.number_input("Start Time (s)", value=0.0, step=0.1)
        z_max_input = st.number_input("End Time (s)", value=max_t, step=0.1)
        final_zoom = (z_min_input, z_max_input)

    # =========================
    # 2. 데이터 동기화 및 보간 계산
    # =========================
    l_adj_time = l_raw_time + final_offset
    cap_interp = np.interp(u_raw_time, l_adj_time, lcr["Cap"], left=np.nan, right=np.nan)
    
    df_sync = pd.DataFrame({
        "Time": u_raw_time, 
        "Stress_kPa": utm["Stress_kPa"], 
        "Cap": cap_interp
    }).dropna()

    # =========================
    # 3. 이중 그래프 출력 (Reference & Zoom)
    # =========================
    # (1) 상단 원본 그래프
    st.subheader("Reference: Original Raw Data (Unadjusted)")
    fig_ref, ax_ref = plt.subplots(figsize=(12, 3))
    ax_ref.plot(u_raw_time, utm["Stress_kPa"], color='tab:blue', alpha=0.4, label='Stress')
    ax_ref_twin = ax_ref.twinx()
    ax_ref_twin.plot(l_raw_time, lcr["Cap"], color='tab:red', alpha=0.4, label='Cap')
    ax_ref.set_title("Initial State (Time Offset = 0)")
    st.pyplot(fig_ref)

    # (2) 하단 확대 및 조정 그래프
    st.subheader("Adjusted & Zoomed View")
    fig_adj, ax_adj1 = plt.subplots(figsize=(12, 5))
    ax_adj1.plot(df_sync['Time'], df_sync['Stress_kPa'], color='tab:blue', label='Stress (kPa)', linewidth=1.5)
    ax_adj1.set_ylabel('Stress (kPa)', color='tab:blue')
    
    ax_adj2 = ax_adj1.twinx()
    ax_adj2.plot(df_sync['Time'], df_sync['Cap'], color='tab:red', label='Capacitance (F)', linewidth=1.5)
    ax_adj2.set_ylabel('Capacitance (F)', color='tab:red')
    
    ax_adj1.set_xlim(final_zoom[0], final_zoom[1])
    ax_adj1.set_xlabel('Time (s)')
    ax_adj1.grid(True, which='both', linestyle='--', alpha=0.5)
    fig_adj.tight_layout()
    st.pyplot(fig_adj)

    # =========================
    # 4. 데이터 저장 및 내보내기
    # =========================
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
