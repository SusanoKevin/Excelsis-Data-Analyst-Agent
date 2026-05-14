from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # must run before any src.* imports that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.auth import ensure_default_admin
from api.routers.auth import router as auth_router
from api.routers.chat import router as chat_router
from api.routers.data import router as data_router
from src.agent import ExcelsisAgent
from src.sql_store import SQLAttendanceStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_default_admin()
    app.state.store = SQLAttendanceStore()
    app.state.agent = ExcelsisAgent(store=app.state.store)
    yield


app = FastAPI(title="Excelsis 360 API", lifespan=lifespan)

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
