import logging
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)
from .config import BOT_TOKEN
from .handlers import (
    start, add_station, search, route, 
    personal_stations, payments, admin, 
    feedback, notifications, update_station,
    donate
)
from .models.db import init_db
from .utils.notifier_task import check_fuel_notifications

# Инициализация БД
init_db()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка здоровья бота"""
    import time
    from .models.db import SessionLocal
    from .models.db_models import Station
    
    start_time = time.time()
    db = SessionLocal()
    try:
        count = db.query(Station).count()
        db_status = "✅ OK"
    except Exception as e:
        db_status = f"❌ Error: {e}"
    finally:
        db.close()
    
    latency = (time.time() - start_time) * 1000
    await update.message.reply_text(
        f"🛠 **Статус системы:**\n"
        f"База данных: {db_status}\n"
        f"АЗС в базе: {count}\n"
        f"Задержка БД: {latency:.1f} мс\n"
        f"Статус: Работает штатно 🚀",
        parse_mode='Markdown'
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⏳ Операция заняла слишком много времени или произошла ошибка. Попробуйте позже."
        )

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    # Фоновые задачи (проверка уведомлений каждые 15 минут)
    job_queue = app.job_queue
    job_queue.run_repeating(check_fuel_notifications, interval=900, first=10)

    # ConversationHandler для добавления АЗС (Личная/Публичная)
    add_station_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["➕ Добавить свою АЗС", "➕ Добавить АЗС"]), add_station.add_station_start),
            CommandHandler("add", add_station.add_station_start)
        ],
        states={
            add_station.CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_station.handle_type)],
            add_station.CHOOSING_LOCATION: [MessageHandler(filters.LOCATION, add_station.handle_location)],
            add_station.ENTERING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_station.handle_name)],
            add_station.ENTERING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_station.handle_address)],
            add_station.CHOOSING_FUEL: [CallbackQueryHandler(add_station.fuel_callback, pattern="^fuel_")],
        },
        fallbacks=[
            CommandHandler("start", start.start),
            MessageHandler(filters.Text("🔙 В меню"), start.start)
        ],
    )

    # ConversationHandler для отзывов о боте
    bot_review_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("⭐ Отзыв о боте"), feedback.start_bot_review)],
        states={
            feedback.ENTERING_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text("🔙 В меню"), feedback.handle_bot_review_text)],
        },
        fallbacks=[
            CommandHandler("start", start.start),
            MessageHandler(filters.Text("🔙 В меню"), start.start)
        ],
    )

    # ConversationHandler для поддержки
    support_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("📞 Связь с нами"), feedback.start_support)],
        states={
            feedback.ENTERING_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Text("🔙 В меню"), feedback.handle_support_text)],
        },
        fallbacks=[
            CommandHandler("start", start.start),
            MessageHandler(filters.Text("🔙 В меню"), start.start)
        ],
    )

    # ConversationHandler для маршрутов
    route_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🚗 Маршрут", "🚀 Маршрут"]), route.route_start)],
        states={
            route.START_POINT: [MessageHandler(filters.LOCATION, route.handle_start_point)],
            route.END_POINT: [MessageHandler(filters.LOCATION, route.handle_end_point)],
        },
        fallbacks=[CommandHandler("start", start.start)],
    )

    # Платежи
    app.add_handler(CommandHandler("premium", payments.premium_command))
    app.add_handler(MessageHandler(filters.Text("💎 Премиум"), payments.premium_command))
    app.add_handler(PreCheckoutQueryHandler(payments.precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payments.successful_payment_callback))

    # Основные команды
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("health", health_check))
    app.add_error_handler(error_handler)
    app.add_handler(add_station_conv)
    app.add_handler(bot_review_conv)
    app.add_handler(support_conv)
    app.add_handler(route_conv)
    
    # Донаты
    donate_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("💖 Поддержать"), donate.start_donate)],
        states={
            donate.ENTERING_DONATE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.Text("🔙 В меню"), donate.handle_donate_amount)
            ]
        },
        fallbacks=[MessageHandler(filters.Text("🔙 В меню"), start.start)],
        allow_reentry=True
    )
    app.add_handler(donate_conv)

    # Поиск и Карта (реагируют и на текст, и на прямую отправку локации)
    app.add_handler(MessageHandler(filters.Text("🔍 Найти АЗС"), search.search_stations))
    app.add_handler(MessageHandler(filters.Text("🗺️ Карта"), search.show_map))
    app.add_handler(MessageHandler(filters.LOCATION, search.handle_location))
    
    app.add_handler(MessageHandler(filters.Text("🔙 В меню"), start.start))
    app.add_handler(MessageHandler(filters.Text("📊 Мои АЗС"), personal_stations.list_personal_stations))
    app.add_handler(MessageHandler(filters.Text("🔔 Уведомления"), notifications.list_notifications))
    
    # Инлайн кнопка "Назад"
    app.add_handler(CallbackQueryHandler(start.start, pattern="^back_to_menu$"))

    # Инлайн кнопки
    app.add_handler(CallbackQueryHandler(feedback.bot_rate_callback, pattern="^bot_rate_"))
    app.add_handler(CallbackQueryHandler(personal_stations.delete_personal_callback, pattern="^delete_personal_"))
    app.add_handler(CallbackQueryHandler(update_station.station_view_callback, pattern="^station_view_"))
    app.add_handler(CallbackQueryHandler(personal_stations.personal_view_callback, pattern="^personal_view_"))
    app.add_handler(CallbackQueryHandler(notifications.subscribe_fuel_start, pattern="^sub_fuel_"))
    app.add_handler(CallbackQueryHandler(notifications.subscribe_fuel_callback, pattern="^sub_type_"))
    app.add_handler(CallbackQueryHandler(update_station.update_fuel_start, pattern="^update_fuel_"))
    app.add_handler(CallbackQueryHandler(update_station.update_fuel_callback, pattern="^fuel_"))
    app.add_handler(CallbackQueryHandler(update_station.update_fuel_text, pattern="^update_fuel_text_"))
    
    # Админка
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    app.add_handler(CommandHandler("pending", admin.list_pending_stations))
    app.add_handler(CommandHandler("reply", admin.reply_to_user))
    app.add_handler(CallbackQueryHandler(admin.moderation_callback, pattern="^(approve|reject)_"))

    print("Бот со всеми доработками запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
