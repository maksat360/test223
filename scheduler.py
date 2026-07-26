# -*- coding: utf-8 -*-
"""
scheduler.py — периодические фоновые задачи.

Например: проверка окончания триального периода компаний
(trial_ends_at в system_config.xlsx, лист Компании).
Использует APScheduler, если он установлен; иначе тихо отключается,
чтобы не ломать запуск основного бота.
"""

from datetime import datetime

import config
import database as db

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False


def check_trial_expirations():
    """Деактивирует компании, у которых истёк триальный период."""
    _, rows = db.read_sheet(config.SYSTEM_CONFIG_FILE, "Компании")
    today = datetime.now().date()

    for row in rows:
        trial_str = row.get("trial_ends_at")
        if not trial_str:
            continue
        try:
            trial_date = datetime.strptime(str(trial_str), "%Y-%m-%d").date()
        except ValueError:
            continue
        if trial_date < today and str(row.get("is_active")).lower() == "да":
            db.update_row(
                config.SYSTEM_CONFIG_FILE,
                lambda r: r.get("company_id") == row.get("company_id"),
                {"is_active": "нет"},
                sheet_name="Компании",
            )


def start_scheduler():
    """Запускает фоновые задачи, если APScheduler доступен."""
    if not _HAS_APSCHEDULER:
        return None
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_trial_expirations, "interval", hours=24)
    scheduler.start()
    return scheduler
