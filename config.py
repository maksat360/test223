# -*- coding: utf-8 -*-
"""
config.py — глобальная конфигурация V2 MES-бота.

Перед запуском обязательно вставьте токен, полученный у @BotFather,
в переменную BOT_TOKEN ниже.
"""

import os

# ============================================================
#  ТОКЕН БОТА
# ============================================================
BOT_TOKEN = "8922842876:AAGGTNakzY2JsJ0B0Y9gU7bFC5asMXCFL-M"

# ============================================================
#  ПУТИ
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
CLOUD_STORAGE_DIR = os.path.join(BASE_DIR, "cloud_storage")

SYSTEM_CONFIG_FILE = os.path.join(CLOUD_STORAGE_DIR, "system_config.xlsx")

# Подпапки внутри cloud_storage/, которые должны существовать всегда
CLOUD_SUBFOLDERS = [
    "Зарплатные_отчеты",
    "Зарплаты",
    "Фото_партий",
    "Фото_брака",
    "Временные",
    "backups",
]

# Имена файлов, которые создаются внутри папки каждой компании
COMPANY_FILE_NAMES = {
    "users": "пользователи.xlsx",
    "batches": "партии.xlsx",
    "time_tracking": "учёт_времени.xlsx",
    "defects": "брак.xlsx",
    "conveyor": "конвейер_настройки.xlsx",
}

# ============================================================
#  КОМПАНИЯ ПО УМОЛЧАНИЮ (создаётся при самом первом запуске)
# ============================================================
DEFAULT_COMPANY_NAME = "TelegramBot ERP"
DEFAULT_ADMIN_LOGIN = "Макс"
DEFAULT_ADMIN_PASSWORD = "123456789"

# ============================================================
#  РОЛИ
# ============================================================
ROLE_SUPERADMIN = "суперадмин"
ROLE_BOSS = "начальник"
ROLE_TECHNOLOGIST = "технолог"
ROLE_TIMEKEEPER = "табельщик"
ROLE_ACCOUNTANT = "бухгалтер"
ROLE_EMPLOYEE = "сотрудник"

ALL_ROLES = [
    ROLE_SUPERADMIN,
    ROLE_BOSS,
    ROLE_TECHNOLOGIST,
    ROLE_TIMEKEEPER,
    ROLE_ACCOUNTANT,
    ROLE_EMPLOYEE,
]

# ============================================================
#  ПОРОГИ ДЭШБОРДА (раздел 9 документации)
# ============================================================
STATUS_OK_MULTIPLIER = 1.5       # время < норма * 1.5 -> ✅
STATUS_WARNING_MULTIPLIER = 2.0  # время > норма * 2   -> ⚠️
STATUS_CRITICAL_MULTIPLIER = 4.0  # время > норма * 4  -> 🚨

# ============================================================
#  СУПЕРАДМИН (Telegram user id, кто может выдавать ID компаний)
# ============================================================
SUPERADMIN_TELEGRAM_IDS = [
    # Впишите сюда свой Telegram numeric id, например: 123456789
]


def ensure_directories():
    """Создаёт все необходимые директории, если их ещё нет."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FONTS_DIR, exist_ok=True)
    os.makedirs(CLOUD_STORAGE_DIR, exist_ok=True)
    for sub in CLOUD_SUBFOLDERS:
        os.makedirs(os.path.join(CLOUD_STORAGE_DIR, sub), exist_ok=True)
