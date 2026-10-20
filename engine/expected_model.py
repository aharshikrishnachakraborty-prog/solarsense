"""Expected-output model: how much AC power should each inverter make right now? (Phase 3)

Run from the solarsense folder with:   python -m engine.expected_model
Trains two models per plant on the EARLIER days, tests them on the LATER days,
keeps the better one, and writes data/processed/expected.parquet.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

from engine import config
from engine.metrics import save_metrics_section
from engine.model_report import make_figures, write_model_card

RF_FEATURES = ["irradiation", "module_temp", "ambient_temp", "hour_decimal", "inverter_code"]


def load_daylight_rows():
    """Daylight rows from clean.parquet (missing inverter readings are kept for prediction)."""
    if not config.CLEAN_FILE.exists():
        raise FileNotFoundError("clean.parquet not found — run: python -m engine.clean_data")
    clean = pd.read_parquet(config.CLEAN_FILE)
    rows = clean[clean["is_daylight"]].copy()
    rows["hour_decimal"] = rows["timestamp"].dt.hour + rows["timestamp"].dt.minute / 60
    return rows


def split_days(plant_rows):
    """Time split: the first TRAIN_FRACTION of days train the model, the rest test it."""
    days = sorted(plant_rows["date"].unique())
    n_train = int(round(len(days) * config.TRAIN_FRACTION))
    return days[:n_train], days[n_train:]


def is_obvious_outage(rows):
    """Strong sunlight but almost no output — clearly not healthy behaviour."""
    return (rows["irradiation"] >= config.OUTAGE_IRRADIATION_MIN) & (rows["ac_kw"] <= config.OUTAGE_AC_MAX_KW)


# --- Model A: physics-style baseline ----------------------------------------
# Solar power is roughly proportional to sunlight, and drops a little as panels
# get hotter than 25 °C:   ac_kw ≈ k × irradiation × (1 − γ × (module_temp − 25))
# Multiplying out:          ac_kw ≈ k × irradiation  −  k×γ × irradiation × (module_temp − 25)
# That is a straight-line (linear) model with two features, so plain linear
# regression finds a = k and b = −k×γ. No intercept: no sun → no power.
def physics_features(rows):
    """The two engineered features of the physics formula."""
    return np.column_stack([rows["irradiation"], rows["irradiation"] * (rows["module_temp"] - 25)])


def train_physics(train_rows):
    """Fit k and γ of the physics formula with linear regression."""
    model = LinearRegression(fit_intercept=False)
    model.fit(physics_features(train_rows), train_rows["ac_kw"])
    k = float(model.coef_[0])
    gamma = float(-model.coef_[1] / k)
    return model, {"k_kw_per_irradiation": round(k, 2), "gamma_per_degC": round(gamma, 5)}


# --- Model B: Random Forest --------------------------------------------------
def train_random_forest(train_rows):
    """Train a Random Forest on sunlight, temperatures, time of day and inverter id."""
    model = RandomForestRegressor(
        n_estimators=config.RF_N_ESTIMATORS, max_depth=config.RF_MAX_DEPTH,
        min_samples_leaf=config.RF_MIN_SAMPLES_LEAF, random_state=config.RANDOM_SEED, n_jobs=-1)
    model.fit(train_rows[RF_FEATURES], train_rows["ac_kw"])
    importance = dict(zip(RF_FEATURES, (round(float(v), 3) for v in model.feature_importances_)))
    return model, importance


def predict(model_name, model, rows):
    """Expected AC power (kW) from either model; power can never be negative."""
    features = physics_features(rows) if model_name == "physics" else rows[RF_FEATURES]
    return np.clip(model.predict(features), 0, None)


def score(actual, predicted):
    """MAE (kW), R² and MAPE (%, only where actual power is meaningful)."""
    meaningful = actual >= config.MAPE_MIN_ACTUAL_KW
    mape = np.mean(np.abs((actual[meaningful] - predicted[meaningful]) / actual[meaningful])) * 100
    return {"mae_kw": round(float(mean_absolute_error(actual, predicted)), 2),
            "r2": round(float(r2_score(actual, predicted)), 4),
            "mape_pct": round(float(mape), 2), "rows": int(len(actual))}


def fit_plant(plant, plant_rows):
    """Train, test and compare both models for one plant; return models and metrics."""
    train_days, test_days = split_days(plant_rows)
    observed = plant_rows[~plant_rows["is_missing"]]
    train = observed[observed["date"].isin(train_days)]
    test = observed[observed["date"].isin(test_days)]
    outage = is_obvious_outage(train)
    train = train[~outage]   # outages removed from TRAINING only

    models, info = {}, {
        "train_dates": [train_days[0], train_days[-1]], "test_dates": [test_days[0], test_days[-1]],
        "train_days": len(train_days), "test_days": len(test_days),
        "train_rows": int(len(train)), "train_outage_rows_removed": int(outage.sum()),
        "test_rows_obvious_outage": int(is_obvious_outage(test).sum())}
    models["physics"], info["physics_coefficients"] = train_physics(train)
    models["random_forest"], info["rf_feature_importance"] = train_random_forest(train)

    healthy_test = test[~is_obvious_outage(test)]
    for name, model in models.items():
        info[name] = {
            "train": score(train["ac_kw"].to_numpy(), predict(name, model, train)),
            "test_all": score(test["ac_kw"].to_numpy(), predict(name, model, test)),
            "test_without_obvious_outages": score(healthy_test["ac_kw"].to_numpy(),
                                                  predict(name, model, healthy_test))}
    # Pick the model with the lower average error on the unseen test days.
    info["chosen_model"] = min(models, key=lambda name: info[name]["test_all"]["mae_kw"])
    return models, info


def add_peer_comparison(table):
    """Compare each inverter with the plant-wide median at the same moment (same sun, same clouds)."""
    usable = (~table["is_missing"]) & (table["expected_kw"] >= config.MIN_EXPECTED_KW_FOR_RATIO)
    table["actual_to_expected"] = np.where(usable, table["ac_kw"] / table["expected_kw"], np.nan)
    table["peer_median_ratio"] = table.groupby(["plant", "timestamp"])["actual_to_expected"].transform("median")
    table["peer_ratio"] = table["actual_to_expected"] / table["peer_median_ratio"].replace(0, np.nan)
    # Peer median expressed in kW for this inverter (what "a typical neighbour" would make here).
    table["peer_median_kw"] = table["expected_kw"] * table["peer_median_ratio"]
    return table


def add_residuals(table):
    """Residual = actual − expected (kW and %), then peer comparison. Reused by validate.py."""
    table["residual_kw"] = table["ac_kw"] - table["expected_kw"]   # blank where reading is missing
    big_enough = table["expected_kw"] >= config.MIN_EXPECTED_KW_FOR_RATIO
    table["residual_pct"] = np.where(big_enough, 100 * table["residual_kw"] / table["expected_kw"], np.nan)
    return add_peer_comparison(table)


def build_expected_table():
    """Train per plant, predict every daylight row, add residuals and peer comparison, save everything."""
    rows = load_daylight_rows()
    results, metrics = [], {"settings": {
        "train_fraction": config.TRAIN_FRACTION, "outage_irradiation_min": config.OUTAGE_IRRADIATION_MIN,
        "outage_ac_max_kw": config.OUTAGE_AC_MAX_KW, "mape_min_actual_kw": config.MAPE_MIN_ACTUAL_KW}}

    for plant in config.PLANTS:
        plant_rows = rows[rows["plant"] == plant].copy()
        inverter_codes = {inv: code for code, inv in enumerate(sorted(plant_rows["inverter"].unique()))}
        plant_rows["inverter_code"] = plant_rows["inverter"].map(inverter_codes)

        models, info = fit_plant(plant, plant_rows)
        for name, model in models.items():
            joblib.dump({"model": model, "inverter_codes": inverter_codes, "features": RF_FEATURES},
                        config.MODELS_DIR / config.MODEL_FILE_TEMPLATE.format(plant=plant, model=name))

        chosen = info["chosen_model"]
        _, test_days = split_days(plant_rows)
        plant_rows["split"] = np.where(plant_rows["date"].isin(test_days), "test", "train")
        plant_rows["model_used"] = chosen
        plant_rows["expected_kw"] = predict(chosen, models[chosen], plant_rows)
        plant_rows["expected_kw_physics"] = predict("physics", models["physics"], plant_rows)
        results.append(plant_rows)
        metrics[f"plant_{plant}"] = info

    table = pd.concat(results, ignore_index=True)
    table = add_residuals(table).drop(columns=["hour_decimal", "inverter_code"])
    table.to_parquet(config.EXPECTED_FILE, index=False)

    save_metrics_section("expected_model", metrics)
    write_model_card(metrics)
    make_figures(table, metrics)
    return table, metrics


def print_summary(metrics):
    """Print the train/test dates and how both models scored."""
    for plant in config.PLANTS:
        info = metrics[f"plant_{plant}"]
        print(f"\nPlant {plant}: train {info['train_dates'][0]} -> {info['train_dates'][1]} "
              f"({info['train_days']} days), test {info['test_dates'][0]} -> {info['test_dates'][1]} "
              f"({info['test_days']} days)")
        print(f"  obvious outage rows removed from training: {info['train_outage_rows_removed']}")
        for name in ["physics", "random_forest"]:
            for part in ["train", "test_all", "test_without_obvious_outages"]:
                s = info[name][part]
                print(f"  {name:13s} {part:29s} MAE {s['mae_kw']:7.2f} kW  R2 {s['r2']:.4f}  MAPE {s['mape_pct']:6.2f}%")
        print(f"  physics: {info['physics_coefficients']} | chosen: {info['chosen_model']}")
        print(f"  RF importance: {info['rf_feature_importance']}")


if __name__ == "__main__":
    _, model_metrics = build_expected_table()
    print_summary(model_metrics)
    print(f"\nSaved {config.EXPECTED_FILE}, models in {config.MODELS_DIR}, {config.MODEL_CARD}")
