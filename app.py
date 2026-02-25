import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import plotly.graph_objects as go

st.set_page_config(page_title="LCR-UTM Analyzer", layout="wide")
st.title("🧪 LCR & UTM 데이터 통합 분석기")

# 1. 파일 업로드
col1, col2 = st.columns(2)
with col1:
    lcr_file = st.file_uploader("1️⃣ LCR 파일 업로드 (LCR.csv)", type=['csv', 'xlsx'])
with col2:
    utm_file = st.file_uploader("2️⃣ UTM 파일 업로드 (UTM.csv)", type=['csv', 'xlsx'])

if lcr_file and utm_file:
    try:
        # --- LCR 파일 처리 (상단 3줄 헤더 건너뛰기) ---
        if lcr_file.name.endswith('.csv'):
            # LCR.csv는 4번째 줄부터 실제 데이터가 시작됨 (skiprows=3)
            df_lcr = pd.read_csv(lcr_file, skiprows=3)
        else:
            df_lcr = pd.read_excel(lcr_file)

        # --- UTM 파일 처리 (한글 인코딩 대응) ---
        if utm_file.name.endswith('.csv'):
            try:
                df_utm = pd.read_csv(utm_file, encoding='utf-8')
            except:
                utm_file.seek(0)
                df_utm = pd.read_csv(utm_file, encoding='cp949')
        else:
            df_utm = pd.read_excel(utm_file)

        st.divider()
        st.subheader("⚙️ 데이터 컬럼 확인")
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("LCR 데이터 로드 완료")
            lcr_time = st.selectbox("LCR 시간 컬럼", df_lcr.columns, index=0) # 보통 Time [s]
            lcr_cp = st.selectbox("LCR Cp 컬럼", df_lcr.columns, index=1)   # 보통 Cp [F]
        with c2:
            st.info("UTM 데이터 로드 완료")
            utm_time = st.selectbox("UTM 시간 컬럼", df_utm.columns, index=0) # 보통 시간
            utm_stress = st.selectbox("UTM 분석 데이터", df_utm.columns, index=1) # 하중 등

        if st.button("🚀 분석 및 그래프 생성"):
            # 데이터 정렬 및 중복 제거 (보간을 위해 필수)
            df_lcr = df_lcr.dropna(subset=[lcr_time, lcr_cp]).sort_values(by=lcr_time)
            df_utm = df_utm.dropna(subset=[utm_time, utm_stress]).sort_values(by=utm_time)

            # --- 보간 로직 ---
            # UTM 시간 범위 내의 LCR 데이터만 사용하도록 제한
            interp_func = interp1d(
                df_lcr[lcr_time], 
                df_lcr[lcr_cp], 
                kind='linear', 
                fill_value="extrapolate"
            )
            
            df_utm['Interpolated_Cp'] = interp_func(df_utm[utm_time])

            # --- 시각화 ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_utm[utm_stress], 
                y=df_utm['Interpolated_Cp'],
                mode='lines+markers',
                name='Stress-Capacitance'
            ))
            
            fig.update_layout(
                title="분석 결과: Stress vs Capacitance",
                xaxis_title=utm_stress,
                yaxis_title=f"보간된 {lcr_cp}",
                template="plotly_white",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 다운로드 버튼
            csv = df_utm.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 결과 데이터(CSV) 다운로드", csv, "combined_result.csv", "text/csv")

    except Exception as e:
        st.error(f"⚠️ 데이터 처리 중 오류 발생: {e}")
        st.info("LCR 파일의 상단 주석이나 UTM 파일의 형식을 확인해 주세요.")
