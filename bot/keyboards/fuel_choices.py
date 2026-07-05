# bot/keyboards/fuel_choices.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_fuel_keyboard(selected_fuels=None):
    if selected_fuels is None:
        selected_fuels = []
    
    fuels = ["АИ-92", "АИ-95", "АИ-98", "ДТ"]
    keyboard = []
    
    for fuel in fuels:
        status = "✅ " if fuel in selected_fuels else ""
        keyboard.append([InlineKeyboardButton(f"{status}{fuel}", callback_data=f"fuel_{fuel}")])
    
    keyboard.append([InlineKeyboardButton("Готово ✅", callback_data="fuel_done")])
    return InlineKeyboardMarkup(keyboard)
