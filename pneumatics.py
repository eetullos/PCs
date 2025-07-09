import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
import matplotlib.pyplot as plt
from PC_Emissions_Sim import simulate_emissions_optimized as simulate_emissions
from generate_pdf_report import generate_pdf_report

from io import BytesIO

from PIL import Image
import base64

# Encode logo as base64 to embed in HTML
with open("eemdl_logo.png", "rb") as image_file:
    encoded_logo = base64.b64encode(image_file.read()).decode()

st.markdown(f"""
    <div style='display: flex; align-items: center;'>
        <img src='data:image/png;base64,{encoded_logo}' style='height: 50px; margin-right: 15px;'>
        <h3 style='margin: 0;'>Intermittent Bleed Pneumatic Controller Simulator v1.0</h3>
    </div>
""", unsafe_allow_html=True)
st.markdown("<hr style='margin-top:0'>", unsafe_allow_html=True)

# --- Sidebar: Input Format Selection ---
st.sidebar.title("Simulation Input Options")

# --- Sidebar Simulation Settings ---
PC_count = st.sidebar.number_input("Number of Pneumatics [1-1,000]", min_value=1, max_value=1000, value=100)
S0_mean = st.sidebar.slider("Initial Properly Operating Population [0-100%]", 0, 100, 82, 1)/100
S0_variation = st.sidebar.slider("Variation in Initial Properly Operating Population [±0-100%]", 0, 100, 10, 1)/100
DTF_min = st.sidebar.number_input("Minimum Number Days to Failure", min_value=1, max_value=90, value=7)
DTF_max = st.sidebar.number_input("Maximum Number Days to Failure", min_value=91, max_value=365, value=180)

today = datetime.today().strftime("%Y-%m-%d")
rounded_S0_mean = int(round(S0_mean * 100))
default_filename = f"PC_Sim_Report_{today}_{PC_count}PCs_{rounded_S0_mean}percent.pdf"
output_filename = st.sidebar.text_input("Output PDF Filename", value=default_filename)

# --- Simulation Parameters ---
timesteps = 365
p_gas = 0.0000192
MC_runs = 100

S0_min = max(0.0, S0_mean - S0_variation)
S0_max = min(1.0, S0_mean + S0_variation)

file_format = st.sidebar.radio("Choose Input Format:", options=["Separate CSV Files", "JSON File"])

# --- Show Download and Upload Widgets Based on Format ---
prop_file = malf_file = json_file = None

if file_format == "Separate CSV Files":
    st.sidebar.markdown("### 📅 Download Default CSV Files")
    st.sidebar.download_button("Download Prop Rates CSV", open("final_prop_rates.csv", "rb"), file_name="final_prop_rates.csv")
    st.sidebar.download_button("Download Malf Rates CSV", open("final_malf_rates.csv", "rb"), file_name="final_malf_rates.csv")
    st.sidebar.markdown("### 📤 Upload Your Own CSVs")
    prop_file = st.sidebar.file_uploader("Upload Prop Rates CSV", type="csv")
    malf_file = st.sidebar.file_uploader("Upload Malf Rates CSV", type="csv")

elif file_format == "JSON File":
    st.sidebar.markdown("### 📅 Download Default JSON File")
    st.sidebar.download_button("Download JSON File", open("final_rates.json", "rb"), file_name="final_rates.json")
    st.sidebar.markdown("### 📤 Upload Your Own JSON")
    json_file = st.sidebar.file_uploader("Upload JSON File", type="json")

# --- Load and Validate Data ---
prop_rates = malf_rates = None

try:
    if file_format == "Separate CSV Files":
        prop_df = pd.read_csv(prop_file) if prop_file else pd.read_csv("final_prop_rates.csv")
        malf_df = pd.read_csv(malf_file) if malf_file else pd.read_csv("final_malf_rates.csv")
        prop_rates = prop_df.iloc[:, 0].dropna().to_numpy()
        malf_rates = malf_df.iloc[:, 0].dropna().to_numpy()
    elif file_format == "JSON File":
        if json_file:
            rates_data = json.load(json_file)
        else:
            with open("final_rates.json", "r") as f:
                rates_data = json.load(f)
        prop_rates = np.array(rates_data.get("prop_rates", []))
        malf_rates = np.array(rates_data.get("malf_rates", []))
except Exception as e:
    st.error(f"Error loading input files: {e}")
    st.stop()

if len(prop_rates) == 0 or len(malf_rates) == 0:
    missing = []
    if len(prop_rates) == 0: missing.append("Properly Operating Rates")
    if len(malf_rates) == 0: missing.append("Malfunctioning Rates")
    st.error(f"Missing or empty input data: {', '.join(missing)}. Please upload valid file(s).")
    st.stop()

# --- Run Simulation ---
if st.button("Run Simulation"):
    DTF_list, S0_list, MC_all_avg_emission_rate, MC_final_cumulative_emission = [], [], [], []

    for _ in range(MC_runs):
        DTF = np.random.randint(DTF_min, DTF_max + 1)
        DTF = max(1, DTF)
        S0 = np.random.uniform(S0_min, S0_max)
        S1 = 1 - S0
        p = S0 / DTF
        r = (p / S1) - p

        DTF_list.append(DTF)
        S0_list.append(S0)

        (emission_rates_each, avg_emission_rate, all_avg_emission_rate, sum_emission_rate, cumulative_emission,
         final_cumulative_emission, state_history, state_history_each) = simulate_emissions(
            PC_count, DTF, S0, timesteps, p_gas, S1, p, r, prop_rates, malf_rates)

        MC_all_avg_emission_rate.append(all_avg_emission_rate)
        MC_final_cumulative_emission.append(final_cumulative_emission)

    # --- Create and Display Split Figures ---
    height_ratio_factor = max(6, PC_count / 100)

    # Page 1: Subplots 0–1
    fig1, axs1 = plt.subplots(2, 1, figsize=(8.27, 11.69), height_ratios=[2, height_ratio_factor])
    axs1[0].plot(range(timesteps), state_history[:, 0], label="Properly Operating", linewidth=2)
    axs1[0].plot(range(timesteps), state_history[:, 1], label="Malfunctioning", linewidth=2)
    axs1[0].axhline(y=r / (p + r), color='blue', linestyle='--', label="Steady State Properly Operating")
    axs1[0].axhline(y=p / (p + r), color='orange', linestyle=':', label="Steady State Malfunctioning")
    axs1[0].set_title("Population Proportions Over Time")
    axs1[0].legend()
    axs1[0].grid(True)

    for i in range(min(100, PC_count)):
        axs1[1].plot(range(timesteps), state_history_each[:, i] + i * 1.5, 'k-', alpha=0.7)
    axs1[1].set_title("Individual PC States Over Time")
    axs1[1].grid(True)

    # Page 2: Subplots 2–4
    fig2, axs2 = plt.subplots(3, 1, figsize=(8.27, 11.69), height_ratios=[4, 2, 2])
    fig2.subplots_adjust(hspace=0.4)
    for i in range(PC_count):
        axs2[0].plot(range(timesteps), emission_rates_each[:, i], 'k-', alpha=0.2)
    axs2[0].plot(range(timesteps), avg_emission_rate, 'r-', linewidth=2, label="Avg Emission")
    axs2[0].set_title("Emission Rates Over Time")
    axs2[0].legend()
    axs2[0].grid(True)

    axs2[1].plot(range(timesteps), sum_emission_rate, 'k-', linewidth=2)
    axs2[1].set_title("Total & Cumulative Emissions")
    ax_secondary = axs2[1].twinx()
    ax_secondary.plot(range(timesteps), cumulative_emission, 'b--', linewidth=2)
    ax_secondary.set_ylabel("Cumulative Emissions (metric tpy)", color='b')
    ax_secondary.tick_params(axis='y', labelcolor='b')

    ax4 = axs2[2]
    bp1 = ax4.boxplot([MC_final_cumulative_emission], vert=True, patch_artist=True, positions=[1])
    for patch in bp1['boxes']: patch.set_facecolor("#1f77b4")
    ax4.set_ylabel("Annual Emissions (metric tons)", color="#1f77b4")
    ax_dtf = ax4.twinx()
    bp2 = ax_dtf.boxplot([DTF_list], vert=True, patch_artist=True, positions=[2])
    for patch in bp2['boxes']: patch.set_facecolor("#ff7f0e")
    ax_dtf.set_ylabel("Days to Failure (DTF)", color="#ff7f0e")

    # Page 3: Subplots 5–8
    fig3, axs3 = plt.subplots(4, 1, figsize=(8.27, 11.69), height_ratios=[3, 3, 3, 3])
    fig3.subplots_adjust(hspace=0.4)

    axs3[0].scatter(DTF_list, MC_final_cumulative_emission, alpha=0.6, color='blue', edgecolor='black')
    axs3[0].set_title("DTF vs Cumulative Emissions")
    axs3[0].grid(True)

    axs3[1].scatter(S0_list, MC_final_cumulative_emission, alpha=0.6, color='orange', edgecolor='black')
    axs3[1].set_title("Properly Operating Portion vs Cumulative Emissions")
    axs3[1].grid(True)

    axs3[2].hist(prop_rates, bins=20, color='blue', alpha=0.7)
    axs3[2].set_title("Histogram of Properly Operating Rates")
    axs3[2].set_xlabel("Whole Gas Emission Rate (SCFH)")
    axs3[2].set_ylabel("Frequency")
    axs3[2].grid(True)

    axs3[3].hist(malf_rates, bins=20, color='orange', alpha=0.7)
    axs3[3].set_title("Histogram of Malfunctioning Rates")
    axs3[3].set_xlabel("Whole Gas Emission Rate (SCFH)")
    axs3[3].set_ylabel("Frequency")
    axs3[3].grid(True)

    st.pyplot(fig1)
    st.pyplot(fig2)
    st.pyplot(fig3)

    mean_avg_emission = np.mean(MC_all_avg_emission_rate)
    std_avg_emission = np.std(MC_all_avg_emission_rate)
    mean_cum_emission = np.mean(MC_final_cumulative_emission)
    std_cum_emission = np.std(MC_final_cumulative_emission)
    mean_S0 = np.mean(S0_list)
    std_S0 = np.std(S0_list)

    summary_text = f"""Simulation Summary\n----------------------------\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nInputs\nPneumatics: {PC_count}\nAvg. Properly Operating Portion: {S0_mean*100:.0f}% ± {S0_variation*100:.0f}%\nMonte Carlo Runs: {MC_runs}\nRange of Potential Days to Failure: {DTF_min} to {DTF_max} days\n\nResults\nAvg. Emission Rate Per Controller: {mean_avg_emission:.1f} ± {std_avg_emission:.1f} scfh\nAvg. Emissions Per Controller: {mean_cum_emission / PC_count:.2f} ± {std_cum_emission / PC_count:.2f} metric tons per year\nPopulation Emissions: {mean_cum_emission:.1f} ± {std_cum_emission:.1f} metric tons per year\nAvg. Days to Failure: {np.mean(DTF_list):.0f}\nStd Dev Days to Failure: {np.std(DTF_list):.0f}\nAvg Properly Operating Portion: {mean_S0*100:.0f}%\nStd Dev Properly Operating Portion: {std_S0*100:.0f}%"""

    st.text(summary_text)

    pdf_buffer = generate_pdf_report(
        figs=[fig1, fig2, fig3],
        summary_text=summary_text,
        prop_rates=prop_rates,
        malf_rates=malf_rates
    )

    st.download_button("Download PDF Report", data=pdf_buffer, file_name=output_filename, mime="application/pdf")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:gray;'>Intermittent Bleed Pneumatic Controller Simulator v1.0 | LICENSE PLACEHOLDER</div>", unsafe_allow_html=True)
