from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models.db import SessionLocal
from bot.models.db_models import PersonalStation
from bot.keyboards.main_menu import get_main_menu
from bot.utils.osm_api import search_stations_nearby
import math

SEARCH_RADIUS_KM = 50.0

async def search_stations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["search_mode"] = "list"
    await update.message.reply_text(
        "🔍 Отправьте вашу геолокацию, чтобы я нашел список ближайших АЗС.\n\n"
        "Чтобы отменить, нажмите «🔙 В меню»",
        reply_markup=get_main_menu()
    )

async def show_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["search_mode"] = "map"
    await update.message.reply_text(
        "🗺️ Отправьте вашу геолокацию, чтобы я открыл карту АЗС в вашем районе.\n\n"
        "Чтобы отменить, нажмите «🔙 В меню»",
        reply_markup=get_main_menu()
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        return

    user_lat = update.message.location.latitude
    user_lon = update.message.location.longitude
    mode = context.user_data.get("search_mode", "list")

    wait_msg = await update.message.reply_text("⏳ Ищем заправки, пожалуйста, подождите...")

    if mode == "map":
        map_url = f"https://www.openstreetmap.org/?mlat={user_lat}&mlon={user_lon}#map=13/{user_lat}/{user_lon}"
        await wait_msg.delete()
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

    # ---- ПОИСК ЧЕРЕЗ OSM (публичные АЗС) ----
    osm_stations = await search_stations_nearby(user_lat, user_lon, radius_km=SEARCH_RADIUS_KM, limit=20)

    # ---- ЛИЧНЫЕ СТАНЦИИ ИЗ БД ----
    db = SessionLocal()
    personal_stations = []
    try:
        personal = db.query(PersonalStation).filter(
            PersonalStation.user_id == update.effective_user.id
        ).all()
        for ps in personal:
            dist = get_distance(user_lat, user_lon, ps.latitude, ps.longitude)
            if dist <= SEARCH_RADIUS_KM:
                personal_stations.append((ps, dist))
    finally:
        db.close()

    # ---- ОБЪЕДИНЯЕМ И СОРТИРУЕМ ----
    all_nearby = []

    # Добавляем OSM станции (превращаем в объект-подобие Station)
    for osm in osm_stations:
        dist = get_distance(user_lat, user_lon, osm['lat'], osm['lon'])
        all_nearby.append({
            'name': osm['name'],
            'address': osm['address'],
            'lat': osm['lat'],
            'lon': osm['lon'],
            'dist': dist,
            'is_personal': False,
            'fuel_available': osm.get('tags', {}).get('fuel', ''),
            'id': None  # для публичных нет id в БД
        })

    # Добавляем личные станции
    for ps, dist in personal_stations:
        all_nearby.append({
            'name': ps.name,
            'address': ps.address,
            'lat': ps.latitude,
            'lon': ps.longitude,
            'dist': dist,
            'is_personal': True,
            'fuel_available': ps.fuel_available if hasattr(ps, 'fuel_available') else {},
            'id': ps.id
        })

    all_nearby.sort(key=lambda x: x['dist'])
    top_results = all_nearby[:5]

    if not top_results:
        await wait_msg.delete()
        await update.message.reply_text(
            "К сожалению, в радиусе 50 км АЗС не найдены.",
            reply_markup=get_main_menu()
        )
        return

    # ---- ФОРМИРУЕМ ОТВЕТ ----
    response = "📍 **Ближайшие АЗС:**\n\n"
    keyboard = []

    for i, s in enumerate(top_results, 1):
        type_str = "🏠 Личная" if s['is_personal'] else "⛽ Публичная"
        fuel_str = ""
        if s['fuel_available']:
            if isinstance(s['fuel_available'], dict):
                available = [f for f, avail in s['fuel_available'].items() if avail]
                if available:
                    fuel_str = "⛽ " + ", ".join(available)
            elif isinstance(s['fuel_available'], str):
                fuel_str = f"⛽ {s['fuel_available']}"

        response += f"🔘 **{s['name']}** ({s['dist']:.1f} км)\n📍 {s['address']}\n{fuel_str}\n\n"
        # Кнопка для просмотра деталей (если есть id и это личная станция)
        if s['is_personal'] and s['id']:
            btn_text = f"🔎 {s['name']} ({s['dist']:.1f} км)"
            callback_data = f"personal_view_{s['id']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        else:
            # Для публичных – кнопка с координатами (можно открыть в картах)
            btn_text = f"📍 {s['name']}"
            coords_url = f"https://www.openstreetmap.org/?mlat={s['lat']}&mlon={s['lon']}#map=16/{s['lat']}/{s['lon']}"
            keyboard.append([InlineKeyboardButton(btn_text, url=coords_url)])

    map_url = f"https://www.openstreetmap.org/?mlat={user_lat}&mlon={user_lon}#map=13/{user_lat}/{user_lon}"
    keyboard.append([InlineKeyboardButton("🗺 Открыть интерактивную карту", url=map_url)])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])

    await wait_msg.delete()
    await update.message.reply_text(
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data["search_mode"] = None

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
