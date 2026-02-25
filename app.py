import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import plotly.graph_objects as go

st.set_page_config(page_title="LCR-UTM Analyzer", layout="wide")
st.title("🧪 LCR & UTM 데이터 통합 분석기")

def load_csv_safe(file, skip=0):
    """인코딩 에러를 방지하며 CSV를 읽는 함수"""
    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc, skiprows=skip)
        except Exception:
            continue
    return None

# 1. 파일 업로드
col1, col2 = st.columns(2)
with col1:
    lcr_file = st.file_uploader("1️⃣ LCR 파일 업로드 (LCR.csv)", type=['csv'])
with col2:
    utm_file = st.file_uploader("2️⃣ UTM 파일 업로드 (UTM.csv)", type=['csv'])

if lcr_file and utm_file:
    try:
        # LCR 파일: 상단 3줄이 주석이므로 3줄 건너뜀
        df_lcr = load_csv_safe(lcr_file, skip=3)
        # UTM 파일: 헤더가 바로 시작되므로 그대로 읽음
        df_utm = load_csv_safe(utm_file, skip=0)

        if df_lcr is None or df_utm is None:
            st.error("파일을 읽을 수 없습니다. 인코딩 형식을 확인해주세요.")
        else:
            st.divider()
            st.subheader("⚙️ 데이터 컬럼 확인")
            
            c1, c2 = st.columns(2)
            with c1:
                lcr_time = st.selectbox("LCR 시간 컬럼", df_lcr.columns, index=0)
                lcr_cp = st.selectbox("LCR Cp 컬럼", df_lcr.columns, index=1)
            with c2:
                utm_time = st.selectbox("UTM 시간 컬럼", df_utm.columns, index=0)
                utm_stress = st.selectbox("UTM 분석 데이터(Stress/Force)", df_utm.columns, index=1)

            if st.button("🚀 분석 및 그래프 생성"):
                # 전처리: 숫자형 변환 및 결측치 제거
                df_lcr[lcr_time] = pd.to_numeric(df_lcr[lcr_time], errors='coerce')
                df_lcr[lcr_cp] = pd.to_numeric(df_lcr[lcr_cp], errors='coerce')
                df_utm[utm_time] = pd.to_numeric(df_utm[utm_time], errors='coerce')
                df_utm[utm_stress] = pd.to_numeric(df_utm[utm_stress], errors='coerce')
                
                df_lcr = df_lcr.dropna().sort_values(by=lcr_time)
                df_utm = df_utm.dropna().sort_values(by=utm_time)

                # 보간 로직
                interp_func = interp1d(df_lcr[lcr_time], df_lcr[lcr_cp], kind='linear', fill_value="extrapolate")
                df_utm['Interpolated_Cp'] = interp_func(df_utm[utm_time])

                # 시각화
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_utm[utm_stress], y=df_utm['Interpolated_Cp'], mode='lines+markers'))
                fig.update_layout(title="Stress vs Capacitance", xaxis_title=utm_stress, yaxis_title="Interpolated Cp", template="plotly_white")
                
                st.plotly_chart(fig, use_container_width=True)
                
                csv = df_utm.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 결과 다운로드", csv, "combined_data.csv", "text/csv")

    except Exception as e:
        st.error(f"⚠️ 데이터 처리 중 오류 발생: {e}")
