import logging
import os
import urllib.request
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # must run before any src.* imports that read env vars

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from api.auth import ensure_default_admin
from api.limiter import limiter
from api.routers.auth import router as auth_router
from api.routers.chat import router as chat_router
from api.routers.data import router as data_router
from src.agent import ExcelsisAgent
from src.sql_store import SQLAttendanceStore

logger = logging.getLogger(__name__)


def _validate_startup(store: SQLAttendanceStore) -> None:
    model  = os.environ.get("MODEL", "phi4:14b")
    server = os.environ.get("SQL_SERVER", "<not set>")
    dbs    = os.environ.get("SQL_DATABASES", store._primary_db)

    ollama_ok = False
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = True
    except Exception:
        logger.warning("Ollama not reachable at http://localhost:11434 — agent responses will fail")

    sql_ok = False
    try:
        store._query("SELECT 1")
        sql_ok = True
    except Exception as e:
        logger.error("SQL Server check failed: %s", e)

    ok = lambda b: "OK" if b else "UNREACHABLE"
    print(
        f"\n{'─' * 52}\n"
        f"  Excelsis 360 — startup\n"
        f"  Model:      {model:<24} {ok(ollama_ok)}\n"
        f"  SQL Server: {server:<24} {ok(sql_ok)}\n"
        f"  Databases:  {dbs}\n"
        f"{'─' * 52}\n"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_default_admin()
    store = SQLAttendanceStore()
    app.state.store = store
    app.state.agent = ExcelsisAgent(store=store)
    _validate_startup(store)
    yield


async def _on_rate_limit_exceeded(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry = getattr(exc, "retry_after", None)
    msg   = f"Rate limit exceeded. Try again in {retry}s." if retry else "Rate limit exceeded."
    return JSONResponse(status_code=429, content={"detail": msg})


app = FastAPI(title="Excelsis 360 API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _on_rate_limit_exceeded)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(data_router, prefix="/data", tags=["data"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
