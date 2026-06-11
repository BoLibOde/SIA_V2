from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.db import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    hourly_uploads: Mapped[list["HourlyUpload"]] = relationship(back_populates="device")
    live_state: Mapped["DeviceLiveState | None"] = relationship(back_populates="device", uselist=False)
    location_history: Mapped[list["DeviceLocation"]] = relationship(back_populates="device")


class HourlyUpload(Base):
    __tablename__ = "hourly_uploads"
    __table_args__ = (
        UniqueConstraint("device_id", "period_start", name="uq_hourly_upload_device_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    good_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    bad_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_temperature_c: Mapped[float] = mapped_column(Float)
    avg_humidity_pct: Mapped[float] = mapped_column(Float)
    avg_co2_ppm: Mapped[int] = mapped_column(Integer)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device: Mapped[Device] = relationship(back_populates="hourly_uploads")


class DeviceLiveState(Base):
    __tablename__ = "device_live_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), unique=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    latest_mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    today_good_count: Mapped[int] = mapped_column(Integer, default=0)
    today_neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    today_bad_count: Mapped[int] = mapped_column(Integer, default=0)
    latest_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_co2_ppm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device: Mapped[Device] = relationship(back_populates="live_state")


class DeviceLocation(Base):
    __tablename__ = "device_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    location: Mapped[str] = mapped_column(String(200), index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, index=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device: Mapped[Device] = relationship(back_populates="location_history")
