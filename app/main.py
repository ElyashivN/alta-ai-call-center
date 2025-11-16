# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine
from app.models import Base
from app.routers import twilio_voice as twilio_router
from app.routers import calls as calls_router
from app.routers import meeting_requests as mr_router

from app.routers import constraints, campaigns, calls, twilio_status, twilio_voice
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Routers
app.include_router(twilio_router.router, prefix="/twilio", tags=["twilio"])
app.include_router(calls_router.router, prefix="/calls", tags=["calls"])
app.include_router(mr_router.router, prefix="/meeting-requests", tags=["meeting-requests"])
app.include_router(constraints.router)
app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
app.include_router(calls.router)
app.include_router(twilio_status.router)
app.include_router(twilio_voice.router)
@app.get("/health")
def health_check():
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "database": db_status,
    }
