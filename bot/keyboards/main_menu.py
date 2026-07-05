from telegram import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    keyboard = [
        [KeyboardButton("🔍 Найти АЗС"), KeyboardButton("🗺️ Карта")],
        [KeyboardButton("➕ Добавить АЗС"), KeyboardButton("📊 Мои АЗС")],
        [KeyboardButton("🚗 Маршрут"), KeyboardButton("🔔 Уведомления")],
        [KeyboardButton("💎 Премиум"), KeyboardButton("📞 Связь с нами")],
        [KeyboardButton("⭐ Отзыв о боте"), KeyboardButton("💖 Поддержать")],
        [KeyboardButton("🔙 В меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
