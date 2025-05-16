from fastapi import APIRouter, Query, Depends, HTTPException
from app.models.schemas.log_event import LogEventCreate
from app.models.log_event import LogEvent
from app.utils.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

@router.get("/get_all_logs", response_model=list[LogEventCreate])
async def get_all_logs(
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(LogEvent).order_by(LogEvent.timestamp))
        logs = result.scalars().all()
        return logs

    except Exception as e:
        print(f"Error fetching all logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.close()