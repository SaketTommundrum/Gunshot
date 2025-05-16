from fastapi import APIRouter, Query, Depends, HTTPException
from app.models.gunshot_event import GunshotEvent
from app.models.schemas.gunshot_event import GunshotEventSchema
from app.utils.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

@router.get("/gunshot_events", response_model=list[GunshotEventSchema])
async def get_gunshot_events(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(GunshotEvent).order_by(GunshotEvent.timestamp.desc()))
        events = result.scalars().all()
        return events
    except Exception as e:
        print(f"Error fetching gunshot events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.close()
        