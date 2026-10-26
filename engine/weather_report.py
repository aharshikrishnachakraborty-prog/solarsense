"""Draw the weather charts: sunniest vs cloudiest day (W1) and panel temperature vs efficiency (W2).

Every number on the charts comes from the weather tables and the "weather" / "temperature" metrics.
"""

import textwrap

import matplotlib

matplotlib.use("Agg")   # draw charts straight to files (no window needed)
import matplotlib.dates  # noqa: E402
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import config  # noqa: E402

FIGURE_FILE = config.FIGURES_DIR / "weather_clear_vs_cloudy.png"
TEMPERATURE_FIGURE_FILE = config.FIGURES_DIR / "temperature_vs_efficiency.png"
SKY_COLOURS = {"Clear": "#F5B700", "Partly cloudy": "#9CC3E6", "Cloudy": "#7A8794", "Overcast": "#3E444C"}
BAND_BOTTOM = 0.92    # the coloured sky band fills the top 8% of each chart


def draw_day(ax, day_rows, title, sentence):
    """One panel: actual sunlight vs clear-sky curve, the gap shaded, sky label band on top."""
    rows = day_rows[day_rows["clear_sky_irr"] > 0].sort_values("timestamp")
    times = rows["timestamp"]
    ax.plot(times, rows["clear_sky_irr"], "--", color="#B07A00", lw=2, label="Clear-sky reference")
    ax.plot(times, rows["irradiation"], color="#1F4E79", lw=2, label="Actual sunlight")
    lost = rows["irradiation"] < rows["clear_sky_irr"]
    ax.fill_between(times, rows["irradiation"], rows["clear_sky_irr"], where=lost, color="#9AA5B1",
                    alpha=0.35, label="Sunlight blocked (clouds)")
    for row in rows.dropna(subset=["sky_label"]).itertuples():
        ax.axvspan(row.timestamp, row.timestamp + pd.Timedelta(minutes=15), ymin=BAND_BOTTOM, ymax=1.0,
                   color=SKY_COLOURS[row.sky_label], lw=0)
    day_start = rows["timestamp"].min().normalize()
    ax.set_xlim(day_start + pd.Timedelta(hours=5), day_start + pd.Timedelta(hours=20))   # same window on every panel
    ax.set_ylim(0, 1.3)
    ax.set_title(title + "\n" + textwrap.fill(sentence, 70), fontsize=9.5, loc="left")
    ax.set_ylabel("Sunlight (irradiation, kW/m²)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.set_xlabel("Time of day")
    ax.grid(alpha=0.3)


def plot_clear_vs_cloudy(table, metrics):
    """2×2 chart: for each plant, its sunniest and cloudiest day (days with good sensor coverage only)."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(config.PLANTS), 2, figsize=(14, 10), sharey=True)
    for row_index, plant in enumerate(config.PLANTS):
        info = metrics["by_plant"][f"plant_{plant}"]
        for col_index, kind in enumerate(["sunniest_day", "cloudiest_day"]):
            day = info[kind]
            day_rows = table[(table["plant"] == plant) & (table["date"].astype(str) == day["date"])]
            label = "Sunniest" if kind == "sunniest_day" else "Cloudiest"
            nice_date = pd.Timestamp(day["date"]).strftime("%d %b")
            title = (f"Plant {plant} — {label} day, {nice_date}: sunshine score {day['sunshine_score']:.0f}/100, "
                     f"average CSI {day['avg_csi']:.2f}")
            draw_day(axes[row_index][col_index], day_rows, title, day["summary"])
    lines, names = axes[0][0].get_legend_handles_labels()
    lines += [matplotlib.patches.Patch(color=colour, label=f"Sky: {name}") for name, colour in SKY_COLOURS.items()]
    fig.legend(lines, names + [f"Sky: {name}" for name in SKY_COLOURS], loc="lower center", ncol=7, fontsize=9)
    fig.suptitle("We read the sky from the sunlight: the grey gap between the clear-sky curve and actual sunlight "
                 f"is what clouds blocked\n(clear-sky curve = {config.CLEAR_SKY_PERCENTILE}th percentile of all "
                 "days at each time — learned from the data, ASSUMPTION)", fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(FIGURE_FILE, dpi=110)
    plt.close(fig)
    return FIGURE_FILE


def plot_temperature_vs_efficiency(fit_rows, temperature):
    """One panel per plant: healthy readings, average per 2 °C, and the fitted straight line."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(config.PLANTS), figsize=(14, 5.5), sharey=True)
    for ax, plant in zip(axes, config.PLANTS):
        rows = fit_rows[fit_rows["plant"] == plant]
        info = temperature["by_plant"][f"plant_{plant}"]
        sample = rows.sample(min(len(rows), config.SCATTER_SAMPLE_POINTS), random_state=config.RANDOM_SEED)
        ax.scatter(sample["module_temp"], 100 * sample["efficiency_norm"], s=4, alpha=0.15, color="#1F4E79",
                   label=f"Healthy readings ({len(sample):,} of {len(rows):,} shown)")
        ax.plot([b["temp_c"] for b in info["binned"]], [b["efficiency_pct"] for b in info["binned"]], "o",
                color="#B07A00", label=f"Average per {config.TEMP_CHART_BIN_C} °C")
        line = info["fit_line"]
        temps = np.array([line["temp_min_c"], line["temp_max_c"]])
        ax.plot(temps, line["efficiency_at_25c_pct"] + line["slope_pct_points_per_c"]
                * (temps - config.REFERENCE_PANEL_TEMP_C), color="#C0392B", lw=2.5,
                label=f"Fitted line: {info['coefficient_pct_per_c']} %/°C")
        low, high = info["ci95_pct_per_c"]
        ax.set_title(f"Plant {plant}: every +1 °C costs ~{abs(info['coefficient_pct_per_c']):.2f}% power\n"
                     f"(95% range {low} to {high} %/°C; typical silicon "
                     f"{config.TYPICAL_TEMP_COEF_RANGE[0]} to {config.TYPICAL_TEMP_COEF_RANGE[1]})", fontsize=10.5, loc="left")
        ax.set_xlabel("Panel (module) temperature, °C")
        ax.set_ylim(70, 125)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8.5, loc="lower left")
    axes[0].set_ylabel("Efficiency (AC power ÷ sunlight), % of the inverter's usual")
    fig.suptitle("Hotter panels make less power per unit of sunlight (healthy readings, sunlight ≥ "
                 f"{config.TEMP_FIT_MIN_IRRADIATION} kW/m²)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(TEMPERATURE_FIGURE_FILE, dpi=110)
    plt.close(fig)
    return TEMPERATURE_FIGURE_FILE

