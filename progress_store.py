"""
progress_store.py
==================
يخزّن رقم آخر درس تم نشره في ملف progress.json داخل جذر المستودع.
الـ workflow مسؤول عن عمل commit/push لهذا الملف بعد كل تشغيل ناجح،
حتى يبقى التقدم محفوظًا بين التشغيلات (GitHub Actions لا يحتفظ بأي حالة بنفسه).
"""

import json
import os

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")


def load_progress() -> int:
    """يرجّع فهرس آخر درس تم نشره + 1 (أي: فهرس الدرس التالي). يبدأ من 0 لو الملف غير موجود."""
    if not os.path.exists(PROGRESS_FILE):
        return 0
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("next_index", 0))
    except (json.JSONDecodeError, ValueError):
        return 0


def save_progress(next_index: int) -> None:
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"next_index": next_index}, f, ensure_ascii=False, indent=2)
