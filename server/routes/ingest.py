from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.db import get_db
from server.models import Device, HourlyUpload
from server.schemas import HourlyUploadRequest, HourlyUploadResponse


router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("/hourly", response_model=HourlyUploadResponse)
def ingest_hourly(payload: HourlyUploadRequest, db: Session = Depends(get_db)) -> HourlyUploadResponse:
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=400, detail="period_end must be after period_start")

    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if device is None:
        device = Device(
            device_id=payload.device_id,
            created_at=datetime.utcnow(),
        )
        db.add(device)
        db.flush()

    existing = (
        db.query(HourlyUpload)
        .filter(HourlyUpload.device_id == device.id)
        .filter(HourlyUpload.period_start == payload.period_start)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="hourly upload already exists for this period")

    hourly_upload = HourlyUpload(
        device_id=device.id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        good_count=payload.mood_counts.good,
        neutral_count=payload.mood_counts.neutral,
        bad_count=payload.mood_counts.bad,
        avg_temperature_c=payload.sensor_avg.temperature_c,
        avg_humidity_pct=payload.sensor_avg.humidity_pct,
        avg_co2_ppm=payload.sensor_avg.co2_ppm,
        sample_count=payload.sample_count,
        created_at=datetime.utcnow(),
    )

    device.last_seen_at = datetime.utcnow()

    db.add(hourly_upload)
    db.commit()

    return HourlyUploadResponse(status="ok", stored=True)
