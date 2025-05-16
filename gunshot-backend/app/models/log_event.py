from sqlalchemy import Column, Integer, Float, BigInteger
from app.models.base import Base

class LogEvent(Base):
    __tablename__ = "log_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(BigInteger, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    mic_id = Column(Integer, nullable=False)