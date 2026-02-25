import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="LCR-UTM Pro Analyzer", layout="wide")
st.title("🧪 LCR-UTM 통합 분석기 (Pa 단위 & Excel 저장)")

def load_csv_safe(file, skip=0):
    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
    for enc in encodings:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc, skiprows=skip)
            # 숫자형 변환 및 유효하지 않은 데이터 정리
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
    # 파일 로드 (LCR은 3줄 스킵, UTM은 1줄 스킵)
    df_lcr = load_csv_safe(lcr_file, skip=3)
    df_utm = load_csv_safe(utm_file, skip=1)

    if df_lcr is not None and df_utm is not None:
        st.divider()
        
        # --- 시편 정보 및 컬럼 매핑 ---
        st.subheader("📏 시편 정보 및 설정")
        c_area, c_map1, c_map2 = st.columns([1, 1, 1])
        
        with c_area:
            area_mm2 = st.number_input("시편 단면적 (mm²)", min_value=0.0001, value=10.0, step=0.1)
        
        with c_map1:
            lcr_time = st.selectbox("LCR 시간 [s]", df_lcr.columns, index=0)
            lcr_cp = st.selectbox("LCR Cp [F]", df_lcr.columns, index=4)
        
        with c_map2:
            utm_time = st.selectbox("UTM 시간 [sec]", df_utm.columns, index=1)
            utm_load = st.selectbox("UTM 하중 [kgf]", df_utm.columns, index=2)

        if st.button("🚀 데이터 분석 및 Excel 생성"):
            # 1. 압력 변환 (kgf -> Pa)
            # Pressure (Pa) = (Force[kgf] * 9.80665) / (Area[mm^2] * 10^-6)
            df_utm['Pressure_Pa'] = (df_utm[utm_load] * 9.80665) / (area_mm2 * 1e-6)

            # 2. 정렬 및 클리닝
            df_lcr = df_lcr.dropna(subset=[lcr_time, lcr_cp]).sort_values(by=lcr_time)
            df_utm = df_utm.dropna(subset=[utm_time, 'Pressure_Pa']).sort_values(by=utm_time)

            # 3. 보간 (Interpolation)
            interp_func = interp1d(df_lcr[lcr_time], df_lcr[lcr_cp], kind='linear', fill_value="extrapolate")
            df_utm['Interpolated_Cp'] = interp_func(df_utm[utm_time])

            # 4. 시각화 (X축: Stress/Pressure, Y축: Cp)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_utm['Pressure_Pa'], 
                y=df_utm['Interpolated_Cp'],
                mode='lines+markers',
                marker=dict(color='firebrick'),
                name='Pressure vs Cp'
            ))
            
            fig.update_layout(
                title=f"Stress (Pa) vs Capacitance (F) - Area: {area_mm2}mm²",
                xaxis_title="Stress (Pressure) [Pa]",
                yaxis_title="Capacitance [F]",
                template="plotly_white",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # 5. Excel 파일 다운로드 생성
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # 결과 데이터 시트
                df_result = df_utm[[utm_time, utm_load, 'Pressure_Pa', 'Interpolated_Cp']]
                df_result.columns = ['Time [s]', 'Load [kgf]', 'Stress [Pa]', 'Capacitance [F]']
                df_result.to_excel(writer, index=False, sheet_name='Analysis_Result')
            
            processed_data = output.getvalue()
            
            st.success("✅ 분석 완료! 아래 버튼을 눌러 결과 파일을 다운로드하세요.")
            st.download_button(
                label="📥 결과 데이터 다운로드 (Excel)",
                data=processed_data,
                file_name="LCR_UTM_Result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
