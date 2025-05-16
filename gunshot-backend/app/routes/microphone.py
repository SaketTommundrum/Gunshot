from fastapi import APIRouter, Depends, HTTPException
from app.models.microphone import Microphone
from app.models.schemas.microphone import MicrophoneSchema
from app.utils.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

@router.get("/get_sensors", response_model=list[MicrophoneSchema])
async def get_sensors(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Microphone))
        microphones = result.scalars().all()
        return [{"mic_id": mic.mic_id, "lat": mic.lat, "lon": mic.lon} for mic in microphones]
    except Exception as e:
        print(f"Error fetching sensors: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.close()  # Ensure the DB session is closed    