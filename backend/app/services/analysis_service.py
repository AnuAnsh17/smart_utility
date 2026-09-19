"""Insights and recommendations, derived by arithmetic rather than generated.

Every sentence this module emits is built from a number that was read off the
document or computed from one. There is no language model in this file, and
that is the point: the assistant layer is allowed to *describe* these findings
but is never the thing that decides what they are.

Each insight records the figure it is based on in its text, so a user can check
it against their own bill. If a figure is missing, the insight that would have
used it is simply not produced — an absent insight is better than a made-up one.
"""

from __future__ import annotations

import logging

from app.schemas import (
    CanonicalBill,
    CanonicalForecast,
    CanonicalInsight,
    CanonicalRecommendation,
    CanonicalWeather,
    ValidationFinding,
)

from app.services import tariff_service

log = logging.getLogger("smart_utility.analysis")

# Declared reference bands, not measurements. Used only to phrase a comparison
# as "above/below the reference band", never presented as the user's own data.
REFERENCE_MONTHLY_KWH = {
    "residential": (110.0, 320.0),
    "commercial": (250.0, 900.0),
    "industrial": (900.0, 4000.0),
    "agricultural": (80.0, 400.0),
}

MIN_DAYS_FOR_DAILY_AVERAGE = 20
SIGNIFICANT_CHANGE = 0.12


def _reference_band(category: str | None) -> tuple[float, float] | None:
    if not category:
        return REFERENCE_MONTHLY_KWH["residential"]
    lowered = category.lower()
    for key, band in REFERENCE_MONTHLY_KWH.items():
        if key in lowered:
            return band
    return None


def _money(value: float, symbol: str = "₹") -> str:
    return f"{symbol}{value:,.0f}"


def build_insights(
    bill: CanonicalBill,
    forecast: CanonicalForecast,
    validation: list[ValidationFinding],
) -> list[CanonicalInsight]:
    insights: list[CanonicalInsight] = []
    units = bill.units_consumed
    amount = bill.total_amount
    symbol = bill.currency_symbol

    # --- what the bill itself says ---------------------------------------
    if units is not None and amount is not None:
        rate = tariff_service.implied_rate(amount, units)
        if rate is not None:
            insights.append(
                CanonicalInsight(
                    id="effective_rate",
                    type="info",
                    icon_name="zap",
                    text=(
                        f"This bill worked out to {symbol}{rate:.2f} per unit "
                        f"({units:g} {bill.unit_label} for {_money(amount, symbol)})."
                    ),
                )
            )

    if units is not None:
        band = _reference_band(bill.tariff_category)
        if band:
            low, high = band
            if units > high:
                insights.append(
                    CanonicalInsight(
                        id="above_reference",
                        type="warning",
                        icon_name="alertTriangle",
                        text=(
                            f"{units:g} {bill.unit_label} is above the usual "
                            f"{low:g}-{high:g} range for this category. Worth a "
                            "look at what changed this period."
                        ),
                    )
                )
            elif units < low:
                insights.append(
                    CanonicalInsight(
                        id="below_reference",
                        type="positive",
                        icon_name="shieldCheck",
                        text=(
                            f"{units:g} {bill.unit_label} is below the usual "
                            f"{low:g}-{high:g} range for this category."
                        ),
                    )
                )
            else:
                insights.append(
                    CanonicalInsight(
                        id="within_reference",
                        type="neutral",
                        icon_name="sparkles",
                        text=(
                            f"{units:g} {bill.unit_label} sits inside the usual "
                            f"{low:g}-{high:g} band for this category."
                        ),
                    )
                )

    # --- movement against the previous period ----------------------------
    history = forecast.historical_trend
    if len(history) >= 2:
        previous, current = history[-2], history[-1]
        if previous.kwh > 0:
            change = (current.kwh - previous.kwh) / previous.kwh
            if abs(change) >= SIGNIFICANT_CHANGE:
                word = "rose" if change > 0 else "fell"
                insights.append(
                    CanonicalInsight(
                        id="period_change",
                        type="warning" if change > 0 else "positive",
                        icon_name="trendingUp" if change > 0 else "shieldCheck",
                        text=(
                            f"Consumption {word} {abs(change) * 100:.0f}% from "
                            f"{previous.kwh:g} to {current.kwh:g} "
                            f"{bill.unit_label} between {previous.full_month} and "
                            f"{current.full_month}."
                        ),
                    )
                )

    # --- daily average ----------------------------------------------------
    days = _period_days(bill.billing_period)
    if units is not None and days and days >= MIN_DAYS_FOR_DAILY_AVERAGE:
        daily = units / days
        insights.append(
            CanonicalInsight(
                id="daily_average",
                type="info",
                icon_name="sparkles",
                text=(
                    f"That is about {daily:.1f} {bill.unit_label} a day across a "
                    f"{days}-day billing period."
                ),
            )
        )

    # --- data quality -----------------------------------------------------
    errors = [f for f in validation if f.severity == "error"]
    warnings = [f for f in validation if f.severity == "warning"]

    if errors:
        insights.append(
            CanonicalInsight(
                id="validation_errors",
                type="warning",
                icon_name="alertTriangle",
                text=(
                    f"{len(errors)} figure{'s' if len(errors) != 1 else ''} on this "
                    "bill did not pass a consistency check. Confirm them against "
                    "the original document."
                ),
            )
        )
    elif warnings:
        insights.append(
            CanonicalInsight(
                id="validation_warnings",
                type="neutral",
                icon_name="alertTriangle",
                text=(
                    f"{len(warnings)} value{'s' if len(warnings) != 1 else ''} are "
                    "worth a second look; nothing was changed automatically."
                ),
            )
        )

    if bill.missing_fields:
        insights.append(
            CanonicalInsight(
                id="missing_fields",
                type="info",
                icon_name="droplet",
                text=(
                    f"{len(bill.missing_fields)} field"
                    f"{'s' if len(bill.missing_fields) != 1 else ''} could not be "
                    "read from this document and has been left blank rather than "
                    "estimated."
                ),
            )
        )

    if not forecast.reliable:
        insights.append(
            CanonicalInsight(
                id="thin_history",
                type="info",
                icon_name="sparkles",
                text=(
                    "Only one period is on file for this connection, so the "
                    "forecast is a projection rather than a trend. Adding earlier "
                    "bills will sharpen it."
                ),
            )
        )

    return insights


def build_recommendations(
    bill: CanonicalBill,
    forecast: CanonicalForecast,
) -> list[CanonicalRecommendation]:
    recommendations: list[CanonicalRecommendation] = []
    units = bill.units_consumed
    symbol = bill.currency_symbol
    category = bill.tariff_category

    # An efficiency recommendation is only honest if we can price the saving.
    if units and units > 0:
        ten_percent = units * 0.10
        saving = tariff_service.estimate(ten_percent, category).total
        recommendations.append(
            CanonicalRecommendation(
                id="ten_percent_cut",
                title="Trim 10% off this period's consumption",
                impact_level="Medium",
                suggested_action=(
                    "Shift the heaviest loads — cooling and water heating — off "
                    "the evening peak, and set cooling two degrees warmer."
                ),
                why_it_matters=(
                    f"A 10% reduction is about {ten_percent:.0f} "
                    f"{bill.unit_label} for a period like this one, which is the "
                    "easiest saving to find without changing equipment."
                ),
                potential_impact=(
                    f"Roughly {_money(saving, symbol)} at the applied tariff, "
                    "before fixed charges."
                ),
                icon_name="leaf",
            )
        )

    if forecast.reliable and forecast.appliance_breakdown:
        top = max(forecast.appliance_breakdown, key=lambda item: item.percentage)
        recommendations.append(
            CanonicalRecommendation(
                id="top_consumer",
                title=f"Start with {top.name}",
                impact_level="High",
                suggested_action=(
                    f"Cooling and heating loads are where most households find "
                    f"savings. Around {top.estimated_kwh:g} {bill.unit_label} of "
                    f"this period's usage is attributable to {top.name} in the "
                    "reference profile."
                ),
                why_it_matters=(
                    f"{top.name} is the single largest slice of the estimated "
                    f"breakdown at {top.percentage:.0f}%."
                ),
                potential_impact=(
                    f"A 20% cut here is about {top.estimated_kwh * 0.2:.0f} "
                    f"{bill.unit_label}."
                ),
                icon_name="zap",
            )
        )

    if bill.tariff_category and forecast.affecting_factors:
        recommendations.append(
            CanonicalRecommendation(
                id="tariff_check",
                title="Confirm your tariff category",
                impact_level="Low",
                suggested_action=(
                    f"This connection is recorded as {bill.tariff_category}. "
                    "Categories and slab rates differ, so confirm it matches what "
                    "your utility has on file."
                ),
                why_it_matters=(
                    "Amounts in this analysis are priced with "
                    f"{tariff_service.schedule_for(category).name}, which is an "
                    "indicative schedule rather than your utility's published one."
                ),
                potential_impact=(
                    "Correcting a category mismatch can change the bill materially."
                ),
                icon_name="shield",
            )
        )

    if not forecast.reliable:
        recommendations.append(
            CanonicalRecommendation(
                id="add_history",
                title="Add earlier bills to unlock forecasting",
                impact_level="Medium",
                suggested_action=(
                    "Upload two or three previous bills for the same consumer "
                    "number. They are matched automatically and build the "
                    "consumption trend."
                ),
                why_it_matters=(
                    "A forecast needs a history. One period is a point, not a "
                    "trend, and this system will not present a single reading as "
                    "a projection."
                ),
                potential_impact=(
                    "Enables month-over-month comparison and a reliable forecast."
                ),
                icon_name="clock",
            )
        )

    return recommendations


def placeholder_forecast() -> CanonicalForecast:
    """A forecast-shaped object that says plainly it is not a forecast.

    ``AnalysisBundle`` requires a forecast, so when one cannot be produced we
    return this rather than a plausible-looking set of zeroes. The ``reliable``
    flag and the empty trends are what the dashboard keys off.
    """
    return CanonicalForecast(
        target_month="Not enough history",
        expected_amount_min=0.0,
        expected_amount_max=0.0,
        expected_units_kwh=0.0,
        historical_trend=[],
        forecast_trend=[],
        affecting_factors=[],
        appliance_breakdown=[],
        reliable=False,
        method="unavailable",
        confidence=0.0,
    )


def weather_note(weather: CanonicalWeather) -> str | None:
    """Surface weather absence in the job warnings, so the UI can explain it."""
    if weather.status == "unavailable":
        return weather.detail_note or "Weather context was unavailable."
    return None


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _period_days(period: str | None) -> int | None:
    """How many days the billing period covers, when the label says so.

    Indian bills state this two ways: an explicit range, or a month name with a
    year. We count days rather than assume a month length.
    """
    if not period:
        return None

    import re
    from datetime import date

    range_match = re.search(
        r"(\d{1,2})[/\s-]*([A-Za-z]{3,9}|\d{1,2})[/\s-]*(\d{2,4})"
        r"\s*(?:to|-|–|—)\s*"
        r"(\d{1,2})[/\s-]*([A-Za-z]{3,9}|\d{1,2})[/\s-]*(\d{2,4})",
        period,
        re.IGNORECASE,
    )
    if range_match:
        start = _parse_date_tuple(*range_match.group(1, 2, 3))
        end = _parse_date_tuple(*range_match.group(4, 5, 6))
        if start and end:
            delta = (end - start).days
            if 0 < delta <= 400:
                return delta

    month_match = re.search(r"\b([A-Za-z]{3,9})\s+(\d{4})\b", period)
    if month_match:
        month = _MONTHS.get(month_match.group(1)[:3].lower())
        if month:
            year = int(month_match.group(2))
            first = date(year, month, 1)
            following = date(year + (month == 12), (month % 12) + 1, 1)
            return (following - first).days

    return None


def _parse_date_tuple(day: str, month: str, year: str):
    from datetime import date

    try:
        day_value = int(day)
        year_value = int(year)
        if year_value < 100:
            year_value += 2000
        if month.isdigit():
            month_value = int(month)
        else:
            month_value = _MONTHS.get(month[:3].lower())
        if not month_value:
            return None
        return date(year_value, month_value, day_value)
    except (ValueError, TypeError):
        return None


def describe() -> dict[str, object]:
    return {
        "reference_bands": REFERENCE_MONTHLY_KWH,
        "significant_change_threshold": SIGNIFICANT_CHANGE,
        "generated_by": "deterministic_analysis",
    }
