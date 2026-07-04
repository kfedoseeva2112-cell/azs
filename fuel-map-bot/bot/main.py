# bot/main.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from .config import BOT_TOKEN
from .handlers import start, add_station, search
from .models.db import engine, Base

# Создаём таблицы в БД (если не существуют)
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("add", add_station.add_station))  # можно сделать через кнопки позже
    app.add_handler(MessageHandler(filters.LOCATION, add_station.handle_location))

    # Пока заглушка для поиска – позже переделаем
    app.add_handler(CommandHandler("search", search.search))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
