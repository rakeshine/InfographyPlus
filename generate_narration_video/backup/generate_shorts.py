import os
import gc
import math
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
BACKGROUND_IMAGE = os.path.join(HERE, "bg4.gif")  # fallback to background.jpeg if .jpg not present
if not os.path.exists(BACKGROUND_IMAGE):
    alt = os.path.join(HERE, "background.jpeg")
    if os.path.exists(alt):
        BACKGROUND_IMAGE = alt

OUTPUT_VIDEO = os.path.join(HERE, "shorts.mp4")

# Video/Text config for Shorts
VIDEO_SIZE = (1080, 1920)  # 9:16
# Prefer a bold, highly legible system font on macOS. Adjust if needed.
FONT = "Helvetica-Bold"
FONT_SIZE = 78                       # larger for vertical layout
TEXT_WIDTH = int(VIDEO_SIZE[0] * 0.85)  # wrap width ~85% of screen width
TEXT_AREA_HEIGHT = int(VIDEO_SIZE[1] * 0.44)  # fixed text box height to avoid vertical jumps
# Position the text box slightly above the true center (reels-style composition)
TEXT_Y = "center"
FPS = 30

# Styling for reels
TEXT_COLOR = "#FFEE58"      # bright lemon
STROKE_COLOR = "#0A0A0A"    # near-black outline
STROKE_WIDTH = 3

# Pause after each text block (seconds)
PAUSE_AFTER = 1.8

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
        # Force measure to compute height, then center vertically
        _ = txt.get_frame(0)
        center_y = (video_size[1] - txt.h) / 2
        txt = txt.set_position(("center", center_y))
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
            # Force render to get accurate height and center vertically
            _ = fallback.get_frame(0)
            center_y = (VIDEO_SIZE[1] - fallback.h) / 2
            fallback = fallback.set_start(cursor).set_duration(seg_duration).set_position(("center", center_y))
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
        pause_center_y = (VIDEO_SIZE[1] - pause_clip.h) / 2
        pause_clip = pause_clip.set_start(cursor + seg_duration).set_duration(PAUSE_AFTER).set_position(("center", pause_center_y))
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
