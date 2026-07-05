from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models.db import SessionLocal
from bot.models.db_models import Station, PersonalStation
from bot.keyboards.main_menu import get_main_menu
import math

# Константы для поиска
SEARCH_RADIUS_KM = 50.0
DEGREE_LAT_KM = 111.0 # 1 градус широты ~ 111 км

async def search_stations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос геолокации для поиска списка АЗС"""
    context.user_data["search_mode"] = "list"
    await update.message.reply_text(
        "🔍 Отправьте вашу геолокацию, чтобы я нашел список ближайших АЗС.\n\n"
        "Чтобы отменить, нажмите «🔙 В меню»",
        reply_markup=get_main_menu()
    )

async def show_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос геолокации для открытия карты"""
    context.user_data["search_mode"] = "map"
    await update.message.reply_text(
        "🗺️ Отправьте вашу геолокацию, чтобы я открыл карту АЗС в вашем районе.\n\n"
        "Чтобы отменить, нажмите «🔙 В меню»",
        reply_markup=get_main_menu()
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной геолокации и поиск АЗС"""
    if not update.message.location:
        return
    
    user_lat = update.message.location.latitude
    user_lon = update.message.location.longitude
    mode = context.user_data.get("search_mode", "list")
    
    # Индикация процесса
    wait_msg = await update.message.reply_text("⏳ Ищем заправки, пожалуйста, подождите...")
    
    if mode == "map":
        # Ссылка на карту со всеми АЗС
        map_url = f"https://www.openstreetmap.org/?mlat={user_lat}&mlon={user_lon}#map=13/{user_lat}/{user_lon}"
        try:
            await wait_msg.delete()
        except:
            pass
        await update.message.reply_text(
            "🗺️ **Интерактивная карта АЗС в вашем районе готова!**\n\n"
            "Нажмите кнопку ниже, чтобы открыть карту в браузере:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Открыть карту", url=map_url)],
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
            ])
        )
        context.user_data["search_mode"] = None
        return
    
    # Оптимизация Bounding Box согласно ТЗ
    # 1 градус широты = 111 км. 50 км = ~0.45 градуса.
    # 1 градус долготы = 111 * cos(lat) км.
    delta_lat = SEARCH_RADIUS_KM / 111.0
    delta_lon = SEARCH_RADIUS_KM / (111.0 * math.cos(math.radians(user_lat)))
    
    min_lat, max_lat = user_lat - delta_lat, user_lat + delta_lat
    min_lon, max_lon = user_lon - delta_lon, user_lon + delta_lon
    
    db = SessionLocal()
    try:
        # Быстрый поиск через Bounding Box и индексы
        # Убираем статус 'active' для теста, так как при импорте он мог не проставиться
        stations = db.query(Station).filter(
            Station.latitude.between(min_lat, max_lat),
            Station.longitude.between(min_lon, max_lon)
        ).all()
        
        personal = db.query(PersonalStation).filter(
            PersonalStation.user_id == update.effective_user.id,
            PersonalStation.latitude.between(min_lat, max_lat),
            PersonalStation.longitude.between(min_lon, max_lon)
        ).all()
        
        all_nearby = []
        
        # Точный расчет расстояния для отфильтрованных АЗС
        for s in stations + personal:
            dist = get_distance(user_lat, user_lon, s.latitude, s.longitude)
            if dist <= SEARCH_RADIUS_KM:
                all_nearby.append((s, dist))
        
        all_nearby.sort(key=lambda x: x[1])
        top_results = all_nearby[:5]
        
        if not top_results:
            await wait_msg.delete()
            await update.message.reply_text(
                "К сожалению, в радиусе 50 км АЗС не найдены.", 
                reply_markup=get_main_menu()
            )
            return

        response = "📍 **Ближайшие АЗС:**\n\n"
        keyboard = []
        
        for i, (s, dist) in enumerate(top_results, 1):
            is_personal = isinstance(s, PersonalStation)
            type_str = "🏠 Личная" if is_personal else "⛽ Публичная"
            
            # Добавляем информацию о топливе
            fuel_str = ""
            if hasattr(s, 'fuel_available') and s.fuel_available:
                available = [f for f, avail in s.fuel_available.items() if avail]
                if available:
                    fuel_str = "⛽ " + ", ".join(available)
            
            response += f"🔘 **{s.name}** ({dist:.1f} км)\n📍 `{s.address}`\n{fuel_str}\n\n"
            btn_text = f"🔎 {s.name} ({dist:.1f} км)"
            callback_data = f"station_view_{s.id}" if not is_personal else f"personal_view_{s.id}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        
        # Ссылка на карту
        map_url = f"https://www.openstreetmap.org/?mlat={user_lat}&mlon={user_lon}#map=13/{user_lat}/{user_lon}"
        keyboard.append([InlineKeyboardButton("🗺 Открыть интерактивную карту", url=map_url)])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
        try:
            await wait_msg.delete()
        except:
            pass
        
        await update.message.reply_text(
            response, 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["search_mode"] = None
    finally:
        db.close()

def get_distance(lat1, lon1, lat2, lon2):
    """Расчет расстояния по формуле гаверсинусов"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
