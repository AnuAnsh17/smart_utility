"""Optional weather context for the forecast.

Weather is **off by default** and the pipeline treats a missing weather
response as ordinary, not as an error. When it is unavailable — disabled, not
configured, offline, timed out, or returning junk — this module returns a
``CanonicalWeather`` with ``status="unavailable"`` and a note explaining which
of those it was. The dashboard renders the section as unavailable and carries
on. Nothing in the analysis path depends on this module succeeding.

What leaves the machine when weather is enabled is a coordinate pair the
operator set in configuration. No address, no consumer number, no bill text.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.schemas import CanonicalWeather

log = logging.getLogger("smart_utility.weather")

IMPACT_HIGH_C = 35.0
IMPACT_MODERATE_C = 30.0


def _unavailable(note: str, *, location: str = "Unknown") -> CanonicalWeather:
    return CanonicalWeather(
        status="unavailable",
        location=location,
        condition="Unavailable",
        impact_level="Low",
        impact_summary="Weather context is not available for this analysis.",
        detail_note=note,
    )


def _impact(temp_c: float) -> tuple[str, str]:
    if temp_c >= IMPACT_HIGH_C:
        return (
            "High",
            "Sustained high temperatures typically push cooling load up, so "
            "consumption may run above the recent average.",
        )
    if temp_c >= IMPACT_MODERATE_C:
        return (
            "Moderate",
            "Warm conditions usually mean some additional cooling demand.",
        )
    return (
        "Low",
        "Current temperatures are unlikely to move household cooling demand "
        "much in either direction.",
    )


def fetch(*, location_label: str | None = None) -> CanonicalWeather:
    """Return today's weather context, or an honest "unavailable"."""
    label = (location_label or "").strip() or "Configured location"

    if not settings.weather_enabled:
        return _unavailable(
            "Weather enrichment is disabled. Set WEATHER_ENABLED=true and "
            "configure coordinates to include local weather context.",
            location=label,
        )

    if settings.weather_latitude is None or settings.weather_longitude is None:
        return _unavailable(
            "Weather enrichment is enabled but no coordinates are configured "
            "(WEATHER_LATITUDE / WEATHER_LONGITUDE).",
            location=label,
        )

    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx is a declared dependency
        return _unavailable("HTTP client is not installed.", location=label)

    url = f"{settings.weather_api_base.rstrip('/')}/forecast"
    params = {
        "latitude": settings.weather_latitude,
        "longitude": settings.weather_longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code",
        "timezone": "auto",
    }

    try:
        with httpx.Client(timeout=settings.weather_timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        # Degrade, do not fail. A forecast without weather is still a forecast.
        log.info("weather unavailable (%s)", type(exc).__name__)
        return _unavailable(
            f"Weather service could not be reached ({type(exc).__name__}).",
            location=label,
        )

    current = payload.get("current") or {}
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")

    if temp is None:
        return _unavailable(
            "Weather service returned no temperature reading.", location=label
        )

    try:
        temp_c = float(temp)
    except (TypeError, ValueError):
        return _unavailable(
            "Weather service returned an unusable temperature value.",
            location=label,
        )

    level, summary = _impact(temp_c)
    humidity_value = None
    if humidity is not None:
        try:
            humidity_value = float(humidity)
        except (TypeError, ValueError):
            humidity_value = None

    return CanonicalWeather(
        status="available",
        location=label,
        temp_c=round(temp_c, 1),
        condition=_condition_label(current.get("weather_code")),
        humidity_percent=humidity_value,
        impact_level=level,
        impact_summary=summary,
        detail_note="Current conditions from the configured weather provider.",
    )


# WMO weather interpretation codes, as published by the provider.
_WMO = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _condition_label(code: object) -> str:
    if code is None:
        return "Unavailable"
    try:
        return _WMO.get(int(code), "Unknown conditions")
    except (TypeError, ValueError):
        return "Unavailable"


def describe() -> dict[str, object]:
    return {
        "enabled": settings.weather_enabled,
        "configured": (
            settings.weather_latitude is not None
            and settings.weather_longitude is not None
        ),
        "provider": settings.weather_api_base,
        "default_status": "unavailable",
    }
