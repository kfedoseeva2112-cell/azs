from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from ..models.db import SessionLocal
from ..models.db_models import Station, PersonalStation
from ..utils.geo import get_address_from_coords
from ..utils.payments import check_subscription
from ..keyboards.fuel_choices import get_fuel_keyboard
from ..keyboards.main_menu import get_main_menu

CHOOSING_TYPE, CHOOSING_LOCATION, ENTERING_NAME, ENTERING_ADDRESS, CHOOSING_FUEL = range(5)

async def add_station_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_premium = check_subscription(user_id)
    
    keyboard = [[KeyboardButton("🏠 Личная (только для меня)")]]
    if is_premium:
        keyboard.append([KeyboardButton("🌍 Публичная (для всех, модерация)")])
    else:
        keyboard.append([KeyboardButton("💎 Публичная (нужен Премиум)")])
        
    await update.message.reply_text(
        "Какой тип АЗС вы хотите добавить?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSING_TYPE

async def handle_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user_id = update.effective_user.id
    
    if "Публичная" in choice:
        if not check_subscription(user_id):
            await update.message.reply_text(
                "Добавление публичных АЗС доступно только владельцам Премиум-подписки.",
                reply_markup=get_main_menu()
            )
            return ConversationHandler.END
        context.user_data["is_public"] = True
    else:
        context.user_data["is_public"] = False
        
    await update.message.reply_text("Пожалуйста, отправьте геолокацию АЗС.")
    return CHOOSING_LOCATION

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    context.user_data["lat"] = location.latitude
    context.user_data["lon"] = location.longitude
    
    # Проверка на дубликаты
    db = SessionLocal()
    is_public = context.user_data["is_public"]
    user_id = update.effective_user.id
    
    # Погрешность 0.0001 (~11 метров)
    epsilon = 0.0001
    
    if is_public:
        exists = db.query(Station).filter(
            Station.latitude.between(location.latitude - epsilon, location.latitude + epsilon),
            Station.longitude.between(location.longitude - epsilon, location.longitude + epsilon)
        ).first()
    else:
        exists = db.query(PersonalStation).filter(
            PersonalStation.user_id == user_id,
            PersonalStation.latitude.between(location.latitude - epsilon, location.latitude + epsilon),
            PersonalStation.longitude.between(location.longitude - epsilon, location.longitude + epsilon)
        ).first()
        
    if exists:
        await update.message.reply_text(
            f"Такая АЗС уже существует ({exists.name}). Вы можете найти её в поиске или отредактировать.",
            reply_markup=get_main_menu()
        )
        db.close()
        return ConversationHandler.END
    
    db.close()
    await update.message.reply_text("Введите название АЗС (например, Лукойл или Моя любимая).")
    return ENTERING_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    
    # Пытаемся получить адрес автоматически
    address = get_address_from_coords(context.user_data["lat"], context.user_data["lon"])
    context.user_data["address"] = address
    
    await update.message.reply_text(
        f"Определенный адрес: {address}\nЕсли он неверный, введите правильный адрес вручную. Если верный, просто напишите «Да».",
    )
    return ENTERING_ADDRESS

async def handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() != "да":
        context.user_data["address"] = text
        
    context.user_data["selected_fuels"] = []
    await update.message.reply_text(
        "Выберите доступное топливо:",
        reply_markup=get_fuel_keyboard([])
    )
    return CHOOSING_FUEL

async def fuel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    selected = context.user_data.get("selected_fuels", [])
    
    if data == "fuel_done":
        db = SessionLocal()
        is_public = context.user_data["is_public"]
        fuel_available = {
            "АИ-92": "АИ-92" in selected,
            "АИ-95": "АИ-95" in selected,
            "АИ-98": "АИ-98" in selected,
            "ДТ": "ДТ" in selected
        }
        
        if is_public:
            station = Station(
                name=context.user_data["name"],
                address=context.user_data["address"],
                latitude=context.user_data["lat"],
                longitude=context.user_data["lon"],
                fuel_available=fuel_available,
                status="pending", # На модерацию
                added_by_user_id=update.effective_user.id
            )
            db.add(station)
            db.flush() # Чтобы получить ID станции
            msg = "✅ Публичная АЗС отправлена на модерацию!"
            
            # Уведомление всем админам
            from ..models.db_models import User
            admins = db.query(User).filter_by(is_admin=True).all()
            for admin in admins:
                try:
                    await context.bot.send_message(
                        admin.id,
                        f"⛽️ **Новая АЗС на модерации!**\nНазвание: {station.name}\nАдрес: {station.address}\n\n"
                        f"Используйте /pending для проверки.",
                        parse_mode="Markdown"
                    )
                except: pass
        else:
            station = PersonalStation(
                user_id=update.effective_user.id,
                name=context.user_data["name"],
                address=context.user_data["address"],
                latitude=context.user_data["lat"],
                longitude=context.user_data["lon"],
                fuel_available=fuel_available
            )
            db.add(station)
            msg = "✅ Личная АЗС добавлена! Она видна только вам."
            
        db.commit()
        db.close()
        await query.edit_message_text(msg)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Возврат в главное меню.",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END

    fuel_type = data.replace("fuel_", "")
    if fuel_type in selected:
        selected.remove(fuel_type)
    else:
        selected.append(fuel_type)
    
    context.user_data["selected_fuels"] = selected
    await query.edit_message_reply_markup(reply_markup=get_fuel_keyboard(selected))
    return CHOOSING_FUEL
