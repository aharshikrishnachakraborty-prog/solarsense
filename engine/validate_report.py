"""Chart for Phase 7: one injected fault being caught by the detector."""

import matplotlib

matplotlib.use("Agg")   # draw charts straight to files (no window needed)
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from engine import config  # noqa: E402

CHART_FILE = "validation_injected_fault_caught.png"


def make_example_chart(example, original_test):
    """Plot original vs injected output, expected output, the injected window and the alert window."""
    if example is None:
        return None
    record, injected, events = example["record"], example["injected"], example["events"]
    date = str(record["start"].date())

    def one_day(table):
        """This inverter's rows on the example day, in time order."""
        rows = table[(table["plant"] == record["plant"]) & (table["inverter"] == record["inverter"])
                     & (table["date"] == date)]
        return rows.sort_values("timestamp")

    before, after = one_day(original_test), one_day(injected)
    alert = events[(events["plant"] == record["plant"]) & (events["inverter"] == record["inverter"])
                   & (events["fault_type"] == "UNDERPERFORMANCE") & (events["start"] < record["end"])
                   & (events["end"] > record["start"])].iloc[0]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.axvspan(record["start"], record["end"], color="#ef4444", alpha=0.12, label="Fault we injected")
    ax.axvspan(alert["start"], alert["end"], ymin=0, ymax=0.06, color="#ef4444", alpha=0.9,
               label="Alert raised by detector")
    ax.plot(before["timestamp"], before["ac_kw"], color="#9ca3af", linewidth=1.5, label="Original (healthy) output")
    ax.plot(after["timestamp"], after["ac_kw"], color="#1f77b4", linewidth=2, label="Output after injection")
    ax.plot(after["timestamp"], after["expected_kw"], color="#f59e0b", linewidth=2, linestyle="--",
            label="Expected (model)")
    kept = round(100 * record["size"])
    ax.set_title(f"Injected fault caught: output cut to {kept}% for "
                 f"{(record['end'] - record['start']).total_seconds() / 3600:g} h "
                 f"(Plant {record['plant']}, {date})")
    ax.set_xlabel("Time of day")
    ax.set_ylabel("Inverter AC power (kW)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / CHART_FILE, dpi=120)
    plt.close(fig)
    return {"file": f"reports/figures/{CHART_FILE}", "plant": int(record["plant"]),
            "inverter": record["inverter"], "date": date, "output_kept_pct": kept,
            "true_kwh": record["true_kwh"], "estimated_kwh": round(float(record["estimated_kwh"]), 1)}
