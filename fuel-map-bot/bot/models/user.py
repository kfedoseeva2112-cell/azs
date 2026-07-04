# bot/models/user.py
from sqlalchemy import Column, Integer, DateTime
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)   # Telegram user_id
    subscription_until = Column(DateTime, nullable=True)  # когда истекает подписка
    created_at = Column(DateTime, default=datetime.utcnow)
