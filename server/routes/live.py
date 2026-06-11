from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.db import get_db
from server.models import Device, DeviceLiveState, HourlyUpload
from server.schemas import LiveDashboardResponse, LiveStateResponse, MoodCountsSchema


router = APIRouter(prefix="/api/v1", tags=["live"])


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _device_live_payload(device: Device, live_state: DeviceLiveState) -> LiveStateResponse:
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


@router.get("/live", response_model=LiveDashboardResponse)
def get_live_dashboard(db: Session = Depends(get_db)) -> LiveDashboardResponse:
    rows = (
        db.query(Device, DeviceLiveState)
        .join(DeviceLiveState, DeviceLiveState.device_id == Device.id)
        .order_by(DeviceLiveState.last_seen_at.desc())
        .all()
    )
    devices = [_device_live_payload(device, live_state) for device, live_state in rows]
    return LiveDashboardResponse(devices=devices, generated_at=_now_naive_utc())


@router.get("/devices/{device_id}/live", response_model=LiveStateResponse)
def get_device_live(device_id: str, db: Session = Depends(get_db)) -> LiveStateResponse:
    row = (
        db.query(Device, DeviceLiveState)
        .join(DeviceLiveState, DeviceLiveState.device_id == Device.id)
        .filter(Device.device_id == device_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="device live state not found")
    return _device_live_payload(row[0], row[1])


@router.get("/devices/{device_id}/today", response_model=LiveStateResponse)
def get_device_today(device_id: str, db: Session = Depends(get_db)) -> LiveStateResponse:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    live_state = db.query(DeviceLiveState).filter(DeviceLiveState.device_id == device.id).first()
    if live_state is not None:
        return _device_live_payload(device, live_state)

    now = _now_naive_utc()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.query(HourlyUpload)
        .filter(HourlyUpload.device_id == device.id)
        .filter(HourlyUpload.period_start >= start_of_day)
        .filter(HourlyUpload.period_start <= now)
        .all()
    )
    good = sum(row.good_count for row in rows)
    neutral = sum(row.neutral_count for row in rows)
    bad = sum(row.bad_count for row in rows)

    if rows:
        sensor_count = len(rows)
        temperature = sum(float(row.avg_temperature_c) for row in rows) / sensor_count
        humidity = sum(float(row.avg_humidity_pct) for row in rows) / sensor_count
        co2 = int(round(sum(float(row.avg_co2_ppm) for row in rows) / sensor_count))
    else:
        temperature = None
        humidity = None
        co2 = None

    return LiveStateResponse(
        device_id=device.device_id,
        location=device.location,
        last_seen_at=device.last_seen_at,
        latest_mood=None,
        today_counts=MoodCountsSchema(good=good, neutral=neutral, bad=bad),
        sensor_current={"temperature_c": temperature, "humidity_pct": humidity, "co2_ppm": co2},
    )
