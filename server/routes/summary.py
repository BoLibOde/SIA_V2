from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.db import get_db
from server.models import Device, HourlyUpload
from server.schemas import MoodCountsSchema, SensorAverageSchema, SummaryResponse


router = APIRouter(prefix="/api/v1/devices", tags=["summary"])


def _score_to_smiley(score: float) -> str:
    if score > 0.25:
        return "good"
    if score < -0.25:
        return "bad"
    return "neutral"


def _range_start(now: datetime, range_name: str) -> datetime:
    if range_name == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_name == "week":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_name == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/{device_id}/summary", response_model=SummaryResponse)
def get_summary(
    device_id: str,
    range: str = Query(default="day", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = _range_start(now, range)

    query = (
        db.query(
            func.coalesce(func.sum(HourlyUpload.good_count), 0),
            func.coalesce(func.sum(HourlyUpload.neutral_count), 0),
            func.coalesce(func.sum(HourlyUpload.bad_count), 0),
            func.coalesce(func.avg(HourlyUpload.avg_temperature_c), 0.0),
            func.coalesce(func.avg(HourlyUpload.avg_humidity_pct), 0.0),
            func.coalesce(func.avg(HourlyUpload.avg_co2_ppm), 0.0),
        )
        .filter(HourlyUpload.device_id == device.id)
        .filter(HourlyUpload.period_start >= start_time)
        .filter(HourlyUpload.period_start <= now)
    )

    result = query.one()
    good_count, neutral_count, bad_count, avg_temperature_c, avg_humidity_pct, avg_co2_ppm = result

    total = good_count + neutral_count + bad_count
    score = 0.0 if total == 0 else (good_count - bad_count) / total
    smiley = _score_to_smiley(score)

    return SummaryResponse(
        device_id=device.device_id,
        range=range,
        counts=MoodCountsSchema(
            good=good_count,
            neutral=neutral_count,
            bad=bad_count,
        ),
        sensor_avg=SensorAverageSchema(
            temperature_c=round(float(avg_temperature_c), 2),
            humidity_pct=round(float(avg_humidity_pct), 2),
            co2_ppm=int(round(float(avg_co2_ppm))),
        ),
        score=round(float(score), 3),
        smiley=smiley,
    )
