from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.db import get_db
from server.models import Device, DeviceLiveState, HourlyUpload
from server.schemas import (
    HourlyUploadRequest,
    HourlyUploadResponse,
    LiveIngestRequest,
    LiveStateResponse,
    MoodCountsSchema,
)


router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/hourly", response_model=HourlyUploadResponse)
def ingest_hourly(payload: HourlyUploadRequest, db: Session = Depends(get_db)) -> HourlyUploadResponse:
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=400, detail="period_end must be after period_start")

    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if device is None:
        device = Device(
            device_id=payload.device_id,
            created_at=_now_naive_utc(),
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
        created_at=_now_naive_utc(),
    )

    device.last_seen_at = _now_naive_utc()

    db.add(hourly_upload)
    db.commit()

    return HourlyUploadResponse(status="ok", stored=True)


@router.post("/live", response_model=LiveStateResponse)
def ingest_live(payload: LiveIngestRequest, db: Session = Depends(get_db)) -> LiveStateResponse:
    event_time = payload.timestamp or _now_naive_utc()

    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if device is None:
        device = Device(
            device_id=payload.device_id,
            created_at=_now_naive_utc(),
        )
        db.add(device)
        db.flush()

    live_state = db.query(DeviceLiveState).filter(DeviceLiveState.device_id == device.id).first()
    if live_state is None:
        live_state = DeviceLiveState(device_id=device.id)
        db.add(live_state)

    live_state.last_seen_at = event_time
    live_state.latest_mood = payload.latest_mood
    live_state.today_good_count = payload.today_counts.good
    live_state.today_neutral_count = payload.today_counts.neutral
    live_state.today_bad_count = payload.today_counts.bad
    live_state.latest_temperature_c = payload.sensor_current.temperature_c
    live_state.latest_humidity_pct = payload.sensor_current.humidity_pct
    live_state.latest_co2_ppm = payload.sensor_current.co2_ppm
    live_state.updated_at = _now_naive_utc()

    device.last_seen_at = event_time
    db.commit()

    return LiveStateResponse(
        device_id=device.device_id,
        location=device.location,
        last_seen_at=live_state.last_seen_at,
        latest_mood=live_state.latest_mood,
        today_counts=MoodCountsSchema(
            good=live_state.today_good_count,
            neutral=live_state.today_neutral_count,
            bad=live_state.today_bad_count,
        ),
        sensor_current={
            "temperature_c": live_state.latest_temperature_c,
            "humidity_pct": live_state.latest_humidity_pct,
            "co2_ppm": live_state.latest_co2_ppm,
        },
    )
