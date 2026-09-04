"""
music_source.py
================
يجلب مقطوعة موسيقية خلفية مجانية ومرخّصة (Creative Commons) من Jamendo،
بمزاج عشوائي مختلف في كل مرة لتنويع الفيديوهات.

يحتاج JAMENDO_CLIENT_ID (مجاني، من https://devportal.jamendo.com — تسجيل بالبريد فقط).
لو المتغير غير موجود أو فشل الجلب لأي سبب، ترجع الدالة None ويكمل الفيديو بدون موسيقى
بدل أن يوقف البوت بالكامل.
"""

import os
import random
import tempfile

import requests

JAMENDO_CLIENT_ID = os.environ.get("JAMENDO_CLIENT_ID", "")

MOOD_TAGS = ["happy", "kids", "children", "cheerful", "fun", "playful", "upbeat"]


def fetch_background_music() -> str | None:
    """يرجع مسار ملف mp3 مؤقت لمقطوعة موسيقية عشوائية، أو None لو تعذّر الجلب."""
    if not JAMENDO_CLIENT_ID:
        print("   ℹ️ JAMENDO_CLIENT_ID غير مضاف، سيُكمل الفيديو بدون موسيقى خلفية.")
        return None

    tag = random.choice(MOOD_TAGS)
    offset = random.randint(0, 50)

    try:
        r = requests.get(
            "https://api.jamendo.com/v3.0/tracks/",
            params={
                "client_id": JAMENDO_CLIENT_ID,
                "format": "json",
                "limit": 1,
                "offset": offset,
                "tags": tag,
                "audioformat": "mp31",
                "vocalinstrumental": "instrumental",
                "order": "popularity_total",
            },
            timeout=15,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None

        audio_url = results[0]["audio"]
        audio_r = requests.get(audio_url, timeout=30)
        audio_r.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(audio_r.content)
        tmp.flush()
        return tmp.name
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠️ تعذّر جلب موسيقى خلفية ({e})، سيُكمل الفيديو بدونها.")
        return None
