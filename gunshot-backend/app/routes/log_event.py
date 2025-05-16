from fastapi import APIRouter, Depends, HTTPException
from app.models.log_event import LogEvent
from app.models.schemas.log_event import LogEventCreate
from app.utils.database import get_db
from app.utils.debounce import handle_debounce
from app.models.microphone import Microphone
from app.utils.websocket_manager import manager
from app.auth.verify_api_key import verify_api_key
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from sqlalchemy import select
from geopy.distance import geodesic
import asyncio

router = APIRouter()

@router.post("/log_event")
async def log_event(event: LogEventCreate, db: AsyncSession = Depends(get_db),
                    api_key: str = Depends(verify_api_key)):
    global last_trigger_time, debounce_task

    try:
        # ✅ Validate latitude & longitude
        if not (-90 <= event.lat <= 90):
            return JSONResponse(status_code=400, content={"error": f"Invalid latitude: {event.lat}"})
        if not (-180 <= event.lon <= 180):
            return JSONResponse(status_code=400, content={"error": f"Invalid longitude: {event.lon}"})

        # ✅ Validate timestamp (convert from microseconds to seconds)
        timestamp_sec = event.timestamp / 1e6
        now = datetime.now(timezone.utc).timestamp()

        if timestamp_sec <= 0 or timestamp_sec > now + (365 * 24 * 60 * 60):  # Must not be >1 year ahead
            return JSONResponse(status_code=400, content={"error": f"Invalid timestamp: {event.timestamp}"})

        # ✅ Offload DB check for duplicate logs (Avoid blocking request)
        existing_log = await db.execute(
            select(LogEvent).where(LogEvent.mic_id == event.mic_id, LogEvent.timestamp == event.timestamp)
        )
        if existing_log.scalar_one_or_none():
            return {"message": "Duplicate log detected"}

        # ✅ Create log entry asynchronously
        log_entry = LogEvent(**event.dict())
        db.add(log_entry)
        await db.commit()

        # ✅ Offload microphone location update
        should_broadcast = await update_microphone_location(db, event)

        # ✅ Broadcast sensor update if needed (Offloaded)
        if should_broadcast:
            asyncio.create_task(broadcast_sensor_update(db))

        #print(f"log timestamp: {event.timestamp}")
        # ✅ Debounced gunshot detection
        await handle_debounce(event.timestamp)

        return {"message": "Log event recorded", "id": log_entry.id}

    except Exception as e:
        print(f"Unhandled error in log_event: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await db.close()

async def update_microphone_location(db: AsyncSession, event: LogEventCreate):
    """ Update microphone location if moved significantly, and determine if broadcast is needed """
    try:
        existing_mic = await db.execute(
            select(Microphone).where(Microphone.mic_id == event.mic_id)
        )
        mic_record = existing_mic.scalar_one_or_none()

        if mic_record:
            # Compute distance only if location changes
            old_location = (mic_record.lat, mic_record.lon)
            new_location = (event.lat, event.lon)
            distance = geodesic(old_location, new_location).meters

            if distance > 10:
                mic_record.lat, mic_record.lon = event.lat, event.lon
                await db.commit()  # Commit only when needed
                return True
        else:
            # Insert new microphone record
            new_mic = Microphone(mic_id=event.mic_id, lat=event.lat, lon=event.lon)
            db.add(new_mic)
            await db.commit()
            return True
        
        return False
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        await db.close()

async def broadcast_sensor_update(db: AsyncSession):
    """ Asynchronously broadcast updated sensor list """
    try:
        sensors_result = await db.execute(select(Microphone))
        sensors = sensors_result.scalars().all()

        sensor_list = [{"mic_id": mic.mic_id, "lat": mic.lat, "lon": mic.lon} for mic in sensors]

        await manager.broadcast({"type": "sensor_update", "sensors": sensor_list})
    except Exception as e:
        raise e 
    finally:
        await db.close()