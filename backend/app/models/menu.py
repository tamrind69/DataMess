
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Menu(Base):
    __tablename__ = "menus"

    __table_args__ = (
        UniqueConstraint(
            "mess_id",
            "weekday",
            "meal_type",
            name="uq_menu_mess_weekday_meal",
        ),
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_menu_weekday",
        ),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner')",
            name="ck_menu_meal_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    mess_id: Mapped[int] = mapped_column(
        ForeignKey("messes.id"),
        nullable=False,
    )

    # Monday = 0, Tuesday = 1, ..., Sunday = 6
    weekday: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    meal_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
