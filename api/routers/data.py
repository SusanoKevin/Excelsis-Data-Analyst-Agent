from fastapi import APIRouter, Depends, Request

from api.deps import get_current_user, get_store
from src.security import UserContext

router = APIRouter()


def _parse_classes(classes_str: str) -> list[str] | None:
    classes = [c.strip() for c in classes_str.split(",") if c.strip()]
    return classes or None


@router.get("/summary")
def summary(request: Request, _: UserContext = Depends(get_current_user)):
    return get_store(request).summary()


@router.get("/at-risk")
def at_risk(
    request: Request,
    threshold: float = 75.0,
    classes: str = "",
    date_from: str = "",
    date_to: str = "",
    _: UserContext = Depends(get_current_user),
):
    store = get_store(request)
    df    = store.get_at_risk(
        threshold=threshold,
        classes=_parse_classes(classes),
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return [] if df.empty else df.to_dict(orient="records")


@router.get("/stats")
def stats(
    request: Request,
    group_by: str = "class",
    period: str = "all",
    classes: str = "",
    date_from: str = "",
    date_to: str = "",
    _: UserContext = Depends(get_current_user),
):
    store = get_store(request)
    df    = store.compute_stats(
        group_by=group_by,
        period=period,
        classes=_parse_classes(classes),
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return [] if df.empty else df.to_dict(orient="records")


@router.get("/trends")
def trends(
    request: Request,
    classes: str = "",
    _: UserContext = Depends(get_current_user),
):
    store = get_store(request)
    cls   = _parse_classes(classes)
    current  = store.compute_stats(group_by="week", period="last_30_days",  classes=cls)
    previous = store.compute_stats(group_by="week", period="prior_30_days", classes=cls)
    return {
        "current":  [] if current.empty  else current.to_dict(orient="records"),
        "previous": [] if previous.empty else previous.to_dict(orient="records"),
    }


@router.get("/sparklines")
def sparklines(
    request: Request,
    ids: str,
    _: UserContext = Depends(get_current_user),
):
    store      = get_store(request)
    safe_ids   = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not safe_ids:
        return {}
    return store.student_weekly_rates(safe_ids)
