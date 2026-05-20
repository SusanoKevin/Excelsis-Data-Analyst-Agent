from fastapi import APIRouter, Depends, Request, Response

from api.deps import get_current_user, get_store
from src.security import UserContext

router = APIRouter()


def _parse_classes(classes_str: str) -> list[str] | None:
    classes = [c.strip() for c in classes_str.split(",") if c.strip()]
    return classes or None


@router.get("/summary")
def summary(request: Request, response: Response, _: UserContext = Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, max-age=300"
    return get_store(request).summary()


@router.get("/alerts")
def alerts(
    request: Request,
    response: Response,
    threshold: float = 75.0,
    classes: str = "",
    date_from: str = "",
    date_to: str = "",
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    store = get_store(request)
    df    = store.get_threshold_alerts(
        threshold=threshold,
        classes=_parse_classes(classes),
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return [] if df.empty else df.to_dict(orient="records")


@router.get("/stats")
def stats(
    request: Request,
    response: Response,
    group_by: str = "class",
    period: str = "all",
    classes: str = "",
    date_from: str = "",
    date_to: str = "",
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
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
    response: Response,
    classes: str = "",
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
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
    response: Response,
    ids: str,
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    store    = get_store(request)
    safe_ids = [x.strip() for x in ids.split(",") if 0 < len(x.strip()) <= 50]
    if not safe_ids:
        return {}
    return store.entity_weekly_rates(safe_ids)
