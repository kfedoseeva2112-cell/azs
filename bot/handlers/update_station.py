# bot/handlers/update_station.py
from telegram import Update
from telegram.ext import ContextTypes
from ..models.db import SessionLocal
from ..models.db_models import Station
from ..keyboards.fuel_choices import get_fuel_keyboard
from ..keyboards.main_menu import get_main_menu

async def update_fuel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    station_id = int(query.data.replace("update_fuel_", ""))
    context.user_data["editing_station_id"] = station_id
    
    db = SessionLocal()
    station = db.query(Station).filter_by(id=station_id).first()
    
    if not station:
        await query.edit_message_text("Ошибка: АЗС не найдена.")
        db.close()
        return

    # Загружаем текущие выбранные типы топлива
    selected = [f for f, avail in station.fuel_available.items() if avail]
    context.user_data["selected_fuels"] = selected
    
    await query.edit_message_text(
        f"⛽️ Обновление статуса АЗС: {station.name}\n📍 {station.address}\n\nВыберите доступное топливо:",
        reply_markup=get_fuel_keyboard(selected)
    )
    db.close()

async def update_fuel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    selected = context.user_data.get("selected_fuels", [])
    station_id = context.user_data.get("editing_station_id")
    
    if not station_id:
        await query.edit_message_text("Сессия истекла. Попробуйте поиск заново.")
        return

    if data.startswith("fuel_"):
        fuel_type = data.replace("fuel_", "")
        
        if fuel_type == "done":
            db = SessionLocal()
            station = db.query(Station).filter_by(id=station_id).first()
            
            if station:
                fuel_available = {
                    "АИ-92": "АИ-92" in selected,
                    "АИ-95": "АИ-95" in selected,
                    "АИ-98": "АИ-98" in selected,
                    "ДТ": "ДТ" in selected
                }
                station.fuel_available = fuel_available
                db.commit()
                
                await query.edit_message_text(f"✅ Статус топлива на АЗС {station.name} успешно обновлен!")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Чем еще могу помочь?",
                    reply_markup=get_main_menu()
                )
            else:
                await query.edit_message_text("Ошибка при сохранении.")
            
            db.close()
            context.user_data.clear()
            return

        # Переключение выбора
        if fuel_type in selected:
            selected.remove(fuel_type)
        else:
            selected.append(fuel_type)
        
        context.user_data["selected_fuels"] = selected
        await query.edit_message_reply_markup(reply_markup=get_fuel_keyboard(selected))

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def station_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    station_id = int(query.data.replace("station_view_", ""))
    db = SessionLocal()
    station = db.query(Station).filter_by(id=station_id).first()
    
    if not station:
        await query.edit_message_text("Ошибка: АЗС не найдена.")
        db.close()
        return
    
    # Формируем текст карточки
    fuel_info = station.fuel_types if hasattr(station, 'fuel_types') and station.fuel_types else "АИ-92: 52.50₽, АИ-95: 57.80₽, ДТ: 63.20₽"
    
    text = (
        f"📦 **Карточка АЗС: {station.name}**\n\n"
        f"📍 **Адрес:** {station.address}\n"
        f"⛽ **Наличие топлива:**\n{fuel_info}\n\n"
        f"⭐ **Рейтинг:** 4.5/5 (12 отзывов)\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("⛽ Обновить статус", callback_data=f"update_fuel_{station.id}")],
        [InlineKeyboardButton("🔔 Подписаться на наличие", callback_data=f"sub_fuel_{station.id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    db.close()
