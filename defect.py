# -*- coding: utf-8 -*-
"""
defect.py — фиксация и обработка брака (раздел 7 документации).
"""

import os
from datetime import datetime

import config
import database as db


def file_paths(company_id):
    company_dir = db.company_dir_path(company_id)
    defects_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["defects"])
    photos_dir = os.path.join(config.CLOUD_STORAGE_DIR, "Фото_брака")
    os.makedirs(photos_dir, exist_ok=True)
    return defects_path, photos_dir


def _next_id(defects_path):
    _, rows = db.read_sheet(defects_path)
    ids = [int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()]
    return (max(ids) + 1) if ids else 1


def register_defect(company_id, login_name, process_id, photo_filename, comment=""):
    """
    Сотрудник фиксирует брак: раздел 7.1.
    photo_filename — имя файла, под которым фото уже сохранено в Фото_брака/.
    """
    defects_path, _ = file_paths(company_id)
    defect_id = _next_id(defects_path)

    db.append_row(
        defects_path,
        {
            "id": defect_id,
            "логин": login_name,
            "процесс": process_id,
            "дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "фото": photo_filename,
            "статус": "новый",
            "комментарий": comment,
        },
    )
    return defect_id


def list_new_defects(company_id):
    """Список необработанных обращений для технолога (раздел 7.2)."""
    defects_path, _ = file_paths(company_id)
    return db.find_rows(defects_path, lambda r: r.get("статус") == "новый")


def resolve_defect(company_id, defect_id, decision, comment=""):
    """
    decision: "принято" или "возврат" (раздел 7.2, кнопки ✅ Принято / 🔄 Возврат).
    """
    defects_path, _ = file_paths(company_id)
    return db.update_row(
        defects_path,
        lambda r: str(r.get("id")) == str(defect_id),
        {"статус": decision, "комментарий": comment},
    )


def defect_stats(company_id):
    """
    Статистика брака по процессам и сотрудникам (раздел 7.3).
    Возвращает (by_process: dict, by_employee: dict).
    """
    defects_path, _ = file_paths(company_id)
    _, rows = db.read_sheet(defects_path)

    by_process = {}
    by_employee = {}
    for row in rows:
        process = str(row.get("процесс", "—"))
        employee = str(row.get("логин", "—"))
        by_process[process] = by_process.get(process, 0) + 1
        by_employee[employee] = by_employee.get(employee, 0) + 1

    return by_process, by_employee
