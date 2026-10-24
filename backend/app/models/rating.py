from sqlalchemy import Integer, DateTime, CheckConstraint, UniqueConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

from datetime import datetime

class Rating(Base):
    __tablename__ = "ratings"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "dish_id",
            "mess_id",
            name="uq_rating_user_dish_mess",
        ),
        CheckConstraint(
            "score >= 1 AND score <= 5",
            name="ck_rating_score_valid",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    dish_id: Mapped[int] = mapped_column(
        ForeignKey("dishes.id"),
        nullable=False,
    )

    mess_id: Mapped[int] = mapped_column(
        ForeignKey("messes.id"),
        nullable=False,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False

    )

