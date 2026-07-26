# -*- coding: utf-8 -*-
"""
time_tracking.py — учёт рабочего времени (раздел 10 документации).
"""

import os
import config
import database as db


def _path(company_id):
    company_dir = db.company_dir_path(company_id)
    return os.path.join(company_dir, config.COMPANY_FILE_NAMES["time_tracking"])


def record_shift(company_id, employee_login, date_str, hours, recorded_by):
    """Табельщик записывает смену сотрудника (раздел 10.1)."""
    path = _path(company_id)
    db.append_row(
        path,
        {
            "логин": employee_login,
            "дата": date_str,
            "часы": hours,
            "записал": recorded_by,
        },
    )


def get_hours_for_month(company_id, employee_login, year, month_number):
    """Сумма часов сотрудника за месяц (раздел 10.2)."""
    path = _path(company_id)
    _, rows = db.read_sheet(path)

    total = 0.0
    for row in rows:
        if str(row.get("логин", "")).strip() != employee_login.strip():
            continue
        date_val = str(row.get("дата", ""))
        # ожидаем формат YYYY-MM-DD
        parts = date_val.split("-")
        if len(parts) < 2:
            continue
        try:
            row_year, row_month = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if row_year == year and row_month == month_number:
            try:
                total += float(row.get("часы") or 0)
            except (TypeError, ValueError):
                pass
    return total
