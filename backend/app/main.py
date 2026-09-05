"""
Revenue Recovery Agent — FastAPI application entry point.

This module wires up the FastAPI application, registers all routers,
and exposes the ASGI `app` object consumed by Uvicorn.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.router import router as agent_router
from app.api.router import router as read_router
from app.db.database import init_db
from app.events.router import router as events_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="Revenue Recovery Agent",
    description=(
        "An AI-powered bounded agent that detects failed payments, "
        "diagnoses revenue risk, chooses recovery actions, and maintains "
        "a full audit trail."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for local frontend development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(events_router)
app.include_router(read_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@app.get("/", tags=["Meta"])
def root() -> dict:
    """Return a brief description of the API."""
    return {
        "api": "Revenue Recovery Agent",
        "version": "0.1.0",
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Meta"])
def health() -> dict:
    """Liveness probe — confirms the service is reachable."""
    return {
        "status": "ok",
        "service": "revenue-recovery-agent",
    }
