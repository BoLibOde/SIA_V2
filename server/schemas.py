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


class SummaryResponse(BaseModel):
    device_id: str
    range: str
    counts: MoodCountsSchema
    sensor_avg: SensorAverageSchema
    score: float
    smiley: str


class GlobalSummaryResponse(BaseModel):
    range: str
    device_count: int
    counts: MoodCountsSchema
    sensor_avg: SensorAverageSchema
    score: float
    smiley: str


class HistoryEntrySchema(BaseModel):
    period_start: str
    period_end: str
    counts: MoodCountsSchema
    score: float
    smiley: str
    avg_temperature_c: float
    avg_humidity_pct: float
    avg_co2_ppm: int


class HistoryResponse(BaseModel):
    device_id: str
    hours: int
    entries: list[HistoryEntrySchema]
