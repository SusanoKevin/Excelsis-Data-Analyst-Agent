import asyncio
import logging
import os
import threading
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
from src.rag_ingestor import run_ingestion
from src.rag_store import ExcelsisRAGStore
from src.sql_store import SQLDataStore

logger = logging.getLogger(__name__)


def _validate_startup(store: SQLDataStore) -> None:
    model  = os.environ.get("MODEL", "qwen2.5:14b")
    server = os.environ.get("SQL_SERVER", "<not set>")
    dbs    = os.environ.get("SQL_DATABASES", store.primary_db)

    if os.environ.get("JWT_SECRET", "change-me-in-production") == "change-me-in-production":
        logger.warning("SECURITY: JWT_SECRET is the default — set JWT_SECRET in .env before production use")

    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_ok = False
    try:
        urllib.request.urlopen(f"{ollama_base_url}/api/tags", timeout=3)
        ollama_ok = True
    except Exception:
        logger.warning("Ollama not reachable at %s — agent responses will fail", ollama_base_url)

    sql_ok = store.ping()
    if not sql_ok:
        logger.error("SQL Server check failed — verify SQL_SERVER and credentials in .env")

    logger.info("Excelsis 360 startup | model=%s (%s) | sql=%s (%s) | dbs=%s",
                model, "OK" if ollama_ok else "UNREACHABLE",
                server, "OK" if sql_ok else "UNREACHABLE",
                dbs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_default_admin()
    store = SQLDataStore()
    rag_store = ExcelsisRAGStore(
        chroma_path=os.getenv("CHROMA_PATH", ".chroma"),
        embed_model=os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
    )
    app.state.store     = store
    app.state.rag_store = rag_store
    app.state.agent     = ExcelsisAgent(store=store, rag_store=rag_store)

    docs_path = os.getenv("DOCS_PATH", "docs")
    threading.Thread(
        target=run_ingestion,
        args=(rag_store, store, docs_path),
        daemon=True,
        name="rag-ingestor",
    ).start()

    await asyncio.to_thread(_validate_startup, store)
    yield
    store.close()


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
