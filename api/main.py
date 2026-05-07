import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # must run before any src.* imports that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.auth import ensure_default_admin
from api.routers.auth import router as auth_router
from api.routers.chat import router as chat_router
from api.routers.data import router as data_router
from api.routers.dashboard import router as dashboard_router
from src.agent import ExcelsisAgent
from src.data_store import AttendanceDataStore
from src.vector_store import AttendanceVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_default_admin()

    data_path = os.getenv("ATTENDANCE_DATA_PATH", "./data/attendance")
    app.state.store = AttendanceDataStore(
        data_path=data_path if Path(data_path).exists() else None
    )
    app.state.vec = AttendanceVectorStore()
    app.state.vec.index_store_summaries(app.state.store)
    app.state.agent = ExcelsisAgent(
        store=app.state.store,
        vector_store=app.state.vec,
    )
    yield


app = FastAPI(title="Excelsis 360 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path("data/dashboards").mkdir(parents=True, exist_ok=True)
app.mount("/dashboards", StaticFiles(directory="data/dashboards"), name="dashboards")

app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(chat_router,      prefix="/chat",      tags=["chat"])
app.include_router(data_router,      prefix="/data",      tags=["data"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
