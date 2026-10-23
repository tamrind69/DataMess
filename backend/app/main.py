
from fastapi import Depends, FastAPI, HTTPException , status
from sqlalchemy import text, select , func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pwdlib import PasswordHash

from app.db.session import get_db
from app.models.mess import Mess
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.dish import Dish
from app.models.user import User
from app.models.rating import Rating
from app.schemas.mess import MessResponse
from app.schemas.menu import MenuResponse
from app.schemas.user import UserCreate
from app.schemas.user_response import UserResponse
from app.schemas.login import LoginRequest
from app.schemas.token import TokenResponse
from app.schemas.rating import RatingCreate , RatingResponse , RatingUpdate , DishRatingSummary

from app.services.menu import get_menu_by_weekday

from app.core.security import create_access_token
from app.core.security import get_current_user

from datetime import datetime


app = FastAPI(
    title="DataMess API",
    description="Campus mess ratings and rush analytics",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected"}


@app.get("/messes", response_model=list[MessResponse])
def get_messes(db: Session = Depends(get_db)):
    statement = select(Mess).order_by(Mess.id)
    return db.scalars(statement).all()


@app.get("/menus/today/{meal_type}" , response_model= MenuResponse)
def get_today_menu(
    meal_type: str,
    db: Session = Depends(get_db)
):
    dt = datetime.now()

    return get_menu_by_weekday(dt.weekday() , meal_type , db)


@app.get("/menus/{weekday}/{meal_type}", response_model=MenuResponse)
def get_menu(
    weekday: int,
    meal_type: str,
    db: Session = Depends(get_db),
):
    return get_menu_by_weekday(weekday, meal_type, db)



password_hasher = PasswordHash.recommended()

@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(User.email == str(payload.email))
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        name=payload.name,
        email=str(payload.email),
        password_hash=password_hasher.hash(payload.password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    return user


@app.post("/auth/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == str(payload.email))
    )

    if user is None or not password_hasher.verify(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/auth/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@app.post(
    "/ratings",
    response_model=RatingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rating(
    payload: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dish = db.get(Dish, payload.dish_id)

    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found",
        )

    rating = Rating(
        user_id=current_user.id,
        dish_id=dish.id,
        score=payload.score,
    )

    db.add(rating)

    try:
        db.commit()
        db.refresh(rating)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this dish",
        )

    return rating


@app.get("/ratings/me", response_model=list[RatingResponse])
def get_my_ratings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Rating).where(
        Rating.user_id == current_user.id
    )
    return db.scalars(statement).all()


@app.put(
    "/ratings/{dish_id}",
    response_model=RatingResponse,
)
def update_rating(
    dish_id: int,
    payload: RatingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dish = db.get(Dish, dish_id)

    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found",
        )

    statement = select(Rating).where(
        Rating.user_id == current_user.id,
        Rating.dish_id == dish_id,
    )
    rating = db.scalar(statement)

    if rating is None:
        rating = Rating(
            user_id=current_user.id,
            dish_id=dish_id,
            score=payload.score,
        )
        db.add(rating)
    else:
        rating.score = payload.score

    db.commit()
    db.refresh(rating)

    return rating


@app.get(
    "/dishes/{dish_id}/ratings",
    response_model=DishRatingSummary,
)
def get_dish_rating_summary(
    dish_id: int,
    db: Session = Depends(get_db),
):
    dish = db.get(Dish, dish_id)

    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found",
        )

    statement = select(
        func.avg(Rating.score),
        func.count(Rating.id),
    ).where(
        Rating.dish_id == dish_id
    )

    average_score, total_ratings = db.execute(statement).one()

    return {
        "dish_id": dish_id,
        "average_score": (
            float(average_score)
            if average_score is not None
            else None
        ),
        "total_ratings": total_ratings,
    }