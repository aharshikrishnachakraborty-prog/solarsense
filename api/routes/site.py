"""Solar Site Planner endpoints (Phase 12): expected monthly energy for a new plant anywhere in India, from
free NASA POWER satellite weather. The calibration numbers were measured by the pipeline (metrics.json)."""

from fastapi import APIRouter, HTTPException, Query

from api.data_store import get_store
from api.schemas import SiteEstimateResponse, SitePresetsResponse
from engine import config
from engine.site_estimator import SiteDataUnavailable, estimate_site

router = APIRouter(prefix="/api", tags=["site estimator"])


@router.get("/site-estimate/presets", response_model=SitePresetsResponse)
def site_presets():
    """Example cities, the default plant size, the allowed area (India) and how accurate the planner is."""
    return {"presets": config.SITE_PRESETS, "default_capacity_kw": config.SITE_DEFAULT_CAPACITY_KW,
            "lat_range": list(config.SITE_LAT_RANGE), "lon_range": list(config.SITE_LON_RANGE),
            "accuracy": get_store().metrics.get("site_accuracy")}


@router.get("/site-estimate", response_model=SiteEstimateResponse)
def site_estimate(lat: float = Query(..., ge=config.SITE_LAT_RANGE[0], le=config.SITE_LAT_RANGE[1],
                                     description="Latitude in degrees north (India only)"),
                  lon: float = Query(..., ge=config.SITE_LON_RANGE[0], le=config.SITE_LON_RANGE[1],
                                     description="Longitude in degrees east (India only)"),
                  capacity_kw: float = Query(..., gt=0, le=config.SITE_MAX_CAPACITY_KW,
                                             description="Plant size in kW (panel rating)")):
    """Expected kWh per month for the last 12 complete months of real weather at this place."""
    section = get_store().metrics.get("site_estimator")
    if not section:
        raise HTTPException(404, "Site estimator not calibrated yet — run the pipeline (python run_all.py).")
    try:
        return estimate_site(lat, lon, capacity_kw, section["calibration"])
    except SiteDataUnavailable as error:
        raise HTTPException(503, str(error)) from error
