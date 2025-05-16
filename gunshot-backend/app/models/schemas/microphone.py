from pydantic import BaseModel

class MicrophoneSchema(BaseModel):
    mic_id: int
    lat: float
    lon: float