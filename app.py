import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Flexible Pressure Sensor: Precision Time Alignment Tool")

# 데이터 업로드 섹션
utm_file = st.file_uploader("Upload UTM File (.xlsx)", type=["xlsx"])
lcr_file = st.file_uploader("Upload LCR File (.csv)", type=["csv"])

# 실험 파라미터
col1, col2 = st.columns(2)
with col1:
    diameter = st.number_input("Sample Diameter (mm)", value=20.0)
with col2:
    baseline_kpa = st.number_input("Baseline Stress Shift (kPa)", value=1.0)

def load_file(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        import io
        string_data = file.getvalue().decode("cp949").splitlines()
        cols = [c.strip() for c in string_data[3].split(',')]
        
        # 키워드 매칭으로 정확한 컬럼 인덱스 추출
        cp_idx = next((i for i, c in enumerate(cols) if "Cp [F]" in c), 4)
        time_idx = next((i for i, c in enumerate(cols) if "Time" in c), 0)
        
        data_rows = [line.split(',') for line in string_data[5:] if line.strip()]
        df = pd.DataFrame(data_rows).iloc[:, :len(cols)]
        df.columns = cols
        df = df.iloc[:, [time_idx, cp_idx]].apply(pd.to_numeric, errors="coerce").dropna()
        df.columns = ["Time", "Cap"]
    else:
        # UTM 데이터: B(Time), C(Load) 열만 선택
        df = pd.read_excel(file, usecols=[1, 2])
        df.columns = ["Time", "Load"]
    return df

if utm_file and lcr_file:
    utm = load_file(utm_file)
    lcr = load_file(lcr_file)

    # 1. 고정된 상단 원본 그래프 (Reference)
    st.divider()
    st.subheader("Reference: Original Raw Data (Unadjusted)")
    u_raw_time = utm["Time"] - utm["Time"].iloc[0]
    l_raw_time = lcr["Time"] - lcr["Time"].iloc[0]
    
    fig_ref, ax_ref = plt.subplots(figsize=(12, 3))
    ax_ref.plot(u_raw_time, utm["Load"], color='tab:blue', alpha=0.5, label='UTM Load')
    ax_ref.set_ylabel('Load (N)', color='tab:blue')
    ax_ref_twin = ax_ref.twinx()
    ax_ref_twin.plot(l_raw_time, lcr["Cap"], color='tab:red', alpha=0.5, label='LCR Cap')
    ax_ref_twin.set_ylabel('Cap (F)', color='tab:red')
    ax_ref.set_xlabel('Time (s)')
    ax_ref.set_title("Original State: Visualizing Initial Lag")
    fig_ref.tight_layout()
    st.pyplot(fig_ref)

    # 2. 하단 조정 인터페이스 (Manual Alignment & Zoom)
    st.divider()
    st.subheader("Fine-Tuning: Manual Alignment & Zoom View")
    
    c1, c2 = st.columns(2)
    with c1:
        time_offset = st.slider("Step 1: Adjust LCR Time Offset (s)", -5.0, 5.0, 0.0, 0.01)
    with c2:
        max_time_val = float(u_raw_time.max())
        zoom_range = st.slider("Step 2: Zoom Time Window (s)", 0.0, max_time_val, (0.0, max_time_val))

    # 데이터 재계산 및 보간
    l_adj_time = l_raw_time + time_offset
    cap_interp = np.interp(u_raw_time, l_adj_time, lcr["Cap"], left=np.nan, right=np.nan)
    
    df_sync = pd.DataFrame({
        "Time": u_raw_time,
        "Load": utm["Load"],
        "Cap": cap_interp
    }).dropna()

    # 확대 및 조정 그래프 출력
    fig_adj, ax_adj1 = plt.subplots(figsize=(12, 5))
    ax_adj1.plot(df_sync['Time'], df_sync['Load'], color='tab:blue', label='Load (UTM)', linewidth=2)
    ax_adj1.set_ylabel('Load (N)', color='tab:blue')
    
    ax_adj2 = ax_adj1.twinx()
    ax_adj2.plot(df_sync['Time'], df_sync['Cap'], color='tab:red', label='Adjusted Cap (LCR)', linewidth=2)
    ax_adj2.set_ylabel('Capacitance (F)', color='tab:red')
    
    # Zoom 설정 적용
    ax_adj1.set_xlim(zoom_range[0], zoom_range[1])
    ax_adj1.set_xlabel('Time (s)')
    ax_adj1.grid(True, which='both', linestyle='--', alpha=0.5)
    
    lines1, labels1 = ax_adj1.get_legend_handles_labels()
    lines2, labels2 = ax_adj2.get_legend_handles_labels()
    ax_adj1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
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
