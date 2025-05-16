from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.log_event import LogEvent
from app.models.microphone import Microphone
from app.utils.database import get_db
from fastapi.responses import JSONResponse

import random
import time
import math

router = APIRouter()

def random_base_in_michigan():
    """Return a random lat/lon within Michigan's bounding box"""
    lat = random.uniform(41.6, 45.0)
    lon = random.uniform(-87.0, -83.0)
    return lat, lon

def offset_coordinates(lat, lon, max_distance_meters):
    """Offset coordinates randomly within max_distance_meters (~200ft)"""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, max_distance_meters)

    delta_lat = (distance * math.cos(angle)) / 111_320
    delta_lon = (distance * math.sin(angle)) / (40075000 * math.cos(math.radians(lat)) / 360)

    return lat + delta_lat, lon + delta_lon

@router.post("/generate_test_logs")
async def generate_test_logs(db: AsyncSession = Depends(get_db)):
    try:
        # ✅ Get the current max mic_id
        result = await db.execute(select(func.max(Microphone.mic_id)))
        max_mic_id = result.scalar() or 0

        base_lat, base_lon = random_base_in_michigan()
        timestamp = int(time.time())  # seconds

        logs = []
        mic_ids = []

        for i in range(4):
            lat, lon = offset_coordinates(base_lat, base_lon, 60)
            mic_id = max_mic_id + i + 1

            # ✅ Check if log already exists
            existing_log = await db.execute(
                select(LogEvent).where(LogEvent.mic_id == mic_id, LogEvent.timestamp == timestamp)
            )
            if existing_log.scalar_one_or_none():
                continue  # Skip duplicates

            # ✅ Insert LogEvent
            log = LogEvent(mic_id=mic_id, lat=lat, lon=lon, timestamp=timestamp)
            db.add(log)
            mic_ids.append(mic_id)

            # ✅ Insert/Update Microphone
            existing_mic = await db.execute(select(Microphone).where(Microphone.mic_id == mic_id))
            mic_record = existing_mic.scalar_one_or_none()

            if mic_record:
                mic_record.lat = lat
                mic_record.lon = lon
            else:
                mic = Microphone(mic_id=mic_id, lat=lat, lon=lon)
                db.add(mic)

        await db.commit()

        return JSONResponse(status_code=201, content={
            "message": "4 synthetic logs and microphones inserted.",
            "base_location": {"lat": base_lat, "lon": base_lon},
            "timestamp": timestamp,
            "mic_ids": mic_ids
        })

    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        await db.close()