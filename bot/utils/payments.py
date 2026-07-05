from datetime import datetime, timedelta
from ..models.db import SessionLocal
from ..models.db_models import User
from telegram import LabeledPrice

STARS_SUBSCRIPTION_PRICE = 50 # 50 Stars

def check_subscription(user_id: int) -> bool:
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        db.close()
        return False
    
    if user.is_admin:
        db.close()
        return True
        
    if user.subscription_until and user.subscription_until > datetime.utcnow():
        db.close()
        return True
    
    db.close()
    return False

async def create_subscription_invoice(update, context):
    title = "Премиум подписка «Народная АЗС»"
    description = "Доступ к публичным АЗС, уведомлениям о топливе и построению маршрутов на 30 дней."
    payload = "premium_subscription_30_days"
    currency = "XTR" # Telegram Stars
    prices = [LabeledPrice("Подписка на 1 месяц", STARS_SUBSCRIPTION_PRICE)]

    await context.bot.send_invoice(
        update.effective_chat.id,
        title,
        description,
        payload,
        "", # Provider token empty for Stars
        currency,
        prices
    )

def add_subscription_days(user_id: int, days: int = 30):
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id)
        db.add(user)
    
    now = datetime.utcnow()
    if user.subscription_until and user.subscription_until > now:
        user.subscription_until += timedelta(days=days)
    else:
        user.subscription_until = now + timedelta(days=days)
    
    db.commit()
    db.close()
