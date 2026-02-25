import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import plotly.graph_objects as go

st.set_page_config(page_title="LCR-UTM Analyzer", layout="wide")
st.title("📊 LCR & UTM 데이터 통합 분석기")

# 1. 파일 업로드
col1, col2 = st.columns(2)
with col1:
    lcr_file = st.file_uploader("1️⃣ LCR 파일 업로드 (Time, Cp)", type=['csv', 'xlsx', 'xls'])
with col2:
    utm_file = st.file_uploader("2️⃣ UTM 파일 업로드 (Time, Stress)", type=['csv', 'xlsx', 'xls'])

if lcr_file and utm_file:
    try:
        # 파일 읽기 함수
        def load_data(file):
            if file.name.endswith('.csv'):
                return pd.read_csv(file)
            return pd.read_excel(file)

        df_lcr = load_data(lcr_file)
        df_utm = load_data(utm_file)

        st.divider()
        st.subheader("⚙️ 데이터 컬럼 매핑")
        
        # 사용자가 직접 컬럼을 선택하게 함 (파일마다 이름이 다를 수 있으므로)
        c1, c2 = st.columns(2)
        with c1:
            st.write("**LCR 데이터**")
            lcr_time = st.selectbox("시간(Time) 컬럼 선택", df_lcr.columns, key="lcr_t")
            lcr_cp = st.selectbox("Cp [F] 컬럼 선택", df_lcr.columns, key="lcr_c")
        with c2:
            st.write("**UTM 데이터**")
            utm_time = st.selectbox("시간(Time) 컬럼 선택", df_utm.columns, key="utm_t")
            utm_stress = st.selectbox("Stress (Kfg/mm^2) 컬럼 선택", df_utm.columns, key="utm_s")

        if st.button("🚀 데이터 통합 및 그래프 생성"):
            # 데이터 정렬
            df_lcr = df_lcr.sort_values(by=lcr_time)
            df_utm = df_utm.sort_values(by=utm_time)

            # --- 핵심 로직: 보간법 (Interpolation) ---
            # UTM의 시간축을 기준으로 LCR의 Cp 값을 추정합니다.
            interp_func = interp1d(
                df_lcr[lcr_time], 
                df_lcr[lcr_cp], 
                kind='linear', 
                fill_value="extrapolate"
            )
            
            # UTM 데이터 프레임에 보간된 Cp 값 추가
            df_utm['Interpolated_Cp'] = interp_func(df_utm[utm_time])

            # --- 그래프 그리기 ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_utm[utm_stress], 
                y=df_utm['Interpolated_Cp'],
                mode='lines+markers',
                marker=dict(size=4),
                line=dict(width=2),
                name='Stress vs Cp'
            ))
            
            fig.update_layout(
                title="Stress-Capacitance 분석 결과",
                xaxis_title=f"Stress ({utm_stress})",
                yaxis_title=f"Interpolated Cp ({lcr_cp})",
                template="plotly_white",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 결과 데이터 미리보기 및 다운로드
            st.subheader("📋 통합 데이터 미리보기")
            st.dataframe(df_utm[[utm_time, utm_stress, 'Interpolated_Cp']].head(10))
            
            csv = df_utm.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 통합 데이터(CSV) 다운로드", csv, "result_combined.csv", "text/csv")

    except Exception as e:
        st.error(f"⚠️ 오류가 발생했습니다: {e}")
        st.info("파일의 데이터 형식이 올바른지 확인해 주세요.")
