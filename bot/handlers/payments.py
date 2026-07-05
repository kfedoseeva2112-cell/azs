from telegram import Update
from telegram.ext import ContextTypes
from ..utils.payments import add_subscription_days, create_subscription_invoice

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from ..models.db import SessionLocal
    from ..models.db_models import User
    
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    is_admin = user.is_admin if user else False
    db.close()
    
    if is_admin:
        await update.message.reply_text(
            "💎 **Статус: Администратор**\n\n"
            "Вам доступны все премиум-функции бота бесплатно:\n"
            "✅ Добавление публичных АЗС\n"
            "✅ Уведомления о топливе\n"
            "✅ Построение маршрутов\n"
            "✅ Просмотр всех заявок",
            parse_mode="Markdown"
        )
        return

    await create_subscription_invoice(update, context)

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Мы всегда принимаем платеж
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    
    if payload == "premium_subscription_30_days":
        add_subscription_days(user_id, 30)
        await update.message.reply_text(
            "🎉 Спасибо за поддержку! Премиум-подписка активирована на 30 дней.\n"
            "Теперь вам доступны публичные АЗС, уведомления и маршруты!"
        )
