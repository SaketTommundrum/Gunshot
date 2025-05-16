from pydantic import BaseModel

class LogEventCreate(BaseModel):
    timestamp: int
    lat: float
    lon: float
    mic_id: int