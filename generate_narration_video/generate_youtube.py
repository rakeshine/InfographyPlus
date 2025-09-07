import os
import gc
import json
import urllib.request
import urllib.parse
import zipfile
import io
import re
import sys
import numpy as np
from moviepy.editor import (
    TextClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
)

# -------------------------------
# YouTube Video Generator (1920x1080)
# Text content is embedded below in TEXT_BLOCKS
# -------------------------------

# Hardcoded content: sequence of segments with durations (seconds)
TEXT_BLOCKS = [
    {"text": "German Car Company hiring in Mahindra City, Chennai.", "duration": 10.0},
    {"text": "Work: 5 days a week. Saturday & Sunday off.", "duration": 10.0},
    {"text": "Eligibility: Male & Female, Age 18–23, Freshers & Experienced.", "duration": 10.0},
    {"text": "Qualifications: Diploma / ITI / Any Degree passout.", "duration": 10.0},
    {"text": "Roles: Assembly Operator – 25 openings (Diploma only).", "duration": 10.0},
    {"text": "Logistics Dept – 15 openings (Degree & Diploma).", "duration": 10.0},
    {"text": "Salary: Diploma – ₹19,800 + OT ₹176/hr.", "duration": 10.0},
    {"text": "Shift: First shift only. Food provided.", "duration": 10.0},
    {"text": "Room facility & bus routes from Tambaram to Chengalpattu.", "duration": 10.0},
    {"text": "Interview Contact: 7769003348 / 9342251196 / 7769003319.", "duration": 10.0}
]

# Paths (adjust if you prefer different assets/output)
HERE = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_IMAGE = os.path.join(HERE, "youtube_bg", "bg2.mp4")  # can be .jpg/.png/.gif/.mp4
if not os.path.exists(BACKGROUND_IMAGE):
    alt = os.path.join(HERE, "background.jpeg")
    if os.path.exists(alt):
        BACKGROUND_IMAGE = alt

# Ensure output directory 'youtube_output' exists next to this script
OUTPUT_DIR = os.path.join(HERE, "youtube_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "video.mp4")

# Video/Text config for standard YouTube
VIDEO_SIZE = (1920, 1080)  # 16:9 landscape
FONT = "Helvetica-Bold"
FONT_SIZE = 64
TEXT_WIDTH = int(VIDEO_SIZE[0] * 0.70)  # ~70% of width for readability
FPS = 30

# Styling
TEXT_COLOR = "#FFEE58"
STROKE_COLOR = "#0A0A0A"
STROKE_WIDTH = 3

# Pause after each text block (seconds)
PAUSE_AFTER = 1.2

# Vertical positioning defaults (can be overridden per background via JSON)
TEXT_POS_MODE = "center"   # 'center' or 'absolute'
TEXT_POS_Y = 0              # absolute y from top if TEXT_POS_MODE == 'absolute'
TEXT_POS_OFFSET = -60       # place slightly above center for 16:9

# Verbose logging for font resolution
VERBOSE = True

# ---------------------------------
# Google Fonts download integration
# ---------------------------------

def _weight_to_name(weight: int) -> str:
    mapping = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
    candidates = sorted(mapping.keys(), key=lambda w: abs(w - int(weight)))
    return mapping[candidates[0]]


def ensure_google_font_ttf(family: str, weight: int, base_dir: str) -> str | None:
    os.makedirs(base_dir, exist_ok=True)
    family_safe = family.replace(" ", "-")
    target_dir = os.path.join(base_dir, "google", family_safe)
    os.makedirs(target_dir, exist_ok=True)

    if VERBOSE:
        print(f"[fonts] Resolving Google Font '{family}' weight {weight} → {_weight_to_name(weight)}")
    desired_name = _weight_to_name(weight)
    try:
        for fn in os.listdir(target_dir):
            if fn.lower().endswith(".ttf") and desired_name.lower() in fn.lower():
                return os.path.join(target_dir, fn)
    except Exception:
        pass

    try:
        url = "https://fonts.google.com/download?family=" + urllib.parse.quote(family)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for member in zf.namelist():
                if member.lower().endswith(".ttf"):
                    name = os.path.basename(member)
                    if not name:
                        continue
                    out_path = os.path.join(target_dir, name)
                    with zf.open(member) as src, open(out_path, "wb") as dst:
                        dst.write(src.read())
        if VERBOSE:
            print(f"[fonts] Downloaded '{family}' ZIP from Google Fonts")
    except Exception:
        if VERBOSE:
            print(f"[fonts] Primary download failed for '{family}'. Trying GitHub fallback...")
        try:
            api_family = family.lower().replace(" ", "")
            base_api = f"https://api.github.com/repos/google/fonts/contents/ofl/{api_family}"
            def fetch_dir(url):
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="ignore"))
            listing = fetch_dir(base_api)
            subdirs = []
            for item in listing:
                if not isinstance(item, dict):
                    continue
                name = item.get("name", "")
                path_url = item.get("download_url") or item.get("browser_download_url") or item.get("html_url")
                if not name:
                    continue
                if name.lower().endswith(".ttf") and path_url:
                    dl_url = path_url.replace("/blob/", "/")
                    req2 = urllib.request.Request(dl_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req2, timeout=30) as r2:
                        ttf_bytes = r2.read()
                    out_path = os.path.join(target_dir, name)
                    with open(out_path, "wb") as f:
                        f.write(ttf_bytes)
                elif item.get("type") == "dir" and name.lower() == "static" and item.get("url"):
                    subdirs.append(item.get("url"))
            for sdir in subdirs:
                static_listing = fetch_dir(sdir)
                for item in static_listing:
                    if isinstance(item, dict) and item.get("name", "").lower().endswith(".ttf"):
                        dl_url = item.get("download_url") or item.get("browser_download_url") or item.get("html_url")
                        if not dl_url:
                            continue
                        dl_url = dl_url.replace("/blob/", "/")
                        req2 = urllib.request.Request(dl_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req2, timeout=30) as r2:
                            ttf_bytes = r2.read()
                        out_path = os.path.join(target_dir, item["name"])
                        with open(out_path, "wb") as f:
                            f.write(ttf_bytes)
            if VERBOSE:
                print(f"[fonts] Downloaded '{family}' from GitHub fallback")
        except Exception:
            if VERBOSE:
                print(f"[fonts] GitHub fallback failed for '{family}'")
            return None

    try:
        files = [f for f in os.listdir(target_dir) if f.lower().endswith(".ttf")]
        if not files:
            return None
        desired = _weight_to_name(weight).lower()
        def score(fn: str) -> tuple:
            n = fn.lower()
            s = 0
            if "italic" in n:
                s -= 10
            if desired in n:
                s += 5
            if "regular" in n and desired == "regular":
                s += 3
            if "[wght]" in n:
                s += 1
            if "[" not in n and "]" not in n:
                s += 2
            return (s, -len(fn))
        files_sorted = sorted(files, key=score, reverse=True)
        best = files_sorted[0]
        path = os.path.join(target_dir, best)
        if VERBOSE:
            print(f"[fonts] Selected best match {path}")
        return path
    except Exception:
        return None


def _parse_font_size(val, default):
    try:
        if isinstance(val, (int, float)):
            return int(float(val))
        if isinstance(val, str):
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", val)
            if m:
                return int(float(m.group(1)))
    except Exception:
        pass
    return default

# Load bg_templates.json from youtube_bg
try:
    templates_path = os.path.join(HERE, "youtube_bg", "bg_templates.json")
    if os.path.exists(templates_path):
        with open(templates_path, "r", encoding="utf-8") as f:
            bg_templates = json.load(f)
        bg_name = os.path.basename(BACKGROUND_IMAGE)
        if bg_name in bg_templates:
            tpl = bg_templates[bg_name]
            try:
                FONT_SIZE = _parse_font_size(tpl.get("font_size", FONT_SIZE), FONT_SIZE)
            except Exception:
                pass
            try:
                TEXT_COLOR = tpl.get("text_color", TEXT_COLOR)
            except Exception:
                pass
            fonts_dir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "fonts")
            if "font_family" in tpl:
                fam = str(tpl["font_family"]).strip()
                if fam.lower().endswith((".ttf", ".otf")):
                    if os.path.isabs(fam):
                        FONT = fam
                    else:
                        candidates = [
                            os.path.join(fonts_dir, fam),
                            os.path.join(fonts_dir, "google", fam),
                            os.path.join(fonts_dir, "google", os.path.basename(fam).split("-")[0], os.path.basename(fam)),
                        ]
                        FONT = candidates[0]
                        for c in candidates:
                            if os.path.exists(c):
                                FONT = c
                                break
                else:
                    try:
                        weight = int(float(tpl.get("font_weight", 400)))
                    except Exception:
                        weight = 400
                    ttf_path = ensure_google_font_ttf(fam, weight, fonts_dir)
                    if ttf_path and os.path.exists(ttf_path):
                        FONT = ttf_path
                    else:
                        FONT = fam
            else:
                font_val = str(tpl.get("font", FONT))
                if os.path.sep in font_val or font_val.lower().endswith((".ttf", ".otf")):
                    abs_path = font_val if os.path.isabs(font_val) else os.path.join(fonts_dir, font_val)
                    FONT = abs_path
                else:
                    inferred_weight = 400
                    fam = re.sub(r"[- ]?(thin|extralight|light|regular|medium|semibold|bold|extrabold|black)\b", "", font_val, flags=re.I).strip()
                    ttf_path = ensure_google_font_ttf(fam, inferred_weight, fonts_dir)
                    if ttf_path and os.path.exists(ttf_path):
                        FONT = ttf_path
                    else:
                        FONT = font_val
            y_val = tpl.get("y", None)
            y_off = tpl.get("y_offset", None)
            if isinstance(y_val, str) and y_val.lower() == "center":
                TEXT_POS_MODE = "center"
            elif isinstance(y_val, (int, float, str)):
                try:
                    TEXT_POS_MODE = "absolute"
                    TEXT_POS_Y = int(float(str(y_val).replace("px", "")))
                except Exception:
                    pass
            if isinstance(y_off, (int, float, str)):
                try:
                    TEXT_POS_OFFSET = int(float(str(y_off).replace("px", "")))
                except Exception:
                    pass
except Exception:
    pass


def typing_clip_by_chars(text: str, duration: float, fontsize: int, font: str, video_size: tuple[int, int], text_width: int):
    chars = list(text)
    n = max(1, len(chars))
    per_char = max(0.01, duration / n)
    subclips = []
    for i in range(1, n + 1):
        part = "".join(chars[:i])
        txt = (
            TextClip(
                part,
                fontsize=fontsize,
                font=font,
                color=TEXT_COLOR,
                method="caption",
                size=(text_width, None),
                align="center",
                stroke_color=STROKE_COLOR,
                stroke_width=STROKE_WIDTH,
                transparent=True,
            ).set_duration(per_char)
        )
        _ = txt.get_frame(0)
        if TEXT_POS_MODE == "absolute":
            y = max(0, min(video_size[1] - txt.h, TEXT_POS_Y))
        else:
            y = (video_size[1] - txt.h) / 2 + TEXT_POS_OFFSET
        txt = txt.set_position(("center", y))
        framed = CompositeVideoClip([txt], size=video_size).set_duration(per_char)
        subclips.append(framed)
    seg_clip = concatenate_videoclips(subclips, method="compose")
    for c in subclips:
        try:
            c.close()
        except Exception:
            pass
    gc.collect()
    return seg_clip


def main():
    total_duration = sum(b["duration"] for b in TEXT_BLOCKS) + len(TEXT_BLOCKS) * PAUSE_AFTER

    # background: support image, gif, or video
    try:
        lower = BACKGROUND_IMAGE.lower()
        if lower.endswith((".gif", ".webp", ".mp4", ".mov", ".mkv", ".avi", ".webm")):
            bg_clip = (
                VideoFileClip(BACKGROUND_IMAGE)
                .without_audio()
                .resize(VIDEO_SIZE)
                .loop(duration=total_duration)
            )
        else:
            bg_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE).set_duration(total_duration)
    except Exception:
        bg_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE).set_duration(total_duration)

    # Image-only mode
    image_mode = any(arg in ("--image", "image", "-i") for arg in sys.argv[1:])
    if image_mode:
        cursor_time = 0.0
        for idx, block in enumerate(TEXT_BLOCKS, start=1):
            seg_text = block["text"].strip()
            seg_duration = max(0.2, float(block["duration"]))
            txt_clip = TextClip(
                seg_text,
                fontsize=FONT_SIZE,
                font=FONT,
                color=TEXT_COLOR,
                method="caption",
                size=(TEXT_WIDTH, None),
                align="center",
                stroke_color=STROKE_COLOR,
                stroke_width=STROKE_WIDTH,
                transparent=True,
            ).set_duration(0.1)
            _ = txt_clip.get_frame(0)
            if TEXT_POS_MODE == "absolute":
                y = max(0, min(VIDEO_SIZE[1] - txt_clip.h, TEXT_POS_Y))
            else:
                y = (VIDEO_SIZE[1] - txt_clip.h) / 2 + TEXT_POS_OFFSET
            txt_clip = txt_clip.set_position(("center", y))

            t_snapshot = max(0.0, min(cursor_time + seg_duration, total_duration - 1e-3))
            try:
                bg_frame = bg_clip.get_frame(t_snapshot)
            except Exception:
                bg_frame = bg_clip.get_frame(0)
            bg_frame_clip = ImageClip(bg_frame).set_duration(0.1)

            comp = CompositeVideoClip([bg_frame_clip, txt_clip], size=VIDEO_SIZE).set_duration(0.1)
            out_path = os.path.join(OUTPUT_DIR, f"shot_{idx:02}.png")
            comp.save_frame(out_path, t=0.0)

            try: comp.close()
            except Exception: pass
            try: bg_frame_clip.close()
            except Exception: pass
            try: txt_clip.close()
            except Exception: pass

            cursor_time += seg_duration + PAUSE_AFTER

        try: bg_clip.close()
        except Exception: pass
        gc.collect()
        print(f"🖼️  Saved {len(TEXT_BLOCKS)} images to {OUTPUT_DIR}")
        return

    # Build text layers
    clips = []
    cursor = 0.0
    for idx, block in enumerate(TEXT_BLOCKS, start=1):
        seg_text = block["text"].strip()
        seg_duration = max(0.2, float(block["duration"]))
        try:
            seg_clip = typing_clip_by_chars(seg_text, seg_duration, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH)
            seg_clip = seg_clip.set_start(cursor)
            clips.append(seg_clip)
        except Exception:
            fallback = TextClip(
                seg_text,
                fontsize=FONT_SIZE,
                font=FONT,
                color=TEXT_COLOR,
                method="caption",
                size=(TEXT_WIDTH, None),
                align="center",
                stroke_color=STROKE_COLOR,
                stroke_width=STROKE_WIDTH,
                transparent=True,
            )
            _ = fallback.get_frame(0)
            if TEXT_POS_MODE == "absolute":
                y = max(0, min(VIDEO_SIZE[1] - fallback.h, TEXT_POS_Y))
            else:
                y = (VIDEO_SIZE[1] - fallback.h) / 2 + TEXT_POS_OFFSET
            fallback = fallback.set_start(cursor).set_duration(seg_duration).set_position(("center", y))
            clips.append(fallback)
        finally:
            gc.collect()

        pause_clip = TextClip(
            seg_text,
            fontsize=FONT_SIZE,
            font=FONT,
            color=TEXT_COLOR,
            method="caption",
            size=(TEXT_WIDTH, None),
            align="center",
            stroke_color=STROKE_COLOR,
            stroke_width=STROKE_WIDTH,
            transparent=True,
        )
        _ = pause_clip.get_frame(0)
        if TEXT_POS_MODE == "absolute":
            y = max(0, min(VIDEO_SIZE[1] - pause_clip.h, TEXT_POS_Y))
        else:
            y = (VIDEO_SIZE[1] - pause_clip.h) / 2 + TEXT_POS_OFFSET
        pause_clip = pause_clip.set_start(cursor + seg_duration).set_duration(PAUSE_AFTER).set_position(("center", y))
        clips.append(pause_clip)

        cursor += seg_duration + PAUSE_AFTER

    final = CompositeVideoClip([bg_clip] + clips, size=VIDEO_SIZE)

    final.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio=False,
        threads=1,
        logger=None,
    )

    final.close()
    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    bg_clip.close()
    gc.collect()

    print(f"✅ YouTube video saved to {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
