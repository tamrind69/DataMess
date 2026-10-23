
from sqlalchemy import select

from app.db.base import Base
from app.db.session import SessionLocal
from app.models.mess import Mess


def main() -> None:
    with SessionLocal() as db:
        existing_mess = db.scalar(
            select(Mess).where(Mess.name == "Boys' Mess")
        )

        if existing_mess:
            print(f"Mess already exists: ID={existing_mess.id}")
            return

        mess = Mess(
            name="Boys' Mess",
            location="NIT Patna",
            is_active=True,
        )

        db.add(mess)
        db.commit()
        db.refresh(mess)

        print(f"Created mess: ID={mess.id}, name={mess.name}")


if __name__ == "__main__":
    main()
