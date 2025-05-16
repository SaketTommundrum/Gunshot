from fastapi import Query, Depends, HTTPException
from app.models.gunshot_event import GunshotEvent
from app.models.schemas.gunshot_event import GunshotEventSchema
from app.utils.database import get_db
from app.models.log_event import LogEvent
from app.utils.estimate_gunshot_location import estimate_gunshot_location
from app.utils.websocket_manager import manager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections import defaultdict
import asyncio



async def detect_gunshots(
    start_time: int = Query(None), 
    end_time: int = Query(None), 
    db: AsyncSession = Depends(get_db)
):
    TIME_THRESHOLD = 1_000_000  # 1 seconds in microseconds 

    # Fetch logs within the specified time range asynchronously
    query = select(LogEvent).order_by(LogEvent.timestamp)
    if start_time is not None:
        query = query.where(LogEvent.timestamp >= start_time)
    else:
        query = query.where(LogEvent.timestamp >= int((datetime.now(timezone.utc).timestamp() - 5) * 1e6))
    if end_time is not None:
        query = query.where(LogEvent.timestamp <= end_time)
    else:
        query = query.where(LogEvent.timestamp <= int(datetime.now(timezone.utc).timestamp() * 1e6))

    result = await db.execute(query)
    logs = sorted(result.scalars().all(), key=lambda log: log.timestamp)
    
    print(f'len(logs) = {len(logs)}')

    grouped_events = []
    active_groups = []

    for log in logs:
        added_to_group = False
        merge_candidates = []

        for group in active_groups:
            #print(f"Checking log {log.id} against group with min_time={group['min_time']} max_time={group['max_time']} mics={group['mic_ids']}")
            if (
                abs(log.timestamp - group["min_time"]) <= TIME_THRESHOLD
                and abs(log.timestamp - group["max_time"]) <= TIME_THRESHOLD
                and log.mic_id not in group["mic_ids"]
            ):
                #print(f"Log {log.id} added to an existing group")
                merge_candidates.append(group)

        if merge_candidates:
            target_group = merge_candidates[0]  # Merge into the closest existing group
            target_group["logs"].append(log)
            target_group["min_time"] = min(target_group["min_time"], log.timestamp)
            target_group["max_time"] = max(target_group["max_time"], log.timestamp)
            target_group["mic_ids"].add(log.mic_id)
            added_to_group = True

        if not added_to_group:
            #print(f"Creating a new group for log {log.id} (mic_id={log.mic_id}, timestamp={log.timestamp})")
            active_groups.append({
                "logs": [log],
                "mic_ids": {log.mic_id},
                "min_time": log.timestamp,
                "max_time": log.timestamp
            })

    #print(f"active_groups: {active_groups}")

    # Filter groups with at least three unique mic_ids
    grouped_events = [group["logs"] for group in active_groups if len(group["mic_ids"]) >= 3]
    # print(f"grouped_events = {grouped_events}")

    # Process gunshot event detection
    gunshot_events = []
    new_events = []

    for group in grouped_events:
        if len(group) < 3:
            continue

        # Keep only the first occurrence of each mic_id
        # unique_logs = {log.mic_id: log for log in group}
        unique_logs = {}
        for log in group:
            if log.mic_id not in unique_logs:
                unique_logs[log.mic_id] = log

        filtered_group = list(unique_logs.values())

        event_location = estimate_gunshot_location(filtered_group)
        if event_location:
            new_event = GunshotEvent(
                timestamp=event_location["time"],
                lat=event_location["lat"],
                lon=event_location["lon"],
                logs=[{
                    "id": l.id,
                    "timestamp": l.timestamp,
                    "lat": l.lat,
                    "lon": l.lon,
                    "mic_id": l.mic_id
                } for l in filtered_group]
            )
            new_events.append(new_event)

            gunshot_events.append({
                "logs": new_event.logs,
                "estimated_location": event_location
            })

    # Bulk insert all events asynchronously
    try:
        if new_events:
            db.add_all(new_events)
            await db.commit()
    except Exception as e:
        await db.rollback()  # Roll back on failure
        print(f"Error processing gunshot events: {e}")
    finally:
        await db.close()
    if gunshot_events:
        # Send detected gunshot events via WebSocket asynchronously
        asyncio.create_task(broadcast_gunshot_event({"gunshot_events": gunshot_events}))

    return {"gunshot_events": gunshot_events}

async def broadcast_gunshot_event(event_data: dict):
    """Send gunshot event to all connected WebSocket clients."""
    await manager.broadcast(event_data)