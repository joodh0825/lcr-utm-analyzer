import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import plotly.graph_objects as go

st.set_page_config(page_title="LCR-UTM Pro Analyzer", layout="wide")
st.title("🧪 LCR-UTM 통합 분석기 (단위 변환 포함)")

def load_csv_safe(file, skip=0):
    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
    for enc in encodings:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc, skiprows=skip)
            # LCR 파일의 "Append 1" 같은 텍스트 행 제거 로직
            df = df.apply(pd.to_numeric, errors='coerce').dropna(how='all')
            return df
        except:
            continue
    return None

col1, col2 = st.columns(2)
with col1:
    lcr_file = st.file_uploader("1️⃣ LCR 파일 (LCR.csv)", type=['csv'])
with col2:
    utm_file = st.file_uploader("2️⃣ UTM 파일 (UTM.csv)", type=['csv'])

if lcr_file and utm_file:
    # LCR은 헤더 3줄 + "Append 1" 행 처리 위해 skip=3 후 전처리
    df_lcr = load_csv_safe(lcr_file, skip=3)
    # UTM은 헤더 2줄(단위 포함) 건너뜀
    df_utm = load_csv_safe(utm_file, skip=1)

    if df_lcr is not None and df_utm is not None:
        st.divider()
        
        # --- 면적 입력 섹션 ---
        st.subheader("📏 시편 정보 입력")
        area_mm2 = st.number_input("시편의 단면적을 입력하세요 (mm²)", min_value=0.0001, value=10.0, step=0.1)
        
        st.subheader("⚙️ 컬럼 매핑")
        c1, c2 = st.columns(2)
        with c1:
            lcr_time = st.selectbox("LCR 시간 [s]", df_lcr.columns, index=0)
            lcr_cp = st.selectbox("LCR Cp [F]", df_lcr.columns, index=4)
        with c2:
            utm_time = st.selectbox("UTM 시간 [sec]", df_utm.columns, index=1)
            utm_load = st.selectbox("UTM 하중 [kgf]", df_utm.columns, index=2)

        if st.button("🚀 분석 및 Pa 단위 변환 실행"):
            # 1. 단위 변환 (kgf -> Pa)
            # 1 kgf = 9.80665 N, 1 mm^2 = 10^-6 m^2
            df_utm['Pressure_Pa'] = (df_utm[utm_load] * 9.80665) / (area_mm2 * 1e-6)

            # 2. 데이터 정렬 및 클리닝
            df_lcr = df_lcr.dropna(subset=[lcr_time, lcr_cp]).sort_values(by=lcr_time)
            df_utm = df_utm.dropna(subset=[utm_time, 'Pressure_Pa']).sort_values(by=utm_time)

            # 3. 보간 (Interpolation)
            interp_func = interp1d(df_lcr[lcr_time], df_lcr[lcr_cp], kind='linear', fill_value="extrapolate")
            df_utm['Interpolated_Cp'] = interp_func(df_utm[utm_time])

            # 4. 시각화 (X축: Pressure (Pa), Y축: Cp (F))
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_utm['Pressure_Pa'], 
                y=df_utm['Interpolated_Cp'],
                mode='lines+markers',
                marker=dict(color='royalblue')
            ))
            
            fig.update_layout(
                title=f"Pressure (Pa) vs Capacitance (F) [Area: {area_mm2} mm²]",
                xaxis_title="Pressure [Pa]",
                yaxis_title="Capacitance [F]",
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 데이터 요약
            st.write(f"✅ 변환 확인: 하중 {df_utm[utm_load].max():.2f} kgf -> 압력 {df_utm['Pressure_Pa'].max():.2e} Pa")
            
            csv = df_utm.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 결과(Pa 변환 데이터) 다운로드", csv, "converted_data.csv", "text/csv")
