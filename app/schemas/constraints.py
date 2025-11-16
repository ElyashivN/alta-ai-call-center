# app/schemas/constraints.py
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


DayCode = Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
TimeOfDayCode = Literal["MORNING", "AFTERNOON", "EVENING", "OFF_HOURS"]


class HardConstraints(BaseModel):
    window_start: datetime
    window_end: datetime
    timezone: str = "UTC"


class SoftConstraints(BaseModel):
    preferred_days_of_week: Optional[List[DayCode]] = Field(default=None)
    preferred_time_of_day: Optional[List[TimeOfDayCode]] = Field(default=None)


class ParsedConstraints(BaseModel):
    hard_constraints: HardConstraints
    soft_constraints: SoftConstraints
