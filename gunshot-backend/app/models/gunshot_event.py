from sqlalchemy import Column, Integer, Float, BigInteger, JSON
from app.models.base import Base

class GunshotEvent(Base):
    __tablename__ = "gunshot_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(BigInteger, nullable=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    logs = Column(JSON, nullable=False)