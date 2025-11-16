# app/routers/twilio_status.py
from typing import Optional

from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.call_status_service import update_call_status

router = APIRouter(prefix="/twilio", tags=["twilio-status"])


@router.post("/status", response_class=Response)
def twilio_status_webhook(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    From: Optional[str] = Form(None),
    To: Optional[str]  = Form(None),
    ErrorCode: Optional[str]  = Form(None),
    ErrorMessage: Optional[str]  = Form(None),
    db: Session = Depends(get_db),
):
    """
    Twilio call status callback webhook.

    Twilio will POST here with fields like:
      - CallSid: Twilio's call ID
      - CallStatus: queued | ringing | in-progress | completed | busy | failed | no-answer | canceled
      - ErrorCode / ErrorMessage (optional failure context)
    """
    update_call_status(
        db=db,
        provider_call_id=CallSid,
        call_status=CallStatus,
        error_code=ErrorCode,
        error_message=ErrorMessage,
    )

    # Just return a minimal TwiML response with the correct media type.
    return Response(content="<Response></Response>", media_type="text/xml")
