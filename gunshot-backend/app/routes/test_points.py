from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log_event import LogEvent
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
    base_lat, base_lon = random_base_in_michigan()
    timestamp = int(time.time())  # microseconds

    logs = []
    for i in range(4):
        lat, lon = offset_coordinates(base_lat, base_lon, 60)  # 60 meters = 200 feet
        log = LogEvent(
            mic_id=100 + i,
            lat=lat,
            lon=lon,
            timestamp=timestamp
        )
        logs.append(log)

    try:
        db.add_all(logs)
        await db.commit()
        return JSONResponse(status_code=201, content={
            "message": "4 synthetic logs inserted.",
            "base_location": {"lat": base_lat, "lon": base_lon},
            "timestamp": timestamp,
            "mic_ids": [log.mic_id for log in logs]
        })
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await db.close()
