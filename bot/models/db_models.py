from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True) # Telegram ID
    username = Column(String)
    subscription_until = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Station(Base):
    __tablename__ = 'stations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    fuel_available = Column(JSON) # e.g. {"АИ-92": true, "АИ-95": false, ...}
    verified = Column(Boolean, default=False)
    partner = Column(Boolean, default=False)
    status = Column(String, default='active') # active, pending, rejected
    added_by_user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class PersonalStation(Base):
    __tablename__ = 'personal_stations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    fuel_available = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey('stations.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer)
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class BotReview(Base):
    __tablename__ = 'bot_reviews'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer)
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class SupportRequest(Base):
    __tablename__ = 'support_requests'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    message = Column(String)
    status = Column(String, default='new') # new, closed
    created_at = Column(DateTime, default=datetime.utcnow)

class FuelNotification(Base):
    __tablename__ = 'fuel_notifications'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    station_id = Column(Integer) # Can be from 'stations' or 'personal_stations'
    is_personal = Column(Boolean, default=False)
    fuel_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
