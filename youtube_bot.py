"""
Cinemora YouTube Bot
======================
سكربت آلي: يولّد فكرة كلمة/جملة إنجليزية مناسبة لأطفال 5-8 سنين عبر Gemini،
يولّد فيديو قصير عبرCinemora (fal.ai)، ويرفعه كـ YouTube Short تلقائيًا.

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
import os
import random
import sys
import time

import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CINEMORA_BACKEND_URL = os.environ["CINEMORA_BACKEND_URL"].rstrip("/")
CINEMORA_OWNER_TOKEN = os.environ["CINEMORA_OWNER_TOKEN"]
YT_CLIENT_ID = os.environ["YT_CLIENT_ID"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]

GEMINI_MODEL = "gemini-2.5-flash"

# وصف الشخصية الثابتة (نور) — يُضاف لكل برومبت فيديو حتى تضل نفس الشخصية بكل حلقة
CHARACTER_DESCRIPTION = (
    "Noor, a cheerful young girl character in 3D Pixar-style cartoon animation: "
    "wavy brown hair in a half-up ponytail with a light blue hair tie, big warm brown eyes, "
    "rosy cheeks, wearing a turquoise puff-sleeve dress with a yellow star on the chest, "
    "white shoes with turquoise socks. She is often joined by a small smiling yellow star "
    "character with a cute face. Soft pastel background with blue sky and clouds, warm "
    "cheerful lighting, high-quality 3D animation style."
)

# مواضيع مناسبة لأطفال 5-8 سنين (يختار الموديل من ضمنها موضوع اليوم عشوائيًا)
TOPICS = [
    "animals", "colors", "numbers 1-10", "family members", "weather",
    "food and fruits", "shapes", "emotions and feelings", "actions/verbs (run, jump, eat)",
    "seasons", "body parts", "vehicles and transportation", "school objects",
    "days of the week", "clothes",
]


def generate_idea() -> dict:
    """يستخدم Gemini لتوليد فكرة فيديو (كلمة/جملة + وصف مشهد + عنوان)."""
    topic = random.choice(TOPICS)
    prompt = f"""You are creating a single YouTube Short to teach English to children aged 5-8.
The channel's main character is named Noor (a friendly cartoon girl) who appears in every video.
Topic category: {topic}

Pick ONE specific word or short phrase from this topic that a 5-8 year old should learn.
Return STRICTLY valid JSON with these exact keys, nothing else, no markdown fences:
{{
  "word": "the English word or short phrase being taught",
  "sentence": "one simple example sentence using the word, max 8 words",
  "video_prompt": "a vivid, simple scene description showing Noor actively demonstrating or pointing to the word's meaning (e.g. holding/pointing at the object, acting out the verb), cheerful and child-friendly, no text/letters in the scene itself — describe ONLY the action/scene, not Noor's appearance (that will be added separately)",
  "title": "a fun YouTube Short title under 60 characters mentioning Noor, include an emoji",
  "description": "a short YouTube description (2-3 sentences) mentioning it's an English lesson for kids with Noor, with the word and sentence, plus 5 relevant hashtags"
}}"""

    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    import json

    idea = json.loads(text)
    # نلصق وصف الشخصية الثابت مع مشهد اليوم لضمان نفس الشكل بكل فيديو
    idea["video_prompt"] = f"{CHARACTER_DESCRIPTION} Scene: {idea['video_prompt']}"
    return idea


def generate_video(video_prompt: str) -> bytes:
    """يولّد فيديو عمودي قصير عبر Cinemora (fal.ai، جودة عالية) ويرجع بايتات الفيديو."""
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
        # base64 data URI (المسار المجاني)
        b64_part = video_url.split(",", 1)[1]
        return base64.b64decode(b64_part)
    else:
        # رابط خارجي (fal.ai)
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

    import json as _json

    boundary = "cinemora_upload_boundary"
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{_json.dumps(metadata)}\r\n"
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
    print("1/3 توليد الفكرة عبر Gemini...")
    idea = generate_idea()
    print(f"   الكلمة: {idea['word']} | العنوان: {idea['title']}")

    print("2/3 توليد الفيديو عبر Cinemora...")
    video_bytes = generate_video(idea["video_prompt"])
    print(f"   حجم الفيديو: {len(video_bytes)} بايت")

    print("3/3 الرفع ليوتيوب...")
    video_id = upload_to_youtube(video_bytes, idea["title"], idea["description"])
    print(f"✅ تم الرفع: https://youtube.com/shorts/{video_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ فشل: {e}", file=sys.stderr)
        sys.exit(1)
