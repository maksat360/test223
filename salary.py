# -*- coding: utf-8 -*-
"""
salary.py — зарплаты сотрудников (раздел 8 документации).

Принцип: пользователи.xlsx используется ТОЛЬКО для авторизации.
Зарплата за каждый месяц лежит в отдельном файле
зарплата_<Месяц>_<Год>.xlsx с обязательными колонками Логин и Итог.
"""

import os
import shutil
from datetime import datetime

import config
import database as db

REQUIRED_COLUMNS = ["Логин", "Итог"]

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def salary_dir(company_id):
    company_dir = db.company_dir_path(company_id)
    path = os.path.join(company_dir, "Зарплаты")
    os.makedirs(path, exist_ok=True)
    return path


def salary_filename(month_name, year):
    return f"зарплата_{month_name}_{year}.xlsx"


def validate_columns(path):
    """Проверяет, что в файле есть колонки Логин и Итог (раздел 8.2)."""
    headers, _ = db.read_sheet(path)
    return all(col in headers for col in REQUIRED_COLUMNS)


def upload_report(company_id, month_name, year, uploaded_file_path):
    """
    Загружает присланный Excel-отчёт (раздел 8.2).
    Если за период уже есть действующий отчёт — архивирует его как _v1, _v2, ...
    перед тем, как новый файл станет действующим.
    Возвращает (ok: bool, message: str).
    """
    if not validate_columns(uploaded_file_path):
        return False, (
            f"Файл должен содержать колонки {', '.join(REQUIRED_COLUMNS)}."
        )

    target_dir = salary_dir(company_id)
    filename = salary_filename(month_name, year)
    target_path = os.path.join(target_dir, filename)

    if os.path.exists(target_path):
        # архивируем старую версию
        version = 1
        while os.path.exists(
            os.path.join(target_dir, filename.replace(".xlsx", f"_v{version}.xlsx"))
        ):
            version += 1
        archived_name = filename.replace(".xlsx", f"_v{version}.xlsx")
        shutil.move(target_path, os.path.join(target_dir, archived_name))

    shutil.copy2(uploaded_file_path, target_path)
    return True, "Отчёт успешно загружен и стал действующим."


def get_salary_for_user(company_id, month_name, year, login_name):
    """Просмотр своей зарплаты (раздел 8.3)."""
    target_dir = salary_dir(company_id)
    path = os.path.join(target_dir, salary_filename(month_name, year))
    if not os.path.exists(path):
        return None
    row = db.find_row(path, lambda r: str(r.get("Логин", "")).strip() == login_name.strip())
    if not row:
        return None
    return row.get("Итог")


def get_all_salaries(company_id, month_name, year):
    """Просмотр всех зарплат начальником (раздел 8.4)."""
    target_dir = salary_dir(company_id)
    path = os.path.join(target_dir, salary_filename(month_name, year))
    if not os.path.exists(path):
        return None
    _, rows = db.read_sheet(path)
    return rows


def list_archive_versions(company_id, month_name, year):
    """Список всех версий отчёта за период (раздел 8.5)."""
    target_dir = salary_dir(company_id)
    base = salary_filename(month_name, year).replace(".xlsx", "")
    versions = []
    for fname in os.listdir(target_dir):
        if fname.startswith(base):
            versions.append(os.path.join(target_dir, fname))
    return sorted(versions)
