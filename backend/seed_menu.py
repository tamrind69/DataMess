
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.mess import Mess
from app.models.menu import Menu
from app.models.dish import Dish
from app.models.menu_item import MenuItem


# Weekday convention: Monday = 0, Sunday = 6.
# Evening tea/snacks are intentionally excluded.
MENU_DATA = {
    0: {  # Monday
        "breakfast": [
            "Paratha",
            "Aloo Chana",
            "Cornflakes with Full-Cream Milk",
            "Tea",
            "Banana",
        ],
        "lunch": [
            "Yellow Dal (Arhar)",
            "Rice",
            "Roti",
            "Sabji",
            "Bhujia",
            "Salad",
            "Pickle",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Dal (Sabut Mung)",
            "Veg Pulao",
            "Roti",
            "Shahi Paneer",
            "Raita",
        ],
    },
    1: {  # Tuesday
        "breakfast": [
            "Poha",
            "Sweet Dalia",
            "Bread with Butter/Jam",
            "Sprouts",
            "Banana",
            "Tea",
        ],
        "lunch": [
            "Rajma",
            "Rice",
            "Roti",
            "Sabji",
            "Bhujia",
            "Salad",
            "Pickles",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Yellow Dal (Arhar)",
            "Sabji",
            "Rice",
            "Roti",
            "Kheer",
            "Salad",
        ],
    },
    2: {  # Wednesday
        "breakfast": [
            "Idli Sambhar",
            "Coconut Chutney",
            "Bread with Butter/Jam",
            "Cornflakes with Full-Cream Milk",
            "Banana",
            "Tea",
        ],
        "lunch": [
            "Yellow Dal (Arhar)",
            "Rice",
            "Roti",
            "Mix Veg",
            "Bhujia",
            "Salad",
            "Pickles",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Dal Makhani",
            "Sabji/Bhujia",
            "Rice",
            "Roti",
            "Rasgulla",
            "Gulab Jamun",
        ],
    },
    3: {  # Thursday
        "breakfast": [
            "Aloo Paratha",
            "Plain Curd",
            "Bread with Butter/Jam",
            "Sprouts",
            "Banana",
            "Tea",
            "Pickle",
        ],
        "lunch": [
            "Chana Dal",
            "Rice",
            "Roti",
            "Lauki Kofta",
            "Onion Pakoda",
            "Papad",
            "Salad",
            "Pickles",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Arhar Dal Tadka",
            "Rice",
            "Puri",
            "Mutter Paneer",
            "Raita",
        ],
    },
    4: {  # Friday
        "breakfast": [
            "Puri",
            "Black Chana",
            "Halwa",
            "Sprouts",
            "Banana",
            "Coffee",
        ],
        "lunch": [
            "Kadhi Pakora",
            "Rice",
            "Roti",
            "Sabji",
            "Bhujia",
            "Salad",
            "Pickles",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Sabut Masoor Dal (Chilka Wala)",
            "Mix Veg",
            "Rice",
            "Roti",
            "Sewai",
        ],
    },
    5: {  # Saturday
        "breakfast": [
            "Chole Bhature",
            "Cornflakes with Full-Cream Milk",
            "Bread with Butter/Jam",
            "Sprouts",
            "Pickles",
            "Banana",
            "Coffee",
        ],
        "lunch": [
            "Sabji",
            "Rice",
            "Roti",
            "Yellow Dal (Arhar)",
            "Papad",
            "Salad",
            "Pickles",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Veg Biryani",
            "Raita",
            "Roti",
            "Chana Dal Tadka",
            "Veg Manchurian",
            "Ice Cream",
            "Gulab Jamun",
        ],
    },
    6: {  # Sunday
        "breakfast": [
            "Masala Dosa/Uttapam",
            "Sambar",
            "Coconut Chutney",
            "Sprouts",
            "Banana",
            "Tea",
        ],
        "lunch": [
            "Kadhi Pakora",
            "Rice",
            "Roti",
            "Sabji",
            "Bhujia",
            "Papad",
            "Salad",
            "Pickles",
            "Seasonal Fruit",
        ],
        "dinner": [
            "Jeera Rice",
            "Poori",
            "Paneer Butter Masala",
            "Chhole",
            "Halwa (Sooji/Moong Dal)",
            "Raita",
        ],
    },
}


def get_or_create_dish(db, name: str) -> Dish:
    dish = db.scalar(select(Dish).where(Dish.name == name))

    if dish is None:
        dish = Dish(name=name)
        db.add(dish)
        db.flush()

    return dish


def get_or_create_menu(
    db,
    mess_id: int,
    weekday: int,
    meal_type: str,
) -> Menu:
    menu = db.scalar(
        select(Menu).where(
            Menu.mess_id == mess_id,
            Menu.weekday == weekday,
            Menu.meal_type == meal_type,
        )
    )

    if menu is None:
        menu = Menu(
            mess_id=mess_id,
            weekday=weekday,
            meal_type=meal_type,
        )
        db.add(menu)
        db.flush()

    return menu


def main() -> None:
    with SessionLocal() as db:
        try:
            mess = db.scalar(
                select(Mess).where(Mess.name == "Boys' Mess")
            )

            if mess is None:
                raise ValueError(
                    "Boys' Mess does not exist. Run seed_mess.py first."
                )

            new_dishes = 0
            new_menus = 0
            new_menu_items = 0

            for weekday, meals in MENU_DATA.items():
                for meal_type, dish_names in meals.items():
                    menu = db.scalar(
                        select(Menu).where(
                            Menu.mess_id == mess.id,
                            Menu.weekday == weekday,
                            Menu.meal_type == meal_type,
                        )
                    )

                    if menu is None:
                        menu = Menu(
                            mess_id=mess.id,
                            weekday=weekday,
                            meal_type=meal_type,
                        )
                        db.add(menu)
                        db.flush()
                        new_menus += 1

                    for dish_name in dish_names:
                        dish = db.scalar(
                            select(Dish).where(
                                Dish.name == dish_name
                            )
                        )

                        if dish is None:
                            dish = Dish(name=dish_name)
                            db.add(dish)
                            db.flush()
                            new_dishes += 1

                        existing_item = db.scalar(
                            select(MenuItem.id).where(
                                MenuItem.menu_id == menu.id,
                                MenuItem.dish_id == dish.id,
                            )
                        )

                        if existing_item is None:
                            db.add(
                                MenuItem(
                                    menu_id=menu.id,
                                    dish_id=dish.id,
                                )
                            )
                            new_menu_items += 1

            db.commit()

            print("Menu seeding completed successfully.")
            print(f"New dishes: {new_dishes}")
            print(f"New menus: {new_menus}")
            print(f"New menu items: {new_menu_items}")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
