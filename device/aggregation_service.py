from datetime import UTC, datetime, timedelta

from device.models import HourlyUploadPayload, MoodCounts, SensorReading


class AggregationService:
    def build_15min_payload(
        self,
        device_id: str,
        sensor_samples: list[SensorReading],
        now: datetime | None = None,
    ) -> HourlyUploadPayload | None:
        """Build a payload for the most recently completed 15-minute window.

        The completed window is determined by snapping the current time back to
        the nearest 15-minute boundary (HH:00, HH:15, HH:30, HH:45):
          period_end   = floor(now, 15 min)
          period_start = period_end - 15 min

        Only samples whose timestamp falls in [period_start, period_end) are
        included.  Mood counts are deliberately omitted: live uploads are the
        sole source of mood measurements and must not be double-counted here.
        """
        current_time = now or datetime.now(UTC)
        quarter = (current_time.minute // 15) * 15
        period_end = current_time.replace(minute=quarter, second=0, microsecond=0)
        period_start = period_end - timedelta(minutes=15)

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
            mood_counts=MoodCounts(),
            sensor_avg_temperature_c=round(avg_temperature, 2),
            sensor_avg_humidity_pct=round(avg_humidity, 2),
            sensor_avg_co2_ppm=int(round(avg_co2)),
            sample_count=len(filtered_samples),
        )

    def build_hourly_payload(
        self,
        device_id: str,
        mood_counts: MoodCounts,
        sensor_samples: list[SensorReading],
        now: datetime | None = None,
    ) -> HourlyUploadPayload | None:
        if not sensor_samples:
            return None

        current_time = now or datetime.now(UTC)
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

    def build_window_payload(
        self,
        device_id: str,
        mood_counts: MoodCounts,
        sensor_samples: list[SensorReading],
        period_start: datetime,
        period_end: datetime,
    ) -> HourlyUploadPayload | None:
        """Build a payload for an arbitrary time window.

        Used by manual upload (U key) to aggregate the data accumulated since the
        last successful aggregate upload checkpoint, without re-sending anything
        that was already uploaded.  ``mood_counts`` must reflect only the presses
        since that checkpoint (i.e. ``gpio_handler.get_hourly_counts()`` which is
        cleared after every successful aggregate upload).
        """
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
