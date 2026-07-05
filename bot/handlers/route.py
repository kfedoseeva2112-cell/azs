import requests
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from ..utils.payments import check_subscription
from ..utils.geo import calculate_distance
from ..models.db import SessionLocal
from ..models.db_models import Station
from ..keyboards.main_menu import get_main_menu

START_POINT, END_POINT = range(2)

async def route_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_subscription(user_id):
        await update.message.reply_text(
            "🚀 Построение маршрутов доступно только в Премиум-версии.\nОформите подписку через кнопку «💎 Премиум».",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END

    await update.message.reply_text("Отправьте вашу текущую геолокацию или начальную точку маршрута.")
    return START_POINT

async def handle_start_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        context.user_data["route_start"] = (update.message.location.latitude, update.message.location.longitude)
    else:
        # В MVP используем только локацию для точности
        await update.message.reply_text("Пожалуйста, отправьте именно геолокацию через меню вложений.")
        return START_POINT
        
    await update.message.reply_text("Теперь отправьте геолокацию конечной точки.")
    return END_POINT

async def handle_end_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        start_lat, start_lon = context.user_data["route_start"]
        end_lat, end_lon = update.message.location.latitude, update.message.location.longitude
    else:
        await update.message.reply_text("Пожалуйста, отправьте геолокацию.")
        return END_POINT

    await update.message.reply_text("⏳ Строю маршрут и ищу АЗС на пути...")
    
    # OSRM API запрос
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        response = requests.get(url).json()
        if response.get("code") != "Ok":
            await update.message.reply_text("Не удалось построить маршрут.", reply_markup=get_main_menu())
            return ConversationHandler.END
            
        # Для MVP: просто ищем АЗС, которые находятся "между" точками в радиусе
        db = SessionLocal()
        stations = db.query(Station).filter_by(status="active").all()
        
        # Фильтруем АЗС, которые находятся близко к прямой линии (упрощенно для MVP)
        # В идеале нужно проверять расстояние от каждой точки маршрута (полилинии)
        on_route = []
        for s in stations:
            # Упрощенная проверка: расстояние до старта + расстояние до финиша не сильно больше общего расстояния
            dist_to_start = calculate_distance(s.latitude, s.longitude, start_lat, start_lon)
            dist_to_end = calculate_distance(s.latitude, s.longitude, end_lat, end_lon)
            total_route_dist = calculate_distance(start_lat, start_lon, end_lat, end_lon)
            
            if dist_to_start + dist_to_end < total_route_dist * 1.2: # Запас 20%
                on_route.append(s)
        
        db.close()
        
        res_msg = f"🛣 Маршрут построен!\n🏁 Расстояние: {response['routes'][0]['distance']/1000:.1f} км\n⏱ Время: {response['routes'][0]['duration']/60:.0f} мин\n\n⛽️ АЗС на пути:\n"
        if not on_route:
            res_msg += "Заправок вдоль маршрута не найдено."
        else:
            for i, s in enumerate(on_route[:5], 1):
                res_msg += f"{i}. {s.name} ({s.address})\n"
        
        await update.message.reply_text(res_msg, reply_markup=get_main_menu())
        
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
        
    return ConversationHandler.END
