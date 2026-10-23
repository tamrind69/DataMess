
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RatingCreate(BaseModel):
    dish_id: int = Field(gt=0)
    score: int = Field(ge=1, le=5)


class RatingUpdate(BaseModel):
    score: int = Field(ge=1, le=5)


class RatingResponse(BaseModel):
    id: int
    dish_id: int
    score: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DishRatingSummary(BaseModel):
    dish_id: int
    average_score: float | None
    total_ratings: int
