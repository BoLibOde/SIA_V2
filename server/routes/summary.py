from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.db import get_db
from server.schemas import GlobalSummaryResponse, HistoryResponse, SummaryResponse
from server.services import summary_service


router = APIRouter(prefix="/api/v1", tags=["summary"])


@router.get("/devices/{device_id}/summary", response_model=SummaryResponse)
def get_device_summary(
    device_id: str,
    range: str = Query(default="day", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    result = summary_service.get_device_summary(db, device_id, range)
    if result is None:
        raise HTTPException(status_code=404, detail="device not found")
    return result


@router.get("/summary/global", response_model=GlobalSummaryResponse)
def get_global_summary(
    range: str = Query(default="day", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db),
) -> GlobalSummaryResponse:
    return summary_service.get_global_summary(db, range)


@router.get("/devices/{device_id}/history", response_model=HistoryResponse)
def get_device_history(
    device_id: str,
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    entries = summary_service.get_device_history(db, device_id, hours)
    if entries is None:
        raise HTTPException(status_code=404, detail="device not found")
    return HistoryResponse(device_id=device_id, hours=hours, entries=entries)

