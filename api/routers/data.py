import io
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File

from api.deps import get_current_user, get_store
from api.models import UploadResponse
from src.security import Permission, UserContext, security

router = APIRouter()


@router.get("/summary")
def summary(request: Request, user: UserContext = Depends(get_current_user)):
    store = get_store(request)
    data = store.summary()
    if user.allowed_classes and "classes" in data:
        data["classes"] = [c for c in data["classes"] if c in user.allowed_classes]
    return data


@router.get("/at-risk")
def at_risk(
    request: Request,
    threshold: float = 75.0,
    user: UserContext = Depends(get_current_user),
):
    security.require(user, Permission.READ_AT_RISK, "at_risk")
    store = get_store(request)
    df = store.get_at_risk(threshold=threshold, grade="all")
    df = security.filter_df(df, user)
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/stats")
def stats(
    request: Request,
    group_by: str = "class",
    period: str = "all",
    user: UserContext = Depends(get_current_user),
):
    store = get_store(request)
    df = store.compute_stats(group_by=group_by, period=period)
    df = security.filter_df(df, user)
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/sparklines")
def sparklines(
    request: Request,
    ids: str,
    user: UserContext = Depends(get_current_user),
):
    security.require(user, Permission.READ_AT_RISK, "sparklines")
    store = get_store(request)
    requested = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not requested:
        return {}
    filtered = security.filter_df(store.merged(), user)
    if filtered.empty:
        return {}
    authorized = {int(sid) for sid in filtered["student_id"].unique()}
    safe_ids = [sid for sid in requested if sid in authorized]
    return store.student_weekly_rates(safe_ids)


@router.post("/upload", response_model=UploadResponse)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
):
    security.require(user, Permission.INGEST_DATA, "upload")
    content = await file.read()
    name = file.filename or "upload"
    suffix = name.rsplit(".", 1)[-1].lower()

    try:
        if suffix == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif suffix in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content))
        elif suffix == "parquet":
            df = pd.read_parquet(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    store = get_store(request)
    result = store.ingest_df(df, name=name.rsplit(".", 1)[0])

    vec = request.app.state.vec
    vec.index_store_summaries(store)

    return UploadResponse(
        dataset_id=result["dataset_id"],
        rows=result["rows"],
        columns=result["columns"],
        message=f"Ingested {result['rows']:,} rows from '{name}'",
    )
