# -*- coding: utf-8 -*-
"""
conveyor.py — производственный конвейер с графом зависимостей
(раздел 6 документации).

Правила:
- Процесс 0 создаёт партию.
- "Зависимость_от" — через запятую ID процессов, после которых этот
  процесс может начаться.
- "Обязательные" — подмножество зависимостей, которые ОБЯЗАНЫ быть
  завершены (остальные зависимости опциональны — партия не блокируется
  их отсутствием, но подхватывает результат, если он есть).
- Процесс без зависимостей (кроме 0) стартует сразу после процесса 0.
"""

import os
import config
import database as db


def _parse_id_list(raw):
    if raw is None or str(raw).strip() == "":
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip() != ""]


def load_stages(company_id):
    """Загружает этапы конвейера из конвейер_настройки.xlsx компании."""
    company_dir = db.company_dir_path(company_id)
    path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["conveyor"])
    _, rows = db.read_sheet(path)

    stages = {}
    for row in rows:
        stage_id = str(row.get("ID")).strip()
        stages[stage_id] = {
            "id": stage_id,
            "название": row.get("Название"),
            "ответственный": row.get("Ответственный"),
            "зависимость_от": _parse_id_list(row.get("Зависимость_от")),
            "обязательные": _parse_id_list(row.get("Обязательные")),
            "цена": row.get("Цена"),
            "норма_времени": row.get("Норма_времени"),
            "фотоотчёт": row.get("Фотоотчёт"),
        }
    return stages


def stage_is_ready(stage, completed_stage_ids):
    """
    Проверяет, может ли этап начаться:
    все ID из "обязательные" должны быть в completed_stage_ids.
    Если "обязательные" пуст, но "зависимость_от" не пуст — этап
    считается точкой сбора: готов, если завершён хотя бы один
    из зависимостей (мягкое условие для опциональных веток).
    """
    required = stage["обязательные"]
    deps = stage["зависимость_от"]

    if not deps:
        return True  # этап без зависимостей (например, процесс 0)

    if required:
        return all(r in completed_stage_ids for r in required)

    # нет обязательных, но есть зависимости -> хватит одного завершённого
    return any(d in completed_stage_ids for d in deps)


def next_available_stages(company_id, completed_stage_ids):
    """Возвращает список этапов, которые можно начать прямо сейчас."""
    stages = load_stages(company_id)
    available = []
    for stage_id, stage in stages.items():
        if stage_id in completed_stage_ids:
            continue
        if stage_is_ready(stage, completed_stage_ids):
            available.append(stage)
    return available


def user_assigned_stage_ids(company_id, login_name):
    """Возвращает список ID процессов, назначенных сотруднику (колонка 'процессы')."""
    company_dir = db.company_dir_path(company_id)
    users_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["users"])
    user = db.find_row(users_path, lambda r: r.get("логин") == login_name)
    if not user:
        return []
    return _parse_id_list(user.get("процессы"))


def create_batch(company_id, batch_name, created_by):
    """Создаёт новую партию (процесс 0 — раскройщик), раздел 6.1."""
    company_dir = db.company_dir_path(company_id)
    batches_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["batches"])

    from datetime import datetime
    _, rows = db.read_sheet(batches_path)
    next_id = 1
    if rows:
        existing_ids = [int(r["id_партии"]) for r in rows if str(r.get("id_партии", "")).isdigit()]
        next_id = (max(existing_ids) + 1) if existing_ids else 1

    db.append_row(
        batches_path,
        {
            "id_партии": next_id,
            "название": batch_name,
            "текущий_процесс": "0",
            "статус": "в производстве",
            "создана": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "прогноз_готовности": "",
        },
    )
    return next_id


def advance_batch(company_id, batch_id, new_stage_id):
    """Обновляет текущий процесс партии (переход по конвейеру)."""
    company_dir = db.company_dir_path(company_id)
    batches_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["batches"])
    return db.update_row(
        batches_path,
        lambda r: str(r.get("id_партии")) == str(batch_id),
        {"текущий_процесс": new_stage_id},
    )


def list_batches(company_id):
    company_dir = db.company_dir_path(company_id)
    batches_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["batches"])
    _, rows = db.read_sheet(batches_path)
    return rows
