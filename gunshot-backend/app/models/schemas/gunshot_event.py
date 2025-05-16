from pydantic import BaseModel

class GunshotEventSchema(BaseModel):
    id: int
    timestamp: int
    lat: float
    lon: float
    logs: object