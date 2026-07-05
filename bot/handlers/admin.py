from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..models.db import SessionLocal
from ..models.db_models import User, Station, SupportRequest

async def check_admin(user_id: int) -> bool:
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    is_admin = user.is_admin if user else False
    db.close()
    return is_admin

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "🛠 **Панель администратора**\n\n"
        "Команды:\n"
        "/pending — АЗС на модерации\n"
        "/support_list — новые тикеты поддержки\n"
        "/stats — статистика бота",
        parse_mode="Markdown"
    )

async def list_pending_stations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    
    db = SessionLocal()
    pending = db.query(Station).filter_by(status="pending").all()
    
    if not pending:
        await update.message.reply_text("Нет АЗС на модерации.")
        db.close()
        return

    for s in pending:
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{s.id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{s.id}")
            ]
        ]
        await update.message.reply_text(
            f"📍 **{s.name}**\n🏠 {s.address}\n👤 От: {s.added_by_user_id}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    db.close()

async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_admin(update.effective_user.id):
        await query.answer("У вас нет прав.")
        return
        
    await query.answer()
    data = query.data
    
    db = SessionLocal()
    if data.startswith("approve_"):
        s_id = int(data.replace("approve_", ""))
        station = db.query(Station).filter_by(id=s_id).first()
        if station:
            station.status = "active"
            db.commit()
            await query.edit_message_text(f"✅ АЗС «{station.name}» одобрена!")
            # Уведомление пользователю
            try:
                await context.bot.send_message(station.added_by_user_id, f"🎉 Ваша АЗС «{station.name}» прошла модерацию и теперь видна всем!")
            except: pass
            
    elif data.startswith("reject_"):
        s_id = int(data.replace("reject_", ""))
        station = db.query(Station).filter_by(id=s_id).first()
        if station:
            station.status = "rejected"
            db.commit()
            await query.edit_message_text(f"❌ АЗС «{station.name}» отклонена.")
            try:
                await context.bot.send_message(station.added_by_user_id, f"😔 К сожалению, ваша АЗС «{station.name}» не прошла модерацию.")
            except: pass
    
    db.close()

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Используйте: `/reply user_id текст`", parse_mode="Markdown")
        return
        
    try:
        user_id = int(context.args[0])
        text = " ".join(context.args[1:])
        
        await context.bot.send_message(
            user_id,
            f"📩 **Ответ от администрации:**\n\n{text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке: {e}")
