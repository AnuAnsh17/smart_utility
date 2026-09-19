"""Consumption forecasting.

The forecast is deliberately the least clever part of this system. It is a
weighted moving average over the months we actually have on file for the same
consumer connection — nothing more.

Three consequences follow, and all three are intentional:

* **We need history to forecast.** A single bill cannot show a trend. With
  fewer than three observations the result is marked ``reliable=False`` and the
  UI is expected to say so, rather than dressing up a guess as a projection.
* **Money comes from the tariff module.** The forecast predicts *units*. Rupees
  are produced by ``tariff_service`` pricing those units. No language model is
  ever in the position of inventing a rupee figure.
* **The method is swappable.** ``method`` is recorded on every result so that a
  future ARIMA/Prophet/LightGBM implementation can coexist with this one and be
  told apart in the database.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.schemas import (
    AffectingFactor,
    ApplianceShare,
    CanonicalBill,
    CanonicalForecast,
    ForecastTrendPoint,
    MonthlyConsumption,
)

from app.services import tariff_service

log = logging.getLogger("smart_utility.forecast")

METHOD = "weighted_moving_average"
MIN_MONTHS_FOR_TREND = 3
FORECAST_HORIZON = 3

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
MONTH_ABBR = tuple(name[:3] for name in MONTH_NAMES)

# Which months carry meaningfully higher load in most of India. Used only to
# explain a movement that is already visible in the data — never to create one.
MONSOON_MONTHS = {6, 7, 8, 9}
SUMMER_MONTHS = {4, 5}

# A named, declared split of a residential load. This is a *model*, not a
# measurement, and the UI labels it as an estimate. It is scaled by the real
# measured consumption, so an implausible input still produces nothing.
APPLIANCE_PROFILE: tuple[tuple[str, float, str], ...] = (
    ("Air Conditioning", 0.32, "#3b82f6"),
    ("Refrigeration", 0.18, "#06b6d4"),
    ("Water Heating", 0.14, "#f59e0b"),
    ("Lighting", 0.12, "#eab308"),
    ("Fans & Cooling", 0.11, "#8b5cf6"),
    ("Electronics", 0.08, "#ec4899"),
    ("Other", 0.05, "#64748b"),
)


@dataclass
class HistoryPoint:
    year: int
    month: int
    kwh: float
    amount: float | None
    is_current: bool = False

    @property
    def sort_key(self) -> tuple[int, int]:
        return (self.year, self.month)

    @property
    def abbr(self) -> str:
        return MONTH_ABBR[self.month - 1]

    @property
    def full(self) -> str:
        return MONTH_NAMES[self.month - 1]


_PERIOD_MONTH = re.compile(
    r"\b(" + "|".join(MONTH_NAMES + MONTH_ABBR) + r")\w*[\s,/-]+(\d{4})\b",
    re.IGNORECASE,
)
_PERIOD_NUMERIC = re.compile(r"\b(0?[1-9]|1[0-2])[/-](\d{4})\b")


def parse_period(period: str | None) -> tuple[int, int] | None:
    """Read a billing period label into ``(year, month)``.

    Only the *first* month mentioned is used. A period spanning a month
    boundary ("01 Jan 2025 - 31 Jan 2025") belongs to the month it opens in,
    which keeps one bill to one point on the trend line.
    """
    if not period:
        return None

    match = _PERIOD_MONTH.search(period)
    if match:
        name, year = match.groups()
        key = name[:3].lower()
        for index, abbr in enumerate(MONTH_ABBR):
            if abbr.lower() == key:
                return (int(year), index + 1)

    match = _PERIOD_NUMERIC.search(period)
    if match:
        month, year = match.groups()
        return (int(year), int(month))

    return None


def _load_json(value: object) -> dict:
    """Read a stored bill back, whichever way it was persisted.

    The column is ``Text`` and the writer uses ``json.dumps``, but an earlier
    revision stored dicts directly and a driver may hand either back. Being
    tolerant here costs nothing and stops a serialisation choice from silently
    disabling the history that the forecast depends on.
    """
    if not value:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


def collect_history(
    session,
    bill: CanonicalBill,
    *,
    current_job_id: str,
    limit: int = 18,
) -> list[HistoryPoint]:
    """Assemble the consumption series for this connection.

    Prior analyses are matched on consumer number when the current bill has
    one. Without a consumer number we cannot honestly claim the older rows
    belong to the same connection, so we return only the current period.
    """
    from app.models import BillAnalysis

    points: list[HistoryPoint] = []
    seen: set[tuple[int, int]] = set()

    current_period = parse_period(bill.billing_period)
    if current_period and bill.units_consumed:
        points.append(
            HistoryPoint(
                year=current_period[0],
                month=current_period[1],
                kwh=float(bill.units_consumed),
                amount=bill.total_amount,
                is_current=True,
            )
        )
        seen.add(current_period)

    if bill.consumer_number:
        rows = (
            session.query(BillAnalysis)
            .filter(BillAnalysis.job_id != current_job_id)
            .order_by(BillAnalysis.created_at.desc())
            .limit(limit * 4)
            .all()
        )
        for row in rows:
            stored = _load_json(row.bill_json)
            if stored.get("consumer_number") != bill.consumer_number:
                continue
            period = parse_period(stored.get("billing_period"))
            units = stored.get("units_consumed")
            if not period or not units or period in seen:
                continue
            points.append(
                HistoryPoint(
                    year=period[0],
                    month=period[1],
                    kwh=float(units),
                    amount=stored.get("total_amount"),
                )
            )
            seen.add(period)
            if len(points) >= limit:
                break

    points.sort(key=lambda point: point.sort_key)
    return points[-limit:]


def _weighted_average(values: list[float]) -> float:
    """Most recent value weighted heaviest. Weights 3:2:1 over the tail."""
    window = values[-3:]
    weights = [1.0, 2.0, 3.0][-len(window):]
    total = sum(weights)
    return sum(value * weight for value, weight in zip(window, weights)) / total


def _confidence(values: list[float]) -> float:
    """Higher with more history and less month-to-month scatter."""
    if not values:
        return 0.0
    count_score = min(len(values), 6) / 6.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return round(count_score * 0.3, 3)
    spread = (max(values) - min(values)) / mean
    stability = max(0.0, 1.0 - min(spread, 1.0))
    return round(max(0.05, min(0.95, count_score * 0.6 + stability * 0.4)), 3)


def build_history_series(
    points: list[HistoryPoint], category: str | None
) -> list[MonthlyConsumption]:
    """Render history for the dashboard, pricing any month that has no amount."""
    series: list[MonthlyConsumption] = []
    for point in points:
        amount = point.amount
        if amount is None:
            amount = tariff_service.estimate(point.kwh, category).total
        series.append(
            MonthlyConsumption(
                month=point.abbr,
                full_month=f"{point.full} {point.year}",
                kwh=round(point.kwh, 2),
                amount=round(float(amount), 2),
                is_current=point.is_current,
            )
        )
    return series


def _next_periods(points: list[HistoryPoint], horizon: int) -> list[tuple[int, int, str]]:
    latest = points[-1]
    year, month = latest.year, latest.month
    out = []
    for _ in range(horizon):
        month += 1
        if month > 12:
            month = 1
            year += 1
        out.append((year, month, MONTH_ABBR[month - 1]))
    return out


def forecast(
    history: list[HistoryPoint],
    bill: CanonicalBill,
    *,
    horizon: int = FORECAST_HORIZON,
) -> CanonicalForecast | None:
    """Project consumption, then price it. Returns ``None`` when unforecastable."""
    if not history:
        return None

    category = bill.tariff_category
    kwh_values = [point.kwh for point in history]
    projected = _weighted_average(kwh_values)
    confidence = _confidence(kwh_values)
    reliable = len(history) >= MIN_MONTHS_FOR_TREND

    periods = _next_periods(history, horizon)
    priced = tariff_service.estimate(projected, category)

    # A flat projection is the honest short-horizon shape: we have no
    # seasonality model, so we do not draw a seasonal curve we cannot support.
    forecast_trend = [
        ForecastTrendPoint(
            month=abbr,
            kwh=round(projected, 2),
            amount_min=priced.total_min,
            amount_max=priced.total_max,
        )
        for _, _, abbr in periods
    ]

    return CanonicalForecast(
        target_month=f"{MONTH_NAMES[periods[0][1] - 1]} {periods[0][0]}",
        expected_amount_min=priced.total_min,
        expected_amount_max=priced.total_max,
        expected_units_kwh=round(projected, 2),
        historical_trend=build_history_series(history, category),
        forecast_trend=forecast_trend,
        affecting_factors=_factors(history, bill, priced),
        appliance_breakdown=_breakdown(projected, reliable),
        reliable=reliable,
        method=METHOD,
        confidence=confidence,
    )


def _factors(history, bill, priced) -> list[AffectingFactor]:
    """Explain the projection using the evidence actually present."""
    factors: list[AffectingFactor] = []
    latest = history[-1]

    if latest.month in SUMMER_MONTHS:
        factors.append(
            AffectingFactor(
                icon="zap",
                title="Peak summer period",
                description=(
                    "Cooling load typically rises through April and May, which is "
                    "when most Indian households record their highest units."
                ),
            )
        )
    elif latest.month in MONSOON_MONTHS:
        factors.append(
            AffectingFactor(
                icon="droplet",
                title="Monsoon period",
                description=(
                    "Cooling demand usually eases from June onwards, though "
                    "dehumidification can keep consumption above the winter floor."
                ),
            )
        )
    else:
        factors.append(
            AffectingFactor(
                icon="zap",
                title="Moderate-demand period",
                description=(
                    "This part of the year is usually neither the summer peak nor "
                    "the winter trough for household electricity demand."
                ),
            )
        )

    if len(history) >= 2:
        previous = history[-2]
        if previous.kwh > 0:
            change = (latest.kwh - previous.kwh) / previous.kwh
            if abs(change) >= 0.05:
                direction = "up" if change > 0 else "down"
                factors.append(
                    AffectingFactor(
                        icon="trendingUp" if change > 0 else "sparkles",
                        title=f"Consumption {direction} {abs(change) * 100:.0f}%",
                        description=(
                            f"The current period reads {latest.kwh:g} units against "
                            f"{previous.kwh:g} in {previous.full}."
                        ),
                    )
                )

    if priced.indicative:
        factors.append(
            AffectingFactor(
                icon="shieldCheck",
                title="Estimated tariff applied",
                description=(
                    f"Amounts are priced with {priced.schedule_name}. Your "
                    "utility's published tariff may differ."
                ),
            )
        )

    if priced.band:
        factors.append(
            AffectingFactor(
                icon="zap",
                title=f"Slab {priced.band} pricing",
                description=(
                    "Units are charged progressively, so consumption in the higher "
                    "slabs moves the total more than the average rate suggests."
                ),
            )
        )

    if bill.meter_type and "smart" in bill.meter_type.lower():
        factors.append(
            AffectingFactor(
                icon="sparkles",
                title="Smart meter connected",
                description=(
                    "Interval data from a smart meter would allow a sharper load "
                    "profile than a single monthly reading permits."
                ),
            )
        )

    return factors


def _breakdown(projected_kwh: float, reliable: bool) -> list[ApplianceShare]:
    """Scale a declared residential load profile by the measured total.

    Returns nothing when the projection is unreliable, because a breakdown of a
    number we do not trust would compound the problem.
    """
    if not reliable or projected_kwh is None or projected_kwh <= 0:
        return []
    return [
        ApplianceShare(
            name=name,
            percentage=round(share * 100, 1),
            color=color,
            estimated_kwh=round(projected_kwh * share, 2),
        )
        for name, share, color in APPLIANCE_PROFILE
    ]


def describe() -> dict[str, object]:
    return {
        "method": METHOD,
        "min_months_for_trend": MIN_MONTHS_FOR_TREND,
        "horizon_months": FORECAST_HORIZON,
        "appliance_profile_is_estimates": True,
    }
