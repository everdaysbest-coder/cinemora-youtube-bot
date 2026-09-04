"""
Cinemora YouTube Bot
======================
سكربت آلي: يأخذ الدرس التالي من المنهج التعليمي (curriculum.py)،
يولّد مشهدًا بصريًا عبر Gemini، يولّد فيديو عبر Cinemora (fal.ai)،
يحرق عليه النص التعليمي وصوت النطق الواضح، ثم يرفعه كـ YouTube Short.

مصمّم للتشغيل كـ Cron Job (3 مرات بالأسبوع) — مرة واحدة في كل تشغيل.

متغيرات البيئة المطلوبة:
  GEMINI_API_KEY        - من aistudio.google.com/apikey
  CINEMORA_BACKEND_URL   - رابط باك اند Cinemora (بدون / بالآخر)
  CINEMORA_OWNER_TOKEN    - owner_token لتجاوز حدود الاستخدام واستخدام fal.ai
  YT_CLIENT_ID             - من Google Cloud Console (Web application)
  YT_CLIENT_SECRET
  YT_REFRESH_TOKEN
"""

import base64
import json
import os
import sys
import time

import requests

from curriculum import get_lesson, total_lessons
from music_source import fetch_background_music
from progress_store import load_progress, save_progress
from tts_audio import generate_narration_audio
from video_compose import compose_final_video, save_bytes_to_temp

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CINEMORA_BACKEND_URL = os.environ["CINEMORA_BACKEND_URL"].rstrip("/")
CINEMORA_OWNER_TOKEN = os.environ["CINEMORA_OWNER_TOKEN"]
YT_CLIENT_ID = os.environ["YT_CLIENT_ID"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]

GEMINI_MODEL_FALLBACKS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]

# وصف الشخصية الثابتة (نور) — يُضاف لكل برومبت فيديو حتى تضل نفس الشخصية بكل حلقة
CHARACTER_DESCRIPTION = (
    "Noor, a cheerful young girl character in 3D Pixar-style cartoon animation: "
    "wavy brown hair in a half-up ponytail with a light blue hair tie, big warm brown eyes, "
    "rosy cheeks, wearing a turquoise puff-sleeve dress with a yellow star on the chest, "
    "white shoes with turquoise socks. She is often joined by a small smiling yellow star "
    "character with a cute face. Soft pastel background with blue sky and clouds, warm "
    "cheerful lighting, high-quality 3D animation style."
)


def build_prompt_for_lesson(lesson: dict) -> str:
    """يبني برومبت لـ Gemini يطلب فقط المشهد البصري والعنوان والوصف —
    الكلمة/الحرف/الجملة تأتي من المنهج مباشرة وليست من اختيار النموذج."""
    stage = lesson["stage"]
    if stage == "alphabet":
        focus = f"the letter '{lesson['letter']}' and the word '{lesson['word']}'"
    elif stage == "vocabulary":
        focus = f"the word '{lesson['word']}' (topic: {lesson['topic']})"
    else:
        focus = f"the sentence '{lesson['sentence']}'"

    return f"""You are creating a single YouTube Short to teach English to children aged 5-10.
The channel's main character is named Noor (a friendly cartoon girl) who appears in every video.
This video's teaching focus is: {focus}

Return STRICTLY valid JSON with these exact keys, nothing else, no markdown fences:
{{
  "video_prompt": "a vivid, simple scene description showing Noor actively demonstrating or acting out the meaning of the focus above, cheerful and child-friendly, no text/letters/subtitles in the scene itself — describe ONLY the action/scene, not Noor's appearance (that will be added separately)",
  "title": "a fun YouTube Short title under 60 characters mentioning Noor, include an emoji",
  "description": "a short YouTube description (2-3 sentences) mentioning it's an English lesson for kids with Noor, plus 5 relevant hashtags"
}}"""


def generate_idea(lesson: dict, retries: int = 7) -> dict:
    """يستخدم Gemini لتوليد المشهد البصري + العنوان + الوصف فقط (المحتوى التعليمي ثابت من المنهج).
    يعيد المحاولة تلقائيًا عند ازدحام الخادم المؤقت (503) أو تجاوز الحد (429)، مع التنقل
    بين عدة نماذج احتياطية (GEMINI_MODEL_FALLBACKS) لتفادي ازدحام نموذج واحد بعينه."""
    prompt = build_prompt_for_lesson(lesson)

    last_error = None
    for attempt in range(retries + 1):
        model = GEMINI_MODEL_FALLBACKS[attempt % len(GEMINI_MODEL_FALLBACKS)]
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": GEMINI_API_KEY,
                },
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
                timeout=45,
            )
            if r.status_code in (429, 503) and attempt < retries:
                wait = min(15 * (attempt + 1), 90)
                next_model = GEMINI_MODEL_FALLBACKS[(attempt + 1) % len(GEMINI_MODEL_FALLBACKS)]
                print(f"   ⚠️ نموذج {model} مزدحم ({r.status_code})، تجربة {next_model} بعد {wait} ثانية...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            idea = json.loads(text)
            idea["video_prompt"] = f"{CHARACTER_DESCRIPTION} Scene: {idea['video_prompt']}"
            return idea
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < retries:
                wait = min(15 * (attempt + 1), 90)
                next_model = GEMINI_MODEL_FALLBACKS[(attempt + 1) % len(GEMINI_MODEL_FALLBACKS)]
                print(f"   ⚠️ محاولة {attempt + 1}/{retries} على {model} فشلت ({e})، تجربة {next_model} بعد {wait} ثانية...")
                time.sleep(wait)
    raise last_error or RuntimeError("فشل توليد الفكرة عبر Gemini بعد عدة محاولات ونماذج مختلفة")


def generate_video(video_prompt: str, retries: int = 2) -> bytes:
    """يولّد فيديو عمودي قصير عبر Cinemora (fal.ai، جودة عالية) ويرجع بايتات الفيديو، مع إعادة محاولة بسيطة."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            return _generate_video_once(video_prompt)
        except Exception as e:  # noqa: BLE001
            last_error = e
            if attempt < retries:
                print(f"   ⚠️ محاولة {attempt + 1} فشلت ({e})، إعادة محاولة...")
                time.sleep(5)
    raise last_error


def _generate_video_once(video_prompt: str) -> bytes:
    params = {"owner_token": CINEMORA_OWNER_TOKEN}
    submit = requests.post(
        f"{CINEMORA_BACKEND_URL}/api/generate/video",
        params=params,
        json={
            "prompt": video_prompt,
            "duration": 10,
            "aspect_ratio": "9:16",
            "provider": "fal",
            "model": "sora-2",
        },
        timeout=30,
    )
    submit.raise_for_status()
    job = submit.json()
    job_id = job["job_id"]

    video_url = None
    for _ in range(90):  # حتى 6 دقايق انتظار
        time.sleep(4)
        status_r = requests.get(
            f"{CINEMORA_BACKEND_URL}/api/generate/video/{job_id}", params=params, timeout=15
        )
        status_r.raise_for_status()
        status = status_r.json()
        if status["status"] == "completed":
            video_url = status["video_url"]
            break
        if status["status"] in ("failed", "error"):
            raise RuntimeError(f"Video generation failed: {status.get('error')}")

    if not video_url:
        raise RuntimeError("Video generation timed out")

    if video_url.startswith("data:"):
        b64_part = video_url.split(",", 1)[1]
        return base64.b64decode(b64_part)
    else:
        vr = requests.get(video_url, timeout=120)
        vr.raise_for_status()
        return vr.content


def get_youtube_access_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
            "refresh_token": YT_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def upload_to_youtube(video_bytes: bytes, title: str, description: str) -> str:
    access_token = get_youtube_access_token()

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": ["english for kids", "learn english", "kids education", "shorts"],
            "categoryId": "27",  # Education
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True},
    }

    boundary = "cinemora_upload_boundary"
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + video_bytes + f"\r\n--{boundary}--".encode("utf-8")

    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "multipart", "part": "snippet,status"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        data=body,
        timeout=300,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"YouTube upload failed [{r.status_code}]: {r.text[:500]}")
    return r.json().get("id", "")


def main():
    next_index = load_progress()
    lesson = get_lesson(next_index)
    print(f"درس اليوم [{next_index + 1}/{total_lessons()}]: مرحلة={lesson['stage']}")

    print("1/4 توليد المشهد البصري عبر Gemini...")
    idea = generate_idea(lesson)
    print(f"   العنوان: {idea['title']}")

    print("2/4 توليد الفيديو عبر Cinemora...")
    raw_video_bytes = generate_video(idea["video_prompt"])
    print(f"   حجم الفيديو الخام: {len(raw_video_bytes)} بايت")

    print("3/4 توليد صوت النطق، جلب موسيقى خلفية، وحرق النص التعليمي...")
    raw_video_path = save_bytes_to_temp(raw_video_bytes, suffix=".mp4")
    narration_path = generate_narration_audio(lesson)
    music_path = fetch_background_music()
    final_video_path = raw_video_path.replace(".mp4", "_final.mp4")
    compose_final_video(raw_video_path, narration_path, lesson["overlay_lines"], final_video_path, music_path)
    with open(final_video_path, "rb") as f:
        final_video_bytes = f.read()
    print(f"   حجم الفيديو النهائي: {len(final_video_bytes)} بايت")

    print("4/4 الرفع ليوتيوب...")
    video_id = upload_to_youtube(final_video_bytes, idea["title"], idea["description"])
    print(f"✅ تم الرفع: https://youtube.com/shorts/{video_id}")

    save_progress(next_index + 1)
    print(f"💾 تم حفظ التقدم — الدرس التالي رقم {next_index + 2}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ فشل: {e}", file=sys.stderr)
        sys.exit(1)
