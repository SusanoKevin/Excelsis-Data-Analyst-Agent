import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from api.deps import get_current_user, get_store
from api.models import DashboardResponse
from src.dashboard import build_modern_static_dashboard
from src.security import UserContext

router = APIRouter()

DASHBOARD_DIR = Path("data/dashboards")


@router.post("/generate", response_model=DashboardResponse)
def generate(request: Request, user: UserContext = Depends(get_current_user)):
    store = get_store(request)
    filename = f"dashboard_{uuid.uuid4().hex[:8]}.png"
    out = DASHBOARD_DIR / filename
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    build_modern_static_dashboard(store, period="all", save=False).savefig(
        str(out), dpi=140, bbox_inches="tight"
    )
    return DashboardResponse(url=f"/dashboards/{filename}")


@router.get("/latest", response_model=DashboardResponse)
def latest(_: UserContext = Depends(get_current_user)):
    files = sorted(DASHBOARD_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return DashboardResponse(url="")
    return DashboardResponse(url=f"/dashboards/{files[0].name}")
