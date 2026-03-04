import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Flexible Pressure Sensor: 10-Cycle Hysteresis Analyzer")

# 데이터 업로드 섹션
utm_file = st.file_uploader("Upload UTM File (.xlsx)", type=["xlsx"])
lcr_file = st.file_uploader("Upload LCR File (.csv)", type=["csv"])

# 실험 파라미터 (공학박사님 설정값 반영)
col1, col2 = st.columns(2)
with col1:
    diameter = st.number_input("Sample Diameter (mm)", value=20.0) # 20mm 샘플
with col2:
    baseline_kpa = st.number_input("Baseline Stress Shift (kPa)", value=1.0)

def load_file(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        # [수정] LCR 데이터: 1~3행, 5행 제외하고 읽기
        import io
        # 파일을 텍스트 스트림으로 읽기 (ParserError 방지)
        string_data = file.getvalue().decode("cp949").splitlines()
        
        # 4행(index 3)에서 컬럼 추출 (쉼표로 분리 및 공백 제거)
        cols = [c.strip() for c in string_data[3].split(',')]
        
        # 6행(index 5)부터 본문 데이터 추출
        data_rows = []
        for line in string_data[5:]:
            if line.strip(): # 빈 줄 제외
                data_rows.append(line.split(','))
        
        # DataFrame 생성 및 컬럼명 부여
        df = pd.DataFrame(data_rows)
        # 데이터 컬럼 수가 헤더와 다를 수 있으므로 필요한 부분만 슬라이싱
        df = df.iloc[:, :len(cols)]
        df.columns = cols
    else:
        # [수정] UTM 데이터: B(Time), C(Load) 열만 선택
        df = pd.read_excel(file, usecols=[1, 2])
    
    df.columns = [str(c).strip() for c in df.columns]
    return df

if utm_file and lcr_file:
    utm_raw = load_file(utm_file)
    lcr_raw = load_file(lcr_file)

    # 컬럼 자동 매칭 시도
    utm_time_col = st.selectbox("Select UTM Time Column", utm_raw.columns, index=0)
    utm_load_col = st.selectbox("Select UTM Load Column", utm_raw.columns, index=1)
    lcr_time_col = st.selectbox("Select LCR Time Column", lcr_raw.columns, index=0)
    lcr_cap_col  = st.selectbox("Select LCR Capacitance Column", lcr_raw.columns, index=1)

    utm = utm_raw[[utm_time_col, utm_load_col]].copy()
    lcr = lcr_raw[[lcr_time_col, lcr_cap_col]].copy()

    utm.columns = ["Time","Load"]
    lcr.columns = ["Time","Cap"]

    # 숫자 데이터 변환 및 정렬
    utm = utm.apply(pd.to_numeric, errors="coerce").dropna()
    lcr = lcr.apply(pd.to_numeric, errors="coerce").dropna()
    utm = utm.sort_values("Time")
    lcr = lcr.sort_values("Time")

    # 압력 계산 (Load to kPa)
    r = (diameter/2) * 1e-3
    A = np.pi * r**2
    utm["Force_N"] = utm["Load"] * 9.80665 # kgf to N
    utm["Stress_kPa"] = (utm["Force_N"]/A)/1000
    utm["Stress_kPa"] -= baseline_kpa

    # 시간축 동기화 (LCR to UTM)
    cap_interp = np.interp(
        utm["Time"],
        lcr["Time"],
        lcr["Cap"],
        left=np.nan,
        right=np.nan
    )

    df = utm.copy()
    df["Cap"] = cap_interp
    df = df.dropna()

    # =========================
    # Double Y-axis Plot: Time vs (Load & Cp)
    # =========================
    st.subheader("Time-Series Synchronization (Load & Cp)")
    
    fig, ax1 = plt.subplots(figsize=(12, 5))

    # 왼쪽 축: Load (N)
    color1 = 'tab:blue'
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Load (N)', color=color1)
    ax1.plot(df['Time'], df['Load'], color=color1, label='Load (UTM)')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)

    # 오른쪽 축: Cp (F)
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Capacitance (F)', color=color2)
    ax2.plot(df['Time'], df['Cap'], color=color2, label='Cp (LCR)')
    ax2.tick_params(axis='y', labelcolor=color2)

    fig.tight_layout()
    st.pyplot(fig)

    # =========================
    # Results & Summary
    # =========================
    if len(valleys) >= 11:
        st.subheader("Hysteresis Results (Cycle 2~11)")
        # hysteresis_vals가 루프 내에서 계산된 후 출력되어야 함
        if 'hysteresis_vals' in locals() and hysteresis_vals:
            st.write(f"Mean Hysteresis: **{np.mean(hysteresis_vals):.3f} %**")
            st.write(f"Standard Deviation: **{np.std(hysteresis_vals):.3f} %**")
            st.line_chart(hysteresis_vals)
    else:
        st.warning(f"Detected only {len(valleys)} cycles. Check data range for Hysteresis analysis.")
