# -*- coding: utf-8 -*-
"""
dashboard.py — производственный дэшборд начальника (раздел 9 документации).

Логика статусов:
  время < норма * 1.5  -> ✅
  время > норма * 2    -> ⚠️
  время > норма * 4    -> 🚨
"""

from datetime import datetime, timedelta

import config
import conveyor


def _status_icon(elapsed_hours, norm_minutes):
    if not norm_minutes:
        return "✅"
    norm_hours = float(norm_minutes) / 60.0
    if elapsed_hours > norm_hours * config.STATUS_CRITICAL_MULTIPLIER:
        return "🚨"
    if elapsed_hours > norm_hours * config.STATUS_WARNING_MULTIPLIER:
        return "⚠️"
    if elapsed_hours < norm_hours * config.STATUS_OK_MULTIPLIER:
        return "✅"
    return "⚠️"


def build_dashboard_text(company_id):
    """Формирует текст дэшборда «📊 Производство» (раздел 9)."""
    batches = conveyor.list_batches(company_id)
    stages = conveyor.load_stages(company_id)

    if not batches:
        return "📊 ПРОИЗВОДСТВО\n\nПока нет активных партий."

    lines = ["📊 ПРОИЗВОДСТВО", ""]
    forecast_line = None

    for batch in batches:
        if str(batch.get("статус", "")).strip() == "готово":
            continue

        stage_id = str(batch.get("текущий_процесс", "")).strip()
        stage = stages.get(stage_id, {})
        stage_name = stage.get("название", f"процесс {stage_id}")
        norm = stage.get("норма_времени")

        created_str = batch.get("создана")
        elapsed_hours = 0.0
        if created_str:
            try:
                created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M")
                elapsed_hours = (datetime.now() - created_dt).total_seconds() / 3600.0
            except ValueError:
                pass

        icon = _status_icon(elapsed_hours, norm)
        batch_name = batch.get("название", f"Партия #{batch.get('id_партии')}")

        if icon == "✅":
            progress = "в процессе"
            lines.append(f"{icon} Партия #{batch.get('id_партии')} — {batch_name} ({progress})")
        elif icon == "⚠️":
            lines.append(
                f"{icon} Партия #{batch.get('id_партии')} — зависла на процессе {stage_id} ({stage_name})"
            )
        else:
            lines.append(
                f"🚨 Партия #{batch.get('id_партии')} — критичное отставание "
                f"(процесс {stage_id}: {stage_name})"
            )
            forecast_line = None

        forecast = batch.get("прогноз_готовности")
        if forecast and not forecast_line:
            forecast_line = f"Прогноз: Партия #{batch.get('id_партии')} будет готова {forecast}"

    if forecast_line:
        lines.append("")
        lines.append(forecast_line)

    return "\n".join(lines)
