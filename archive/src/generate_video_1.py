from moviepy.editor import *
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter, ImageSequence
import numpy as np
import os
from pathlib import Path
from textwrap import wrap
import json
import cairosvg
import pyttsx3
from pydub import AudioSegment
import time

# Paths
svg_path = "../output/final.svg"
converted_image_path = "../output/final.png"
cartoon_path = "../assets/testing/man.gif"
json_path = "../assets/content.json"
audio_folder = "../assets/testing/audio"
bullet_icon_path="../assets/images/bullet_spiral.gif"
font_path = Path("../assets/fonts/Roboto-VariableFont_wdth,wght.ttf")
output_path = "../output/final_video.mp4"

if not os.path.exists(converted_image_path) or os.path.getmtime(svg_path) > os.path.getmtime(converted_image_path):
    cairosvg.svg2png(url=svg_path, write_to=converted_image_path)

# Get actual image dimensions
original_image = PILImage.open(converted_image_path)
canvas_size = original_image.size

def gif_to_transparent_clip(gif_path, duration, resize_height=None, position=("left", "center")):
    gif = PILImage.open(gif_path)
    frames = []
    durations = []
    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        np_frame = np.array(rgba)
        frames.append(np_frame)
        durations.append(frame.info.get("duration", 100))
    fps = 1000 / (sum(durations) / len(durations))
    clip = ImageSequenceClip(frames, fps=fps)
    if resize_height:
        clip = clip.resize(height=resize_height)
    looped = clip.loop(duration=duration)
    return looped.set_position(position)

def blur_image(image_clip, sigma=10):
    frame = image_clip.get_frame(0)
    pil_image = PILImage.fromarray(frame)
    blurred = pil_image.filter(ImageFilter.GaussianBlur(radius=sigma))
    return ImageClip(np.array(blurred)).set_duration(image_clip.duration).set_position("center")


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


def create_typewriter_dialogue_clip(full_text, cartoon_path=None, background_clip=None,
                                    dialogue_duration=2, bullet_icon_path=bullet_icon_path):
    total_chars = len(full_text)
    total_chars = len(full_text)
    # Ensure we don't divide by zero or go negative
    effective_duration = max(0.5, dialogue_duration - 4.0)
    typing_speed = total_chars / effective_duration  # chars per second
    duration = total_chars / typing_speed
    fps = 24

    # Load the bullet icon
    try:
        bullet_icon = PILImage.open(bullet_icon_path).convert("RGBA")
        bullet_icon_size = (32, 32)
        bullet_icon = bullet_icon.resize(bullet_icon_size, PILImage.LANCZOS)
    except:
        bullet_icon = None
        bullet_icon_size = (0, 0)

    # Box metrics
    left_width = int(canvas_size[0] * 0.2)
    padding = int(canvas_size[0] * 0.03)
    box_x0 = left_width + padding
    box_y0 = padding
    box_x1 = canvas_size[0] - padding
    box_y1 = canvas_size[1] - padding
    box_width = box_x1 - box_x0
    box_height = box_y1 - box_y0
    bullet_spacing = 10

    # Determine best font and wrap lines ONCE
    max_font_size = int(canvas_size[1] * 0.07)
    min_font_size = 10
    final_font = None
    final_wrapped_lines = []

    for font_size in range(max_font_size, min_font_size - 1, -2):
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except:
            font = ImageFont.load_default()

        text_area_width = box_width - 2 * padding - bullet_icon_size[0] - 10
        wrapped_lines = pixel_wrap(full_text, font, text_area_width)

        total_height = 0
        for _, line in wrapped_lines:
            line_height = font.getbbox(line)[3] - font.getbbox(line)[1]
            total_height += line_height + bullet_spacing

        if total_height <= box_height - 2 * padding:
            final_font = font
            final_wrapped_lines = wrapped_lines
            break

    if final_font is None:
        final_font = ImageFont.truetype(str(font_path), min_font_size)
        final_wrapped_lines = pixel_wrap(full_text, final_font, text_area_width)

    def make_frame(t):
        chars_to_show = int((t / duration) * total_chars)
        partial_text = full_text[:chars_to_show]
        wrapped_lines = pixel_wrap(partial_text, final_font, text_area_width)

        bg_frame = background_clip.get_frame(t)
        pil_bg = PILImage.fromarray(bg_frame).convert("RGBA")
        draw = ImageDraw.Draw(pil_bg)

        # Draw dialogue box
        radius = 30
        draw.rounded_rectangle(
            [box_x0, box_y0, box_x1, box_y1],
            radius=radius,
            fill=(255, 255, 255, 240),
            outline=(50, 50, 50, 255),
            width=6
        )

        # Draw text
        text_y = box_y0 + padding
        for is_bullet, line in wrapped_lines:
            line_height = final_font.getbbox(line)[3] - final_font.getbbox(line)[1]
            if is_bullet and bullet_icon:
                icon_x = box_x0 + padding
                icon_y = text_y + (line_height - bullet_icon_size[1]) // 2
                pil_bg.paste(bullet_icon, (icon_x, icon_y), bullet_icon)
                text_x = icon_x + bullet_icon_size[0] + 10
            else:
                text_x = box_x0 + padding

            draw.text((text_x, text_y), line, font=final_font, fill="black")
            text_y += line_height + bullet_spacing

        frame = np.array(pil_bg.convert("RGB"))
        return frame[:, :, :3]

    dialogue_clip = VideoClip(make_frame=make_frame, duration=dialogue_duration).set_fps(fps)

    overlays = [dialogue_clip]
    if cartoon_path:
        character = gif_to_transparent_clip(cartoon_path, duration=dialogue_duration, resize_height=300)
        character = character.set_position((int(canvas_size[0] * 0.03), "center"))
        overlays.append(character)

    return CompositeVideoClip(overlays).set_duration(dialogue_duration)


def create_magnifier_zoom(base_clip, start_pos, end_pos, zoom_factor=2.0, size=(150, 150),
                          border_color="white", border_width=4, pulse_duration=3.5, pulse_scale=1.15, fps=24):
    total_duration = base_clip.duration + pulse_duration

    def make_frame(t):
        if t < base_clip.duration:
            interp = t / base_clip.duration
            pos_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * interp)
            pos_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * interp)
            scale = 1.0
        else:
            interp = (t - base_clip.duration) / pulse_duration
            pos_x, pos_y = end_pos
            scale = 1 + 0.05 * np.sin(2 * np.pi * 2 * interp)

        frame = base_clip.get_frame(0)
        crop_size = int(size[0] / zoom_factor), int(size[1] / zoom_factor)
        crop_x0 = max(pos_x - crop_size[0] // 2, 0)
        crop_y0 = max(pos_y - crop_size[1] // 2, 0)
        crop_x1 = min(crop_x0 + crop_size[0], frame.shape[1])
        crop_y1 = min(crop_y0 + crop_size[1], frame.shape[0])
        cropped = frame[crop_y0:crop_y1, crop_x0:crop_x1]

        final_size = (int(size[0] * scale), int(size[1] * scale))
        resized = np.array(PILImage.fromarray(cropped).resize(final_size, resample=PILImage.BICUBIC))

        img = PILImage.new("RGBA", final_size, (0, 0, 0, 0))
        img.paste(PILImage.fromarray(resized), (0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([border_width // 2, border_width // 2, final_size[0] - border_width // 2, final_size[1] - border_width // 2], outline=border_color, width=border_width)

        shadow = PILImage.new("RGBA", (final_size[0]+10, final_size[1]+10), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((5, 5, final_size[0]+5, final_size[1]+5), fill=(0, 0, 0, 80))
        shadow.paste(img, (5, 5), img)

        return np.array(shadow.convert("RGB"))

    def make_mask(t):
        if t < base_clip.duration:
            scale = 1.0
        else:
            interp = (t - base_clip.duration) / pulse_duration
            scale = 1 + 0.05 * np.sin(2 * np.pi * 2 * interp)
        final_size = (int((size[0]+10) * scale), int((size[1]+10) * scale))
        mask_img = PILImage.new("L", final_size, 0)
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse((0, 0, final_size[0], final_size[1]), fill=255)
        return np.array(mask_img).astype(np.float32) / 255.0

    clip = VideoClip(make_frame=make_frame, duration=total_duration).set_fps(fps)
    mask = VideoClip(make_frame=make_mask, ismask=True, duration=total_duration).set_fps(fps)
    clip = clip.set_mask(mask)

    return clip.set_position(lambda t: (
        int(start_pos[0] + (end_pos[0] - start_pos[0]) * min(t / base_clip.duration, 1.0)),
        int(start_pos[1] + (end_pos[1] - start_pos[1]) * min(t / base_clip.duration, 1.0))
    ))

import wave

def is_valid_wav(path):
    try:
        with wave.open(path, 'rb') as wf:
            duration = wf.getnframes() / float(wf.getframerate())
            return duration > 0
    except:
        return False

# Generate video parts
with open(json_path, "r", encoding="utf-8") as f:
    content_blocks = json.load(f)

# Init TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 180)
def generate_tts(text, out_path):
    temp_path = out_path.replace(".wav", "_tmp.wav")
    
    # Step 1: Generate speech to temporary file
    tts_engine.save_to_file(text, temp_path)
    tts_engine.runAndWait()

    # Step 2: Wait for file to finish writing (up to 5s)
    timeout = 5
    while not os.path.exists(temp_path) and timeout > 0:
        time.sleep(0.1)
        timeout -= 0.1

    if not os.path.exists(temp_path):
        raise Exception(f"TTS temp file was not created: {temp_path}")

    # Step 3: Convert to proper PCM WAV format
    try:
        sound = AudioSegment.from_file(temp_path)
        sound.export(out_path, format="wav")
        os.remove(temp_path)
        print(f"✅ TTS saved: {out_path}")
    except Exception as e:
        print(f"❌ Error converting TTS for {out_path}: {e}")

clips = []
for block_index, block in enumerate(content_blocks):
    title = block.get("title", "")
    for point_index, point in enumerate(block.get("points", [])):
        base_name = f"block{block_index+1}_point{point_index+1}"
        audio_path = os.path.join(audio_folder, base_name + ".wav")

        # If audio missing, generate via TTS
        if not os.path.exists(audio_path):
            print(f"Generating TTS for: {base_name}, {point}")
            generate_tts(point, audio_path)

        # Wait up to 2s for valid WAV
        for _ in range(20):
            if is_valid_wav(audio_path):
                break
            time.sleep(0.1)
        else:
            raise Exception(f"Invalid or incomplete audio file: {audio_path}")

        audio_clip = AudioFileClip(audio_path)
        dialogue_dur = audio_clip.duration
        magnifier_dur = min(3.0, dialogue_dur * 0.5)
        total_dur = dialogue_dur + magnifier_dur

        infographic_clip = ImageClip(converted_image_path).set_duration(total_dur).crossfadein(0.6)
        end_pos = (300 + block_index * 150, 300 + point_index * 120)
        start_pos = (-200, 100)

        magnifier = create_magnifier_zoom(
            base_clip=infographic_clip.set_duration(magnifier_dur),
            start_pos=start_pos,
            end_pos=end_pos,
            zoom_factor=2.0
        )

        blurred = blur_image(infographic_clip).subclip(0, dialogue_dur)
        dialogue = create_typewriter_dialogue_clip(
            point,
            cartoon_path,
            background_clip=blurred,
            dialogue_duration=dialogue_dur
        ).crossfadein(0.6)

        overlay = CompositeVideoClip([blurred, dialogue])
        fade_duration = 0.6
        scene = CompositeVideoClip([
            infographic_clip,
            magnifier.set_start(0).crossfadein(0.6),
            overlay.set_start(magnifier_dur)
        ], size=canvas_size).set_duration(total_dur).fadeout(fade_duration).set_audio(audio_clip)

        clips.append(scene)

if not clips:
    raise ValueError("No video clips generated. Check your JSON structure and audio paths.")

final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", audio=True)