"""Tariff arithmetic: consumption (kWh) in, rupees out.

Money is never produced by a language model in this system. Every rupee figure
the dashboard shows comes from this module, which is ordinary deterministic
arithmetic over a declared slab table. An LLM may only ever *describe* a number
that was computed here.

The default schedule is an indicative domestic slab table for an Indian
distribution utility. Real tariffs differ by state, category and financial
year, so the schedule is:

* **declared** — the slabs are data, not hidden in code paths;
* **named in the output** so the UI can label the number as an estimate;
* **overridable** per deployment if a real DISCOM schedule is supplied.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("smart_utility.tariff")


@dataclass(frozen=True)
class Slab:
    """Energy charge band. ``up_to`` is the upper bound in kWh; use ``None``
    for the final, open-ended slab."""

    up_to: float | None
    rate: float


@dataclass(frozen=True)
class TariffSchedule:
    name: str
    slabs: tuple[Slab, ...]
    fixed_charge: float = 0.0
    duty_percent: float = 0.0
    currency_symbol: str = "₹"
    indicative: bool = True

    def band(self, kwh: float) -> int | None:
        """Which slab the given monthly consumption falls into."""
        if kwh <= 0:
            return None
        for index, slab in enumerate(self.slabs, start=1):
            if slab.up_to is None or kwh <= slab.up_to:
                return index
        return len(self.slabs)


@dataclass
class TariffEstimate:
    kwh: float
    energy_charge: float
    fixed_charge: float
    duty: float
    total: float
    effective_rate: float
    schedule_name: str
    currency_symbol: str = "₹"
    indicative: bool = True
    band: int | None = None
    breakdown: list[dict[str, float | str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def total_min(self) -> float:
        return round(self.total * 0.92, 2)

    @property
    def total_max(self) -> float:
        return round(self.total * 1.12, 2)


# Indicative domestic schedule. Progressive slabs, small fixed charge, and a
# duty levied on the energy charge — the common shape of an Indian LT-I bill.
DOMESTIC_SCHEDULE = TariffSchedule(
    name="Indicative domestic (LT-I)",
    slabs=(
        Slab(up_to=100, rate=3.50),
        Slab(up_to=200, rate=5.20),
        Slab(up_to=500, rate=7.10),
        Slab(up_to=None, rate=8.90),
    ),
    fixed_charge=60.0,
    duty_percent=6.0,
)

COMMERCIAL_SCHEDULE = TariffSchedule(
    name="Indicative commercial (LT-II)",
    slabs=(
        Slab(up_to=200, rate=7.90),
        Slab(up_to=500, rate=9.40),
        Slab(up_to=None, rate=10.80),
    ),
    fixed_charge=120.0,
    duty_percent=8.0,
)

AGRICULTURAL_SCHEDULE = TariffSchedule(
    name="Indicative agricultural (LT-V)",
    slabs=(Slab(up_to=None, rate=4.30),),
    fixed_charge=40.0,
    duty_percent=0.0,
)

SCHEDULES: dict[str, TariffSchedule] = {
    "residential": DOMESTIC_SCHEDULE,
    "domestic": DOMESTIC_SCHEDULE,
    "commercial": COMMERCIAL_SCHEDULE,
    "industrial": COMMERCIAL_SCHEDULE,
    "agricultural": AGRICULTURAL_SCHEDULE,
    "agriculture": AGRICULTURAL_SCHEDULE,
}


def schedule_for(category: str | None) -> TariffSchedule:
    if not category:
        return DOMESTIC_SCHEDULE
    lowered = category.lower()
    for key, schedule in SCHEDULES.items():
        if key in lowered:
            return schedule
    return DOMESTIC_SCHEDULE


def estimate(kwh: float, category: str | None = None) -> TariffEstimate:
    """Price a monthly consumption figure against the resolved schedule.

    Progressive bands are charged cumulatively: the first 100 units at the
    first rate, the next 100 at the second, and so on. That is how the slab is
    actually billed, and it is why a naive ``kwh * top_rate`` overestimates.
    """
    schedule = schedule_for(category)
    notes: list[str] = []

    if kwh is None or kwh <= 0:
        return TariffEstimate(
            kwh=float(kwh or 0.0),
            energy_charge=0.0,
            fixed_charge=0.0,
            duty=0.0,
            total=0.0,
            effective_rate=0.0,
            schedule_name=schedule.name,
            currency_symbol=schedule.currency_symbol,
            indicative=schedule.indicative,
            notes=["no consumption figure available; nothing to price"],
        )

    energy = 0.0
    remaining = float(kwh)
    lower = 0.0
    breakdown: list[dict[str, float | str]] = []

    for slab in schedule.slabs:
        if remaining <= 0:
            break
        width = remaining if slab.up_to is None else min(remaining, slab.up_to - lower)
        if width <= 0:
            continue
        charge = width * slab.rate
        energy += charge
        breakdown.append(
            {
                "slab": (
                    f"{lower:g}-{slab.up_to:g}" if slab.up_to is not None
                    else f"{lower:g}+"
                ),
                "units": round(width, 2),
                "rate": slab.rate,
                "charge": round(charge, 2),
            }
        )
        remaining -= width
        lower = slab.up_to if slab.up_to is not None else lower + width

    duty = energy * (schedule.duty_percent / 100.0)
    total = energy + schedule.fixed_charge + duty

    if schedule.indicative:
        notes.append(
            f"{schedule.name} is an indicative schedule, not your utility's "
            "published tariff. Treat the amount as an estimate."
        )

    return TariffEstimate(
        kwh=round(float(kwh), 2),
        energy_charge=round(energy, 2),
        fixed_charge=round(schedule.fixed_charge, 2),
        duty=round(duty, 2),
        total=round(total, 2),
        effective_rate=round(total / float(kwh), 3),
        schedule_name=schedule.name,
        currency_symbol=schedule.currency_symbol,
        indicative=schedule.indicative,
        band=schedule.band(float(kwh)),
        breakdown=breakdown,
        notes=notes,
    )


def implied_rate(amount: float | None, kwh: float | None) -> float | None:
    """What the user was actually charged per unit, from the bill itself.

    Preferred over the schedule wherever both figures exist, because it is
    measured rather than modelled.
    """
    if not amount or not kwh or kwh <= 0:
        return None
    return round(amount / kwh, 3)


def describe() -> dict[str, object]:
    return {
        "schedules": {
            name: {
                "slabs": [
                    {"up_to": s.up_to, "rate": s.rate} for s in schedule.slabs
                ],
                "fixed_charge": schedule.fixed_charge,
                "duty_percent": schedule.duty_percent,
            }
            for name, schedule in SCHEDULES.items()
        },
        "indicative": True,
    }
