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
        try:
            # 먼저 전체를 읽어서 헤더와 데이터를 분리
            raw_df = pd.read_csv(file, header=None, encoding="cp949")
            # 4행(index 3)을 컬럼명으로 사용
            cols = raw_df.iloc[3].tolist()
            # 6행(index 5)부터 실제 데이터
            df = raw_df.iloc[5:].copy()
            df.columns = cols
        except Exception as e:
            # 에러 발생 시 엔진 변경 시도
            raw_df = pd.read_csv(file, header=None, engine="python", encoding="cp949")
            cols = raw_df.iloc[3].tolist()
            df = raw_df.iloc[5:].copy()
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

    # 사이클 감지 및 분석 로직 (중략 - 기존 로직 유지)
    stress = df["Stress_kPa"].values
    d = np.diff(stress)
    sign_change = np.where(np.diff(np.sign(d)) != 0)[0]
    valleys = [idx for idx in sign_change if stress[idx] < np.mean(stress)]
    valleys = np.array(valleys)

    if len(valleys) >= 11:
        fig, ax = plt.subplots(figsize=(10, 6))
        hysteresis_vals = []

        for i in range(1, 11):
            a, b = valleys[i], valleys[i+1]
            seg = df.iloc[a:b+1]
            C0 = seg["Cap"].iloc[0]
            deltaC = (seg["Cap"] - C0) / C0
            ax.plot(seg["Stress_kPa"], deltaC, alpha=0.7, label=f'Cycle {i+1}')

            # 히스테리시스 계산 (Loading vs Unloading)
            s = seg["Stress_kPa"].values
            c = deltaC.values
            p = np.argmax(s)
            s_load, c_load = s[:p+1], c[:p+1]
            s_un, c_un = s[p:], c[p:]
            
            grid = np.linspace(min(s), max(s), 200)
            cL = np.interp(grid, np.sort(s_load), c_load[np.argsort(s_load)])
            cU = np.interp(grid, np.sort(s_un), c_un[np.argsort(s_un)])
            H = np.max(np.abs(cL - cU)) * 100
            hysteresis_vals.append(H)

        ax.set_xlabel("Stress (kPa)")
        ax.set_ylabel("ΔC / C0")
        ax.set_title("Hysteresis Loop (Cycle 2~11)")
        st.pyplot(fig)

        # 결과 요약
        st.subheader("Hysteresis Results (Cycle 2~11)")
        st.write(f"Mean: {np.mean(hysteresis_vals):.3f} % | Std: {np.std(hysteresis_vals):.3f} %")
    else:
        st.warning(f"Detected only {len(valleys)} cycles. Check data range.")
