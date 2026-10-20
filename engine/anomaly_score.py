"""Optional extra AI check: an "unusual day" score per inverter per day (Phase 5).

Run from the solarsense folder with:   python -m engine.anomaly_score
Isolation Forest "finds the odd ones out" among inverter-days. It is ONLY an
extra hint for the dashboard — it never creates alerts by itself.
"""

import pandas as pd
from sklearn.ensemble import IsolationForest

from engine import config
from engine.assumptions import record_assumption
from engine.metrics import save_metrics_section

FEATURES = ["performance_ratio", "peer_ratio_mean", "peer_ratio_min", "residual_pct_mean",
            "residual_pct_min", "residual_pct_std", "missing_pct", "temp_delta_mean"]


def build_daily_features(table):
    """One row per inverter per day, summarising how that day went."""
    table = table.assign(temp_delta=table["module_temp"] - table["ambient_temp"])
    present = table[~table["is_missing"]]
    energy = present.groupby(["plant", "inverter", "date"])[["ac_kw", "expected_kw"]].sum()
    days = present.groupby(["plant", "inverter", "date"]).agg(
        peer_ratio_mean=("peer_ratio", "mean"), peer_ratio_min=("peer_ratio", "min"),
        residual_pct_mean=("residual_pct", "mean"), residual_pct_min=("residual_pct", "min"),
        residual_pct_std=("residual_pct", "std"))
    days["performance_ratio"] = energy["ac_kw"] / energy["expected_kw"]
    # Missing % and temperature use ALL daylight rows (including missing readings).
    all_rows = table.groupby(["plant", "inverter", "date"]).agg(
        missing_pct=("is_missing", "mean"), temp_delta_mean=("temp_delta", "mean"))
    all_rows["missing_pct"] *= 100
    days = all_rows.join(days, how="left").reset_index()
    # A day with no readings at all has no performance numbers: treat it as "completely missing".
    return days.fillna({"performance_ratio": 0, "peer_ratio_mean": 0, "peer_ratio_min": 0,
                        "residual_pct_mean": -100, "residual_pct_min": -100, "residual_pct_std": 0})


def score_days(days):
    """Fit one Isolation Forest per plant; lower score = more unusual."""
    scored = []
    for plant, plant_days in days.groupby("plant"):
        forest = IsolationForest(n_estimators=config.ANOMALY_N_ESTIMATORS,
                                 contamination=config.ANOMALY_CONTAMINATION,
                                 random_state=config.RANDOM_SEED)
        forest.fit(plant_days[FEATURES])
        plant_days = plant_days.copy()
        plant_days["anomaly_score"] = forest.score_samples(plant_days[FEATURES]).round(4)
        plant_days["is_unusual"] = forest.predict(plant_days[FEATURES]) == -1
        scored.append(plant_days)
    return pd.concat(scored, ignore_index=True)


def rule_alert_days(alerts):
    """Set of (plant, inverter, date) that already have a rule-based inverter alert."""
    inverter_alerts = alerts[alerts["inverter"] != "ALL"]   # sensor/overheating are plant-wide
    covered = set()
    for row in inverter_alerts.itertuples():
        for day in pd.date_range(row.start.normalize(), (row.end - pd.Timedelta(minutes=1)).normalize()):
            covered.add((row.plant, row.inverter, str(day.date())))
    return covered


def compare_with_rules(scored, alerts):
    """How much does the unusual-day flag overlap with our rule-based alerts?"""
    covered = rule_alert_days(alerts)
    scored["has_rule_alert"] = [(p, i, d) in covered for p, i, d in
                                zip(scored["plant"], scored["inverter"], scored["date"])]
    unusual = scored["is_unusual"]
    stats = {"inverter_days": int(len(scored)), "unusual_days": int(unusual.sum()),
             "unusual_with_rule_alert": int((unusual & scored["has_rule_alert"]).sum()),
             "unusual_without_rule_alert": int((unusual & ~scored["has_rule_alert"]).sum()),
             "rule_alert_days": int(scored["has_rule_alert"].sum()),
             "rule_alert_days_not_unusual": int((~unusual & scored["has_rule_alert"]).sum()),
             "contamination": config.ANOMALY_CONTAMINATION, "by_plant": {}}
    stats["overlap_pct"] = round(100 * stats["unusual_with_rule_alert"] / max(stats["unusual_days"], 1), 1)
    # Inverters that are repeatedly "unusual" without any rule alert = a quiet watch list.
    new_days = scored[unusual & ~scored["has_rule_alert"]]
    repeat = new_days.groupby(["plant", "inverter"]).size().sort_values(ascending=False).head(3)
    stats["repeat_unusual_without_rule_alert"] = [
        {"plant": int(plant), "inverter": inverter, "unusual_days": int(count),
         "median_peer_ratio_all_days": round(float(scored.loc[(scored["plant"] == plant)
                                                              & (scored["inverter"] == inverter),
                                                              "peer_ratio_mean"].median()), 3)}
        for (plant, inverter), count in repeat.items()]
    for plant, group in scored.groupby("plant"):
        stats["by_plant"][f"plant_{plant}"] = {
            "unusual_days": int(group["is_unusual"].sum()),
            "unusual_without_rule_alert": int((group["is_unusual"] & ~group["has_rule_alert"]).sum())}
    return scored, stats


def run():
    """Build features, score every inverter-day, compare with rules, save results."""
    table = pd.read_parquet(config.EXPECTED_FILE)
    alerts = pd.read_parquet(config.ALERTS_FILE)
    scored, stats = compare_with_rules(score_days(build_daily_features(table)), alerts)
    scored.to_parquet(config.ANOMALY_DAYS_FILE, index=False)
    save_metrics_section("anomaly_score", stats)
    record_assumption(
        key="anomaly_contamination", title="Share of inverter-days Isolation Forest treats as unusual",
        value=100 * config.ANOMALY_CONTAMINATION, unit="%",
        why="Isolation Forest needs an expected share of odd days; we have no labels to measure it. "
            "Used only for the optional 'unusual day' hint, never for alerts.",
        source="Chosen by the team (engine/config.py)")
    return scored, stats


if __name__ == "__main__":
    scored_days, overlap = run()
    print({k: v for k, v in overlap.items()})
