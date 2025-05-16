from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log_event import LogEvent
from app.models.gunshot_event import GunshotEvent
from app.models.microphone import Microphone
from app.utils.database import get_db
from app.auth.verify_api_key import verify_api_key  # if you still want this protected

router = APIRouter()

@router.delete("/delete_events")
async def delete_all_events_and_microphones(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),  # remove this line if you don’t need auth
):
    """
    DELETE /gunshot_events
    — Remove every GunshotEvent,LogEvent and every Microphone.
    """
    try:
        # 1) Bulk‑delete all gunshot events
        await db.execute(delete(GunshotEvent))
        # 2) Bulk‑delete all microphones
        await db.execute(delete(Microphone))
        # 3) Bulk‑delete all log events
        await db.execute(delete(LogEvent))
        # 4) Commit both as one transaction
        await db.commit()

        return {
            "message": "All gunshot events, logs and microphones have been deleted successfully"
        }
    except Exception as e:
        print(f"Error clearing gunshot events & microphones: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.close()
