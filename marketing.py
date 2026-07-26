# -*- coding: utf-8 -*-
"""
marketing.py — компании-витрины и PR-сообщения при перегрузке (раздел 15).
"""

SHOWCASE_COMPANIES = [
    "Азия Текстиль",
    "Бишкек Швей",
]

PR_OVERLOAD_MESSAGE = "Извините, нас стало слишком много, сервер не справляется."


def is_showcase_company(company_name: str) -> bool:
    return company_name in SHOWCASE_COMPANIES
