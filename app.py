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
        cols = [c.strip() for c in string_data[3].split(',')]
        data_rows = [line.split(',') for line in string_data[5:] if line.strip()]
        df = pd.DataFrame(data_rows).iloc[:, :len(cols)]
        df.columns = cols
    else:
        df = pd.read_excel(file, usecols=[1, 2])
    df.columns = [str(c).strip() for c in df.columns]
    return df

if utm_file and lcr_file:
    utm_raw = load_file(utm_file)
    lcr_raw = load_file(lcr_file)

    # 컬럼 선택
    c1, c2, c3, c4 = st.columns(4)
    with c1: utm_time_col = st.selectbox("UTM Time", utm_raw.columns, index=0)
    with c2: utm_load_col = st.selectbox("UTM Load", utm_raw.columns, index=1)
    with c3: lcr_time_col = st.selectbox("LCR Time", lcr_raw.columns, index=0)
    with c4: lcr_cap_col  = st.selectbox("LCR Cap", lcr_raw.columns, index=1)

    # 데이터 정제
    utm = utm_raw[[utm_time_col, utm_load_col]].apply(pd.to_numeric, errors="coerce").dropna().sort_values(utm_time_col)
    lcr = lcr_raw[[lcr_time_col, lcr_cap_col]].apply(pd.to_numeric, errors="coerce").dropna().sort_values(lcr_time_col)
    utm.columns, lcr.columns = ["Time", "Load"], ["Time", "Cap"]

    # 압력 계산
    r = (diameter/2) * 1e-3
    A = np.pi * r**2
    utm["Stress_kPa"] = ((utm["Load"] * 9.80665)/A)/1000 - baseline_kpa

    # 동기화
    cap_interp = np.interp(utm["Time"], lcr["Time"], lcr["Cap"], left=np.nan, right=np.nan)
    df = utm.copy()
    df["Cap"] = cap_interp
    df = df.dropna()

    # 1. 시계열 동기화 그래프
    st.subheader("Time-Series Synchronization (Load & Cp)")
    fig_sync, ax1 = plt.subplots(figsize=(12, 4))
    ax1.plot(df['Time'], df['Load'], color='tab:blue', label='Load (N)')
    ax1.set_ylabel('Load (N)', color='tab:blue')
    ax2 = ax1.twinx()
    ax2.plot(df['Time'], df['Cap'], color='tab:red', label='Cp (F)')
    ax2.set_ylabel('Capacitance (F)', color='tab:red')
    st.pyplot(fig_sync)

    # 2. 사이클 감지 및 히스테리시스 분석
    stress = df["Stress_kPa"].values
    d = np.diff(stress)
    sign_change = np.where(np.diff(np.sign(d)) != 0)[0]
    valleys = np.array([idx for idx in sign_change if stress[idx] < np.mean(stress)])

    if len(valleys) >= 11:
        st.subheader("Hysteresis Loop (Cycle 2~11)")
        fig_hys, ax_hys = plt.subplots(figsize=(8, 6))
        hysteresis_vals = []

        for i in range(1, 11):
            seg = df.iloc[valleys[i]:valleys[i+1]+1]
            C0 = seg["Cap"].iloc[0]
            deltaC = (seg["Cap"] - C0) / C0
            ax_hys.plot(seg["Stress_kPa"], deltaC, alpha=0.5)

            # 히스테리시스 정량화 (Loading/Unloading 분리)
            s, c = seg["Stress_kPa"].values, deltaC.values
            p = np.argmax(s)
            s_l, c_l = s[:p+1], c[:p+1]
            s_u, c_u = s[p:], c[p:]
            grid = np.linspace(min(s), max(s), 200)
            cL = np.interp(grid, np.sort(s_l), c_l[np.argsort(s_l)])
            cU = np.interp(grid, np.sort(s_u), c_u[np.argsort(s_u)])
            hysteresis_vals.append(np.max(np.abs(cL - cU)) * 100)

        ax_hys.set_xlabel("Stress (kPa)"); ax_hys.set_ylabel("ΔC / C0")
        st.pyplot(fig_hys)

        # 3. 결과 요약
        st.subheader("Hysteresis Summary")
        res_col1, res_col2 = st.columns(2)
        res_col1.metric("Mean Hysteresis", f"{np.mean(hysteresis_vals):.3f} %")
        res_col2.metric("Std Deviation", f"{np.std(hysteresis_vals):.3f} %")
        st.line_chart(hysteresis_vals)
    else:
        st.warning(f"Detected only {len(valleys)} cycles. Check data range.")
