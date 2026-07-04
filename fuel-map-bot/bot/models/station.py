# bot/models/station.py
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from .db import Base
from datetime import datetime

class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)          # название АЗС (если есть)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    fuel_available = Column(JSON, nullable=False, default=dict)  # {"92": True, "95": False, ...}
    added_by_user_id = Column(Integer, nullable=False)           # кто добавил
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
