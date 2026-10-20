"""Response shapes (pydantic models) — they document every endpoint on the /docs page."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# The ratio actual ÷ expected energy. Shown to people as "Actual vs expected" (the field keeps its
# internal name so the pipeline files do not change).
AVE_TITLE = "Actual vs expected"
AVE_HELP = ("Actual ÷ expected energy (1.0 = 100%). Above 100% means the plant produced more than "
            "our model estimated.")


class PlantInfo(BaseModel):
    plant: int
    inverters: int
    first_date: str
    last_date: str
    worst_loss_date: str = Field(description="Day with the highest energy lost (default replay date).")


class PlantsResponse(BaseModel):
    plants: list[PlantInfo]
    dates: list[str]
    default_plant: int
    default_date: str


class Overview(BaseModel):
    plant: int
    date: str
    takeaway: str
    actual_kwh: float
    expected_kwh: float
    performance_ratio: Optional[float] = Field(title=AVE_TITLE, description=AVE_HELP)
    fault_loss_kwh: float
    fault_loss_inr: float
    at_risk_kwh: float
    at_risk_inr: float
    active_alerts_by_severity: dict[str, int] = Field(
        description="Open/acknowledged alerts on this day, excluding data-quality notices.")
    data_quality_notices: list[dict[str, Any]] = Field(
        description="Plant-wide sensor/data issues with no energy lost (shown as a notice, not an alert).")
    inverters_needing_attention: int
    tariff_inr_per_kwh: float
    tariff_note: str


class TimeseriesPoint(BaseModel):
    timestamp: str
    actual_kw: float
    expected_kw: float
    expected_kw_all: float
    irradiation: Optional[float]
    missing_inverters: int


class TimeseriesResponse(BaseModel):
    plant: int
    date: str
    points: list[TimeseriesPoint]


class HeatmapResponse(BaseModel):
    plant: int
    inverters: list[str]
    dates: list[str]
    performance_ratio: list[list[Optional[float]]] = Field(title=AVE_TITLE, description=AVE_HELP)
    fault_loss_kwh: list[list[float]]


class AlertSummary(BaseModel):
    id: str
    plant: int
    inverter: str
    fault_type: str
    start: str
    end: str
    duration_hours: float
    severity: str
    energy_loss_kwh: float
    energy_at_risk_kwh: float
    money_loss_inr: float
    money_at_risk_inr: float
    reason: str
    recommended_action: str
    status: str
    status_updated_at: Optional[str] = None


class AlertsResponse(BaseModel):
    count: int
    alerts: list[AlertSummary]


class AlertDetail(AlertSummary):
    evidence: dict[str, Any]
    series_kind: Literal["intervals", "daily", "none"]
    series: list[dict[str, Any]]
    tariff_note: str


class StatusUpdate(BaseModel):
    status: Literal["Open", "Acknowledged", "Resolved"]


class StatusResponse(BaseModel):
    id: str
    status: str
    updated_at: str


class InverterResponse(BaseModel):
    inverter: str
    plant: int
    date: str
    series: list[dict[str, Any]]
    alerts: list[AlertSummary]
    daily_history: list[dict[str, Any]]
    pr_trend: Optional[dict[str, Any]] = None


class LossesResponse(BaseModel):
    plant: Optional[int]
    days: int
    total: dict[str, float]
    by_fault_type: list[dict[str, Any]]
    top_inverters: list[dict[str, Any]]
    daily_trend: list[dict[str, Any]]
    projection_note: str
    tariff_note: str


class Assumption(BaseModel):
    key: str
    title: str
    value: Any
    unit: str
    why: str
    source: str
