# app/routers/constraints.py
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.constraints import ParsedConstraints
from app.services.constraints_nlp_service import (
    parse_natural_language_constraints,
)

router = APIRouter(prefix="/constraints", tags=["constraints"])


class ConstraintParseRequest(BaseModel):
    instruction: str
    timezone: str = "UTC"
    # Optional 'now' for determinism in tests / simulations
    now: Optional[datetime] = None


@router.post("/parse", response_model=ParsedConstraints)
def parse_constraints(req: ConstraintParseRequest) -> ParsedConstraints:
    """
    Turn a natural-language instruction into hard/soft constraints JSON.

    Example input:
      {
        "instruction": "Try to book in the next two weeks, preferably Tue–Thu mornings",
        "timezone": "Asia/Jerusalem"
      }
    """
    now = req.now or datetime.utcnow()
    return parse_natural_language_constraints(
        instruction=req.instruction,
        now=now,
        timezone=req.timezone,
    )
