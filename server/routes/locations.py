from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.db import get_db
from server.models import Device, DeviceLocation
from server.schemas import (
    DeviceLocationAssignRequest,
    DeviceLocationAssignResponse,
    DeviceLocationSchema,
)


router = APIRouter(prefix="/api/v1/devices", tags=["locations"])


@router.post("/{device_id}/location", response_model=DeviceLocationAssignResponse)
def assign_device_location(
    device_id: str,
    payload: DeviceLocationAssignRequest,
    db: Session = Depends(get_db),
) -> DeviceLocationAssignResponse:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    start_time = payload.valid_from or datetime.utcnow()
    open_range = (
        db.query(DeviceLocation)
        .filter(DeviceLocation.device_id == device.id)
        .filter(DeviceLocation.valid_to.is_(None))
        .order_by(DeviceLocation.valid_from.desc())
        .first()
    )
    if open_range is not None:
        if start_time <= open_range.valid_from:
            raise HTTPException(
                status_code=400,
                detail="valid_from must be after current location valid_from",
            )
        open_range.valid_to = start_time

    location_row = DeviceLocation(
        device_id=device.id,
        location=payload.location,
        valid_from=start_time,
        valid_to=None,
        created_at=datetime.utcnow(),
    )
    db.add(location_row)
    device.location = payload.location
    db.commit()
    db.refresh(location_row)

    return DeviceLocationAssignResponse(
        status="ok",
        device_id=device.device_id,
        location=DeviceLocationSchema(
            location=location_row.location,
            valid_from=location_row.valid_from,
            valid_to=location_row.valid_to,
        ),
    )


@router.get("/{device_id}/locations", response_model=list[DeviceLocationSchema])
def get_device_locations(device_id: str, db: Session = Depends(get_db)) -> list[DeviceLocationSchema]:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    rows = (
        db.query(DeviceLocation)
        .filter(DeviceLocation.device_id == device.id)
        .order_by(DeviceLocation.valid_from.asc())
        .all()
    )
    return [
        DeviceLocationSchema(location=row.location, valid_from=row.valid_from, valid_to=row.valid_to)
        for row in rows
    ]
