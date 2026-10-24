from sqlalchemy import select, func
from app.models.mess import Mess
from app.models.menu import Menu
from app.models.dish import Dish
from app.models.menu_item import MenuItem
from seed_mess import seed_messes
from seed_menu import seed_menus


def test_seed_mess_idempotent(db_session):
    # First seed run
    stats1 = seed_messes(db_session)
    assert stats1["created"] == 2
    assert stats1["existing"] == 0

    messes = db_session.scalars(select(Mess).order_by(Mess.id)).all()
    assert len(messes) == 2
    names = {m.name for m in messes}
    assert names == {"Boys' Mess", "Girls' Mess"}
    assert all(m.is_active for m in messes)

    # Second seed run (must be idempotent)
    stats2 = seed_messes(db_session)
    assert stats2["created"] == 0
    assert stats2["existing"] == 2

    # Total messes count remains 2
    assert db_session.scalar(select(func.count(Mess.id))) == 2


def test_seed_menu_idempotent_and_shared_dishes(db_session):
    # Ensure messes are seeded first
    seed_messes(db_session)

    # First menu seed run
    stats1 = seed_menus(db_session)
    assert stats1["new_menus"] == 42  # 7 days * 3 meals * 2 messes = 42 menus
    assert stats1["new_dishes"] > 0
    assert stats1["new_menu_items"] > 0

    total_dishes_1 = db_session.scalar(select(func.count(Dish.id)))
    total_menus_1 = db_session.scalar(select(func.count(Menu.id)))
    total_items_1 = db_session.scalar(select(func.count(MenuItem.id)))

    # Verify both messes have menus for every day and meal
    for mess_name in ["Boys' Mess", "Girls' Mess"]:
        mess = db_session.scalar(select(Mess).where(Mess.name == mess_name))
        menu_count = db_session.scalar(
            select(func.count(Menu.id)).where(Menu.mess_id == mess.id)
        )
        assert menu_count == 21  # 7 days * 3 meals

    # Verify Dish names are globally unique
    dish_names = db_session.scalars(select(Dish.name)).all()
    assert len(dish_names) == len(set(dish_names))

    # Second menu seed run (must be idempotent)
    stats2 = seed_menus(db_session)
    assert stats2["new_dishes"] == 0
    assert stats2["new_menus"] == 0
    assert stats2["new_menu_items"] == 0

    total_dishes_2 = db_session.scalar(select(func.count(Dish.id)))
    total_menus_2 = db_session.scalar(select(func.count(Menu.id)))
    total_items_2 = db_session.scalar(select(func.count(MenuItem.id)))

    assert total_dishes_1 == total_dishes_2
    assert total_menus_1 == total_menus_2
    assert total_items_1 == total_items_2
