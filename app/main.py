import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.models import User, UserPhoto, UserProfile, ConversationMessage, ConversationState, Like, Match, DirectMessage, BlockedUser  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        logger.warning("SECRET_KEY is using the insecure default value. Set a secure key via environment variable.")
    Base.metadata.create_all(bind=engine)
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    yield


app = FastAPI(title="AI Dating App", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from app.routers import auth, profile, chat, discover, matches, messages, block, account  # noqa: E402

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(discover.router, prefix="/api/v1/discover", tags=["discover"])
app.include_router(matches.router, prefix="/api/v1/matches", tags=["matches"])
app.include_router(messages.router, prefix="/api/v1/matches", tags=["messages"])
app.include_router(block.router, prefix="/api/v1/block", tags=["block"])
app.include_router(account.router, prefix="/api/v1/account", tags=["account"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
