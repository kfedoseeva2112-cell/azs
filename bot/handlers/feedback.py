from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from ..models.db import SessionLocal
from ..models.db_models import User, Review, BotReview, SupportRequest
from ..keyboards.main_menu import get_main_menu

ENTERING_REVIEW, ENTERING_SUPPORT = range(2)

async def start_bot_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(str(i) + " ⭐", callback_data=f"bot_rate_{i}") for i in range(1, 6)]]
    await update.message.reply_text(
        "⭐ Оцените работу нашего бота:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bot_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rating = int(query.data.replace("bot_rate_", ""))
    context.user_data["bot_rating"] = rating
    await query.edit_message_text(f"Вы поставили {rating} ⭐. Напишите ваш отзыв (или отправьте «-», чтобы пропустить):")
    return ENTERING_REVIEW

async def handle_bot_review_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 В меню":
        from .start import start
        return await start(update, context)
        
    rating = context.user_data.get("bot_rating")
    user_id = update.effective_user.id
    
    db = SessionLocal()
    review = BotReview(user_id=user_id, rating=rating, comment=text if text != "-" else "")
    db.add(review)
    db.commit()
    db.close()
    
    await update.message.reply_text("✅ Спасибо за ваш отзыв!", reply_markup=get_main_menu())
    
    # Уведомление всем админам об отзыве
    db = SessionLocal()
    admins = db.query(User).filter_by(is_admin=True).all()
    for admin in admins:
        try:
            await context.bot.send_message(
                admin.id, 
                f"🌟 **Новый отзыв о боте!**\nОценка: {rating} ⭐\nТекст: {text}"
            )
        except: pass
    db.close()
    
    return ConversationHandler.END

# Поддержка
async def start_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напишите ваше сообщение в поддержку. Мы ответим в ближайшее время.\n\n"
        "Чтобы отменить, нажмите кнопку «🔙 В меню»",
        reply_markup=get_main_menu()
    )
    return ENTERING_SUPPORT

async def handle_support_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔙 В меню":
        from .start import start
        return await start(update, context)
        
    user_id = update.effective_user.id
    username = update.effective_user.username or "без username"
    
    db = SessionLocal()
    req = SupportRequest(user_id=user_id, message=text)
    db.add(req)
    db.commit()
    db.close()
    
    await update.message.reply_text("✅ Ваше сообщение отправлено в поддержку.", reply_markup=get_main_menu())
    
    # Пересылка всем админам
    db = SessionLocal()
    admins = db.query(User).filter_by(is_admin=True).all()
    for admin in admins:
        try:
            await context.bot.send_message(
                admin.id,
                f"📬 **Новое сообщение в поддержку!**\nОт: ID {user_id} (@{username})\n\n{text}\n\n"
                f"Чтобы ответить, используйте: `/reply {user_id} Ваш ответ`",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error sending to admin {admin.id}: {e}")
    db.close()
        
    return ConversationHandler.END
