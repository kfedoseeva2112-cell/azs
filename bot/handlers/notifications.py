from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..models.db import SessionLocal
from ..models.db_models import FuelNotification, Station, PersonalStation
from ..utils.payments import check_subscription
from ..keyboards.main_menu import get_main_menu

async def subscribe_fuel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not check_subscription(user_id):
        await query.message.reply_text("🔔 Уведомления о топливе доступны только по Премиум-подписке.")
        return

    # Формат: sub_fuel_{station_id}_{is_personal}
    parts = query.data.split("_")
    station_id = int(parts[2])
    is_personal = parts[3] == "1"
    
    context.user_data["sub_station_id"] = station_id
    context.user_data["sub_is_personal"] = is_personal
    
    keyboard = [
        [InlineKeyboardButton("АИ-92", callback_data="sub_type_АИ-92")],
        [InlineKeyboardButton("АИ-95", callback_data="sub_type_АИ-95")],
        [InlineKeyboardButton("АИ-98", callback_data="sub_type_АИ-98")],
        [InlineKeyboardButton("ДТ", callback_data="sub_type_ДТ")]
    ]
    
    await query.edit_message_text(
        "Выберите тип топлива, о появлении которого вы хотите получать уведомления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def subscribe_fuel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    fuel_type = query.data.replace("sub_type_", "")
    station_id = context.user_data.get("sub_station_id")
    is_personal = context.user_data.get("sub_is_personal")
    user_id = update.effective_user.id
    
    if not station_id:
        await query.edit_message_text("Ошибка сессии.")
        return

    db = SessionLocal()
    # Проверка на дубликат подписки
    exists = db.query(FuelNotification).filter_by(
        user_id=user_id, 
        station_id=station_id, 
        is_personal=is_personal,
        fuel_type=fuel_type
    ).first()
    
    if not exists:
        notif = FuelNotification(
            user_id=user_id,
            station_id=station_id,
            is_personal=is_personal,
            fuel_type=fuel_type
        )
        db.add(notif)
        db.commit()
        await query.edit_message_text(f"✅ Вы подписались на уведомления о {fuel_type}!")
    else:
        await query.edit_message_text(f"Вы уже подписаны на {fuel_type} для этой АЗС.")
    
    db.close()

async def list_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список активных подписок пользователя"""
    user_id = update.effective_user.id
    db = SessionLocal()
    notifs = db.query(FuelNotification).filter_by(user_id=user_id).all()
    
    if not notifs:
        await update.message.reply_text(
            "🔔 У вас пока нет активных подписок на уведомления о топливе.\n\n"
            "Чтобы подписаться, найдите нужную АЗС через поиск и нажмите «🔔 Уведомить о топливе».",
            reply_markup=get_main_menu()
        )
        db.close()
        return

    response = "🔔 **Ваши подписки на уведомления:**\n\n"
    for n in notifs:
        # Пытаемся найти название АЗС
        if n.is_personal:
            s = db.query(PersonalStation).filter_by(id=n.station_id).first()
        else:
            s = db.query(Station).filter_by(id=n.station_id).first()
        
        s_name = s.name if s else "Неизвестная АЗС"
        response += f"📍 {s_name}\n⛽ Топливо: {n.fuel_type}\n\n"
    
    db.close()
    await update.message.reply_text(response, parse_mode='Markdown', reply_markup=get_main_menu())
