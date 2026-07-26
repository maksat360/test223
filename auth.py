# -*- coding: utf-8 -*-
"""
auth.py — авторизация пользователей и регистрация новых компаний
(разделы 4 и 5 документации).
"""

import hashlib
import os

import config
import database as db


def hash_password(password: str) -> str:
    """SHA-256 хеш пароля (раздел 12: пароли хешируются)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def list_companies():
    """Возвращает список активных компаний из system_config.xlsx."""
    _, rows = db.read_sheet(config.SYSTEM_CONFIG_FILE, "Компании")
    return [r for r in rows if str(r.get("is_active", "")).lower() in ("да", "yes", "true", "1")]


def get_company_by_name(name):
    return db.find_row(
        config.SYSTEM_CONFIG_FILE,
        lambda r: r.get("company_name") == name,
        sheet_name="Компании",
    )


def get_company_by_id(company_id):
    return db.find_row(
        config.SYSTEM_CONFIG_FILE,
        lambda r: r.get("company_id") == company_id,
        sheet_name="Компании",
    )


def login(company_id, login_name, password):
    """
    Проверяет логин/пароль в пользователи.xlsx компании.
    Пароли в файле хранятся как хеш SHA-256.
    Возвращает словарь пользователя, либо None.
    """
    company_dir = db.company_dir_path(company_id)
    users_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["users"])

    hashed = hash_password(password)

    user = db.find_row(
        users_path,
        lambda r: str(r.get("логин", "")).strip() == login_name.strip()
        and str(r.get("пароль", "")).strip() == hashed,
    )

    # Поддержка первого запуска, когда пароль в файле ещё не захеширован
    if not user:
        user = db.find_row(
            users_path,
            lambda r: str(r.get("логин", "")).strip() == login_name.strip()
            and str(r.get("пароль", "")).strip() == password.strip(),
        )
        if user:
            # мигрируем пароль на хеш при первом успешном входе
            db.update_row(
                users_path,
                lambda r: r.get("логин") == user.get("логин"),
                {"пароль": hashed},
            )

    return user


def create_invite_id(length=8):
    """Суперадмин создаёт новый свободный ID и кладёт его в пул приглашений."""
    import random
    import string
    alphabet = string.ascii_uppercase + string.digits
    while True:
        candidate = "".join(random.choices(alphabet, k=length))
        existing = db.find_row(
            config.SYSTEM_CONFIG_FILE,
            lambda r: r.get("ID") == candidate,
            sheet_name="Приглашения",
        )
        if not existing:
            db.append_row(
                config.SYSTEM_CONFIG_FILE,
                {"ID": candidate, "Статус": "свободен", "Компания": ""},
                sheet_name="Приглашения",
            )
            return candidate


def check_invite_id(invite_id):
    """Возвращает строку приглашения, если ID существует и свободен."""
    row = db.find_row(
        config.SYSTEM_CONFIG_FILE,
        lambda r: str(r.get("ID", "")).strip() == invite_id.strip(),
        sheet_name="Приглашения",
    )
    if row and str(row.get("Статус", "")).strip() == "свободен":
        return row
    return None


def register_company(invite_id, company_name, admin_name, admin_password, employee_count=None):
    """
    Регистрирует новую компанию по свободному ID (раздел 4.3, ветка «У меня есть ID»).
    Создаёт папку компании, файлы, запись в Компании/Администраторы,
    и помечает ID как занятый.
    """
    invite = check_invite_id(invite_id)
    if not invite:
        return None

    company_id = invite_id  # используем сам инвайт-ID как company_id

    db.append_row(
        config.SYSTEM_CONFIG_FILE,
        {
            "company_id": company_id,
            "company_name": company_name,
            "is_active": "да",
            "trial_ends_at": "",
        },
        sheet_name="Компании",
    )

    hashed = hash_password(admin_password)
    db.append_row(
        config.SYSTEM_CONFIG_FILE,
        {
            "admin_login": admin_name,
            "admin_password": hashed,
            "company_id": company_id,
            "role": config.ROLE_BOSS,
        },
        sheet_name="Администраторы",
    )

    db.update_row(
        config.SYSTEM_CONFIG_FILE,
        lambda r: r.get("ID") == invite_id,
        {"Статус": "занят", "Компания": company_name},
        sheet_name="Приглашения",
    )

    company_dir = db.company_dir_path(company_id)
    files = db.ensure_company_files(company_dir)

    # Обновляем пользователя-админа хешированным паролем и его именем
    db.update_row(
        files["users"],
        lambda r: True,  # первая (единственная) строка — дефолтный админ
        {
            "логин": admin_name,
            "пароль": hashed,
            "имя": admin_name,
            "роль": config.ROLE_BOSS,
            "процессы": "",
        },
    )

    return {
        "company_id": company_id,
        "company_name": company_name,
        "admin_login": admin_name,
    }


def request_new_invite(requester_name, company_name_request):
    """
    Ветка «Получить ID» (раздел 4.3): заявка сохраняется, чтобы суперадмин
    увидел её и выдал ID вручную после оплаты.
    """
    db.append_row(
        config.SYSTEM_CONFIG_FILE,
        {"setting_key": f"заявка::{requester_name}", "setting_value": company_name_request},
        sheet_name="Настройки",
    )


def get_user_role(company_id, login_name):
    company_dir = db.company_dir_path(company_id)
    users_path = os.path.join(company_dir, config.COMPANY_FILE_NAMES["users"])
    user = db.find_row(users_path, lambda r: r.get("логин") == login_name)
    return user.get("роль") if user else None
