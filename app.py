import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

st.set_page_config(layout="wide")
st.title("10-Cycle Hysteresis Analyzer (ΔC/C)")

# -----------------------------
# File Upload
# -----------------------------
utm_file = st.file_uploader("Upload UTM File (csv or xlsx)", type=["csv","xlsx"])
lcr_file = st.file_uploader("Upload LCR File (csv or xlsx)", type=["csv","xlsx"])

diameter = st.number_input("Sample Diameter (mm)", value=20.0)
baseline_kpa = st.number_input("Baseline Stress Shift (kPa)", value=1.0)

# -----------------------------
# Safe Load Function
# -----------------------------
def load_file(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        try:
            df = pd.read_csv(file)
        except:
            df = pd.read_csv(file, encoding="cp949", engine="python")
    else:
        df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# -----------------------------
# Main
# -----------------------------
if utm_file and lcr_file:

    utm = load_file(utm_file)
    lcr = load_file(lcr_file)

    # -------------------------
    # Auto Column Detection
    # -------------------------
    try:
        utm_time_col = next(c for c in utm.columns if "time" in c.lower())
        utm_load_col = next(c for c in utm.columns if "load" in c.lower())
        lcr_time_col = next(c for c in lcr.columns if "time" in c.lower())
        lcr_cap_col  = next(c for c in lcr.columns if "cap" in c.lower())
    except:
        st.error("Column detection failed. Please ensure column names contain 'Time', 'Load', 'Cap'.")
        st.stop()

    utm = utm[[utm_time_col, utm_load_col]].dropna()
    lcr = lcr[[lcr_time_col, lcr_cap_col]].dropna()

    utm.columns = ["Time","Load"]
    lcr.columns = ["Time","Cap"]

    utm = utm.sort_values("Time")
    lcr = lcr.sort_values("Time")

    # -------------------------
    # Stress Conversion (Circular sample)
    # -------------------------
    r = (diameter/2) * 1e-3
    A = np.pi * r**2

    utm["Force_N"] = utm["Load"] * 9.80665
    utm["Stress_kPa"] = (utm["Force_N"]/A)/1000
    utm["Stress_kPa"] = utm["Stress_kPa"] - baseline_kpa

    # -------------------------
    # Align LCR to UTM time
    # -------------------------
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

    if len(df) < 100:
        st.error("Data overlap too small. Check time alignment.")
        st.stop()

    # -------------------------
    # Cycle Detection (11 cycles expected)
    # -------------------------
    stress = df["Stress_kPa"].values

    peaks, _ = find_peaks(stress, height=0.5*np.max(stress), distance=len(stress)/15)

    if len(peaks) < 11:
        st.warning(f"Detected {len(peaks)} peaks. Expected 11.")
    if len(peaks) < 2:
        st.error("Cycle detection failed.")
        st.stop()

    valleys = []
    valleys.append(np.argmin(stress[:peaks[0]+1]))

    for i in range(len(peaks)-1):
        a,b = peaks[i], peaks[i+1]
        valleys.append(np.argmin(stress[a:b+1]) + a)

    valleys.append(np.argmin(stress[peaks[-1]:]) + peaks[-1])
    valleys = np.array(valleys)

    # -------------------------
    # Plot Hysteresis (Cycle 2~11)
    # -------------------------
    fig, ax = plt.subplots()

    hysteresis_vals = []

    for i in range(1, min(11, len(valleys)-1)):

        a,b = valleys[i], valleys[i+1]
        seg = df.iloc[a:b+1]

        C0 = seg["Cap"].iloc[0]
        deltaC = (seg["Cap"] - C0) / C0

        ax.plot(seg["Stress_kPa"], deltaC)

        # hysteresis calculation
        s = seg["Stress_kPa"].values
        c = deltaC.values

        p = np.argmax(s)

        s_load, c_load = s[:p+1], c[:p+1]
        s_un, c_un = s[p:], c[p:]

        s_min = max(min(s_load), min(s_un))
        s_max = min(max(s_load), max(s_un))

        if s_max <= s_min:
            continue

        grid = np.linspace(s_min, s_max, 200)

        cL = np.interp(grid, np.sort(s_load), c_load[np.argsort(s_load)])
        cU = np.interp(grid, np.sort(s_un), c_un[np.argsort(s_un)])

        H = np.max(np.abs(cL - cU)) * 100
        hysteresis_vals.append(H)

    ax.set_xlabel("Stress (kPa)")
    ax.set_ylabel("ΔC / C0")
    ax.set_title("Hysteresis Loop (Cycle 2~11)")
    st.pyplot(fig)

    # -------------------------
    # Results
    # -------------------------
    if hysteresis_vals:
        st.subheader("Hysteresis Results (Cycle 2~11)")
        st.write(f"Mean: {np.mean(hysteresis_vals):.3f} %")
        st.write(f"Std: {np.std(hysteresis_vals):.3f} %")
        st.line_chart(hysteresis_vals)
    else:
        st.warning("Hysteresis calculation skipped.")
