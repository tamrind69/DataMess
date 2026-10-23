
from pydantic import BaseModel


class DishInMenu(BaseModel):
    id : int
    name: str
    average_rating: float | None
    rating_count: int


class MenuResponse(BaseModel):
    weekday: int
    meal_type: str
    dishes: list[DishInMenu]
