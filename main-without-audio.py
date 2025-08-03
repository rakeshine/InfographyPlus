import os, json
import cairosvg
from moviepy.editor import *
from pathlib import Path
from config import *
from tts_utils import generate_tts
from video.effects import blur_image
from video.dialogue import create_typewriter_dialogue_clip
from video.svg_utils import process_svg
from PIL import Image as PILImage, ImageDraw
import time
import numpy as np

def create_click_effect_clip(x, y, w, h, duration, canvas_size, fps=24):
    """ Creates an animated rectangular highlight ripple effect """
    base_img = PILImage.open(converted_image_path).convert("RGBA")

    def make_frame(t):
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame, 'RGBA')
        
        # Animation: rectangle border flashes expanding and fading
        max_border_width = 10
        # Oscillate width and alpha to create pulse effect
        pulse = (np.sin(2 * np.pi * t * 2) + 1) / 2  # oscillates 0 to 1 twice per second
        border_width = int(max_border_width * pulse)
        alpha = int(150 + 105 * pulse)  # oscillates between 150 and 255

        color = (0, 120, 255, alpha)  # Blue rectangle with varying opacity

        # Draw expanding rectangle border from (x,y,w,h) outward by border_width/2 each side
        rect_coords = [
            x - border_width // 2,
            y - border_width // 2,
            x + w + border_width // 2,
            y + h + border_width // 2
        ]

        # Draw the border (rectangle outline)
        draw.rounded_rectangle(rect_coords, outline=color, width=max(border_width, 1), radius=50)

        return np.array(frame.convert("RGB"))  # Convert RGBA to RGB for MoviePy compositing

    click_effect_clip = VideoClip(make_frame, duration=duration)
    click_effect_clip = click_effect_clip.set_fps(fps).resize(newsize=canvas_size)
    return click_effect_clip


# convert SVG to PNG if modified
process_svg(svg_path, json_path, output_svg_path)
cairosvg.svg2png(url=output_svg_path, write_to=converted_image_path)

# get image size
canvas_size = PILImage.open(converted_image_path).size

with open("/Users/rakeshvijayakumar/Documents/Business/SmartSolutions/InfogrpahyPlus/content.json", "r", encoding="utf-8") as f:
    content_blocks = json.load(f)

clips = []
for block_index, block in enumerate(content_blocks):
    title = block.get("title", "")
    position = block.get("position", "")
    points = block.get("points", [])
    if not points:
        continue

    # Combine title + bullet points
    dialogue_text = f"{title}\n" + "\n".join([f"• {point}" for point in points])
    base_name = f"block{block_index+1}"

    dialogue_dur = 4
    magnifier_dur = min(3.0, dialogue_dur * 0.4)
    total_dur = dialogue_dur + magnifier_dur

    infographic_clip = ImageClip(converted_image_path).set_duration(total_dur).crossfadein(0.6)
    clips.append(CompositeVideoClip([infographic_clip], size=canvas_size).set_duration(3))
    blurred = blur_image(infographic_clip).subclip(0, dialogue_dur)

    dialogue = create_typewriter_dialogue_clip(
        dialogue_text,
        cartoon_path,
        background_clip=blurred,
        dialogue_duration=dialogue_dur,
        canvas_size=canvas_size
    ).crossfadein(0.6)

    overlay = CompositeVideoClip([blurred, dialogue])

    scene = CompositeVideoClip([
        infographic_clip,
        create_click_effect_clip(
            round(position.get("x", 0)), 
            round(position.get("y", 0)) - 25, 
            round(position.get("width", 0)),
            round(position.get("height", 0)) + 25,
            duration=2, canvas_size=canvas_size),
        overlay.set_start(magnifier_dur)
    ], size=canvas_size).set_duration(total_dur)

    clips.append(scene)

print('Start Concatenating')
final_video = concatenate_videoclips(clips)
final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", audio=True, threads=4)