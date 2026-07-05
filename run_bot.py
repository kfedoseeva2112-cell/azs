#!/usr/bin/env python3
"""
Точка запуска бота (из директории fuel-map-bot)
"""
import sys
import os

# Добавляем текущую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import main

if __name__ == "__main__":
    main()
