#Intermittent Bleed Pneumatic Controller Simulator v1.0

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from io import BytesIO
import numpy as np
import os
from PIL import Image


def wrap_list(label, values, wrap=10):
    lines = [f"{label} ({len(values)} values):"]
    for i in range(0, len(values), wrap):
        chunk = values[i:i + wrap]
        lines.append(", ".join(f"{v:.4f}" for v in chunk))
    return lines


def add_branded_elements(fig, page_num):
    """Add top-centered logo and bottom footer to a figure."""
    fig_width, fig_height = fig.get_size_inches()
    dpi = fig.get_dpi()

    footer_text = "Intermittent Bleed Pneumatic Controller Simulator v1.0 | Energy Emissions Modeling and Data Lab"
    fig.text(0.5, 0.02, footer_text, ha='center', fontsize=8, color='gray')
    fig.text(0.98, 0.02, f"Page {page_num}", ha='right', fontsize=8, color='gray')

    logo_path = os.path.join(os.path.dirname(__file__), "eemdl_logo.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_width_inch = 1.5
            logo_width_px = int(logo_width_inch * dpi)
            scale = logo_width_px / logo.width
            logo_resized = logo.resize((logo_width_px, int(logo.height * scale)), Image.LANCZOS)
            logo_arr = np.array(logo_resized) / 255.0

            xo = int((fig_width * dpi - logo_arr.shape[1]) / 2)
            yo = int(fig_height * dpi - logo_arr.shape[0] - 15)

            fig.figimage(logo_arr, xo=xo, yo=yo, origin='upper', zorder=10)
        except Exception as e:
            print(f"Error rendering logo: {e}")


def generate_pdf_report(figs, summary_text, prop_rates, malf_rates):
    """Generates a multipage PDF report with branding and visual layout."""
    pdf_buffer = BytesIO()
    page_counter = 1

    with PdfPages(pdf_buffer) as pdf:
        # --- Render each figure ---
        for fig in figs:
            fig.subplots_adjust(top=0.88, bottom=0.1)
            add_branded_elements(fig, page_counter)
            pdf.savefig(fig)
            page_counter += 1

        # --- Page: Summary Text (A4) ---
        summary_fig = plt.figure(figsize=(8.27, 11.69))  # A4 size
        plt.axis('off')
        for i, line in enumerate(summary_text.strip().split('\n')):
            plt.text(0.05, 0.95 - i * 0.03, line, va='top', fontsize=10, family='monospace')
        add_branded_elements(summary_fig, page_counter)
        pdf.savefig(summary_fig)
        plt.close(summary_fig)
        page_counter += 1

        # --- Pages: Long Lists of Emission Rates (A4) ---
        for label, values in [("Properly Operating Rates", prop_rates),
                              ("Malfunctioning Rates", malf_rates)]:
            lines = wrap_list(label, values)
            lines_per_page = 80
            for i in range(0, len(lines), lines_per_page):
                chunk = lines[i:i + lines_per_page]
                list_fig = plt.figure(figsize=(8.27, 11.69))  # A4 size
                plt.axis('off')
                for j, line in enumerate(chunk):
                    plt.text(0.05, 0.95 - j * 0.025, line, va='top', fontsize=9, family='monospace')
                add_branded_elements(list_fig, page_counter)
                pdf.savefig(list_fig)
                plt.close(list_fig)
                page_counter += 1

    pdf_buffer.seek(0)
    return pdf_buffer
