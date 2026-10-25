from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal
from app.models.mess import Mess

MESS_DEFINITIONS = [
    {"name": "Boys' Mess", "location": "NIT Patna", "is_active": True},
    {"name": "Girls' Mess", "location": "NIT Patna", "is_active": True},
]


def seed_messes(db: Session) -> dict[str, int]:
    created = 0
    existing = 0
    for mess_info in MESS_DEFINITIONS:
        existing_mess = db.scalar(
            select(Mess).where(Mess.name == mess_info["name"])
        )

        if existing_mess:
            existing += 1
            print(f"Mess already exists: ID={existing_mess.id}, name={existing_mess.name}")
            continue

        mess = Mess(
            name=mess_info["name"],
            location=mess_info["location"],
            is_active=mess_info["is_active"],
        )

        db.add(mess)
        created += 1

    db.commit()
    return {"created": created, "existing": existing}


def main() -> None:
    with SessionLocal() as db:
        stats = seed_messes(db)
        print(f"Mess seeding completed: created={stats['created']}, existing={stats['existing']}")


if __name__ == "__main__":
    main()
