import os, json
import cairosvg
from moviepy.editor import *
from pathlib import Path
from config import *
from tts_utils import generate_tts
from video.effects import blur_image
from video.dialogue import create_typewriter_dialogue_clip
from video.magnifier import create_magnifier_zoom
from video.svg_utils import process_svg
from PIL import Image as PILImage
import time

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
    audio_path = os.path.join(audio_folder, base_name + ".wav")

    if not os.path.exists(audio_path):
        generate_tts(dialogue_text, audio_path)

    audio_clip = AudioFileClip(audio_path)
    dialogue_dur = audio_clip.duration
    magnifier_dur = min(3.0, dialogue_dur * 0.4)
    total_dur = dialogue_dur + magnifier_dur

    infographic_clip = ImageClip(converted_image_path).set_duration(total_dur).crossfadein(0.6)
    
    # Fixed or varied magnifier position per block
    end_pos = (round(position.get("x", 0)), round(position.get("y", 0)))
    start_pos = (-200, 100)

    magnifier_start_time = 4.0
    magnifier = create_magnifier_zoom(
        base_clip=infographic_clip.set_duration(magnifier_dur),
        start_pos=start_pos,
        end_pos=end_pos,
        zoom_factor=2.0
    ).set_start(magnifier_start_time).crossfadein(0.6)

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
        magnifier.set_start(0).crossfadein(0.6),
        overlay.set_start(magnifier_dur)
    ], size=canvas_size).set_duration(total_dur).fadeout(0.6).set_audio(audio_clip)

    clips.append(scene)

print('Start Concatenating')
final_video = concatenate_videoclips(clips)
final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", audio=True, threads=4)