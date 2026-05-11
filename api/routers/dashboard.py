from pathlib import Path

from fastapi import APIRouter, Depends, Request

from api.deps import get_current_user, get_store
from api.models import DashboardResponse
from src.dashboard import build_full_dashboard, write_html
from src.security import UserContext

router = APIRouter()

DASHBOARD_DIR = Path("data/dashboards")


@router.post("/generate", response_model=DashboardResponse)
def generate(request: Request, user: UserContext = Depends(get_current_user)):
    store = get_store(request)
    fig   = build_full_dashboard(store, period="all",
                                 classes=user.allowed_classes or None)
    return DashboardResponse(url=write_html(fig))


@router.get("/latest", response_model=DashboardResponse)
def latest(_: UserContext = Depends(get_current_user)):
    files = sorted(DASHBOARD_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return DashboardResponse(url="")
    return DashboardResponse(url=f"/dashboards/{files[0].name}")
