from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.db import get_db
from server.models import Device, DeviceLocation, HourlyUpload
from server.schemas import (
    MoodCountsSchema,
    SensorAverageSchema,
    SummaryResponse,
    SummarySeriesPointSchema,
)


summary_router = APIRouter(prefix="/api/v1", tags=["summary"])
legacy_router = APIRouter(prefix="/api/v1/devices", tags=["summary"])


def _score_to_smiley(score: float) -> str:
    if score > 0.25:
        return "good"
    if score < -0.25:
        return "bad"
    return "neutral"


def _bucket_start(ts: datetime, group_by: str) -> datetime:
    if group_by == "hour":
        return ts.replace(minute=0, second=0, microsecond=0)
    if group_by == "day":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    if group_by == "week":
        week_start = ts - timedelta(days=ts.weekday())
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    if group_by == "month":
        return ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if group_by == "year":
        return ts.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


def _summary_range(now: datetime, range_name: str) -> tuple[datetime, datetime]:
    if range_name == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_name == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_name == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif range_name == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _build_location_map(db: Session, device_ids: set[int]) -> dict[int, list[DeviceLocation]]:
    if not device_ids:
        return {}
    rows = (
        db.query(DeviceLocation)
        .filter(DeviceLocation.device_id.in_(device_ids))
        .order_by(DeviceLocation.device_id.asc(), DeviceLocation.valid_from.asc())
        .all()
    )
    result: dict[int, list[DeviceLocation]] = defaultdict(list)
    for row in rows:
        result[row.device_id].append(row)
    return result


def _location_at(history: list[DeviceLocation], ts: datetime) -> str | None:
    found = None
    for item in history:
        if item.valid_from <= ts and (item.valid_to is None or ts < item.valid_to):
            found = item.location
    return found


def _build_summary(
    db: Session,
    from_dt: datetime,
    to_dt: datetime,
    group_by: str,
    device_filter: str | None = None,
    location_filter: str | None = None,
) -> SummaryResponse:
    base_query = (
        db.query(HourlyUpload, Device)
        .join(Device, Device.id == HourlyUpload.device_id)
        .filter(HourlyUpload.period_start >= from_dt)
        .filter(HourlyUpload.period_start <= to_dt)
    )
    if device_filter:
        base_query = base_query.filter(Device.device_id == device_filter)
    rows = base_query.order_by(HourlyUpload.period_start.asc()).all()

    device_pk_ids = {device.id for _, device in rows}
    location_map = _build_location_map(db, device_pk_ids)

    totals_good = 0
    totals_neutral = 0
    totals_bad = 0
    weighted_temp_sum = 0.0
    weighted_humidity_sum = 0.0
    weighted_co2_sum = 0.0
    weighted_sensor_count = 0

    grouped: dict[tuple[datetime, str, str | None], dict[str, float | int]] = defaultdict(
        lambda: {
            "good": 0,
            "neutral": 0,
            "bad": 0,
            "temp_sum": 0.0,
            "humidity_sum": 0.0,
            "co2_sum": 0.0,
            "weight": 0,
        }
    )

    for upload, device in rows:
        location = _location_at(location_map.get(device.id, []), upload.period_start) or device.location
        if location_filter and location != location_filter:
            continue

        totals_good += upload.good_count
        totals_neutral += upload.neutral_count
        totals_bad += upload.bad_count

        sensor_weight = upload.sample_count if upload.sample_count > 0 else 1
        weighted_sensor_count += sensor_weight
        weighted_temp_sum += float(upload.avg_temperature_c) * sensor_weight
        weighted_humidity_sum += float(upload.avg_humidity_pct) * sensor_weight
        weighted_co2_sum += float(upload.avg_co2_ppm) * sensor_weight

        bucket = _bucket_start(upload.period_start, group_by)
        group_key = (bucket, device.device_id, location)
        grouped[group_key]["good"] += upload.good_count
        grouped[group_key]["neutral"] += upload.neutral_count
        grouped[group_key]["bad"] += upload.bad_count
        grouped[group_key]["temp_sum"] += float(upload.avg_temperature_c) * sensor_weight
        grouped[group_key]["humidity_sum"] += float(upload.avg_humidity_pct) * sensor_weight
        grouped[group_key]["co2_sum"] += float(upload.avg_co2_ppm) * sensor_weight
        grouped[group_key]["weight"] += sensor_weight

    total_votes = totals_good + totals_neutral + totals_bad
    if weighted_sensor_count > 0:
        avg_temperature = round(weighted_temp_sum / weighted_sensor_count, 2)
        avg_humidity = round(weighted_humidity_sum / weighted_sensor_count, 2)
        avg_co2 = int(round(weighted_co2_sum / weighted_sensor_count))
    else:
        avg_temperature = 0.0
        avg_humidity = 0.0
        avg_co2 = 0

    score = 0.0 if total_votes == 0 else (totals_good - totals_bad) / total_votes
    percentages = MoodCountsSchema(
        good=0 if total_votes == 0 else int(round((totals_good * 100) / total_votes)),
        neutral=0 if total_votes == 0 else int(round((totals_neutral * 100) / total_votes)),
        bad=0 if total_votes == 0 else int(round((totals_bad * 100) / total_votes)),
    )

    series: list[SummarySeriesPointSchema] = []
    for key in sorted(grouped.keys(), key=lambda item: (item[0], item[1], item[2] or "")):
        bucket, device_id, location = key
        values = grouped[key]
        bucket_total = int(values["good"] + values["neutral"] + values["bad"])
        bucket_score = 0.0 if bucket_total == 0 else (values["good"] - values["bad"]) / bucket_total
        weight = int(values["weight"])
        if weight > 0:
            bucket_temperature = round(float(values["temp_sum"]) / weight, 2)
            bucket_humidity = round(float(values["humidity_sum"]) / weight, 2)
            bucket_co2 = int(round(float(values["co2_sum"]) / weight))
        else:
            bucket_temperature = 0.0
            bucket_humidity = 0.0
            bucket_co2 = 0
        series.append(
            SummarySeriesPointSchema(
                bucket_start=bucket,
                device_id=device_id,
                location=location,
                counts=MoodCountsSchema(
                    good=int(values["good"]),
                    neutral=int(values["neutral"]),
                    bad=int(values["bad"]),
                ),
                sensor_avg=SensorAverageSchema(
                    temperature_c=bucket_temperature,
                    humidity_pct=bucket_humidity,
                    co2_ppm=bucket_co2,
                ),
                score=round(float(bucket_score), 3),
                smiley=_score_to_smiley(bucket_score),
            )
        )

    return SummaryResponse(
        from_dt=from_dt,
        to_dt=to_dt,
        group_by=group_by,
        device_filter=device_filter,
        location_filter=location_filter,
        counts=MoodCountsSchema(good=totals_good, neutral=totals_neutral, bad=totals_bad),
        percentages=percentages,
        sensor_avg=SensorAverageSchema(
            temperature_c=avg_temperature,
            humidity_pct=avg_humidity,
            co2_ppm=avg_co2,
        ),
        score=round(float(score), 3),
        smiley=_score_to_smiley(score),
        series=series,
    )


@summary_router.get("/summary", response_model=SummaryResponse)
def get_summary(
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    device_id: str | None = Query(default=None),
    location: str | None = Query(default=None),
    group_by: str = Query(default="day", pattern="^(hour|day|week|month|year)$"),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    now = datetime.utcnow()
    resolved_from = from_dt or now.replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_to = to_dt or now
    if resolved_to <= resolved_from:
        raise HTTPException(status_code=400, detail="to must be after from")
    return _build_summary(
        db=db,
        from_dt=resolved_from,
        to_dt=resolved_to,
        group_by=group_by,
        device_filter=device_id,
        location_filter=location,
    )


@legacy_router.get("/{device_id}/summary", response_model=SummaryResponse)
def get_device_summary_legacy(
    device_id: str,
    range: str = Query(default="day", pattern="^(day|week|month|year)$"),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    now = datetime.utcnow()
    start, end = _summary_range(now, range)
    return _build_summary(
        db=db,
        from_dt=start,
        to_dt=end,
        group_by="day",
        device_filter=device_id,
        location_filter=None,
    )
