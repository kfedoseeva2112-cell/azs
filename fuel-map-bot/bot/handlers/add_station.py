# bot/handlers/add_station.py
from telegram import Update
from telegram.ext import ContextTypes
from ..models.db import SessionLocal
from ..models.station import Station
from ..models.user import User
import json

async def add_station(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправь геолокацию АЗС (кнопка 📎 → Location)")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    user_id = update.effective_user.id

    # Проверяем, есть ли пользователь в БД, если нет – создаём
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id)
        db.add(user)
        db.commit()

    # Создаём новую АЗС (пока без топлива, потом спросим)
    station = Station(
        latitude=location.latitude,
        longitude=location.longitude,
        address="Адрес пока не определён",   # позже через геокодер
        fuel_available={"92": True, "95": True, "98": False, "DT": False},  # заглушка
        added_by_user_id=user_id
    )
    db.add(station)
    db.commit()
    db.close()

    await update.message.reply_text("✅ АЗС добавлена! Спасибо!")
