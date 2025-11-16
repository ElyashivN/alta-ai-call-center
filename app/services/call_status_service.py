# app/services/call_status_service.py
from typing import Optional

from sqlalchemy.orm import Session

from app.models.call import Call


def update_call_status(
    db: Session,
    provider_call_id: str,
    call_status: str,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Optional[Call]:
    """
    Update the status of a Call given the Twilio callback.

    - provider_call_id is Twilio's CallSid
    - call_status is Twilio's CallStatus ("queued", "ringing", "in-progress",
      "completed", "busy", "failed", "no-answer", "canceled", ...)
    - error_code / error_message are optional diagnostic fields.

    We **don't** rely on extra DB columns here, so this is safe even if
    Call only has `status`.
    """
    call = db.query(Call).filter_by(provider_call_id=provider_call_id).first()
    if not call:
        # No matching call; nothing to update.
        return None

    # Minimal: always update .status
    setattr(call, "status", call_status)

    # If you've already added error fields as real columns, this will
    # persist. If not, it just becomes an in-memory attribute (harmless).
    if error_code is not None:
        setattr(call, "error_code", error_code)
    if error_message is not None:
        setattr(call, "error_message", error_message)

    db.add(call)
    db.commit()
    db.refresh(call)
    return call
