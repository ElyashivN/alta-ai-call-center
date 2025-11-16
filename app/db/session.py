# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# For SQLite, `check_same_thread=False` is needed for FastAPI dev usage
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    from sqlalchemy.orm import Session
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
