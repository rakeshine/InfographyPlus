import os
import gc
import math
import json
import urllib.request
import urllib.parse
import zipfile
import io
import re
from moviepy.editor import (
    TextClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
)

# -------------------------------
# YouTube Shorts Generator (1080x1920)
# Text content is embedded below in TEXT_BLOCKS
# -------------------------------

# Paths (adjust if you prefer different assets/output)
HERE = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_IMAGE = os.path.join(HERE, "shorts_bg", "bg4.gif")  # fallback to background.jpeg if .jpg not present
if not os.path.exists(BACKGROUND_IMAGE):
    alt = os.path.join(HERE, "background.jpeg")
    if os.path.exists(alt):
        BACKGROUND_IMAGE = alt

# Ensure output directory 'shorts_output' exists next to this script
OUTPUT_DIR = os.path.join(HERE, "shorts_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "shorts.mp4")

# Video/Text config for Shorts
VIDEO_SIZE = (1080, 1920)  # 9:16
# Prefer a bold, highly legible system font on macOS. Adjust if needed.
FONT = "Helvetica-Bold"
FONT_SIZE = 78                       # larger for vertical layout
TEXT_WIDTH = int(VIDEO_SIZE[0] * 0.85)  # wrap width ~85% of screen width
FPS = 30

# Styling for reels
TEXT_COLOR = "#FFEE58"      # bright lemon
STROKE_COLOR = "#0A0A0A"    # near-black outline
STROKE_WIDTH = 3

# Pause after each text block (seconds)
PAUSE_AFTER = 1.8

# Vertical positioning defaults (can be overridden per background via JSON)
TEXT_POS_MODE = "center"   # 'center' or 'absolute'
TEXT_POS_Y = 0              # absolute y from top if TEXT_POS_MODE == 'absolute'
TEXT_POS_OFFSET = 0         # pixel offset added to centered position (positive moves down)

# Verbose logging for font resolution (set to False to reduce console logs)
VERBOSE = True

# ---------------------------------
# Google Fonts download integration
# ---------------------------------
def _weight_to_name(weight: int) -> str:
    mapping = {
        100: "Thin",
        200: "ExtraLight",
        300: "Light",
        400: "Regular",
        500: "Medium",
        600: "SemiBold",
        700: "Bold",
        800: "ExtraBold",
        900: "Black",
    }
    # snap to nearest standard weight
    candidates = sorted(mapping.keys(), key=lambda w: abs(w - int(weight)))
    return mapping[candidates[0]]


def ensure_google_font_ttf(family: str, weight: int, base_dir: str) -> str | None:
    """Download a Google Font family ZIP and return a local TTF path for the requested weight.

    - family: e.g., "Poppins", "Roboto Slab" (with spaces)
    - weight: numeric (e.g., 400, 700)
    - base_dir: directory where fonts should be stored (assets/fonts)
    Returns absolute path to a .ttf if found, otherwise None.
    """
    os.makedirs(base_dir, exist_ok=True)
    family_safe = family.replace(" ", "-")
    target_dir = os.path.join(base_dir, "google", family_safe)
    os.makedirs(target_dir, exist_ok=True)

    if VERBOSE:
        print(f"[fonts] Resolving Google Font '{family}' weight {weight} → {_weight_to_name(weight)}")
    # If already downloaded, try to match locally first
    desired_name = _weight_to_name(weight)
    try:
        for fn in os.listdir(target_dir):
            if fn.lower().endswith(".ttf") and desired_name.lower() in fn.lower():
                return os.path.join(target_dir, fn)
    except Exception:
        pass

    # Download ZIP from Google Fonts (may require a User-Agent)
    try:
        url = "https://fonts.google.com/download?family=" + urllib.parse.quote(family)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Extract only TTF files into target_dir
            for member in zf.namelist():
                if member.lower().endswith(".ttf"):
                    # Sanitize filename
                    name = os.path.basename(member)
                    if not name:
                        continue
                    out_path = os.path.join(target_dir, name)
                    # Write file
                    with zf.open(member) as src, open(out_path, "wb") as dst:
                        dst.write(src.read())
        if VERBOSE:
            print(f"[fonts] Downloaded '{family}' ZIP from Google Fonts")
    except Exception:
        if VERBOSE:
            print(f"[fonts] Primary download failed for '{family}'. Trying GitHub fallback...")
        # Fallback: fetch TTFs via GitHub API from google/fonts (including static subdir)
        try:
            api_family = family.lower().replace(" ", "")
            base_api = f"https://api.github.com/repos/google/fonts/contents/ofl/{api_family}"
            def fetch_dir(url):
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="ignore"))

            listing = fetch_dir(base_api)
            subdirs = []
            # Download TTFs in root and capture 'static' folder if present
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

            # Also fetch static dir TTFs (preferred for weight-specific files)
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

    # Try to find best matching TTF now
    try:
        files = [f for f in os.listdir(target_dir) if f.lower().endswith(".ttf")]
        if not files:
            return None

        # If we only have a variable [wght] file and not the static desired weight, try to fetch the static weight directly
        have_desired = any(_weight_to_name(weight).lower() in f.lower() for f in files)
        have_non_italic = any(("italic" not in f.lower()) for f in files)
        only_variable = all("[wght]" in f.lower() for f in files)
        if (not have_desired or not have_non_italic) and only_variable:
            fam_plain = family.replace(" ", "")
            desired_name = _weight_to_name(weight)
            # Map desired weight name to suffix
            suffix = desired_name
            # Compose a likely static filename: FamilyName-Weight.ttf
            static_file = f"{family.replace(' ', '')}-{suffix}.ttf"
            raw_urls = [
                f"https://raw.githubusercontent.com/google/fonts/main/ofl/{fam_plain}/static/{static_file}",
                f"https://raw.githubusercontent.com/google/fonts/main/ofl/{fam_plain}/{static_file}",
            ]
            for raw in raw_urls:
                try:
                    req3 = urllib.request.Request(raw, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req3, timeout=30) as r3:
                        ttf_bytes = r3.read()
                    out_path = os.path.join(target_dir, static_file)
                    with open(out_path, "wb") as f:
                        f.write(ttf_bytes)
                    if VERBOSE:
                        print(f"[fonts] Pulled static weight directly {out_path}")
                    files.append(static_file)
                    break
                except Exception:
                    continue

        # Score files: prefer non-italic, prefer static weight match, then variable non-italic
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
                s += 1  # variable font, acceptable but less ideal than static named weight
            # prefer files from static naming convention (no brackets)
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

def _infer_weight_from_name(name: str) -> int:
    n = name.lower()
    # explicit numeric weight if present
    m = re.search(r"\b(100|200|300|400|500|600|700|800|900)\b", n)
    if m:
        return int(m.group(1))
    # common keywords
    if "black" in n:
        return 900
    if "extrabold" in n or "extra-bold" in n or "x-bold" in n or "xbold" in n:
        return 800
    if "semibold" in n or "semi-bold" in n:
        return 600
    if "bold" in n:
        return 700
    if "medium" in n:
        return 500
    if "light" in n:
        return 300
    if "thin" in n:
        return 100
    return 400

# Override typography and vertical position from bg_templates.json if there is a matching entry for the selected background
try:
    templates_path = os.path.join(HERE, "shorts_bg", "bg_templates.json")
    if os.path.exists(templates_path):
        with open(templates_path, "r", encoding="utf-8") as f:
            bg_templates = json.load(f)
        bg_name = os.path.basename(BACKGROUND_IMAGE)
        if bg_name in bg_templates:
            tpl = bg_templates[bg_name]
            # If a direct font path or family is provided, apply; support Google Fonts auto-download
            FONT_SIZE = int(float(tpl.get("font_size", FONT_SIZE)))
            TEXT_COLOR = tpl.get("text_color", TEXT_COLOR)

            # Preferred order: use google font if specified, else use provided font string as-is
            fonts_dir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "fonts")
            if "font_family" in tpl:
                fam = str(tpl["font_family"]).strip()
                # If user provided a filename (e.g., 'Montserrat-Bold.ttf'), resolve it under assets/fonts
                if fam.lower().endswith((".ttf", ".otf")):
                    if os.path.isabs(fam):
                        FONT = fam
                    else:
                        # Try common locations
                        candidates = []
                        # as given relative to assets/fonts
                        candidates.append(os.path.join(fonts_dir, fam))
                        # under assets/fonts/google
                        candidates.append(os.path.join(fonts_dir, "google", fam))
                        # under assets/fonts/google/<Family>/
                        base_name = os.path.basename(fam)
                        fam_dir = re.split(r"[- ]", base_name, maxsplit=1)[0]
                        candidates.append(os.path.join(fonts_dir, "google", fam_dir, base_name))
                        FONT = candidates[0]
                        for c in candidates:
                            if os.path.exists(c):
                                FONT = c
                                break
                else:
                    weight = int(float(tpl.get("font_weight", 400)))
                    ttf_path = ensure_google_font_ttf(fam, weight, fonts_dir)
                    if ttf_path and os.path.exists(ttf_path):
                        FONT = ttf_path
                    else:
                        # fallback to family name (requires system-installed font)
                        FONT = fam
            else:
                # Support 'font' as either a direct path, a system family, or a Google family hint
                font_val = str(tpl.get("font", FONT))
                fonts_dir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "fonts")

                # If it looks like a path or endswith ttf/otf, resolve absolute path
                if os.path.sep in font_val or font_val.lower().endswith((".ttf", ".otf")):
                    abs_path = font_val if os.path.isabs(font_val) else os.path.join(fonts_dir, font_val)
                    FONT = abs_path
                else:
                    # Treat as family name; try Google Fonts download using inferred weight
                    inferred_weight = _infer_weight_from_name(font_val)
                    # Remove common suffixes like -Bold/-Regular from family
                    fam = re.sub(r"[- ]?(thin|extralight|light|regular|medium|semibold|bold|extrabold|black)\b", "", font_val, flags=re.I).strip()
                    ttf_path = ensure_google_font_ttf(fam, inferred_weight, fonts_dir)
                    if ttf_path and os.path.exists(ttf_path):
                        FONT = ttf_path
                    else:
                        # fallback to provided string; requires system-installed font
                        FONT = font_val

            # Vertical position handling
            y_val = tpl.get("y", None)
            y_off = tpl.get("y_offset", None)
            if isinstance(y_val, str) and y_val.lower() == "center":
                TEXT_POS_MODE = "center"
            elif isinstance(y_val, (int, float)):
                TEXT_POS_MODE = "absolute"
                TEXT_POS_Y = int(float(y_val))
            # Optional offset from centered baseline
            if isinstance(y_off, (int, float)):
                TEXT_POS_OFFSET = int(float(y_off))
except Exception:
    # Silently ignore issues and keep defaults
    pass

# Hardcoded content: sequence of segments with durations (seconds)
TEXT_BLOCKS = [
    {"text": "5 quick tips to instantly improve your presentations.", "duration": 2.2},
    {"text": "1) Open with a strong hook—state a bold result or question.", "duration": 2.0},
    {"text": "2) Use one key idea per slide. Remove anything that doesn’t support it.", "duration": 2.2},
    {"text": "3) Tell a story—set up, conflict, resolution. Keep momentum.", "duration": 2.0},
    {"text": "4) Use large text and high contrast. Design for the back row.", "duration": 2.0},
    {"text": "5) Rehearse out loud. Time yourself and trim ruthlessly.", "duration": 2.2},
    {"text": "Follow for more concise comms tips!", "duration": 1.8},
]


def typing_clip_by_chars(text: str, duration: float, fontsize: int, font: str, video_size: tuple[int, int], text_width: int):
    """Create a typing animation by revealing characters progressively."""
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
            )
            .set_duration(per_char)
        )
        # Force measure to compute height, then compute vertical position
        _ = txt.get_frame(0)
        if TEXT_POS_MODE == "absolute":
            y = max(0, min(video_size[1] - txt.h, TEXT_POS_Y))
        else:
            y = (video_size[1] - txt.h) / 2 + TEXT_POS_OFFSET
        txt = txt.set_position(("center", y))
        # Wrap into full-frame so position is preserved across concatenation
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
    # total duration from text blocks + pauses
    total_duration = sum(b["duration"] for b in TEXT_BLOCKS) + len(TEXT_BLOCKS) * PAUSE_AFTER

    # background
    try:
        if BACKGROUND_IMAGE.lower().endswith((".gif", ".webp")):
            # Use VideoFileClip for animated backgrounds and loop to full duration
            bg_clip = (
                VideoFileClip(BACKGROUND_IMAGE)
                .without_audio()
                .resize(VIDEO_SIZE)
                .loop(duration=total_duration)
            )
        else:
            bg_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE).set_duration(total_duration)
    except Exception:
        # Fallback to static image behavior if video decoding fails
        bg_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE).set_duration(total_duration)

    # build text layers
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
            # Fallback: static caption if font/rendering fails
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
            # Force render to get accurate height and compute vertical position
            _ = fallback.get_frame(0)
            if TEXT_POS_MODE == "absolute":
                y = max(0, min(VIDEO_SIZE[1] - fallback.h, TEXT_POS_Y))
            else:
                y = (VIDEO_SIZE[1] - fallback.h) / 2 + TEXT_POS_OFFSET
            fallback = fallback.set_start(cursor).set_duration(seg_duration).set_position(("center", y))
            clips.append(fallback)
        finally:
            gc.collect()

        # Add a post-text pause using a transparent static caption (avoids black background)
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

    # Animated vector overlays (non-intrusive corners)
    proj_root = os.path.dirname(HERE)
    vectors = []
    candidates = [
        #os.path.join(proj_root, "assets", "images", "atom.gif"),
        #os.path.join(proj_root, "assets", "images", "bullet_spiral.gif"),
    ]
    available = [p for p in candidates if os.path.exists(p)]

    overlay_clips = []
    for i, gif_path in enumerate(available[:2]):
        try:
            v = VideoFileClip(gif_path).resize(width=180).loop(duration=total_duration)
            # Subtle orbital motion to add life
            def pos_func_factory(i):
                def pos_func(t):
                    # base corner positions with margins
                    margin = 24
                    if i == 0:
                        base = (margin, margin)  # top-left
                    else:
                        base = (VIDEO_SIZE[0] - margin - v.w, VIDEO_SIZE[1] - margin - v.h)  # bottom-right
                    dx = 8 * math.sin(0.8 * t + i)
                    dy = 8 * math.cos(0.6 * t + i)
                    return (base[0] + dx, base[1] + dy)
                return pos_func

            v = v.set_position(pos_func_factory(i)).set_duration(total_duration)
            overlay_clips.append(v)
        except Exception:
            continue

    final = CompositeVideoClip([bg_clip] + overlay_clips + clips, size=VIDEO_SIZE)

    final.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio=False,  # silent shorts by default; swap to audio clip if desired
        threads=1,
        logger=None,
    )

    # cleanup
    final.close()
    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    for v in overlay_clips:
        try:
            v.close()
        except Exception:
            pass
    bg_clip.close()
    gc.collect()

    print(f"✅ Shorts video saved to {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
