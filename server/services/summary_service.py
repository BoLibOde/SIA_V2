from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from server.models import Device, HourlyUpload
from server.schemas import (
    HistoryEntrySchema,
    MoodCountsSchema,
    SensorAverageSchema,
)


def _score_to_smiley(score: float) -> str:
    if score > 0.25:
        return "good"
    if score < -0.25:
        return "bad"
    return "neutral"


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
                avg_temperature_c=float(row.avg_temperature_c),
                avg_humidity_pct=float(row.avg_humidity_pct),
                avg_co2_ppm=int(row.avg_co2_ppm),
            )
        )
    return entries
