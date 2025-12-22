from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from types import SimpleNamespace

from app.core.settings import settings
from app.utils.logger import setup_logging
from app.utils.limiter import limiter, custom_rate_limit_exceeded_handler


setup_logging(settings.LOG_LEVEL)


from contextlib import asynccontextmanager
from app.db.mongo import connect_to_mongo, close_mongo_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Rate Limiter
# -----------------------------
app.state = SimpleNamespace()
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded, custom_rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# -----------------------------
# Routers
# -----------------------------
from app.api import chat
app.include_router(chat.router)


# -----------------------------
# Root Endpoint
# -----------------------------
@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    return {
        "message": f"{settings.APP_NAME} Running",
        "version": settings.VERSION,
    }
