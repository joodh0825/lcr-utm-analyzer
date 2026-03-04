import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Flexible Pressure Sensor: 10-Cycle Hysteresis Analyzer")

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
        # 4행(index 3)에서 컬럼명을 리스트로 추출
        cols = [c.strip() for c in string_data[3].split(',')]
        
        # [핵심 수정] Cp [F]가 포함된 컬럼 인덱스를 직접 찾음
        cp_idx = next((i for i, c in enumerate(cols) if "Cp [F]" in c), 4) # 못 찾으면 기본 5열
        time_idx = next((i for i, c in enumerate(cols) if "Time" in c), 0)
        
        data_rows = [line.split(',') for line in string_data[5:] if line.strip()]
        df = pd.DataFrame(data_rows).iloc[:, :len(cols)]
        df.columns = cols
        # 필요한 컬럼만 추출하여 숫자형 변환
        df = df.iloc[:, [time_idx, cp_idx]].apply(pd.to_numeric, errors="coerce").dropna()
        df.columns = ["Time", "Cap"]
    else:
        df = pd.read_excel(file, usecols=[1, 2])
        df.columns = ["Time", "Load"]
    return df

if utm_file and lcr_file:
    utm = load_file(utm_file)
    lcr = load_file(lcr_file)

    # 시작 시간 0으로 맞추기 (Sync 준비)
    utm["Time"] -= utm["Time"].iloc[0]
    lcr["Time"] -= lcr["Time"].iloc[0]

    # UTM 시간축 기준으로 LCR 데이터 보간 (시간 보간)
    cap_interp = np.interp(utm["Time"], lcr["Time"], lcr["Cap"], left=np.nan, right=np.nan)
    df_sync = utm.copy()
    df_sync["Cap_Interp"] = cap_interp
    df_sync = df_sync.dropna()

    # =========================
    # Double Y-axis Plot: Time-Series
    # =========================
    st.subheader("Time-Series Synchronization (Load & Interpolated Cp)")
    fig, ax1 = plt.subplots(figsize=(12, 5))

    color1 = 'tab:blue'
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Load (N)', color=color1)
    ax1.plot(df_sync['Time'], df_sync['Load'], color=color1, label='Load (UTM)', alpha=0.8)
    ax1.tick_params(axis='y', labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Capacitance (F)', color=color2)
    ax2.plot(df_sync['Time'], df_sync['Cap_Interp'], color=color2, label='Interpolated Cp', linewidth=1.5)
    ax2.tick_params(axis='y', labelcolor=color2)

    fig.tight_layout()
    st.pyplot(fig)

    # 데이터 확인용 테이블 (선택 사항)
    st.write("Synchronized Data Preview", df_sync.head())
