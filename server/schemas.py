from datetime import datetime

from pydantic import BaseModel, Field


class MoodCountsSchema(BaseModel):
    good: int = Field(default=0, ge=0)
    neutral: int = Field(default=0, ge=0)
    bad: int = Field(default=0, ge=0)


class SensorAverageSchema(BaseModel):
    temperature_c: float
    humidity_pct: float
    co2_ppm: int


class LiveSensorSchema(BaseModel):
    temperature_c: float | None = None
    humidity_pct: float | None = None
    co2_ppm: int | None = None


class HourlyUploadRequest(BaseModel):
    device_id: str
    period_start: datetime
    period_end: datetime
    mood_counts: MoodCountsSchema
    sensor_avg: SensorAverageSchema
    sample_count: int = Field(default=0, ge=0)


class HourlyUploadResponse(BaseModel):
    status: str = "ok"
    stored: bool = True


class LiveIngestRequest(BaseModel):
    device_id: str
    timestamp: datetime | None = None
    latest_mood: str | None = Field(default=None, pattern="^(good|neutral|bad)$")
    today_counts: MoodCountsSchema
    sensor_current: LiveSensorSchema = Field(default_factory=LiveSensorSchema)


class LiveStateResponse(BaseModel):
    device_id: str
    location: str | None = None
    last_seen_at: datetime | None = None
    latest_mood: str | None = None
    today_counts: MoodCountsSchema
    sensor_current: LiveSensorSchema


class LiveDashboardResponse(BaseModel):
    devices: list[LiveStateResponse]
    generated_at: datetime


class DeviceLocationAssignRequest(BaseModel):
    location: str = Field(min_length=1, max_length=200)
    valid_from: datetime | None = None


class DeviceLocationSchema(BaseModel):
    location: str
    valid_from: datetime
    valid_to: datetime | None = None


class DeviceLocationAssignResponse(BaseModel):
    status: str = "ok"
    device_id: str
    location: DeviceLocationSchema


class SummarySeriesPointSchema(BaseModel):
    bucket_start: datetime
    device_id: str
    location: str | None = None
    counts: MoodCountsSchema
    sensor_avg: SensorAverageSchema
    score: float
    smiley: str


class SummaryResponse(BaseModel):
    from_dt: datetime
    to_dt: datetime
    group_by: str
    device_filter: str | None = None
    location_filter: str | None = None
    counts: MoodCountsSchema
    percentages: MoodCountsSchema
    sensor_avg: SensorAverageSchema
    score: float
    smiley: str
    series: list[SummarySeriesPointSchema]
