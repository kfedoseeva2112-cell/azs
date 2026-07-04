# bot/handlers/search.py
from telegram import Update
from telegram.ext import ContextTypes

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Функция поиска пока в разработке. Отправь геолокацию, чтобы найти АЗС рядом.")
