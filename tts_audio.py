"""
tts_audio.py
============
يولّد نطقًا صوتيًا واضحًا وبطيئًا مناسبًا للأطفال، عبر gTTS.
"""

import tempfile

from gtts import gTTS


def build_narration_text(lesson: dict) -> str:
    """يبني نص السرد المنطوق حسب نوع الدرس (حرف / مفردة / قراءة)."""
    stage = lesson["stage"]
    if stage == "alphabet":
        letter = lesson["letter"]
        word = lesson["word"]
        # كرّر الحرف مرتين لتثبيته بذهن الطفل
        return f"{letter}. {letter}. {letter} is for {word}. {lesson['sentence']}"
    elif stage == "vocabulary":
        word = lesson["word"]
        return f"{word}. {word}. {lesson['sentence']}"
    else:  # reading
        sentence = lesson["sentence"]
        return f"{sentence} {sentence}"


def generate_narration_audio(lesson: dict) -> str:
    """يولّد ملف mp3 مؤقت ويرجع مساره."""
    text = build_narration_text(lesson)
    tts = gTTS(text=text, lang="en", slow=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tmp.name)
    return tmp.name
