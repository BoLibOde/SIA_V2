from datetime import datetime, timedelta

from device.models import HourlyUploadPayload, MoodCounts, SensorReading


class AggregationService:
    def build_hourly_payload(
        self,
        device_id: str,
        mood_counts: MoodCounts,
        sensor_samples: list[SensorReading],
        now: datetime | None = None,
    ) -> HourlyUploadPayload | None:
        if not sensor_samples:
            return None

        current_time = now or datetime.utcnow()
        period_end = current_time.replace(minute=0, second=0, microsecond=0)
        period_start = period_end - timedelta(hours=1)

        filtered_samples = [
            sample
            for sample in sensor_samples
            if period_start <= sample.timestamp < period_end
        ]

        if not filtered_samples:
            return None

        avg_temperature = sum(sample.temperature_c for sample in filtered_samples) / len(filtered_samples)
        avg_humidity = sum(sample.humidity_pct for sample in filtered_samples) / len(filtered_samples)
        avg_co2 = sum(sample.co2_ppm for sample in filtered_samples) / len(filtered_samples)

        return HourlyUploadPayload(
            device_id=device_id,
            period_start=period_start,
            period_end=period_end,
            mood_counts=MoodCounts(
                good=mood_counts.good,
                neutral=mood_counts.neutral,
                bad=mood_counts.bad,
            ),
            sensor_avg_temperature_c=round(avg_temperature, 2),
            sensor_avg_humidity_pct=round(avg_humidity, 2),
            sensor_avg_co2_ppm=int(round(avg_co2)),
            sample_count=len(filtered_samples),
        )
