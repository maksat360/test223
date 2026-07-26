# -*- coding: utf-8 -*-
"""
main.py — точка входа V2 MES-бота.

Запуск:
    ./start.sh
или напрямую:
    python3 main.py
"""

import logging
import os
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
import database as db
import auth
import conveyor
import defect
import salary
import time_tracking
import dashboard
import marketing
import scheduler as bg_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("v2_bot")

MONTHS_RU = salary.MONTHS_RU


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def session(context: ContextTypes.DEFAULT_TYPE):
    """Короткий доступ к user_data — тут хранится текущая сессия пользователя."""
    return context.user_data


def role_menu_buttons(role: str):
    """Возвращает список кнопок reply-клавиатуры под роль (раздел 5)."""
    buttons = []

    if role == config.ROLE_BOSS:
        buttons = [
            ["📊 Производство", "📊 Все зарплаты"],
            ["📤 Загрузить отчёт", "📥 Архив отчётов"],
            ["📈 Статистика брака", "➕ Новая партия"],
            ["🚪 Выйти"],
        ]
    elif role == config.ROLE_TECHNOLOGIST:
        buttons = [
            ["📋 Брак", "📈 Статистика брака"],
            ["🚪 Выйти"],
        ]
    elif role == config.ROLE_TIMEKEEPER:
        buttons = [
            ["➕ Записать смену"],
            ["🚪 Выйти"],
        ]
    elif role == config.ROLE_ACCOUNTANT:
        buttons = [
            ["📤 Загрузить отчёт"],
            ["🚪 Выйти"],
        ]
    else:  # сотрудник
        buttons = [
            ["📋 Мои задачи", "📸 Брак"],
            ["💰 Моя зарплата", "⏱ Мои часы"],
            ["🚪 Выйти"],
        ]

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, greeting=None):
    s = session(context)
    role = s.get("role", config.ROLE_EMPLOYEE)
    text = greeting or f"Меню ({role}):"
    await update.effective_chat.send_message(text, reply_markup=role_menu_buttons(role))


def month_keyboard(prefix: str):
    rows = []
    row = []
    for i, name in enumerate(MONTHS_RU, start=1):
        row.append(InlineKeyboardButton(name, callback_data=f"{prefix}:{i}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def year_keyboard(prefix: str):
    current_year = datetime.now().year
    years = [current_year - 1, current_year, current_year + 1]
    row = [InlineKeyboardButton(str(y), callback_data=f"{prefix}:{y}") for y in years]
    return InlineKeyboardMarkup([row])


# ============================================================
#  /start И АВТОРИЗАЦИЯ
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session(context).clear()
    companies = auth.list_companies()

    buttons = [
        [InlineKeyboardButton(f"🏢 {c.get('company_name')}", callback_data=f"co:{c.get('company_id')}")]
        for c in companies
    ]
    buttons.append([InlineKeyboardButton("🆕 Зарегистрировать компанию", callback_data="reg:start")])

    await update.effective_chat.send_message(
        "🏢 Выберите компанию:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_company_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, company_id: str):
    company = auth.get_company_by_id(company_id)
    if not company:
        await update.callback_query.message.reply_text("Компания не найдена.")
        return

    session(context)["pending_company_id"] = company_id
    session(context)["awaiting"] = "login_credentials"
    await update.callback_query.message.reply_text(
        "Введите логин и пароль через пробел, например:\nМакс 123456789",
        reply_markup=ReplyKeyboardRemove(),
    )


async def try_login(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    s = session(context)
    company_id = s.get("pending_company_id")
    parts = text.strip().split(maxsplit=1)
    if len(parts) != 2:
        await update.message.reply_text("Формат неверный. Введите: логин пароль")
        return

    login_name, password = parts
    user = auth.login(company_id, login_name, password)
    if not user:
        await update.message.reply_text("❌ Неверный логин или пароль. Попробуйте снова.")
        return

    s["company_id"] = company_id
    s["login"] = user.get("логин")
    s["name"] = user.get("имя") or user.get("логин")
    s["role"] = user.get("роль") or config.ROLE_EMPLOYEE
    s.pop("awaiting", None)
    s.pop("pending_company_id", None)

    await update.message.reply_text(f"👋 Добро пожаловать, {s['name']}!")
    await show_main_menu(update, context)


# ============================================================
#  РЕГИСТРАЦИЯ НОВОЙ КОМПАНИИ (раздел 4.3)
# ============================================================

async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("🔑 У меня есть ID", callback_data="reg:has_id")],
        [InlineKeyboardButton("🆔 Получить ID", callback_data="reg:get_id")],
    ]
    await update.callback_query.message.reply_text(
        "Регистрация компании:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def registration_has_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session(context)["awaiting"] = "invite_id_input"
    await update.callback_query.message.reply_text("Введите ваш ID:")


async def registration_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session(context)["awaiting"] = "get_id_company_name"
    await update.callback_query.message.reply_text(
        "Введите название вашей компании — мы передадим заявку администратору:"
    )


async def handle_registration_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    s = session(context)
    awaiting = s.get("awaiting")

    if awaiting == "invite_id_input":
        invite = auth.check_invite_id(text.strip())
        if not invite:
            await update.message.reply_text(
                "❌ ID не найден или уже занят. Проверьте и попробуйте снова."
            )
            return
        s["reg_invite_id"] = text.strip()
        s["awaiting"] = "reg_company_name"
        await update.message.reply_text("✅ ID подтверждён. Введите название компании:")

    elif awaiting == "reg_company_name":
        s["reg_company_name"] = text.strip()
        s["awaiting"] = "reg_admin_name"
        await update.message.reply_text("Введите имя администратора:")

    elif awaiting == "reg_admin_name":
        s["reg_admin_name"] = text.strip()
        s["awaiting"] = "reg_admin_password"
        await update.message.reply_text("Придумайте пароль администратора:")

    elif awaiting == "reg_admin_password":
        s["reg_admin_password"] = text.strip()
        s["awaiting"] = "reg_employee_count"
        await update.message.reply_text("Сколько сотрудников примерно будет в системе?")

    elif awaiting == "reg_employee_count":
        result = auth.register_company(
            invite_id=s["reg_invite_id"],
            company_name=s["reg_company_name"],
            admin_name=s["reg_admin_name"],
            admin_password=s["reg_admin_password"],
            employee_count=text.strip(),
        )
        s.clear()
        if result:
            await update.message.reply_text(
                f"✅ Компания «{result['company_name']}» зарегистрирована!\n"
                f"ID компании: {result['company_id']}\n"
                f"Логин администратора: {result['admin_login']}\n\n"
                "Отправьте /start, чтобы войти."
            )
        else:
            await update.message.reply_text("❌ Не удалось зарегистрировать компанию. ID уже занят.")

    elif awaiting == "get_id_company_name":
        auth.request_new_invite(
            requester_name=update.effective_user.full_name,
            company_name_request=text.strip(),
        )
        s.pop("awaiting", None)
        await update.message.reply_text(
            "✅ Заявка отправлена. Администратор свяжется с вами."
        )
        for superadmin_id in config.SUPERADMIN_TELEGRAM_IDS:
            try:
                await context.bot.send_message(
                    superadmin_id,
                    f"🆕 Новая заявка на регистрацию: «{text.strip()}» "
                    f"от {update.effective_user.full_name}",
                )
            except Exception:
                logger.warning("Не удалось уведомить суперадмина %s", superadmin_id)


# ============================================================
#  СОТРУДНИК: МОИ ЗАДАЧИ / БРАК / ЗАРПЛАТА / ЧАСЫ
# ============================================================

async def show_my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    stage_ids = conveyor.user_assigned_stage_ids(s["company_id"], s["login"])
    if not stage_ids:
        await update.message.reply_text("У вас пока не назначено ни одного процесса.")
        return

    stages = conveyor.load_stages(s["company_id"])
    lines = ["📋 Мои задачи:", ""]
    for sid in stage_ids:
        stage = stages.get(sid)
        if stage:
            lines.append(f"• Процесс {sid} — {stage.get('название')}")
        else:
            lines.append(f"• Процесс {sid}")
    await update.message.reply_text("\n".join(lines))


async def prompt_defect_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session(context)["awaiting"] = "defect_photo"
    await update.message.reply_text("📸 Отправьте фото брака одним сообщением.")


async def handle_defect_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    if s.get("awaiting") != "defect_photo":
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()

    photos_dir = os.path.join(config.CLOUD_STORAGE_DIR, "Фото_брака")
    os.makedirs(photos_dir, exist_ok=True)
    filename = f"{s['login']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(photos_dir, filename)
    await file.download_to_drive(filepath)

    stage_ids = conveyor.user_assigned_stage_ids(s["company_id"], s["login"])
    process_id = stage_ids[0] if stage_ids else ""

    defect_id = defect.register_defect(
        s["company_id"], s["login"], process_id, filename
    )
    s.pop("awaiting", None)
    await update.message.reply_text(f"✅ Брак зафиксирован (заявка №{defect_id}).")


async def prompt_salary_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите год:", reply_markup=year_keyboard("myyear")
    )


async def prompt_hours_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите год для просмотра часов:", reply_markup=year_keyboard("hoursyear")
    )


# ============================================================
#  НАЧАЛЬНИК: ДЭШБОРД / ЗАРПЛАТЫ / СТАТИСТИКА / ПАРТИИ
# ============================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    text = dashboard.build_dashboard_text(s["company_id"])
    await update.message.reply_text(text)


async def prompt_all_salaries_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите год:", reply_markup=year_keyboard("allyear")
    )


async def prompt_upload_report_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "За какой год отчёт?", reply_markup=year_keyboard("uploadyear")
    )


async def prompt_archive_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите год архива:", reply_markup=year_keyboard("archiveyear")
    )


async def show_defect_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    by_process, by_employee = defect.defect_stats(s["company_id"])

    lines = ["📈 Статистика брака", "", "По процессам:"]
    if by_process:
        for process, count in by_process.items():
            lines.append(f"  Процесс {process}: {count}")
    else:
        lines.append("  Нет данных")

    lines.append("")
    lines.append("По сотрудникам:")
    if by_employee:
        for employee, count in by_employee.items():
            lines.append(f"  {employee}: {count}")
    else:
        lines.append("  Нет данных")

    await update.message.reply_text("\n".join(lines))


async def prompt_new_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session(context)["awaiting"] = "new_batch_name"
    await update.message.reply_text("Введите название новой партии:")


# ============================================================
#  ТЕХНОЛОГ: ОБРАБОТКА БРАКА
# ============================================================

async def show_defect_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    pending = defect.list_new_defects(s["company_id"])
    if not pending:
        await update.message.reply_text("Новых обращений по браку нет.")
        return

    for item in pending:
        buttons = [
            [
                InlineKeyboardButton("✅ Принято", callback_data=f"defect:{item['id']}:принято"),
                InlineKeyboardButton("🔄 Возврат", callback_data=f"defect:{item['id']}:возврат"),
            ]
        ]
        await update.message.reply_text(
            f"Заявка №{item['id']}\nСотрудник: {item.get('логин')}\n"
            f"Процесс: {item.get('процесс')}\nДата: {item.get('дата')}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


# ============================================================
#  ТАБЕЛЬЩИК: УЧЁТ ВРЕМЕНИ
# ============================================================

async def prompt_record_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session(context)["awaiting"] = "shift_input"
    await update.message.reply_text(
        "Введите данные смены в формате:\nлогин ГГГГ-ММ-ДД часы\n"
        "Например: Иванов 2026-07-21 8"
    )


async def handle_shift_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    s = session(context)
    parts = text.strip().split()
    if len(parts) != 3:
        await update.message.reply_text("Формат неверный. Пример: Иванов 2026-07-21 8")
        return
    login_name, date_str, hours_str = parts
    try:
        hours = float(hours_str)
    except ValueError:
        await update.message.reply_text("Часы должны быть числом.")
        return

    time_tracking.record_shift(s["company_id"], login_name, date_str, hours, s["login"])
    s.pop("awaiting", None)
    await update.message.reply_text("✅ Смена записана.")


# ============================================================
#  ТЕКСТОВЫЙ РОУТЕР (кнопки reply-клавиатуры и awaiting-состояния)
# ============================================================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    text = update.message.text.strip()
    awaiting = s.get("awaiting")

    # --- многошаговые вводы, ожидающие простого текста ---
    if awaiting == "login_credentials":
        await try_login(update, context, text)
        return

    if awaiting in (
        "invite_id_input", "reg_company_name", "reg_admin_name",
        "reg_admin_password", "reg_employee_count", "get_id_company_name",
    ):
        await handle_registration_text(update, context, text)
        return

    if awaiting == "shift_input":
        await handle_shift_input(update, context, text)
        return

    if awaiting == "new_batch_name":
        batch_id = conveyor.create_batch(s["company_id"], text, s["login"])
        s.pop("awaiting", None)
        await update.message.reply_text(f"✅ Партия #{batch_id} создана.")
        return

    # --- если пользователь ещё не авторизован ---
    if "company_id" not in s:
        await update.message.reply_text("Пожалуйста, начните с команды /start.")
        return

    # --- кнопки главного меню ---
    if text == "🚪 Выйти":
        s.clear()
        await update.message.reply_text("Вы вышли.", reply_markup=ReplyKeyboardRemove())
        return

    if text == "📋 Мои задачи":
        await show_my_tasks(update, context)
    elif text == "📸 Брак":
        await prompt_defect_photo(update, context)
    elif text == "💰 Моя зарплата":
        await prompt_salary_year(update, context)
    elif text == "⏱ Мои часы":
        await prompt_hours_year(update, context)
    elif text == "📊 Производство":
        await show_dashboard(update, context)
    elif text == "📊 Все зарплаты":
        await prompt_all_salaries_year(update, context)
    elif text == "📤 Загрузить отчёт":
        await prompt_upload_report_year(update, context)
    elif text == "📥 Архив отчётов":
        await prompt_archive_year(update, context)
    elif text == "📈 Статистика брака":
        await show_defect_stats(update, context)
    elif text == "➕ Новая партия":
        await prompt_new_batch(update, context)
    elif text == "📋 Брак":
        await show_defect_queue(update, context)
    elif text == "➕ Записать смену":
        await prompt_record_shift(update, context)
    else:
        await update.message.reply_text("Не понял команду. Используйте кнопки меню.")


# ============================================================
#  ЗАГРУЗКА ФАЙЛОВ ОТЧЁТОВ (бухгалтер / начальник)
# ============================================================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(context)
    pending = s.get("salary_upload_pending")
    if not pending:
        return  # не ожидаем документ прямо сейчас

    document = update.message.document
    if not document.file_name.lower().endswith((".xlsx", ".xls")):
        await update.message.reply_text("Пришлите файл в формате .xlsx")
        return

    file = await document.get_file()
    tmp_dir = os.path.join(config.CLOUD_STORAGE_DIR, "Временные")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"upload_{update.effective_user.id}.xlsx")
    await file.download_to_drive(tmp_path)

    year = pending["year"]
    month_name = MONTHS_RU[pending["month"] - 1]

    ok, message = salary.upload_report(s["company_id"], month_name, year, tmp_path)
    os.remove(tmp_path)
    s.pop("salary_upload_pending", None)
    await update.message.reply_text(("✅ " if ok else "❌ ") + message)


# ============================================================
#  CALLBACK-РОУТЕР (инлайн-кнопки)
# ============================================================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    s = session(context)

    if data.startswith("co:"):
        await handle_company_selected(update, context, data.split(":", 1)[1])
        return

    if data == "reg:start":
        await registration_start(update, context)
        return
    if data == "reg:has_id":
        await registration_has_id(update, context)
        return
    if data == "reg:get_id":
        await registration_get_id(update, context)
        return

    if data.startswith("defect:"):
        _, defect_id, decision = data.split(":")
        defect.resolve_defect(s["company_id"], defect_id, decision)
        await query.message.edit_text(query.message.text + f"\n\n➡️ Статус: {decision}")
        return

    if data.startswith("myyear:"):
        year = int(data.split(":")[1])
        s["salary_year_selected"] = year
        await query.message.reply_text("Выберите месяц:", reply_markup=month_keyboard("mymonth"))
        return

    if data.startswith("mymonth:"):
        month_num = int(data.split(":")[1])
        year = s.get("salary_year_selected")
        month_name = MONTHS_RU[month_num - 1]
        total = salary.get_salary_for_user(s["company_id"], month_name, year, s["login"])
        if total is None:
            await query.message.reply_text(f"Нет данных за {month_name} {year}.")
        else:
            await query.message.reply_text(
                f"💰 Зарплата за {month_name} {year}. Итого: {total} сом."
            )
        return

    if data.startswith("hoursyear:"):
        year = int(data.split(":")[1])
        s["hours_year_selected"] = year
        await query.message.reply_text("Выберите месяц:", reply_markup=month_keyboard("hoursmonth"))
        return

    if data.startswith("hoursmonth:"):
        month_num = int(data.split(":")[1])
        year = s.get("hours_year_selected")
        total = time_tracking.get_hours_for_month(s["company_id"], s["login"], year, month_num)
        await query.message.reply_text(
            f"⏱ Часы за {MONTHS_RU[month_num - 1]} {year}: {total}"
        )
        return

    if data.startswith("allyear:"):
        year = int(data.split(":")[1])
        s["all_salary_year_selected"] = year
        await query.message.reply_text("Выберите месяц:", reply_markup=month_keyboard("allmonth"))
        return

    if data.startswith("allmonth:"):
        month_num = int(data.split(":")[1])
        year = s.get("all_salary_year_selected")
        month_name = MONTHS_RU[month_num - 1]
        rows = salary.get_all_salaries(s["company_id"], month_name, year)
        if rows is None:
            await query.message.reply_text(f"Нет отчёта за {month_name} {year}.")
            return
        lines = [f"📊 Зарплаты за {month_name} {year}", ""]
        fund = 0.0
        for row in rows:
            total = row.get("Итог") or 0
            try:
                fund += float(total)
            except (TypeError, ValueError):
                pass
            lines.append(f"{row.get('Логин')} — {total} сом")
        lines.append("")
        lines.append(f"Общий фонд: {fund} сом")
        await query.message.reply_text("\n".join(lines))
        return

    if data.startswith("uploadyear:"):
        year = int(data.split(":")[1])
        s["upload_year_selected"] = year
        await query.message.reply_text("Выберите месяц:", reply_markup=month_keyboard("uploadmonth"))
        return

    if data.startswith("uploadmonth:"):
        month_num = int(data.split(":")[1])
        s["salary_upload_pending"] = {"year": s.get("upload_year_selected"), "month": month_num}
        await query.message.reply_text("Прикрепите Excel-файл отчёта (.xlsx).")
        return

    if data.startswith("archiveyear:"):
        year = int(data.split(":")[1])
        s["archive_year_selected"] = year
        await query.message.reply_text("Выберите месяц:", reply_markup=month_keyboard("archivemonth"))
        return

    if data.startswith("archivemonth:"):
        month_num = int(data.split(":")[1])
        year = s.get("archive_year_selected")
        month_name = MONTHS_RU[month_num - 1]
        versions = salary.list_archive_versions(s["company_id"], month_name, year)
        if not versions:
            await query.message.reply_text(f"Архив за {month_name} {year} пуст.")
            return
        lines = [f"📥 Версии отчёта за {month_name} {year}:"]
        lines += [os.path.basename(v) for v in versions]
        await query.message.reply_text("\n".join(lines))
        return


# ============================================================
#  ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================

def main():
    config.ensure_directories()
    created = db.bootstrap_default_company()
    if created:
        print("✅ Компания создана!")
        print(f"ID: {created['company_id']}")
        print(f"Логин: {created['admin_login']}")
        print(f"Пароль: {created['admin_password']}")

    if config.BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print(
            "⚠️  Вставьте токен бота в config.py (переменная BOT_TOKEN), "
            "полученный у @BotFather, и запустите снова."
        )
        return

    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.PHOTO, handle_defect_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("🚀 V2 бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
