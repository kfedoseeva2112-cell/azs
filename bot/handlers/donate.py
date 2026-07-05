# bot/handlers/donate.py
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes, ConversationHandler
from ..keyboards.main_menu import get_main_menu

ENTERING_DONATE_AMOUNT = range(100, 101)

async def start_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💖 **Поддержите развитие проекта!**\n\n"
        "Вы можете отправить любое количество Telegram Stars.\n"
        "Ваша поддержка поможет нам делать бота лучше!\n\n"
        "Введите сумму (в Stars) или нажмите «🔙 В меню»:",
        reply_markup=get_main_menu()
    )
    return ENTERING_DONATE_AMOUNT

async def handle_donate_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_str = update.message.text
    if not amount_str.isdigit():
        await update.message.reply_text("Пожалуйста, введите число (количество Stars).")
        return ENTERING_DONATE_AMOUNT
    
    amount = int(amount_str)
    if amount < 1:
        await update.message.reply_text("Сумма должна быть больше 0.")
        return ENTERING_DONATE_AMOUNT

    # Создаем инвойс для Telegram Stars
    title = "Поддержка проекта"
    description = f"Добровольное пожертвование в размере {amount} Stars"
    payload = f"donate_{update.effective_user.id}_{amount}"
    currency = "XTR"
    prices = [LabeledPrice("Донат", amount)]

    await update.message.reply_invoice(
        title=title,
        description=description,
        payload=payload,
        provider_token="", # Пусто для Telegram Stars
        currency=currency,
        prices=prices
    )
    # После отправки инвойса, диалог должен завершиться
    return ConversationHandler.END
