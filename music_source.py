"""
music_source.py
================
يختار مقطوعة موسيقية خلفية عشوائية من ملفات mp3 محلية موجودة في مجلد music/
داخل المستودع (رفعتها يدويًا مرة واحدة من مصدر مجاني مثل incompetech.com).

لا يحتاج أي اتصال إنترنت أو تسجيل أو مفتاح API — فقط ملفات ثابتة موثوقة.
لو المجلد فارغًا أو غير موجود، ترجع الدالة None ويكمل الفيديو بدون موسيقى
بدل أن يوقف البوت بالكامل.
"""

import os
import random

MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")


def fetch_background_music() -> str | None:
    """يرجع مسار ملف mp3 عشوائي من مجلد music/، أو None لو المجلد فارغ/غير موجود."""
    if not os.path.isdir(MUSIC_DIR):
        print("   ℹ️ مجلد music/ غير موجود، سيُكمل الفيديو بدون موسيقى خلفية.")
        return None

    tracks = [
        os.path.join(MUSIC_DIR, f)
        for f in os.listdir(MUSIC_DIR)
        if f.lower().endswith((".mp3", ".wav", ".m4a"))
    ]

    if not tracks:
        print("   ℹ️ لا توجد ملفات موسيقى في music/، سيُكمل الفيديو بدون موسيقى خلفية.")
        return None

    chosen = random.choice(tracks)
    print(f"   🎵 موسيقى الخلفية: {os.path.basename(chosen)}")
    return chosen
