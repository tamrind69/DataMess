
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.dish import Dish
from app.models.mess import Mess
from app.models.rating import Rating


def get_menu_by_weekday(
    weekday: int,
    meal_type: str,
    db: Session,
):
    if weekday < 0 or weekday > 6:
        raise HTTPException(
            status_code=400,
            detail="weekday must be between 0 (Monday) and 6 (Sunday)",
        )

    if meal_type not in {"breakfast", "lunch", "dinner"}:
        raise HTTPException(
            status_code=400,
            detail="meal_type must be breakfast, lunch, or dinner",
        )

    mess = db.scalar(
        select(Mess).where(Mess.name == "Boys' Mess")
    )

    if mess is None:
        raise HTTPException(
            status_code=404,
            detail="Boys' Mess not found",
        )

    menu = db.scalar(
        select(Menu).where(
            Menu.mess_id == mess.id,
            Menu.weekday == weekday,
            Menu.meal_type == meal_type,
        )
    )

    if menu is None:
        raise HTTPException(
            status_code=404,
            detail="Menu not found",
        )

    statement = (
        select(
            Dish.id,
            Dish.name,
            func.avg(Rating.score).label("average_rating"),
            func.count(Rating.id).label("rating_count"),
        )
        .join(MenuItem, MenuItem.dish_id == Dish.id)
        .outerjoin(Rating, Rating.dish_id == Dish.id)
        .where(MenuItem.menu_id == menu.id)
        .group_by(Dish.id, Dish.name, MenuItem.id)
        .order_by(MenuItem.id)
    )

    results = db.execute(statement).all()

    dishes = [
        {
            "id": dish_id,
            "name": name,
            "average_rating": (
                float(average_rating)
                if average_rating is not None
                else None
            ),
            "rating_count": rating_count,
        }
        for dish_id, name, average_rating, rating_count in results
    ]

    return {
        "weekday": menu.weekday,
        "meal_type": menu.meal_type,
        "dishes": dishes,
    }
