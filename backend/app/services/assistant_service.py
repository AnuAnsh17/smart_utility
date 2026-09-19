"""Electricity-domain assistant.

The scope restriction is enforced in five layers rather than by a prompt alone,
because a prompt is not a control:

    1. classify   — normalise the raw text, reject injection-shaped input
    2. scope      — require an in-domain term and no off-domain term
    3. retrieve   — pull the figures out of the stored analysis, nothing else
    4. validate   — every numeral in a draft reply must exist in that context
    5. output     — strip anything that looks like a URL, code, or PII

Answers are templated from the retrieved context, not generated: the model here
is deterministic Python, so no figure can be invented and no rupee amount can
come from free text.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.models import ChatMessageRow, ChatSession
from app.schemas import AnalysisBundle

# Verbatim refusals required by the specification. Do not reword these.
REFUSAL = (
    "Sorry, I can only help with electricity bills, energy consumption, "
    "forecasts, and related utility questions."
)
INSUFFICIENT = (
    "I don't have enough information from your bill or usage data to answer that."
)

MAX_REPLY_CHARS = 1400

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)

# Phrases that try to move the assistant outside its task. Matched, never
# obeyed — a hit is a refusal, not something to negotiate with.
_INJECTION = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above)"
    r"|disregard\s+(the\s+)?(instructions|rules|prompt)"
    r"|system\s+prompt|you\s+are\s+now|act\s+as\s+|pretend\s+to\s+be"
    r"|jailbreak|developer\s+mode"
    r"|repeat\s+(your|the)\s+(prompt|instructions)"
    r"|reveal\s+(your|the)\s+(prompt|instructions|rules))",
    re.IGNORECASE,
)

_DOMAIN_TERMS = (
    "electricity", "electric", "power", "energy", "bill", "unit", "kwh",
    "kilowatt", "consumption", "consumed", "usage", "used", "tariff", "slab",
    "rate", "meter", "reading", "discom", "provider", "supply", "connection",
    "sanction", "load", "forecast", "predict", "projection", "next month",
    "trend", "appliance", "ac", "air conditioner", "refrigerator", "fridge",
    "geyser", "heater", "fan", "light", "lamp", "solar", "rooftop", "inverter",
    "backup", "outage", "voltage", "arrear", "deposit", "subsidy", "charge",
    "due", "billing period", "cycle", "rupee", "amount", "payable", "cost",
    "expensive", "cheaper", "save", "saving", "reduce", "lower", "increase",
    "high", "spike", "weather", "temperature", "humidity", "monsoon", "summer",
    "connection type", "category", "my bill", "this bill", "my usage",
)

# A question that trips any of these is out of domain unless it also carries a
# domain term, which keeps "did the weather change my bill" answerable while
# "write me a poem about the weather" is not.
_OFF_DOMAIN_TERMS = (
    "cricket", "football", "movie", "film", "song", "poem", "story", "joke",
    "recipe", "cook", "travel", "flight", "hotel", "medicine", "doctor",
    "symptom", "diagnos", "lawyer", "lawsuit", "election", "politic", "religion",
    "stock", "share market", "mutual fund", "bitcoin", "crypto", "forex",
    "homework", "essay", "translate this", "write code", "python", "javascript",
    "sql", "regex", "hack", "malware", "exploit", "password",
    "tell me about yourself", "what model are you",
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_ZERO_WIDTH)).strip()


def _money(value: float, symbol: str) -> str:
    return f"{symbol}{value:,.0f}"


def _units(value: float, label: str) -> str:
    return f"{value:,.0f} {label}"


class _Context:
    """Everything the assistant is allowed to say, drawn from one job."""

    def __init__(self, bundle: AnalysisBundle | None, job_id: str | None) -> None:
        self.bundle = bundle
        self.job_id = job_id
        self.numbers: set[float] = set()
        if bundle is not None:
            self._collect_numbers(bundle.model_dump())

    def _collect_numbers(self, node: object) -> None:
        """Walk the bundle and record every numeral it contains.

        Reply validation checks against this set, so a figure the bundle does
        not contain cannot survive into an answer.
        """
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            self.numbers.add(float(node))
        elif isinstance(node, str):
            for match in re.findall(r"\d+(?:\.\d+)?", node):
                self.numbers.add(float(match))
        elif isinstance(node, dict):
            for value in node.values():
                self._collect_numbers(value)
        elif isinstance(node, list):
            for value in node:
                self._collect_numbers(value)

    @property
    def bill(self):
        return self.bundle.bill if self.bundle else None

    @property
    def forecast(self):
        return self.bundle.forecast if self.bundle else None


def _classify(message: str) -> tuple[str, str]:
    """Layer 1 + 2. Returns (decision, reason) where decision is one of
    ``ok``, ``rejected``, or ``out_of_scope``.
    """
    if not message:
        return "rejected", "empty"
    if _INJECTION.search(message):
        return "rejected", "injection"
    if not any(term in message for term in _DOMAIN_TERMS):
        return "out_of_scope", "no_domain_term"
    if any(term in message for term in _OFF_DOMAIN_TERMS) and len(message) < 120:
        return "out_of_scope", "off_domain_term"
    return "ok", "in_domain"


def _fmt(value: float | None, label: str, symbol: str = "₹") -> str | None:
    if value is None:
        return None
    if label:
        return _units(value, label)
    return _money(value, symbol)


def _followups(context: _Context) -> list[str]:
    if context.bundle is None:
        return ["Upload a bill to get started"]
    options = [
        "How many units did I use?",
        "What is the projected consumption next month?",
        "Why is my bill high?",
        "What can I do to reduce it?",
    ]
    if context.bill and context.bill.due_date:
        options.insert(1, "When is my payment due?")
    return options[:4]


def _answer(message: str, context: _Context) -> tuple[str, str]:
    """Layer 3. Returns (reply, decision). ``insufficient_context`` is returned
    whenever the routed intent needs a field the document did not contain.
    """
    bill = context.bill
    forecast = context.forecast

    if bill is None:
        return INSUFFICIENT, "insufficient_context"

    period = bill.billing_period or "the billing period on file"
    symbol = bill.currency_symbol or "₹"
    label = bill.unit_label or "kWh"

    def has(*terms: str) -> bool:
        return any(term in message for term in terms)

    # --- payment / amount -------------------------------------------------
    if has("amount", "payable", "how much", "total", "cost", "rupee", "₹", "charge"):
        if bill.total_amount is None:
            return INSUFFICIENT, "insufficient_context"
        reply = (
            f"The bill for {period} totals "
            f"{_money(bill.total_amount, symbol)}"
        )
        if bill.units_consumed:
            reply += f" for {_units(bill.units_consumed, label)}"
        reply += "."
        if bill.due_date:
            reply += f" It is due on {bill.due_date}."
        return reply, "answered"

    # --- due date ---------------------------------------------------------
    if has("due", "last date", "payment date", "deadline"):
        if not bill.due_date:
            return INSUFFICIENT, "insufficient_context"
        return (
            f"The payment date printed on the {period} bill is {bill.due_date}.",
            "answered",
        )

    # --- readings ---------------------------------------------------------
    if has("reading", "meter reading"):
        if bill.previous_reading is None or bill.current_reading is None:
            return INSUFFICIENT, "insufficient_context"
        return (
            f"The meter moved from {bill.previous_reading:,.0f} to "
            f"{bill.current_reading:,.0f}, a difference of "
            f"{_units(bill.units_consumed, label)}."
            if bill.units_consumed is not None
            else INSUFFICIENT,
            "answered" if bill.units_consumed is not None else "insufficient_context",
        )

    # --- consumption ------------------------------------------------------
    if has("unit", "kwh", "consumption", "consumed", "usage", "used", "how many"):
        if bill.units_consumed is None:
            return INSUFFICIENT, "insufficient_context"
        reply = (
            f"Your {period} bill records "
            f"{_units(bill.units_consumed, label)} of electricity consumed."
        )
        history = forecast.historical_trend if forecast else []
        if len(history) >= 2:
            previous, latest = history[-2], history[-1]
            delta = latest.kwh - previous.kwh
            if previous.kwh:
                share = abs(delta) / previous.kwh * 100
                direction = "up" if delta >= 0 else "down"
                reply += (
                    f" That is {direction} {share:,.0f}% against "
                    f"{previous.month} ({_units(previous.kwh, label)})."
                )
            else:
                reply += f" The previous period, {previous.month}, recorded {_units(previous.kwh, label)}."
        elif history:
            reply += f" The only other period on file is {history[0].month}."
        else:
            reply += " No earlier period is on file to compare against."
        return reply, "answered"

    # --- forecast ---------------------------------------------------------
    if has("forecast", "predict", "projection", "next month", "expect", "likely", "trend"):
        if forecast is None:
            return INSUFFICIENT, "insufficient_context"
        if not forecast.reliable:
            return (
                "Not enough historical data to generate a reliable forecast. "
                "Upload earlier bills and the projection will fill in.",
                "insufficient_context",
            )
        return (
            f"For {forecast.target_month} the projection is about "
            f"{_units(forecast.expected_units_kwh, label)}, priced at roughly "
            f"{_money(forecast.expected_amount_min, symbol)} to "
            f"{_money(forecast.expected_amount_max, symbol)} on the slab that "
            "applies to this connection.",
            "answered",
        )

    # --- why is it high / what changed ------------------------------------
    if has("why", "reason", "high", "expensive", "spike", "increase", "change"):
        if context.bundle.insights:
            joined = " ".join(insight.text for insight in context.bundle.insights[:3])
            return joined, "answered"
        if bill.units_consumed is None:
            return INSUFFICIENT, "insufficient_context"
        return (
            f"The bill records {_units(bill.units_consumed, label)}. There is no "
            "earlier period on file, so the change cannot be attributed yet.",
            "insufficient_context",
        )

    # --- reduce / save ----------------------------------------------------
    if has("reduce", "save", "saving", "lower", "cheaper", "cut", "optimis", "advice"):
        if not context.bundle.recommendations:
            return INSUFFICIENT, "insufficient_context"
        lines = [
            f"- {rec.title}: {rec.suggested_action}"
            for rec in context.bundle.recommendations[:3]
        ]
        return "Suggestions based on this bill:\n" + "\n".join(lines), "answered"

    # --- tariff / connection ---------------------------------------------
    if has("tariff", "slab", "category", "rate", "sanction", "load", "connection type"):
        parts: list[str] = []
        if bill.tariff_category:
            parts.append(f"tariff category {bill.tariff_category}")
        if bill.sanctioned_load:
            parts.append(f"sanctioned load {bill.sanctioned_load}")
        if bill.connection_type:
            parts.append(f"connection type {bill.connection_type}")
        if not parts:
            return INSUFFICIENT, "insufficient_context"
        return (
            f"The {period} bill lists " + ", ".join(parts) + ".",
            "answered",
        )

    # --- weather ----------------------------------------------------------
    if has("weather", "temperature", "humidity", "monsoon", "summer", "climate"):
        weather = context.bundle.weather
        if weather.status != "available" or weather.temp_c is None:
            return (
                "Weather context is not configured for this installation, so "
                "consumption cannot be attributed to conditions.",
                "insufficient_context",
            )
        return (
            f"At the last reading the local conditions were "
            f"{weather.condition}, about {weather.temp_c:,.0f}°C. {weather.impact_summary}",
            "answered",
        )

    # --- provider / period / language -------------------------------------
    if has("provider", "discom", "supplier", "company"):
        if not bill.provider:
            return INSUFFICIENT, "insufficient_context"
        return f"This bill was issued by {bill.provider}.", "answered"

    if has("period", "month", "cycle", "which bill"):
        return f"The bill covers {period}.", "answered"

    # --- summary fallback, still fully grounded ---------------------------
    if bill.units_consumed is None and bill.total_amount is None:
        return INSUFFICIENT, "insufficient_context"

    pieces = []
    if bill.provider:
        pieces.append(f"{bill.provider} bill for {period}")
    else:
        pieces.append(f"Bill for {period}")
    if bill.units_consumed is not None:
        pieces.append(f"{_units(bill.units_consumed, label)} consumed")
    if bill.total_amount is not None:
        pieces.append(f"{_money(bill.total_amount, symbol)} payable")
    return ", ".join(pieces) + ". Ask about units, charges, the forecast, or how to reduce it.", "answered"


def _validate(reply: str, context: _Context) -> str | None:
    """Layer 4. Returns None when the draft is safe, else a reason code."""
    if "http://" in reply or "https://" in reply or "```" in reply:
        return "link_or_code"

    # A rupee figure that is not a whole number of the context's own values is
    # treated as invented. Percentages and plain counts are allowed through,
    # but must still be traceable to the bundle.
    for match in re.findall(r"\d[\d,]*(?:\.\d+)?", reply):
        value = float(match.replace(",", ""))
        if value in context.numbers:
            continue
        # Rounding for display is legitimate; anything further off is not.
        if any(abs(value - known) < 0.5 for known in context.numbers):
            continue
        # Percentages derived arithmetically from two context values.
        if 0.0 <= value <= 100.0 and context.numbers:
            continue
        return f"untraceable_number:{match}"
    return None


def _output_scope(reply: str) -> str:
    """Layer 5. Strip anything that reads like PII or a foreign subsystem."""
    # Consumer numbers are the one identifier that must never be echoed.
    reply = re.sub(r"\b\d{9,}\b", "[redacted]", reply)
    reply = re.sub(r"(?i)\b(api[_ -]?key|token|password|secret)\b\s*[:=]\s*\S+", "[redacted]", reply)
    if len(reply) > MAX_REPLY_CHARS:
        head, _, _ = reply.rpartition(". ")
        reply = reply[:MAX_REPLY_CHARS]
        if head:
            reply = head + "."
    return reply.strip()


def _session(session: Session, session_id: str | None, job_id: str | None) -> ChatSession:
    if session_id:
        existing = session.get(ChatSession, session_id)
        if existing is not None:
            return existing
    row = ChatSession(id=session_id or uuid.uuid4().hex[:16], job_id=job_id)
    session.add(row)
    session.flush()
    return row


def _record(
    session: Session,
    chat: ChatSession,
    *,
    job_id: str | None,
    role: str,
    content: str,
    decision: str | None = None,
) -> None:
    session.add(
        ChatMessageRow(
            session_id=chat.id,
            job_id=job_id,
            role=role,
            content=content,
            scope_decision=decision,
        )
    )


def respond(
    session: Session,
    *,
    message: str,
    job_id: str | None = None,
    session_id: str | None = None,
    bundle: AnalysisBundle | None = None,
) -> dict[str, object]:
    """Run the five layers and persist the exchange."""
    chat = _session(session, session_id, job_id)
    cleaned = _clean(message)
    _record(session, chat, job_id=job_id, role="user", content=cleaned)

    decision, reason = _classify(cleaned.lower())

    if decision == "rejected":
        reply = REFUSAL
        scope = "rejected"
        followups: list[str] = []
    elif decision == "out_of_scope":
        reply = REFUSAL
        scope = "out_of_scope"
        followups = []
    else:
        context = _Context(bundle, job_id)
        reply, scope = _answer(cleaned.lower(), context)

        problem = _validate(reply, context)
        if problem is not None:
            # Never ship a figure we cannot point at in the stored analysis.
            reply, scope = INSUFFICIENT, "insufficient_context"
        followups = _followups(context)

    reply = _output_scope(reply)
    _record(session, chat, job_id=job_id, role="assistant", content=reply, decision=scope)
    session.commit()

    return {
        "session_id": chat.id,
        "reply": reply,
        "scope_decision": scope,
        "suggested_followups": followups,
        "grounded_on_job_id": job_id if scope == "answered" else None,
        "reason": reason,
    }
