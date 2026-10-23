from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MealType = Literal["breakfast", "lunch", "dinner"]
RushLevel = Literal["low", "moderate", "high"]


class RushReportCreate(BaseModel):
    mess_id: int = Field(gt=0)
    meal_type: MealType
    level: RushLevel


class RushReportResponse(BaseModel):
    id: int
    mess_id: int
    meal_type: MealType
    level: RushLevel
    slot_start: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RushSummaryResponse(BaseModel):
    mess_id: int
    meal_type: MealType
    slot_start: datetime
    current_rush: Literal["low", "moderate", "high", "mixed", "no_data_yet"]
    current_reports: int
    predicted_rush: Literal[
        "low", "moderate", "high", "mixed", "not_enough_historical_data"
    ]
    historical_reports: int
