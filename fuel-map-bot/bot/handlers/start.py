# bot/handlers/start.py
from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Это Народная карта АЗС.\n"
        "Чтобы добавить заправку, отправь геолокацию и укажи топливо.\n"
        "Чтобы найти АЗС рядом, отправь геолокацию или напиши /search."
    )
