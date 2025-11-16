# app/services/call_script_service.py
from __future__ import annotations

import os

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None


_BASE_SCRIPT = (
    "Hi, this is Elyashiv, calling to schedule your meeting. "
    "Please say one time that works for you in the requested window, "
    "or press 1 for the earliest available time, "
    "2 for a later time in the window, and then wait."
)


def generate_call_script(meeting_title: str | None = None) -> str:
    """
    Returns a short script for the IVR to read.

    - If OpenAI is not configured, we return a fixed script (exactly what tests expect).
    - If OpenAI is configured, we let the model lightly rewrite / personalize the script.
    """
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return _BASE_SCRIPT

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        context_title = meeting_title or "the upcoming meeting"

        system_msg = (
            "You write short, friendly outbound call scripts for an AI voice bot. "
            "Output only what the bot should say, in plain text, no XML."
        )
        user_msg = (
            "Write a single short paragraph inviting the lead to share their availability "
            f"for {context_title}. Mention that they can either say a time that works for "
            "them or press 1 for the earliest time and 2 for a later time in the window."
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=200,
        )
        script = (resp.choices[0].message.content or "").strip()

        # Guardrail: never return empty; keep base text as a backup
        return script or _BASE_SCRIPT
    except Exception:
        return _BASE_SCRIPT
