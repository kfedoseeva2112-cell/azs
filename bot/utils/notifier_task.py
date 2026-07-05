import asyncio
from ..models.db import SessionLocal
from ..models.db_models import FuelNotification, Station, PersonalStation, User
from datetime import datetime

async def check_fuel_notifications(context):
    db = SessionLocal()
    notifications = db.query(FuelNotification).all()
    
    for n in notifications:
        # Проверяем подписку пользователя (на всякий случай)
        user = db.query(User).filter_by(id=n.user_id).first()
        if not user or (user.subscription_until and user.subscription_until < datetime.utcnow() and not user.is_admin):
            continue

        station = None
        if n.is_personal:
            station = db.query(PersonalStation).filter_by(id=n.station_id).first()
        else:
            station = db.query(Station).filter_by(id=n.station_id, status="active").first()
            
        if station and station.fuel_available.get(n.fuel_type):
            # Топливо появилось! Отправляем уведомление
            try:
                msg = f"🔔 **На АЗС {station.name} появилось топливо {n.fuel_type}!**\n📍 {station.address}"
                await context.bot.send_message(chat_id=n.user_id, text=msg, parse_mode="Markdown")
                # Удаляем уведомление после отправки (или оставляем, если нужно постоянно)
                db.delete(n)
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
                
    db.commit()
    db.close()
