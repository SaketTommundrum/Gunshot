import asyncio
from app.utils.database import AsyncSessionLocal
from app.utils.detect_gunshots import detect_gunshots

DEBOUNCE_TIME = 1  # seconds
latest_log_timestamp = None  # Tracks the latest timestamp
debounce_task = None
debounce_lock = asyncio.Lock()

async def debounce_detect_gunshots():
    global latest_log_timestamp, debounce_task
    nsec = 2  # Time window for gunshot detection

    while True:
        await asyncio.sleep(DEBOUNCE_TIME)

        async with debounce_lock:
            # Get the latest timestamp and reset it to avoid missing future logs
            timestamp_to_process = latest_log_timestamp
            latest_log_timestamp = None

        if timestamp_to_process:
            start_time = timestamp_to_process - int(nsec * 1e6)
            end_time = timestamp_to_process

            #print(f"Triggering gunshot detection from {start_time} to {end_time}")

            async with AsyncSessionLocal() as db:
                try:
                    await detect_gunshots(start_time, end_time, db)
                except Exception as e:
                    print(f"Error during gunshot detection: {e}")

async def handle_debounce(new_timestamp):
    global latest_log_timestamp, debounce_task

    async with debounce_lock:
        # Always update the latest log timestamp
        if latest_log_timestamp is None or new_timestamp > latest_log_timestamp:
            latest_log_timestamp = new_timestamp

        # Start debounce task only once
        if debounce_task is None or debounce_task.done():
            debounce_task = asyncio.create_task(debounce_detect_gunshots())
