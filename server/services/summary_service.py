from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from server.models import Device, HourlyUpload
from server.schemas import (
    GlobalSummaryResponse,
    HistoryEntrySchema,
    MoodCountsSchema,
    SensorAverageSchema,
    SummaryResponse,
)


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


def get_device_summary(db: Session, device_id: str, range_name: str) -> SummaryResponse | None:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = _range_start(now, range_name)

    result = (
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
        .one()
    )

    good, neutral, bad, avg_temp, avg_hum, avg_co2 = result
    total = good + neutral + bad
    score = 0.0 if total == 0 else (good - bad) / total

    return SummaryResponse(
        device_id=device.device_id,
        range=range_name,
        counts=MoodCountsSchema(good=good, neutral=neutral, bad=bad),
        sensor_avg=SensorAverageSchema(
            temperature_c=round(float(avg_temp), 2),
            humidity_pct=round(float(avg_hum), 2),
            co2_ppm=int(round(float(avg_co2))),
        ),
        score=round(float(score), 3),
        smiley=_score_to_smiley(score),
    )


def get_global_summary(db: Session, range_name: str) -> GlobalSummaryResponse:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = _range_start(now, range_name)

    result = (
        db.query(
            func.coalesce(func.sum(HourlyUpload.good_count), 0),
            func.coalesce(func.sum(HourlyUpload.neutral_count), 0),
            func.coalesce(func.sum(HourlyUpload.bad_count), 0),
            func.coalesce(func.avg(HourlyUpload.avg_temperature_c), 0.0),
            func.coalesce(func.avg(HourlyUpload.avg_humidity_pct), 0.0),
            func.coalesce(func.avg(HourlyUpload.avg_co2_ppm), 0.0),
            func.count(func.distinct(HourlyUpload.device_id)),
        )
        .filter(HourlyUpload.period_start >= start_time)
        .filter(HourlyUpload.period_start <= now)
        .one()
    )

    good, neutral, bad, avg_temp, avg_hum, avg_co2, device_count = result
    total = good + neutral + bad
    score = 0.0 if total == 0 else (good - bad) / total

    return GlobalSummaryResponse(
        range=range_name,
        device_count=int(device_count),
        counts=MoodCountsSchema(good=good, neutral=neutral, bad=bad),
        sensor_avg=SensorAverageSchema(
            temperature_c=round(float(avg_temp), 2),
            humidity_pct=round(float(avg_hum), 2),
            co2_ppm=int(round(float(avg_co2))),
        ),
        score=round(float(score), 3),
        smiley=_score_to_smiley(score),
    )


def get_device_history(db: Session, device_id: str, hours: int) -> list[HistoryEntrySchema] | None:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=hours)

    rows = (
        db.query(HourlyUpload)
        .filter(HourlyUpload.device_id == device.id)
        .filter(HourlyUpload.period_start >= since)
        .order_by(HourlyUpload.period_start)
        .all()
    )

    entries = []
    for row in rows:
        total = row.good_count + row.neutral_count + row.bad_count
        score = 0.0 if total == 0 else (row.good_count - row.bad_count) / total
        entries.append(
            HistoryEntrySchema(
                period_start=row.period_start.isoformat(),
                period_end=row.period_end.isoformat(),
                counts=MoodCountsSchema(
                    good=row.good_count,
                    neutral=row.neutral_count,
                    bad=row.bad_count,
                ),
                score=round(float(score), 3),
                smiley=_score_to_smiley(score),
                avg_temperature_c=row.avg_temperature_c,
                avg_humidity_pct=row.avg_humidity_pct,
                avg_co2_ppm=row.avg_co2_ppm,
            )
        )
    return entries
