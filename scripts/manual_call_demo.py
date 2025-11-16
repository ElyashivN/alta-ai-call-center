# scripts/manual_call_demo.py
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.lead import Lead
from app.models.meeting_request import MeetingRequest, MeetingRequestStatus
from app.schemas.constraints import HardConstraints
from app.services.call_service import initiate_outbound_call
from app.services.twilio_client import TwilioClient


def main() -> None:
    settings = get_settings()

    # Real Twilio client using your env / .env settings
    twilio_client = TwilioClient(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        from_number=settings.TWILIO_PHONE_NUMBER,
        voice_url=settings.TWILIO_VOICE_WEBHOOK_URL,
    )

    db = SessionLocal()
    try:
        # 1) Create (or reuse) your lead
        lead = (
            db.query(Lead)
            .filter(Lead.phone == "+972546688243")
            .first()
        )
        if not lead:
            lead = Lead(
                name="<INSERT-YOUR-NAME>",
                phone="+<INSERT-YOUR-PHONE->",
                email="<INSERT-YOUR-EMAIL>",
                company="Manual Demo",
                timezone="Asia/Jerusalem",
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            print(f"Created lead id={lead.id} for {lead.name} ({lead.phone})")
        else:
            print(f"Reusing existing lead id={lead.id} for {lead.name} ({lead.phone})")

        # 2) Create a MeetingRequest for the next ~3 days
        now = datetime.now(timezone.utc)
        hc = HardConstraints(
            window_start=now + timedelta(hours=1),
            window_end=now + timedelta(days=3),
            timezone="Asia/Jerusalem",
        )

        mr = MeetingRequest(
            owner_id="manual-demo",
            title="Manual outbound demo",
            duration_minutes=30,
            max_bookings=1,
            status=MeetingRequestStatus.ACTIVE,
            hard_constraints=hc.model_dump(mode="json"),
            soft_constraints=None,
        )
        db.add(mr)
        db.commit()
        db.refresh(mr)
        print(
            "Created meeting_request id="
            f"{mr.id} with window {hc.window_start} → {hc.window_end}"
        )

        # 3) Kick off the outbound call using the existing service
        call = initiate_outbound_call(
            db=db,
            twilio_client=twilio_client,
            lead=lead,
            meeting_request=mr,
        )
        print(
            f"Created call id={call.id} provider_call_id={call.provider_call_id} "
            f"for lead_id={call.lead_id}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
