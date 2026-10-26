"""Where did the energy go? Split each day's energy into a waterfall that adds up exactly (Phase W3).

Run from the solarsense folder with:   python -m engine.energy_breakdown
Reads weather_15min.parquet (W1+W2) and daily_plant.parquet (Phase 6), writes energy_breakdown.parquet
and saves totals under "breakdown" in reports/metrics.json.

The waterfall, in the order things happen to the sunlight:
  Clear-sky potential   what the plant would make under a clear sky with panels at 25 °C
  − Cloud loss          sunlight blocked by clouds × the plant's power per unit of sunlight at 25 °C   (NATURAL)
  − Heat loss           panels hotter than 25 °C make less power (Phase W2)                           (NATURAL)
  − Fault loss          confirmed losses from our alerts (trips, underperformance, ...)               (FIXABLE)
  − Not measured        expected energy while an inverter sent no readings — fault or fine, unknown   (UNKNOWN)
  − Other               what is left: normal model error, small issues below our alert thresholds (can be ±)
  = Actual energy
Order of subtraction: first the sky (how much sun arrived), then heat (what the panels made of that sun), then
faults (what the equipment failed to deliver). Each step starts from what the previous one left, so nothing is
counted twice. "Other" is defined as the remainder, which is why the parts always add up to the actual energy.
"""

import pandas as pd

from engine import config
from engine.metrics import load_metrics, save_metrics_section
from engine.weather_text import indian

PART_NAMES = {"cloud_loss_kwh": "clouds", "heat_loss_kwh": "heat", "fault_loss_kwh": "faults",
              "not_measured_kwh": "not measured", "other_kwh": "other"}


def load_inputs():
    """The 15-minute weather/heat table and the daily plant energy table."""
    for path in [config.WEATHER_15MIN_FILE, config.DAILY_PLANT_FILE]:
        if not path.exists():
            raise FileNotFoundError(f"{path.name} not found — run the earlier pipeline steps first "
                                    "(python -m engine.weather, then python -m engine.losses).")
    return pd.read_parquet(config.WEATHER_15MIN_FILE), pd.read_parquet(config.DAILY_PLANT_FILE)


def power_per_sunlight_at_25c(weather):
    """kW a plant makes per 1 kW/m² of sunlight with panels at 25 °C (ratio of sums on sunny readings)."""
    sunny = weather[weather["irradiation"] >= config.BREAKDOWN_FIT_MIN_IRRADIATION]
    sums = sunny.groupby("plant")[["power_at_25c_kw", "irradiation"]].sum()
    return (sums["power_at_25c_kw"] / sums["irradiation"]).to_dict()


def cloud_loss_per_reading(weather, k25_by_plant):
    """Power the blocked sunlight would have made: (clear-sky − actual sunlight) × power per unit sunlight.

    Negative for a few readings where sunlight was ABOVE the clear-sky curve (bright cloud edges) — kept,
    so the sums stay honest. Readings without a weather measurement get 0 (we cannot see the sky then).
    """
    blocked = (weather["clear_sky_irr"] - weather["irradiation"]).fillna(0)
    return blocked * weather["plant"].map(k25_by_plant)


def build_breakdown(weather, daily_plant, k25_by_plant):
    """One waterfall per plant and day; every part in kWh."""
    weather = weather.assign(cloud_loss_kw=cloud_loss_per_reading(weather, k25_by_plant),
                             date=weather["date"].astype(str))
    # Per day, from the 15-minute table (kW × 0.25 h = kWh).
    sums = weather.groupby(["plant", "date"])[
        ["power_at_25c_kw", "cloud_loss_kw", "heat_loss_kw", "plant_expected_kw"]].sum() * config.INTERVAL_HOURS
    sums.columns = ["at_25c_actual_sun_kwh", "cloud_loss_kwh", "heat_loss_kwh", "expected_all_kwh"]
    days = sums.reset_index().merge(
        daily_plant[["plant", "date", "actual_kwh", "expected_kwh", "fault_loss_kwh"]], on=["plant", "date"])
    days["clear_sky_potential_kwh"] = days["at_25c_actual_sun_kwh"] + days["cloud_loss_kwh"]
    # daily_plant's expected_kwh only counts readings we have; the rest is energy we could not measure.
    days["not_measured_kwh"] = days["expected_all_kwh"] - days["expected_kwh"]
    days["other_kwh"] = days["expected_kwh"] - days["fault_loss_kwh"] - days["actual_kwh"]
    days["natural_loss_kwh"] = days["cloud_loss_kwh"] + days["heat_loss_kwh"]
    days["fixable_loss_kwh"] = days["fault_loss_kwh"]
    days["fault_loss_inr"] = days["fault_loss_kwh"] * config.TARIFF_INR_PER_KWH
    days["natural_loss_inr"] = days["natural_loss_kwh"] * config.TARIFF_INR_PER_KWH
    for part in PART_NAMES:
        days[part.replace("_kwh", "_pct")] = 100 * days[part] / days["clear_sky_potential_kwh"]
    days["actual_pct"] = 100 * days["actual_kwh"] / days["clear_sky_potential_kwh"]
    days["summary"] = [describe_waterfall(row) for row in days.itertuples()]
    columns = ["plant", "date", "clear_sky_potential_kwh", *PART_NAMES, "actual_kwh", "natural_loss_kwh",
               "fixable_loss_kwh", "fault_loss_inr", "natural_loss_inr",
               *[p.replace("_kwh", "_pct") for p in PART_NAMES], "actual_pct", "summary"]
    return days[columns].round(2)


def describe_waterfall(day):
    """Plain-English sentence, e.g. '17 Jun: clouds cost 2,100 kWh, heat 900 kWh, faults 300 kWh (fixable).'"""
    pretty = pd.Timestamp(day.date).strftime("%d %b")
    return (f"{pretty}: clouds cost {indian(day.cloud_loss_kwh)} kWh and heat {indian(day.heat_loss_kwh)} kWh "
            f"(natural, nobody can fix them); faults cost {indian(day.fault_loss_kwh)} kWh (fixable).")


def totals(days):
    """Whole-period waterfall for a set of days (all parts summed, plus % of the clear-sky potential)."""
    parts = ["clear_sky_potential_kwh", *PART_NAMES, "actual_kwh", "natural_loss_kwh", "fixable_loss_kwh",
             "fault_loss_inr", "natural_loss_inr"]
    result = {part: round(float(days[part].sum()), 1) for part in parts}
    potential = result["clear_sky_potential_kwh"]
    result["pct_of_potential"] = {PART_NAMES.get(part, "actual"): round(100 * result[part] / potential, 2)
                                  for part in [*PART_NAMES, "actual_kwh"]}
    return result


def build_metrics(days, k25_by_plant, inverters_by_plant):
    """The "breakdown" section of metrics.json: method, per-plant totals and example days."""
    physics = load_metrics().get("expected_model", {})
    result = {"order": ["clear_sky_potential", *[PART_NAMES[p] for p in PART_NAMES], "actual"],
              "kind": {PART_NAMES[p]: kind for p, kind in config.BREAKDOWN_PARTS.items()},
              "method": ("Clear-sky potential = power at 25 °C with the actual sunlight (Phase W2) + cloud loss. "
                         "Cloud loss = (clear-sky sunlight − actual sunlight) × the plant's power per unit of "
                         "sunlight at 25 °C. Other = the remainder, so the parts always add up to actual energy."),
              "tariff_inr_per_kwh": config.TARIFF_INR_PER_KWH, "by_plant": {}}
    for plant, plant_days in days.groupby("plant"):
        # Cross-check: the Phase 3 physics model's kW per unit sunlight (one inverter, 25 °C) × number of inverters.
        k_physics = physics.get(f"plant_{plant}", {}).get("physics_coefficients", {}).get("k_kw_per_irradiation")
        n_inverters = inverters_by_plant[plant]
        cloudiest = plant_days.loc[plant_days["cloud_loss_kwh"].idxmax()]
        faultiest = plant_days.loc[plant_days["fault_loss_kwh"].idxmax()]
        result["by_plant"][f"plant_{plant}"] = {
            **totals(plant_days),
            "power_per_sunlight_at_25c_kw": round(float(k25_by_plant[plant]), 1),
            "physics_model_cross_check_kw": round(k_physics * n_inverters, 1) if k_physics else None,
            "biggest_cloud_loss_day": {"date": cloudiest["date"], "cloud_loss_kwh": cloudiest["cloud_loss_kwh"],
                                       "summary": cloudiest["summary"]},
            "biggest_fault_loss_day": {"date": faultiest["date"], "fault_loss_kwh": faultiest["fault_loss_kwh"],
                                       "summary": faultiest["summary"]}}
    result["total"] = totals(days)
    return result


def compute_breakdown():
    """Run the whole waterfall step and save every output."""
    weather, daily_plant = load_inputs()
    k25_by_plant = power_per_sunlight_at_25c(weather)
    days = build_breakdown(weather, daily_plant, k25_by_plant)
    days.to_parquet(config.ENERGY_BREAKDOWN_FILE, index=False)
    inverters = pd.read_parquet(config.DAILY_INVERTER_FILE, columns=["plant", "inverter"])
    metrics = build_metrics(days, k25_by_plant, inverters.groupby("plant")["inverter"].nunique().to_dict())
    save_metrics_section("breakdown", metrics)
    return metrics


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows terminals and the "−" sign
    result = compute_breakdown()
    for plant, info in {**result["by_plant"], "both plants": result["total"]}.items():
        print(f"\n{plant}: clear-sky potential {info['clear_sky_potential_kwh']:,.0f} kWh")
        for part in [*PART_NAMES, "actual_kwh"]:
            name = PART_NAMES.get(part, "actual")
            print(f"  {'=' if name == 'actual' else '−'} {name:13s} {info[part]:>13,.0f} kWh  "
                  f"({info['pct_of_potential'][name]}% of potential)")
        if "power_per_sunlight_at_25c_kw" in info:
            print(f"  power per unit sunlight at 25 °C: {info['power_per_sunlight_at_25c_kw']:,} kW "
                  f"(physics model cross-check {info['physics_model_cross_check_kw']})")
            print(f"  biggest cloud day: {info['biggest_cloud_loss_day']['summary']}")
            print(f"  biggest fault day: {info['biggest_fault_loss_day']['summary']}")
