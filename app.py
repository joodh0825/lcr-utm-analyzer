import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import plotly.graph_objects as go

st.set_page_config(page_title="LCR-UTM 분석기", layout="wide")
st.title("🧪 LCR & UTM 데이터 통합 분석기")

# 파일 업로드 섹션
col1, col2 = st.columns(2)
with col1:
    lcr_file = st.file_uploader("1️⃣ LCR 파일 (Time, Cp)", type=['csv', 'xlsx'])
with col2:
    utm_file = st.file_uploader("2️⃣ UTM 파일 (시간, Stress)", type=['csv', 'xlsx'])

if lcr_file and utm_file:
    try:
        # 데이터 읽기
        df_lcr = pd.read_csv(lcr_file) if lcr_file.name.endswith('.csv') else pd.read_excel(lcr_file)
        df_utm = pd.read_csv(utm_file) if utm_file.name.endswith('.csv') else pd.read_excel(utm_file)

        st.divider()
        st.subheader("⚙️ 데이터 매핑 설정")
        
        # 실제 파일의 컬럼명 선택 (사용자가 직접 선택 가능하게 구성)
        c1, c2, c3 = st.columns(3)
        with c1:
            lcr_time_col = st.selectbox("LCR 시간 컬럼", df_lcr.columns)
            lcr_cp_col = st.selectbox("LCR Cp 컬럼", df_lcr.columns)
        with c2:
            utm_time_col = st.selectbox("UTM 시간 컬럼", df_utm.columns)
            utm_stress_col = st.selectbox("UTM Stress 컬럼", df_utm.columns)

        if st.button("🚀 분석 시작 (보간법 적용)"):
            # 1. 시간 기준 정렬
            df_lcr = df_lcr.sort_values(by=lcr_time_col)
            df_utm = df_utm.sort_values(by=utm_time_col)

            # 2. 보간 함수 생성 (LCR 데이터를 기준으로)
            # UTM 시간축에 맞는 Cp 값을 추정함
            interp_func = interp1d(
                df_lcr[lcr_time_col], 
                df_lcr[lcr_cp_col], 
                kind='linear', 
                fill_value="extrapolate"
            )
            
            # 3. UTM 데이터에 보간된 Cp 값 추가
            df_utm['Interpolated_Cp'] = interp_func(df_utm[utm_time_col])

            # 4. 그래프 시각화 (X: Stress, Y: Cp)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_utm[utm_stress_col], 
                y=df_utm['Interpolated_Cp'],
                mode='lines+markers',
                name='Stress vs Cp'
            ))
            
            fig.update_layout(
                title="Stress-Capacitance Curve",
                xaxis_title=f"Stress ({utm_stress_col})",
                yaxis_title=f"Cp ({lcr_cp_col})",
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 데이터 다운로드 버튼
            csv = df_utm.to_csv(index=False).encode('utf-8')
            st.download_button("📊 결과 데이터 다운로드(CSV)", csv, "result.csv", "text/csv")

    except Exception as e:
        st.error(f"에러 발생: {e}. 파일의 컬럼명이나 형식을 확인해주세요.")
