from sqlalchemy import Column, Integer, Float
from app.models.base import Base

class Microphone(Base):
    __tablename__ = "microphones"
    mic_id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)