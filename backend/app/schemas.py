"""Canonical internal types and the mapper to the frontend's frozen contract.

Two layers live here:

1. ``Canonical*`` — the backend's own representation. Every extracted field is
   nullable and carries provenance. Missing means missing: we never guess.
2. ``Frontend*`` — the exact shapes declared in ``src/types/*.ts``. The mapper
   at the bottom of this file converts layer 1 into layer 2 and is the only
   place the two are allowed to touch.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ProvenanceSource = Literal["ocr", "rule", "agent", "derived", "user"]
JobStatus = Literal["queued", "processing", "completed", "failed"]
UiStepId = Literal["upload", "language", "extract", "patterns", "weather", "dashboard"]
UiStepStatus = Literal["pending", "processing", "completed"]

InsightBadgeType = Literal["warning", "positive", "neutral", "info"]
InsightIcon = Literal[
    "zap", "shieldCheck", "droplet", "sparkles", "alertTriangle", "trendingUp"
]
RecommendationIcon = Literal["leaf", "shield", "clock", "zap"]
ImpactLevel = Literal["High", "Medium", "Low"]
WeatherImpactLevel = Literal["Low", "Moderate", "High"]
WeatherStatus = Literal["available", "unavailable"]


# ---------------------------------------------------------------------------
# Layer 1 — canonical, provenance-carrying
# ---------------------------------------------------------------------------


class Provenance(BaseModel):
    """Where a single field's value came from and how much to trust it."""

    model_config = ConfigDict(extra="forbid")

    source: ProvenanceSource = "rule"
    page: int | None = None
    confidence: float = 0.0
    # Raw OCR snippet the value was read from. Kept for audit, stripped from
    # every API response and every log line by default.
    raw_text: str | None = Field(default=None, exclude=True)
    flags: list[str] = Field(default_factory=list)


class ValidationFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    field: str | None = None
    message: str


class CanonicalBill(BaseModel):
    """Every field nullable. A null value means "not present in the document"."""

    model_config = ConfigDict(extra="forbid")

    provider: str | None = None
    consumer_number: str | None = None
    billing_period: str | None = None
    bill_date: str | None = None
    due_date: str | None = None
    previous_reading: float | None = None
    current_reading: float | None = None
    units_consumed: float | None = None
    unit_label: str = "kWh"
    total_amount: float | None = None
    currency_symbol: str = "₹"
    meter_type: str | None = None
    tariff_category: str | None = None
    sanctioned_load: str | None = None
    connection_type: str | None = None
    address_present: bool = False
    # Not a field on the document: the name of the file it was read from. Kept
    # as a first-class value rather than smuggled through provenance, because
    # provenance snippets are stripped from responses and this one is shown.
    source_file_name: str | None = None

    provenance: dict[str, Provenance] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    detected_language: str = "English"
    ocr_engine: str | None = None
    ocr_mean_confidence: float | None = None


class MonthlyConsumption(BaseModel):
    month: str
    full_month: str
    kwh: float
    amount: float
    is_current: bool = False


class ForecastTrendPoint(BaseModel):
    month: str
    kwh: float
    amount_min: float
    amount_max: float


class AffectingFactor(BaseModel):
    icon: str
    title: str
    description: str


class ApplianceShare(BaseModel):
    name: str
    percentage: float
    color: str
    estimated_kwh: float


class CanonicalForecast(BaseModel):
    target_month: str
    expected_amount_min: float
    expected_amount_max: float
    expected_units_kwh: float
    historical_trend: list[MonthlyConsumption] = Field(default_factory=list)
    forecast_trend: list[ForecastTrendPoint] = Field(default_factory=list)
    affecting_factors: list[AffectingFactor] = Field(default_factory=list)
    appliance_breakdown: list[ApplianceShare] = Field(default_factory=list)
    # "Not enough historical data to generate a reliable forecast."
    reliable: bool = True
    method: str = "weighted_moving_average"
    confidence: float = 0.0


class CanonicalWeather(BaseModel):
    status: WeatherStatus = "unavailable"
    location: str = "Unknown"
    temp_c: float | None = None
    condition: str = "Unavailable"
    humidity_percent: float | None = None
    impact_level: WeatherImpactLevel = "Low"
    impact_summary: str = ""
    detail_note: str = ""


class CanonicalInsight(BaseModel):
    id: str
    type: InsightBadgeType
    icon_name: InsightIcon
    text: str


class CanonicalRecommendation(BaseModel):
    id: str
    title: str
    impact_level: ImpactLevel
    suggested_action: str
    why_it_matters: str
    potential_impact: str
    icon_name: RecommendationIcon


class AnalysisBundle(BaseModel):
    """Full backend-side result for a job."""

    job_id: str
    bill: CanonicalBill
    forecast: CanonicalForecast
    weather: CanonicalWeather
    insights: list[CanonicalInsight] = Field(default_factory=list)
    recommendations: list[CanonicalRecommendation] = Field(default_factory=list)
    validation: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer 2 — the frontend contract (src/types/*.ts)
# ---------------------------------------------------------------------------


class FrontendBill(BaseModel):
    id: str
    fileName: str
    provider: str | None = None
    consumerNumber: str | None = None
    billingPeriod: str | None = None
    billDate: str | None = None
    dueDate: str | None = None
    previousReading: float | None = None
    currentReading: float | None = None
    unitsConsumed: float | None = None
    unitLabel: str = "kWh"
    totalAmount: float | None = None
    currencySymbol: str = "₹"
    language: str = "English"
    meterType: str | None = None
    tariffCategory: str | None = None


class FrontendInsight(BaseModel):
    id: str
    type: InsightBadgeType
    iconName: InsightIcon
    text: str


class FrontendRecommendation(BaseModel):
    id: str
    title: str
    impactLevel: ImpactLevel
    suggestedAction: str
    whyItMatters: str
    potentialImpact: str
    iconName: RecommendationIcon


class FrontendForecast(BaseModel):
    targetMonth: str
    expectedAmountMin: float
    expectedAmountMax: float
    expectedUnitsKwh: float
    historicalTrend: list[dict[str, Any]]
    forecastTrend: list[dict[str, Any]]
    affectingFactors: list[dict[str, Any]]
    applianceBreakdown: list[dict[str, Any]]
    reliable: bool = True


class FrontendWeather(BaseModel):
    location: str
    tempC: float | None = None
    condition: str
    humidityPercent: float | None = None
    impactLevel: WeatherImpactLevel
    impactSummary: str
    detailNote: str
    weatherStatus: WeatherStatus = "unavailable"


class FrontendAnalysisResult(BaseModel):
    bill: FrontendBill
    insights: list[FrontendInsight]
    forecast: FrontendForecast
    weather: FrontendWeather
    recommendations: list[FrontendRecommendation]


# ---------------------------------------------------------------------------
# API envelopes
# ---------------------------------------------------------------------------


class JobTiming(BaseModel):
    stage: str
    duration_ms: int


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage: str
    ui_step: UiStepId
    ui_step_index: int
    progress: float
    message: str
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)
    timings: list[JobTiming] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


class UploadAcceptedResponse(BaseModel):
    job_id: str
    document_id: str
    file_name: str
    size_bytes: int
    status: JobStatus
    events_url: str
    status_url: str


class AnalysisResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage: str
    ui_step: UiStepId
    progress: float
    message: str
    warnings: list[str] = Field(default_factory=list)
    timings: list[JobTiming] = Field(default_factory=list)
    # The frozen frontend contract.
    analysis: FrontendAnalysisResult
    # Additive: safe to ignore on the client, useful for confidence UI.
    provenance: dict[str, Any] = Field(default_factory=dict)
    validation: list[ValidationFinding] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    detected_language: str = "English"
    ocr_engine: str | None = None
    ocr_mean_confidence: float | None = None


class DocumentSummary(BaseModel):
    """One row of the local document library.

    Every extracted value is nullable: a field the reader could not find stays
    null here rather than being filled with a placeholder, so the list never
    shows a figure that is not on the original document.
    """

    id: str
    job_id: str | None = None
    file_name: str
    provider: str | None = None
    billing_period: str | None = None
    units: float | None = None
    amount: float | None = None
    unit_label: str = "kWh"
    currency_symbol: str = "₹"
    status: JobStatus
    uploaded_at: datetime
    size_bytes: int
    detected_language: str | None = None
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary] = Field(default_factory=list)
    total: int = 0


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    ocr: dict[str, Any]
    agent: dict[str, Any]
    database: dict[str, Any]
    weather: dict[str, Any]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    job_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    scope_decision: Literal[
        "answered", "out_of_scope", "insufficient_context", "rejected"
    ]
    suggested_followups: list[str] = Field(default_factory=list)
    grounded_on_job_id: str | None = None


# ---------------------------------------------------------------------------
# Mapper — canonical -> frontend
# ---------------------------------------------------------------------------


def to_frontend_analysis(bundle: AnalysisBundle) -> FrontendAnalysisResult:
    bill = bundle.bill
    forecast = bundle.forecast
    weather = bundle.weather

    return FrontendAnalysisResult(
        bill=FrontendBill(
            id=f"bill-{bundle.job_id}",
            fileName=bill.source_file_name or "uploaded_bill",
            provider=bill.provider,
            consumerNumber=bill.consumer_number,
            billingPeriod=bill.billing_period,
            billDate=bill.bill_date,
            dueDate=bill.due_date,
            previousReading=bill.previous_reading,
            currentReading=bill.current_reading,
            unitsConsumed=bill.units_consumed,
            unitLabel=bill.unit_label,
            totalAmount=bill.total_amount,
            currencySymbol=bill.currency_symbol,
            language=bill.detected_language,
            meterType=bill.meter_type,
            tariffCategory=bill.tariff_category,
        ),
        insights=[
            FrontendInsight(
                id=i.id, type=i.type, iconName=i.icon_name, text=i.text
            )
            for i in bundle.insights
        ],
        forecast=FrontendForecast(
            targetMonth=forecast.target_month,
            expectedAmountMin=forecast.expected_amount_min,
            expectedAmountMax=forecast.expected_amount_max,
            expectedUnitsKwh=forecast.expected_units_kwh,
            historicalTrend=[
                {
                    "month": m.month,
                    "fullMonth": m.full_month,
                    "kwh": m.kwh,
                    "amount": m.amount,
                    **({"isCurrent": True} if m.is_current else {}),
                }
                for m in forecast.historical_trend
            ],
            forecastTrend=[
                {
                    "month": p.month,
                    "kwh": p.kwh,
                    "amountMin": p.amount_min,
                    "amountMax": p.amount_max,
                }
                for p in forecast.forecast_trend
            ],
            affectingFactors=[
                {"icon": f.icon, "title": f.title, "description": f.description}
                for f in forecast.affecting_factors
            ],
            applianceBreakdown=[
                {
                    "name": a.name,
                    "percentage": a.percentage,
                    "color": a.color,
                    "estimatedKwh": a.estimated_kwh,
                }
                for a in forecast.appliance_breakdown
            ],
            reliable=forecast.reliable,
        ),
        weather=FrontendWeather(
            location=weather.location,
            tempC=weather.temp_c,
            condition=weather.condition,
            humidityPercent=weather.humidity_percent,
            impactLevel=weather.impact_level,
            impactSummary=weather.impact_summary,
            detailNote=weather.detail_note,
            weatherStatus=weather.status,
        ),
        recommendations=[
            FrontendRecommendation(
                id=r.id,
                title=r.title,
                impactLevel=r.impact_level,
                suggestedAction=r.suggested_action,
                whyItMatters=r.why_it_matters,
                potentialImpact=r.potential_impact,
                iconName=r.icon_name,
            )
            for r in bundle.recommendations
        ],
    )
