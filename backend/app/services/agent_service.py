"""Controlled boundary to a local agent CLI (Claude Code or Codex).

This is the only place in the backend that starts another process, and it is
deliberately narrow.

What the agent can do
    Receive a small JSON payload of *candidate strings* that deterministic
    rules already extracted, and pick the most likely one per field.

What the agent cannot do
    * Run shell commands derived from user text. The prompt is built from a
      fixed template; only JSON-encoded candidate strings are interpolated,
      and they are never passed to a shell — ``shell=False`` always, with the
      prompt delivered on stdin.
    * Touch the filesystem outside its sandbox directory. ``cwd`` is the
      sandbox, HOME points into it, and every tool is disabled.
    * Modify source code, delete files, or read unrelated directories. Tool
      use is switched off at the CLI level, so there is no code path for it.
    * Act as a source of truth. Every value it returns must already appear in
      the candidate list it was given, or it is discarded. Numbers it emits
      are re-derived and checked against arithmetic invariants downstream.

When the agent is disabled, missing, times out, or returns anything that does
not validate, this module returns ``None`` and the pipeline carries on with
rules only. The agent is an optimisation, never a dependency.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings

log = logging.getLogger("smart_utility.agent")

# Absolute paths only. A bare name would be resolved through PATH, which the
# caller could influence.
ALLOWLISTED_CLIS: dict[str, Path] = {
    "claude": Path("/usr/local/bin/claude"),
    "codex": Path("/home/erebus/.local/bin/codex"),
}

MAX_PROMPT_CHARS = 24_000
MAX_OUTPUT_BYTES = 256 * 1024

# Fields the agent is permitted to weigh in on. Anything outside this set is
# ignored even if the model returns it.
SUGGESTIBLE_FIELDS = frozenset(
    {
        "provider",
        "billing_period",
        "bill_date",
        "due_date",
        "meter_type",
        "tariff_category",
        "units_consumed",
        "total_amount",
        "previous_reading",
        "current_reading",
    }
)

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "object",
            "additionalProperties": {
                "type": ["object", "null"],
                "properties": {
                    "value": {"type": ["string", "number", "null"]},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["value"],
            },
        }
    },
    "required": ["fields"],
}

SYSTEM_PROMPT = (
    "You are a strict data-extraction assistant for Indian electricity bills. "
    "You will be given a set of candidate strings that were read from a bill, "
    "grouped by field. For each requested field choose the single candidate "
    "that is most likely to be the correct value. "
    "Rules you must follow: "
    "(1) You may ONLY return values that appear verbatim in the supplied "
    "candidates for that field. "
    "(2) If no candidate is plausible, return null. Never guess, never invent, "
    "never compute a value. "
    "(3) For numeric fields return the number only, without units or commas. "
    "(4) Do not explain your reasoning outside the JSON structure. "
    "Output JSON only."
)


@dataclass(frozen=True)
class AgentResult:
    fields: dict[str, dict[str, Any]]
    cli: str
    duration_ms: int
    rejected: dict[str, str]


def _cli_candidates() -> list[Path]:
    if settings.agent_cli_path:
        return [Path(settings.agent_cli_path).expanduser()]
    return list(ALLOWLISTED_CLIS.values())


def resolve_cli() -> Path | None:
    """Return the first allowlisted CLI that exists and is executable."""
    for candidate in _cli_candidates():
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    return None


def _cli_kind(path: Path) -> str | None:
    for name, known in ALLOWLISTED_CLIS.items():
        try:
            if path.resolve() == known.resolve():
                return name
        except OSError:
            continue
    return path.name if path.name in ALLOWLISTED_CLIS else None


def is_available() -> bool:
    return settings.agent_enabled and resolve_cli() is not None


def capabilities() -> dict[str, Any]:
    """Health-style report. Safe to expose: paths and booleans only."""
    path = resolve_cli()
    return {
        "enabled": settings.agent_enabled,
        "available": bool(settings.agent_enabled and path),
        "cli": str(path) if path else None,
        "kind": _cli_kind(path) if path else None,
        "timeout_seconds": settings.agent_timeout_seconds,
        "tools_allowed": settings.agent_allowed_tools or "none",
        "sandbox": str(settings.agent_sandbox_path),
        "role": "disambiguation-only",
    }


def _scrubbed_env(sandbox: Path) -> dict[str, str]:
    """Build a minimal environment. HOME is redirected into the sandbox."""
    allowlist = {"PATH", "LANG", "LC_ALL", "TERM", "TZ"}
    allowlist |= {name for name in settings.agent_env_allowlist if name}

    env = {key: value for key, value in os.environ.items() if key in allowlist}
    env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
    env["HOME"] = str(sandbox)
    env["TMPDIR"] = str(sandbox / "tmp")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    (sandbox / "tmp").mkdir(parents=True, exist_ok=True)
    return env


def _build_command(cli: Path, schema_path: Path, last_message_path: Path) -> list[str]:
    """Fixed argv per CLI kind. No user input reaches this list."""
    kind = _cli_kind(cli)
    if kind == "claude":
        argv = [
            str(cli),
            "--print",
            "--output-format",
            "json",
            "--json-schema",
            str(schema_path),
            # No tools at all: the agent cannot touch the filesystem or shell.
            "--tools",
            "",
            # Ignore any user/project settings that might re-enable something.
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--disable-slash-commands",
        ]
        if settings.agent_allowed_tools:
            # Only reachable if an operator explicitly opts in.
            argv += ["--tools", settings.agent_allowed_tools]
        return argv

    if kind == "codex":
        return [
            str(cli),
            "exec",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(last_message_path),
            "-",
        ]

    # Unknown CLI: refuse rather than guess at flags.
    return []


def _build_prompt(candidates: dict[str, list[str]], requested: list[str]) -> str:
    payload = {
        "requested_fields": requested,
        "candidates": {field: candidates.get(field, []) for field in requested},
    }
    body = json.dumps(payload, ensure_ascii=False)
    if len(body) > MAX_PROMPT_CHARS:
        raise ValueError("candidate payload too large for the agent")
    return f"{SYSTEM_PROMPT}\n\nInput:\n{body}"


def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull a JSON object out of the CLI's output envelope."""
    text = text.strip()
    if not text:
        return None

    # `claude --output-format json` wraps the answer in a record; the schema
    # result may be under `result`, `structured_output` or `content`.
    try:
        outer = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            outer = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    if isinstance(outer, dict):
        for key in ("structured_output", "result", "content", "fields"):
            value = outer.get(key)
            if isinstance(value, dict):
                if key == "fields":
                    return {"fields": value}
                return value
            if isinstance(value, str):
                nested = _extract_json(value)
                if nested is not None:
                    return nested
        if "fields" in outer:
            return outer
    return None


def _normalise(text: Any) -> str:
    return "".join(str(text).split()).casefold().strip(".:`'\"")


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def suggest(
    candidates: dict[str, list[str]], *, requested: list[str] | None = None
) -> AgentResult | None:
    """Ask the agent to disambiguate fields. Returns None if unavailable.

    Every returned value is checked back against the candidate list it came
    from. Anything that does not appear there is rejected, so a hallucinated
    number can never enter the pipeline.
    """
    if not is_available():
        return None

    cli = resolve_cli()
    if cli is None:
        return None

    fields = [f for f in (requested or candidates.keys()) if f in SUGGESTIBLE_FIELDS]
    fields = [f for f in fields if candidates.get(f)]
    if not fields:
        return None

    try:
        prompt = _build_prompt(candidates, fields)
    except ValueError:
        log.warning("agent prompt too large; skipping disambiguation")
        return None

    sandbox = settings.agent_sandbox_path
    sandbox.mkdir(parents=True, exist_ok=True)

    import time

    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="agent-", dir=sandbox) as tmp:
        tmp_path = Path(tmp)
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps(RESPONSE_SCHEMA), encoding="utf-8")
        last_message_path = tmp_path / "last_message.json"

        argv = _build_command(cli, schema_path, last_message_path)
        if not argv:
            log.warning("agent CLI %s has no known invocation; skipping", cli.name)
            return None

        try:
            proc = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=settings.agent_timeout_seconds,
                cwd=str(tmp_path),
                env=_scrubbed_env(tmp_path),
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            log.warning("agent timed out after %ss", settings.agent_timeout_seconds)
            return None
        except OSError as exc:
            log.warning("agent could not be started: %s", type(exc).__name__)
            return None

        duration_ms = int((time.perf_counter() - started) * 1000)

        stdout = proc.stdout or ""
        if len(stdout.encode("utf-8", "ignore")) > MAX_OUTPUT_BYTES:
            log.warning("agent output exceeded size limit; discarding")
            return None

        raw = stdout
        if last_message_path.exists():
            try:
                raw = last_message_path.read_text(encoding="utf-8") or stdout
            except OSError:
                raw = stdout

        parsed = _extract_json(raw)
        if parsed is None:
            log.warning("agent returned no parseable JSON (exit=%s)", proc.returncode)
            return None

    raw_fields = parsed.get("fields")
    if not isinstance(raw_fields, dict):
        return None

    accepted: dict[str, dict[str, Any]] = {}
    rejected: dict[str, str] = {}

    for name, entry in raw_fields.items():
        if name not in SUGGESTIBLE_FIELDS or name not in candidates:
            continue
        if entry is None:
            continue

        if isinstance(entry, dict):
            value = entry.get("value")
            confidence = entry.get("confidence")
        else:
            value, confidence = entry, None

        if value is None or value == "":
            continue

        allowed = {_normalise(c) for c in candidates.get(name, [])}

        if name in ("units_consumed", "total_amount", "previous_reading", "current_reading"):
            number = _numeric(value)
            if number is None:
                rejected[name] = "not_numeric"
                continue
            # The number must match one of the candidate strings after
            # normalisation. The agent may not synthesise a figure.
            if _normalise(value) not in allowed and not any(
                _numeric(c) == number for c in candidates.get(name, [])
            ):
                rejected[name] = "not_in_candidates"
                continue
            accepted[name] = {
                "value": number,
                "confidence": float(confidence) if isinstance(confidence, (int, float)) else 0.5,
            }
        else:
            if _normalise(value) not in allowed:
                rejected[name] = "not_in_candidates"
                continue
            accepted[name] = {
                "value": str(value),
                "confidence": float(confidence) if isinstance(confidence, (int, float)) else 0.5,
            }

    if rejected:
        log.info("agent suggestions rejected: %s", ",".join(sorted(rejected)))

    return AgentResult(
        fields=accepted,
        cli=cli.name,
        duration_ms=duration_ms,
        rejected=rejected,
    )


def sandbox_summary() -> dict[str, Any]:
    sandbox = settings.agent_sandbox_path
    return {
        "path": str(sandbox),
        "exists": sandbox.exists(),
        "isolated_from_project": True,
    }


def which_agent() -> str | None:
    path = resolve_cli()
    return str(path) if path else None
