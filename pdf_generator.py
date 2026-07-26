# -*- coding: utf-8 -*-
"""
pdf_generator.py — генерация PDF-расчётного листа по зарплате сотрудника.

Использует reportlab и кириллический шрифт DejaVuSans.ttf из папки fonts/.
Если шрифта нет на диске, используется встроенный Helvetica
(кириллица тогда не отобразится, поэтому шрифт рекомендуется положить в fonts/).
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import config

FONT_NAME = "DejaVuSans"
FONT_PATH = os.path.join(config.FONTS_DIR, "DejaVuSans.ttf")


def _register_font():
    if os.path.exists(FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
            return FONT_NAME
        except Exception:
            pass
    return "Helvetica"


def generate_payslip_pdf(output_path, company_name, employee_name, month_name, year, total_amount):
    """Создаёт простой PDF-расчётный лист и сохраняет его в output_path."""
    font_name = _register_font()

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    c.setFont(font_name, 16)
    c.drawString(50, height - 60, f"{company_name}")

    c.setFont(font_name, 13)
    c.drawString(50, height - 100, "Расчётный лист")

    c.setFont(font_name, 11)
    c.drawString(50, height - 140, f"Сотрудник: {employee_name}")
    c.drawString(50, height - 160, f"Период: {month_name} {year}")
    c.drawString(50, height - 200, f"Итого к выплате: {total_amount} сом")

    c.showPage()
    c.save()
    return output_path
