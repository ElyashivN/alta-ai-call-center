# app/services/constraints_nlp_service.py
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo

from app.schemas.constraints import ParsedConstraints, HardConstraints, SoftConstraints

try:
    # OpenAI Python SDK (v1+)
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - library not installed in test env
    OpenAI = None


# ---------- Heuristic helpers (used as fallback and for tests) ----------

_BASE_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DAY_CODE = {
    "mon": "MON",
    "tue": "TUE",
    "wed": "WED",
    "thu": "THU",
    "fri": "FRI",
    "sat": "SAT",
    "sun": "SUN",
}
_FULL_NAME_TO_BASE = {
    "monday": "mon",
    "tuesday": "tue",
    "wednesday": "wed",
    "thursday": "thu",
    "friday": "fri",
    "saturday": "sat",
    "sunday": "sun",
}


def _extract_preferred_days(text_lower: str) -> List[str]:
    """
    Handle:
      - explicit days like "Tuesday", "Thu"
      - ranges like "Mon-Wed", "Tue–Thu" (inclusive)
    """
    normalized = (
        text_lower.replace("–", "-")
        .replace("—", "-")
        .replace(" to ", "-")
    )

    found: set[str] = set()

    # 1) Ranges like "tue-thu"
    for i, start_base in enumerate(_BASE_DAYS):
        for j, end_base in enumerate(_BASE_DAYS):
            if i > j:
                continue
            pattern = f"{start_base}-{end_base}"
            if pattern in normalized:
                for k in range(i, j + 1):
                    base = _BASE_DAYS[k]
                    found.add(_DAY_CODE[base])

    # 2) Full names: "tuesday", "friday"
    for full_name, base in _FULL_NAME_TO_BASE.items():
        if full_name in normalized:
            found.add(_DAY_CODE[base])

    # 3) Abbreviations "mon", "tue", etc.
    for base in _BASE_DAYS:
        if base in normalized:
            found.add(_DAY_CODE[base])

    return sorted(found) if found else []


def _extract_preferred_time_of_day(text_lower: str) -> List[str]:
    tod: list[str] = []
    if "morning" in text_lower:
        tod.append("MORNING")
    if "afternoon" in text_lower:
        tod.append("AFTERNOON")
    if "evening" in text_lower or "night" in text_lower:
        tod.append("EVENING")
    return tod


def _heuristic_parse(
    instruction: str,
    now: datetime,
    timezone: str,
) -> ParsedConstraints:
    """
    The deterministic behavior used in tests.
    """
    tz = ZoneInfo(timezone)
    now_tz = now.astimezone(tz)

    # Default: next 7 days
    window_start = now_tz
    window_end = now_tz + timedelta(days=7)

    text_lower = instruction.lower()

    if "next two weeks" in text_lower:
        window_end = now_tz + timedelta(days=14)

    preferred_days = _extract_preferred_days(text_lower)
    preferred_tod = _extract_preferred_time_of_day(text_lower)

    hc = HardConstraints(
        window_start=window_start,
        window_end=window_end,
        timezone=timezone,
    )
    sc = SoftConstraints(
        preferred_days_of_week=preferred_days or None,
        preferred_time_of_day=preferred_tod or None,
    )

    return ParsedConstraints(hard_constraints=hc, soft_constraints=sc)


# ---------- Public entry point with optional OpenAI ----------


def parse_natural_language_constraints(
    instruction: str,
    now: datetime,
    timezone: str,
) -> ParsedConstraints:
    """
    In production:
      - try OpenAI to parse complex instructions into JSON
      - validate & coerce JSON into ParsedConstraints
    In tests / offline:
      - fall back to a deterministic heuristic.
    """
    # Try OpenAI first (only if SDK + API key present)
    if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            system_msg = (
                "You convert natural-language scheduling constraints into JSON. "
                "Return ONLY valid JSON, with keys: "
                "{ "
                "  'hard_constraints': {"
                "    'window_start': ISO8601 string,"
                "    'window_end': ISO8601 string,"
                "    'timezone': string"
                "  },"
                "  'soft_constraints': {"
                "    'preferred_days_of_week': [ 'MON'|'TUE'|... ],"
                "    'preferred_time_of_day': [ 'MORNING'|'AFTERNOON'|'EVENING' ]"
                "  }"
                "}"
            )

            user_msg = (
                f"Instruction: {instruction!r}\n"
                f"Now (UTC): {now.isoformat()}\n"
                f"Lead timezone: {timezone}\n"
                "Infer a reasonable window_start/window_end around 'now' if needed. "
                "If something is missing, make a reasonable assumption."
            )

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=400,
            )
            raw = resp.choices[0].message.content or "{}"
            parsed = json.loads(raw)

            hc_data = parsed.get("hard_constraints") or {}
            sc_data = parsed.get("soft_constraints") or {}

            ws_str = hc_data.get("window_start")
            we_str = hc_data.get("window_end")

            if not ws_str or not we_str:
                # If the model didn't give a proper window, fall back
                return _heuristic_parse(instruction, now, timezone)

            ws = datetime.fromisoformat(ws_str)
            we = datetime.fromisoformat(we_str)
            tz_str = hc_data.get("timezone") or timezone

            hc = HardConstraints(
                window_start=ws,
                window_end=we,
                timezone=tz_str,
            )
            sc = SoftConstraints(
                preferred_days_of_week=sc_data.get("preferred_days_of_week"),
                preferred_time_of_day=sc_data.get("preferred_time_of_day"),
            )

            return ParsedConstraints(hard_constraints=hc, soft_constraints=sc)
        except Exception:
            # Any error → fallback to deterministic behavior
            pass

    # Fallback path (what your tests rely on)
    return _heuristic_parse(instruction, now, timezone)
