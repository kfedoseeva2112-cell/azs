# bot/handlers/start.py
from telegram import Update
from telegram.ext import ContextTypes
from ..keyboards.main_menu import get_main_menu
from ..models.db import SessionLocal
from ..models.db_models import User

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Регистрация пользователя
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id)
        db.add(user)
        db.commit()
    db.close()

    text = (
        "👋 Привет! Это Народная карта АЗС.\n\n"
        "📍 Находите ближайшие заправки.\n"
        "➕ Добавляйте новые АЗС и делитесь информацией о топливе.\n"
        "🚀 Стройте маршруты через проверенные заправки."
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, reply_markup=get_main_menu())
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu())
