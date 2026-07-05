from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..models.db import SessionLocal
from ..models.db_models import PersonalStation
from ..keyboards.main_menu import get_main_menu

async def list_personal_stations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    stations = db.query(PersonalStation).filter_by(user_id=user_id).all()
    
    if not stations:
        await update.message.reply_text(
            "📊 У вас пока нет личных АЗС.\nДобавьте их через кнопку «➕ Добавить свою АЗС».",
            reply_markup=get_main_menu()
        )
        db.close()
        return

    response = "📊 **Ваши личные АЗС:**\n\n"
    for s in stations:
        fuels = [f for f, avail in s.fuel_available.items() if avail]
        fuels_str = ", ".join(fuels) if fuels else "не указано"
        response += f"📍 **{s.name}**\n🏠 {s.address}\n⛽️ {fuels_str}\n\n"
        
    # Добавим кнопки управления для последней или через инлайн
    # Для MVP выведем список, а управление сделаем через инлайн кнопки под каждой
    keyboard = []
    for s in stations:
        keyboard.append([
            InlineKeyboardButton(f"📝 {s.name}", callback_data=f"edit_personal_{s.id}"),
            InlineKeyboardButton(f"❌ Удалить", callback_data=f"delete_personal_{s.id}")
        ])
    
    await update.message.reply_text(
        response, 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    db.close()

async def personal_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    station_id = int(query.data.replace("personal_view_", ""))
    db = SessionLocal()
    station = db.query(PersonalStation).filter_by(id=station_id).first()
    
    if not station:
        await query.edit_message_text("Ошибка: АЗС не найдена.")
        db.close()
        return
    
    fuels = [f for f, avail in station.fuel_available.items() if avail]
    fuels_str = ", ".join(fuels) if fuels else "не указано"
    
    text = (
        f"🏠 **Личная АЗС: {station.name}**\n\n"
        f"📍 **Адрес:** {station.address}\n"
        f"⛽ **Топливо:** {fuels_str}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ Удалить", callback_data=f"delete_personal_{station.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    db.close()

async def delete_personal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    station_id = int(query.data.replace("delete_personal_", ""))
    user_id = update.effective_user.id
    
    db = SessionLocal()
    station = db.query(PersonalStation).filter_by(id=station_id, user_id=user_id).first()
    
    if station:
        db.delete(station)
        db.commit()
        await query.edit_message_text(f"✅ Личная АЗС «{station.name}» удалена.")
    else:
        await query.edit_message_text("Ошибка: АЗС не найдена.")
    
    db.close()
