"""
video_compose.py
=================
يأخذ فيديو نور (المولَّد من Cinemora) + ملف صوت النطق، ويرجع فيديو نهائي:
  - النص التعليمي محروق (drawtext) بشكل واضح للأطفال
  - الصوت الأصلي مستبدل بصوت نطق واضح ومقروء (gTTS)، مع صمت في الآخر لو الصوت أقصر من الفيديو

يعتمد على وجود ffmpeg/ffprobe مثبّتين على الجهاز (يُثبَّتان في workflow).
"""

import subprocess
import tempfile

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _escape_drawtext(text: str) -> str:
    """يهرّب الرموز الخاصة اللي ممكن تكسر فلتر drawtext في ffmpeg."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\u2019")  # نستبدل الفاصلة العليا برمز مشابه بصريًا لتفادي كسر الفلتر
    )


def _get_duration_seconds(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _build_drawtext_chain(overlay_lines: list) -> str:
    """يبني سلسلة فلاتر drawtext، سطر فوق الآخر، بخط كبير وواضح مع حدود سوداء."""
    filters = []
    n_lines = len(overlay_lines)
    # نوزّع الأسطر عموديًا بالثلث السفلي من الفيديو
    base_y_fraction = 0.62
    line_gap_fraction = 0.14
    for i, line in enumerate(overlay_lines):
        escaped = _escape_drawtext(line)
        fontsize = 100 if n_lines == 1 or i == 0 else 64
        y_fraction = base_y_fraction + i * line_gap_fraction
        filters.append(
            f"drawtext=fontfile={FONT_PATH}:text='{escaped}':"
            f"fontsize={fontsize}:fontcolor=white:borderw=6:bordercolor=black:"
            f"x=(w-text_w)/2:y=h*{y_fraction}"
        )
    return ",".join(filters)


def compose_final_video(raw_video_path: str, narration_audio_path: str, overlay_lines: list, output_path: str) -> None:
    """
    يدمج الفيديو الأصلي مع نص محروق وصوت النطق، ويحفظ الناتج في output_path.
    """
    video_duration = _get_duration_seconds(raw_video_path)
    drawtext_chain = _build_drawtext_chain(overlay_lines)

    filter_complex = (
        f"[0:v]{drawtext_chain}[v];"
        f"[1:a]apad[a]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", raw_video_path,
        "-i", narration_audio_path,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-t", str(video_duration),
        "-c:v", "libx264", "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def save_bytes_to_temp(video_bytes: bytes, suffix: str = ".mp4") -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(video_bytes)
    tmp.flush()
    return tmp.name
