from moviepy.editor import ImageSequenceClip
from PIL import Image as PILImage, ImageSequence
import numpy as np

def gif_to_transparent_clip(gif_path, duration, resize_height=None, position=("left", "center")):
    gif = PILImage.open(gif_path)
    frames = []
    durations = []
    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        w, h = rgba.size
        cropped = rgba.crop((50, 0, w - 20, h))  # Manual crop

        np_frame = np.array(cropped)

        frames.append(np_frame)
        durations.append(frame.info.get("duration", 100))
    fps = 1000 / (sum(durations) / len(durations))
    clip = ImageSequenceClip(frames, fps=fps)
    if resize_height:
        clip = clip.resize(height=resize_height)
    looped = clip.loop(duration=duration)
    return looped.set_position(position)


def pixel_wrap(text, font, max_width):
    lines = []
    for para in text.splitlines():
        words = para.strip().split()
        if not words:
            continue
        line = ""
        first_line = True
        for word in words:
            test_line = f"{line} {word}".strip()
            if font.getlength(test_line) <= max_width:
                line = test_line
            else:
                if line:
                    lines.append((first_line, line))  # Bullet only first visual line
                    first_line = False
                line = word
        if line:
            lines.append((first_line, line))  # Bullet if it's the first line
    return lines