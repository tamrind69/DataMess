
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
from app.models.rush_report import RushReport
from app.schemas.mess import MessResponse
from app.schemas.menu import MenuResponse
from app.schemas.user import UserCreate
from app.schemas.user_response import UserResponse
from app.schemas.login import LoginRequest
from app.schemas.token import TokenResponse
from app.schemas.rating import RatingCreate , RatingResponse , RatingUpdate , DishRatingSummary
from app.schemas.rush_report import (
    RushReportCreate,
    RushReportResponse,
    RushSummaryResponse,
)

from app.services.menu import get_menu_by_weekday

from app.core.security import create_access_token
from app.core.security import get_current_user

from datetime import datetime, timedelta

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="DataMess API",
    description="Campus mess ratings and rush analytics",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Serving windows are local server time. Each window is divided into
# 15-minute slots anchored at its start time.
RUSH_MEAL_WINDOWS = {
    "breakfast": (7, 30, 10, 0),
    "lunch": (12, 30, 14, 30),
    "dinner": (20, 0, 22, 0),
}


@app.post(
    "/rush/reports",
    response_model=RushReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rush_report(
    payload: RushReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Use server time so clients cannot choose or backdate their slot.
    now = datetime.now()
    start_hour, start_minute, end_hour, end_minute = RUSH_MEAL_WINDOWS[
        payload.meal_type
    ]
    meal_start = now.replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    )
    meal_end = now.replace(
        hour=end_hour, minute=end_minute, second=0, microsecond=0
    )

    if not (meal_start <= now < meal_end):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rush reports for {payload.meal_type} are only accepted "
                   f"between {start_hour:02d}:{start_minute:02d} and "
                   f"{end_hour:02d}:{end_minute:02d}.",
        )

    mess = db.get(Mess, payload.mess_id)
    if mess is None or not mess.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active mess not found",
        )

    elapsed_minutes = int((now - meal_start).total_seconds() // 60)
    slot_start = meal_start + timedelta(minutes=(elapsed_minutes // 15) * 15)

    report = RushReport(
        user_id=current_user.id,
        mess_id=mess.id,
        meal_type=payload.meal_type,
        level=payload.level,
        slot_start=slot_start,
    )
    db.add(report)

    try:
        db.commit()
        db.refresh(report)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a rush report for this mess, meal, and 15-minute slot.",
        )

    return report


@app.get(
    "/rush/summary/{mess_id}/{meal_type}",
    response_model=RushSummaryResponse,
)
def get_rush_summary(
    mess_id: int,
    meal_type: str,
    db: Session = Depends(get_db),
):
    if meal_type not in RUSH_MEAL_WINDOWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="meal_type must be breakfast, lunch, or dinner.",
        )

    mess = db.get(Mess, mess_id)
    if mess is None or not mess.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active mess not found",
        )

    # Keep slot calculation identical to report submission.
    now = datetime.now()
    start_hour, start_minute, end_hour, end_minute = RUSH_MEAL_WINDOWS[meal_type]
    meal_start = now.replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    )
    meal_end = now.replace(
        hour=end_hour, minute=end_minute, second=0, microsecond=0
    )

    if not (meal_start <= now < meal_end):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rush summaries for {meal_type} are only available during "
                   f"serving hours ({start_hour:02d}:{start_minute:02d}-"
                   f"{end_hour:02d}:{end_minute:02d}).",
        )

    elapsed_minutes = int((now - meal_start).total_seconds() // 60)
    slot_start = meal_start + timedelta(minutes=(elapsed_minutes // 15) * 15)
    slot_end = slot_start + timedelta(minutes=15)

    current_reports = db.scalars(
        select(RushReport).where(
            RushReport.mess_id == mess_id,
            RushReport.meal_type == meal_type,
            RushReport.slot_start == slot_start,
        )
    ).all()

    current_counts = {}
    for report in current_reports:
        current_counts[report.level] = current_counts.get(report.level, 0) + 1

    if not current_reports:
        current_rush = "no_data_yet"
    else:
        highest_current_count = max(current_counts.values())
        current_winners = [
            level for level, count in current_counts.items()
            if count == highest_current_count
        ]
        current_rush = current_winners[0] if len(current_winners) == 1 else "mixed"

    # Match the same clock-time slot, but only reports from earlier calendar days.
    historical_reports = db.scalars(
        select(RushReport).where(
            RushReport.mess_id == mess_id,
            RushReport.meal_type == meal_type,
            func.date(RushReport.slot_start) < now.date(),
            func.extract("hour", RushReport.slot_start) == slot_start.hour,
            func.extract("minute", RushReport.slot_start) == slot_start.minute,
        )
    ).all()

    historical_count = len(historical_reports)
    if historical_count < 5:
        predicted_rush = "not_enough_historical_data"
    else:
        historical_counts = {}
        for report in historical_reports:
            historical_counts[report.level] = historical_counts.get(report.level, 0) + 1
        highest_historical_count = max(historical_counts.values())
        historical_winners = [
            level for level, count in historical_counts.items()
            if count == highest_historical_count
        ]
        predicted_rush = (
            historical_winners[0]
            if len(historical_winners) == 1
            else "mixed"
        )

    return {
        "mess_id": mess_id,
        "meal_type": meal_type,
        "slot_start": slot_start,
        "current_rush": current_rush,
        "current_reports": len(current_reports),
        "predicted_rush": predicted_rush,
        "historical_reports": historical_count,
    }
