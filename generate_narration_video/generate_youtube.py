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
import time
from moviepy.editor import (
    TextClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
)
from moviepy.audio.fx.volumex import volumex as audio_volumex
from PIL import Image, ImageDraw, ImageFont
import textwrap

# Ensure project root is on sys.path for sibling package imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# -------------------------------
# YouTube Video Generator (1920x1080)
# Text content is embedded below in TEXT_BLOCKS
# -------------------------------

# Hardcoded content: sequence of segments with durations (seconds)
TEXT_BLOCKS = [
    {
        "text": "German Car Company hiring in Mahindra City, Chennai.",
        "duration": 10.0,
        "audio_text": "Hello friends, German car company hiring now in Mahindra City, Chennai."
    },
    {
        "text": "Work: 5 days a week. Saturday & Sunday off.",
        "duration": 10.0,
        "audio_text": "Work is only five days a week... Saturday and Sunday full holiday."
    },
    {
        "text": "Eligibility: Male & Female, Age 18–23, Freshers & Experienced.",
        "duration": 10.0,
        "audio_text": "Eligibility: Boys and girls, age eighteen to twenty three... Freshers also welcome, experienced also okay."
    },
    {
        "text": "Qualifications: Diploma / ITI / Any Degree passout.",
        "duration": 10.0,
        "audio_text": "Qualification needed: Diploma, ITI, or any degree pass out."
    },
    {
        "text": "Roles: Assembly Operator – 25 openings (Diploma only).",
        "duration": 10.0,
        "audio_text": "Assembly operator job... Twenty five openings available... Diploma candidates only."
    },
    {
        "text": "Logistics Dept – 15 openings (Degree & Diploma).",
        "duration": 10.0,
        "audio_text": "Logistics department also hiring... Fifteen openings for degree and diploma candidates."
    },
    {
        "text": "Salary: Diploma – ₹19,800 + OT ₹176/hr.",
        "duration": 10.0,
        "audio_text": "Salary for diploma candidates is nineteen thousand eight hundred... Plus overtime, one seventy six rupees per hour extra."
    },
    {
        "text": "Shift: First shift only. Food provided.",
        "duration": 10.0,
        "audio_text": "Shift is first shift only... Free food will be provided."
    },
    {
        "text": "Room facility & bus routes from Tambaram to Chengalpattu.",
        "duration": 10.0,
        "audio_text": "Room facility available... Company bus also running from Tambaram to Chengalpattu."
    },
    {
        "text": "Interview Contact: 7769003348 / 9342251196 / 7769003319.",
        "duration": 10.0,
        "audio_text": "For interview details, contact these numbers... seven seven six nine double zero, three three four eight... or nine three four two two five, one one nine six... or seven seven six nine double zero, three three one nine."
    },
    {
        "text": "",
        "duration": 8.0,
        "audio_text": "Friends, this is a good opportunity... Apply fast and don’t miss it."
    }
]


# Paths (adjust if you prefer different assets/output)
HERE = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_IMAGE = os.path.join(HERE, "youtube_bg", "bg3.mp4")  # can be .jpg/.png/.gif/.mp4
if not os.path.exists(BACKGROUND_IMAGE):
    alt = os.path.join(HERE, "background.jpeg")
    if os.path.exists(alt):
        BACKGROUND_IMAGE = alt

# Ensure output directory 'youtube_output' exists next to this script
OUTPUT_DIR = os.path.join(HERE, "youtube_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "video.mp4")
OUTPUT_AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)

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

# Audio/TTS configuration for a more energetic "youtuber" tone
YOUTUBER_SPEED = 1.06   # slight speed-up
YOUTUBER_VOLUME = 1.08  # slight volume boost
TTS_LANG = "en"
TTS_TLD = "co.in"        # adjust if you want a different accent (e.g., "co.in")

def speed_audio(aclip, factor: float):
    """Return a clip played at a different speed without using audio_speedx.
    For factor > 1.0, audio plays faster (shorter duration). For factor < 1.0, slower.
    """
    try:
        if factor is None or abs(factor - 1.0) < 1e-3:
            return aclip
        sped = aclip.fl_time(lambda t: t * factor)
        # Adjust duration explicitly
        try:
            sped.duration = float(aclip.duration) / float(factor)
        except Exception:
            pass
        return sped
    except Exception:
        return aclip

# ---------------------------------
# Google Fonts download integration
# ---------------------------------

def _weight_to_name(weight: int) -> str:
    mapping = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
    candidates = sorted(mapping.keys(), key=lambda w: abs(w - int(weight)))
    return mapping[candidates[0]]


def ensure_google_font_ttf(family: str, weight: int, base_dir: str) -> str | None:
    t0 = time.perf_counter()
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
        if VERBOSE:
            print(f"[perf] Google ZIP request start for '{family}'")
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
            print(f"[perf] Google ZIP finished in {time.perf_counter()-t0:.2f}s")
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
            if VERBOSE:
                print(f"[perf] GitHub listing start for '{family}'")
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
                        t1 = time.perf_counter()
                        with urllib.request.urlopen(req2, timeout=30) as r2:
                            ttf_bytes = r2.read()
                        out_path = os.path.join(target_dir, item["name"])
                        with open(out_path, "wb") as f:
                            f.write(ttf_bytes)
                        if VERBOSE:
                            print(f"[perf] GitHub fallback download finished in {time.perf_counter()-t1:.2f}s")
            if VERBOSE:
                print(f"[fonts] Downloaded '{family}' from GitHub fallback")
                print(f"[perf] GitHub fallback finished in {time.perf_counter()-t0:.2f}s")
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
            print(f"[perf] Font resolution total {time.perf_counter()-t0:.2f}s")
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
        try:
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
        except Exception:
            framed = _pil_text_clip(part, per_char, fontsize, font, video_size, text_width)
        subclips.append(framed)
    seg_clip = concatenate_videoclips(subclips, method="compose")
    for c in subclips:
        try:
            c.close()
        except Exception:
            pass
    gc.collect()
    return seg_clip


def static_text_clip(text: str, duration: float, fontsize: int, font: str, video_size: tuple[int, int], text_width: int):
    """Create a positioned static text clip for the given duration."""
    try:
        txt = (
            TextClip(
                text,
                fontsize=fontsize,
                font=font,
                color=TEXT_COLOR,
                method="caption",
                size=(text_width, None),
                align="center",
                stroke_color=STROKE_COLOR,
                stroke_width=STROKE_WIDTH,
                transparent=True,
            ).set_duration(max(0.01, duration))
        )
        _ = txt.get_frame(0)
        if TEXT_POS_MODE == "absolute":
            y = max(0, min(video_size[1] - txt.h, TEXT_POS_Y))
        else:
            y = (video_size[1] - txt.h) / 2 + TEXT_POS_OFFSET
        return CompositeVideoClip([txt.set_position(("center", y))], size=video_size).set_duration(max(0.01, duration))
    except Exception:
        return _pil_text_clip(text, duration, fontsize, font, video_size, text_width)


def _pil_text_clip(text: str, duration: float, fontsize: int, font_path_or_name: str, video_size: tuple[int, int], text_width: int):
    """Fallback: render text using Pillow and return an ImageClip with transparency."""
    # Resolve font path
    try:
        if os.path.isfile(font_path_or_name):
            font_obj = ImageFont.truetype(font_path_or_name, fontsize)
        else:
            font_obj = ImageFont.truetype("arial.ttf", fontsize)
    except Exception:
        font_obj = ImageFont.load_default()

    # Wrap text to fit width
    max_width_px = text_width
    lines = []
    for paragraph in str(text).splitlines():
        if not paragraph:
            lines.append("")
            continue
        # Greedy wrap
        words = paragraph.split()
        cur = []
        for w in words:
            trial = (" ".join(cur + [w])).strip()
            w_px = font_obj.getlength(trial) if hasattr(font_obj, "getlength") else font_obj.getsize(trial)[0]
            if w_px <= max_width_px or not cur:
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))

    # Compute text block size
    line_height = (font_obj.size + 10)
    text_h = max(line_height * max(1, len(lines)), line_height)
    text_w = max_width_px

    # Create transparent image and draw text with stroke
    img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y_cursor = 0
    for line in lines:
        if not line:
            y_cursor += line_height
            continue
        line_w = font_obj.getlength(line) if hasattr(font_obj, "getlength") else font_obj.getsize(line)[0]
        x = (text_w - line_w) / 2
        # Stroke
        for dx in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
            for dy in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y_cursor + dy), line, font=font_obj, fill=STROKE_COLOR)
        # Fill
        draw.text((x, y_cursor), line, font=font_obj, fill=TEXT_COLOR)
        y_cursor += line_height

    # Convert to MoviePy ImageClip
    np_img = np.array(img)
    clip = ImageClip(np_img).set_duration(max(0.01, duration))
    # Position vertically similar to TextClip logic
    h = np_img.shape[0]
    if TEXT_POS_MODE == "absolute":
        y = max(0, min(video_size[1] - h, TEXT_POS_Y))
    else:
        y = (video_size[1] - h) / 2 + TEXT_POS_OFFSET
    return CompositeVideoClip([clip.set_position(("center", y))], size=video_size).set_duration(max(0.01, duration))


def main():
    # Determine mode early
    image_mode = any(arg in ("--image", "image", "-i") for arg in sys.argv[1:])
    if VERBOSE:
        print(f"[perf] main start | mode={'image' if image_mode else 'video'}")
    t_main0 = time.perf_counter()

    if image_mode:
        # In image mode, we don't need TTS. Compute duration from provided durations.
        total_duration = sum(max(0.2, float(b.get("duration", 1.0))) for b in TEXT_BLOCKS) + len(TEXT_BLOCKS) * PAUSE_AFTER
    else:
        # First pass: generate/load audio per block and measure processed durations
        blocks_audio = []  # list of dicts: {"path", "duration"}
        for idx, block in enumerate(TEXT_BLOCKS, start=1):
            seg_text = block["text"].strip()
            audio_path = os.path.join(OUTPUT_AUDIO_DIR, f"block_{idx:02}.mp3")
            # Prefer audio_text if provided for narration
            speak_text = str(block.get("audio_text", seg_text)).strip() or seg_text

            try:
                t_tts0 = time.perf_counter()
                from generate_infography_video.handler.audio_handler import generate_tts
                if not os.path.exists(audio_path):
                    generate_tts(speak_text, audio_path)
                    if VERBOSE:
                        print(f"[perf][block {idx}] TTS generated in {time.perf_counter()-t_tts0:.2f}s")
                else:
                    if VERBOSE:
                        print(f"[perf][block {idx}] TTS cached: {audio_path}")
            except Exception as e:
                if VERBOSE:
                    print(f"[audio] TTS generation failed for block {idx}: {e}")

            processed_duration = None
            if os.path.exists(audio_path):
                try:
                    t_ap0 = time.perf_counter()
                    aclip = AudioFileClip(audio_path)
                    if YOUTUBER_VOLUME and abs(YOUTUBER_VOLUME - 1.0) > 1e-3:
                        aclip = aclip.fx(audio_volumex, YOUTUBER_VOLUME)
                    if YOUTUBER_SPEED and abs(YOUTUBER_SPEED - 1.0) > 1e-3:
                        aclip = speed_audio(aclip, YOUTUBER_SPEED)
                    processed_duration = float(aclip.duration)
                    aclip.close()
                    if VERBOSE:
                        print(f"[perf][block {idx}] audio load+fx {time.perf_counter()-t_ap0:.2f}s | dur={processed_duration:.2f}s")
                except Exception as e:
                    if VERBOSE:
                        print(f"[audio] Failed to load/process audio for block {idx}: {e}")

            if processed_duration is None:
                processed_duration = max(0.2, float(block.get("duration", 3.0)))
                audio_path = None

            blocks_audio.append({"path": audio_path, "duration": processed_duration})

        total_duration = sum(b["duration"] for b in blocks_audio) + len(blocks_audio) * PAUSE_AFTER

    # Background: support image, gif, or video, loop to full computed duration
    try:
        t_bg0 = time.perf_counter()
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
        if VERBOSE:
            print(f"[perf] background setup {time.perf_counter()-t_bg0:.2f}s | total_duration={total_duration:.2f}s")
    except Exception:
        bg_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE).set_duration(total_duration)

    # Image-only mode
    if image_mode:
        cursor_time = 0.0
        for idx, block in enumerate(TEXT_BLOCKS, start=1):
            seg_text = block["text"].strip()
            seg_duration = max(0.2, float(block["duration"]))
            t_shot0 = time.perf_counter()
            # Use PIL-based rendering directly to avoid ImageMagick dependency
            txt_clip = _pil_text_clip(seg_text, 0.1, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH)

            t_snapshot = max(0.0, min(cursor_time + seg_duration, total_duration - 1e-3))
            try:
                bg_frame = bg_clip.get_frame(t_snapshot)
            except Exception:
                bg_frame = bg_clip.get_frame(0)
            bg_frame_clip = ImageClip(bg_frame).set_duration(0.1)

            comp = CompositeVideoClip([bg_frame_clip, txt_clip], size=VIDEO_SIZE).set_duration(0.1)
            out_path = os.path.join(OUTPUT_DIR, f"shot_{idx:02}.png")
            comp.save_frame(out_path, t=0.0)
            if VERBOSE:
                print(f"[perf][image][block {idx}] snapshot saved in {time.perf_counter()-t_shot0:.2f}s | path={out_path}")

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

    # Build text layers and audio timeline
    clips = []
    audio_timeline = []
    cursor = 0.0
    for idx, (block, ba) in enumerate(zip(TEXT_BLOCKS, blocks_audio), start=1):
        seg_text = block["text"].strip()
        audio_dur = max(0.2, float(ba["duration"]))

        # Typing animation set to a little faster than the voice length
        typing_dur = max(0.4, min(audio_dur * 0.65, audio_dur - 0.2))
        hold_dur = max(0.0, audio_dur - typing_dur)

        t_blk0 = time.perf_counter()
        try:
            typing = typing_clip_by_chars(seg_text, typing_dur, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH).set_start(cursor)
            clips.append(typing)
        except Exception:
            fallback = static_text_clip(seg_text, typing_dur, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH).set_start(cursor)
            clips.append(fallback)
        finally:
            gc.collect()

        if hold_dur > 0.001:
            hold_clip = static_text_clip(seg_text, hold_dur, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH).set_start(cursor + typing_dur)
            clips.append(hold_clip)

        # Add small pause after the audio ends, keeping the last frame
        if PAUSE_AFTER > 1e-3:
            pause_clip = static_text_clip(seg_text, PAUSE_AFTER, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH).set_start(cursor + audio_dur)
            clips.append(pause_clip)

        # Attach audio (if exists) aligned with the block start
        if ba["path"] and os.path.exists(ba["path"]):
            try:
                aclip = AudioFileClip(ba["path"]) 
                if YOUTUBER_VOLUME and abs(YOUTUBER_VOLUME - 1.0) > 1e-3:
                    aclip = aclip.fx(audio_volumex, YOUTUBER_VOLUME)
                if YOUTUBER_SPEED and abs(YOUTUBER_SPEED - 1.0) > 1e-3:
                    aclip = speed_audio(aclip, YOUTUBER_SPEED)
                aclip = aclip.set_start(cursor)
                audio_timeline.append(aclip)
            except Exception as e:
                if VERBOSE:
                    print(f"[audio] Could not add audio for block {idx}: {e}")

        if VERBOSE:
            print(f"[perf][block {idx}] build clips {time.perf_counter()-t_blk0:.2f}s | audio_dur={audio_dur:.2f}s typing={typing_dur:.2f}s hold={hold_dur:.2f}s")
        cursor += audio_dur + PAUSE_AFTER

    t_comp0 = time.perf_counter()
    final = CompositeVideoClip([bg_clip] + clips, size=VIDEO_SIZE)
    if VERBOSE:
        print(f"[perf] composite build {time.perf_counter()-t_comp0:.2f}s")

    # Build and attach audio track if any
    if audio_timeline:
        try:
            t_aud0 = time.perf_counter()
            composite_audio = CompositeAudioClip(audio_timeline)
            final = final.set_audio(composite_audio)
            if VERBOSE:
                print(f"[perf] composite audio {time.perf_counter()-t_aud0:.2f}s")
        except Exception as e:
            if VERBOSE:
                print(f"[audio] Failed to set composite audio: {e}")

    if VERBOSE:
        print("[perf] write_videofile start")
    t_write0 = time.perf_counter()
    final.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio=bool(audio_timeline),
        threads=1,
        logger=None,
    )
    if VERBOSE:
        print(f"[perf] write_videofile finished in {time.perf_counter()-t_write0:.2f}s")

    final.close()
    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    bg_clip.close()
    for a in audio_timeline:
        try:
            a.close()
        except Exception:
            pass
    gc.collect()

    print(f"✅ YouTube video saved to {OUTPUT_VIDEO}")
    if VERBOSE:
        print(f"[perf] main total {time.perf_counter()-t_main0:.2f}s")


if __name__ == "__main__":
    main()
