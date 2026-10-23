from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RushReport(Base):
    __tablename__ = "rush_reports"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "mess_id",
            "meal_type",
            "slot_start",
            name="uq_rush_report_user_mess_meal_slot",
        ),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner')",
            name="ck_rush_report_meal_type_valid",
        ),
        CheckConstraint(
            "level IN ('low', 'moderate', 'high')",
            name="ck_rush_report_level_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    mess_id: Mapped[int] = mapped_column(
        ForeignKey("messes.id"),
        nullable=False,
        index=True,
    )

    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)

    level: Mapped[str] = mapped_column(String(10), nullable=False)

    # The start of the 15-minute interval, calculated by the backend.
    slot_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
