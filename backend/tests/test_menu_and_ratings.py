from datetime import datetime
from app.models.mess import Mess
from app.models.menu import Menu
from app.models.dish import Dish
from app.models.menu_item import MenuItem
from app.models.user import User
from app.core.security import create_access_token
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def setup_messes_and_menus(db):
    boys_mess = Mess(name="Boys' Mess", location="NIT Patna", is_active=True)
    girls_mess = Mess(name="Girls' Mess", location="NIT Patna", is_active=True)
    inactive_mess = Mess(name="Old Mess", location="NIT Patna", is_active=False)
    db.add_all([boys_mess, girls_mess, inactive_mess])
    db.commit()

    paratha = Dish(name="Paratha")
    poha = Dish(name="Poha")
    dosa = Dish(name="Dosa")
    db.add_all([paratha, poha, dosa])
    db.commit()

    today_weekday = datetime.now().weekday()

    # Boys' Mess Menu: Paratha and Poha
    boys_menu = Menu(mess_id=boys_mess.id, weekday=today_weekday, meal_type="breakfast")
    db.add(boys_menu)
    db.flush()
    db.add(MenuItem(menu_id=boys_menu.id, dish_id=paratha.id))
    db.add(MenuItem(menu_id=boys_menu.id, dish_id=poha.id))

    # Girls' Mess Menu: Paratha and Dosa
    girls_menu = Menu(mess_id=girls_mess.id, weekday=today_weekday, meal_type="breakfast")
    db.add(girls_menu)
    db.flush()
    db.add(MenuItem(menu_id=girls_menu.id, dish_id=paratha.id))
    db.add(MenuItem(menu_id=girls_menu.id, dish_id=dosa.id))

    db.commit()
    return boys_mess, girls_mess, inactive_mess, paratha, poha, dosa


def test_mess_specific_menus(client, db_session):
    boys_mess, girls_mess, inactive_mess, paratha, poha, dosa = setup_messes_and_menus(db_session)

    # Fetch Boys' Mess menu
    res_boys = client.get(f"/menus/today/breakfast?mess_id={boys_mess.id}")
    assert res_boys.status_code == 200
    data_boys = res_boys.json()
    assert data_boys["mess_id"] == boys_mess.id
    dish_names_boys = [d["name"] for d in data_boys["dishes"]]
    assert "Paratha" in dish_names_boys
    assert "Poha" in dish_names_boys
    assert "Dosa" not in dish_names_boys

    # Fetch Girls' Mess menu
    res_girls = client.get(f"/menus/today/breakfast?mess_id={girls_mess.id}")
    assert res_girls.status_code == 200
    data_girls = res_girls.json()
    assert data_girls["mess_id"] == girls_mess.id
    dish_names_girls = [d["name"] for d in data_girls["dishes"]]
    assert "Paratha" in dish_names_girls
    assert "Dosa" in dish_names_girls
    assert "Poha" not in dish_names_girls

    # Non-existent mess returns 404
    res_not_found = client.get("/menus/today/breakfast?mess_id=999")
    assert res_not_found.status_code == 404
    assert res_not_found.json()["detail"] == "Active mess not found"

    # Inactive mess returns 404
    res_inactive = client.get(f"/menus/today/breakfast?mess_id={inactive_mess.id}")
    assert res_inactive.status_code == 404
    assert res_inactive.json()["detail"] == "Active mess not found"


def test_rating_isolation_between_messes(client, db_session, test_user, auth_headers):
    boys_mess, girls_mess, _, paratha, _, _ = setup_messes_and_menus(db_session)

    # Second user for second rating
    user2 = User(
        name="User Two",
        email="user2@example.com",
        password_hash=password_hasher.hash("pass"),
    )
    db_session.add(user2)
    db_session.commit()
    auth_headers2 = {"Authorization": f"Bearer {create_access_token(user2.id)}"}

    # User 1 rates Paratha with 5 in Boys' Mess
    post_res = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": paratha.id, "score": 5, "mess_id": boys_mess.id},
    )
    assert post_res.status_code == 201
    assert post_res.json()["mess_id"] == boys_mess.id

    # Verify menu rating for Boys' Mess reflects score 5
    res_boys = client.get(f"/menus/today/breakfast?mess_id={boys_mess.id}").json()
    dish_boys = next(d for d in res_boys["dishes"] if d["id"] == paratha.id)
    assert dish_boys["average_rating"] == 5.0
    assert dish_boys["rating_count"] == 1

    # Verify Girls' Mess menu still has NO ratings for Paratha
    res_girls = client.get(f"/menus/today/breakfast?mess_id={girls_mess.id}").json()
    dish_girls = next(d for d in res_girls["dishes"] if d["id"] == paratha.id)
    assert dish_girls["average_rating"] is None
    assert dish_girls["rating_count"] == 0

    # User 2 rates Paratha with 3 in Girls' Mess
    post_res2 = client.post(
        "/ratings",
        headers=auth_headers2,
        json={"dish_id": paratha.id, "score": 3, "mess_id": girls_mess.id},
    )
    assert post_res2.status_code == 201
    assert post_res2.json()["mess_id"] == girls_mess.id

    # Verify Boys' Mess still has average 5.0, count 1
    res_boys2 = client.get(f"/menus/today/breakfast?mess_id={boys_mess.id}").json()
    dish_boys2 = next(d for d in res_boys2["dishes"] if d["id"] == paratha.id)
    assert dish_boys2["average_rating"] == 5.0
    assert dish_boys2["rating_count"] == 1

    # Verify Girls' Mess now has average 3.0, count 1
    res_girls2 = client.get(f"/menus/today/breakfast?mess_id={girls_mess.id}").json()
    dish_girls2 = next(d for d in res_girls2["dishes"] if d["id"] == paratha.id)
    assert dish_girls2["average_rating"] == 3.0
    assert dish_girls2["rating_count"] == 1

    # Check dish rating summary scoped to mess
    summary_boys = client.get(f"/dishes/{paratha.id}/ratings?mess_id={boys_mess.id}").json()
    assert summary_boys["average_score"] == 5.0
    assert summary_boys["total_ratings"] == 1

    summary_girls = client.get(f"/dishes/{paratha.id}/ratings?mess_id={girls_mess.id}").json()
    assert summary_girls["average_score"] == 3.0
    assert summary_girls["total_ratings"] == 1

    # Check /ratings/me scoped to mess
    my_boys = client.get(f"/ratings/me?mess_id={boys_mess.id}", headers=auth_headers).json()
    assert len(my_boys) == 1
    assert my_boys[0]["dish_id"] == paratha.id
    assert my_boys[0]["score"] == 5

    my_girls = client.get(f"/ratings/me?mess_id={girls_mess.id}", headers=auth_headers).json()
    assert len(my_girls) == 0

    # User 1 can also rate Paratha in Girls' Mess separately without collision
    post_girls = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": paratha.id, "score": 1, "mess_id": girls_mess.id},
    )
    assert post_girls.status_code == 201

    # Girls' Mess average now reflects User 2 (score 3) and User 1 (score 1) => 2.0
    res_girls3 = client.get(f"/menus/today/breakfast?mess_id={girls_mess.id}").json()
    dish_girls3 = next(d for d in res_girls3["dishes"] if d["id"] == paratha.id)
    assert dish_girls3["average_rating"] == 2.0
    assert dish_girls3["rating_count"] == 2

    # Boys' Mess average remains completely unaffected at 5.0
    res_boys3 = client.get(f"/menus/today/breakfast?mess_id={boys_mess.id}").json()
    dish_boys3 = next(d for d in res_boys3["dishes"] if d["id"] == paratha.id)
    assert dish_boys3["average_rating"] == 5.0
    assert dish_boys3["rating_count"] == 1


def test_invalid_mess_dish_combinations(client, db_session, test_user, auth_headers):
    boys_mess, girls_mess, inactive_mess, paratha, poha, dosa = setup_messes_and_menus(db_session)

    # Dosa is ONLY on Girls' Mess menu, NOT Boys' Mess menu.
    # Attempting to rate Dosa in Boys' Mess must return 400
    res_invalid_dish = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": dosa.id, "score": 4, "mess_id": boys_mess.id},
    )
    assert res_invalid_dish.status_code == 400
    assert res_invalid_dish.json()["detail"] == "Dish does not belong to the selected mess menu"

    # Rating with inactive mess returns 404
    res_inactive = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": paratha.id, "score": 4, "mess_id": inactive_mess.id},
    )
    assert res_inactive.status_code == 404
    assert res_inactive.json()["detail"] == "Active mess not found"

    # Rating with non-existent mess returns 404
    res_bad_mess = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": paratha.id, "score": 4, "mess_id": 9999},
    )
    assert res_bad_mess.status_code == 404
    assert res_bad_mess.json()["detail"] == "Active mess not found"

    # Rating with non-existent dish returns 404
    res_bad_dish = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": 9999, "score": 4, "mess_id": boys_mess.id},
    )
    assert res_bad_dish.status_code == 404
    assert res_bad_dish.json()["detail"] == "Dish not found"

    # Duplicate rating for the same mess returns 409
    res_first = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": paratha.id, "score": 4, "mess_id": boys_mess.id},
    )
    assert res_first.status_code == 201

    res_duplicate = client.post(
        "/ratings",
        headers=auth_headers,
        json={"dish_id": paratha.id, "score": 5, "mess_id": boys_mess.id},
    )
    assert res_duplicate.status_code == 409
    assert "already rated" in res_duplicate.json()["detail"]

    # Updating rating: valid update
    res_update = client.put(
        f"/ratings/{paratha.id}",
        headers=auth_headers,
        json={"score": 2, "mess_id": boys_mess.id},
    )
    assert res_update.status_code == 200
    assert res_update.json()["score"] == 2

    # Updating rating for a dish not in mess menu returns 400
    res_update_invalid = client.put(
        f"/ratings/{dosa.id}",
        headers=auth_headers,
        json={"score": 2, "mess_id": boys_mess.id},
    )
    assert res_update_invalid.status_code == 400
    assert res_update_invalid.json()["detail"] == "Dish does not belong to the selected mess menu"
