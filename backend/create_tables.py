from app.db.base import Base
import app.db.models  # registers all models
from app.db.session import engine

Base.metadata.create_all(bind=engine)
print("Database tables created successfully.")