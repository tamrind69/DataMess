
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    __table_args__ = (
        UniqueConstraint(
            "menu_id",
            "dish_id",
            name="uq_menu_item_menu_dish",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    menu_id: Mapped[int] = mapped_column(
        ForeignKey("menus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dish_id: Mapped[int] = mapped_column(
        ForeignKey("dishes.id"),
        nullable=False,
        index=True,
    )
