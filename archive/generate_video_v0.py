from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os

# Settings
image_path = "assets/infographic.jpg"
text_folder = "assets/texts"
output_path = "output/final_video.mp4"

canvas_size = (1280, 720)
magnifier_duration = 1.0
dialogue_duration = 2.0
point_duration = 5.0

# Load infographic image
infographic = ImageClip(image_path).set_duration(point_duration * 4).resize(height=canvas_size[1])

# Helper: Create a blurred background
def blur_image(image_clip, sigma=10):
    frame = image_clip.get_frame(0)
    pil_image = Image.fromarray(frame)
    blurred = pil_image.filter(ImageFilter.GaussianBlur(radius=sigma))
    return ImageClip(np.array(blurred)).set_duration(image_clip.duration).set_position("center")


# Helper: Create a dialogue overlay
def create_dialogue_box(text, cartoon_path=None):
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    padding = 40
    text_area = (canvas_size[0] * 0.7, canvas_size[1] - 2 * padding)
    box_coords = [padding, padding, canvas_size[0] - padding, canvas_size[1] - padding]
    draw.rounded_rectangle(box_coords, radius=30, fill=(255, 255, 255, 230))

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((canvas_size[0] * 0.3 + padding, canvas_size[1] * 0.3), text, fill="black", font=font)

    background = ImageClip(np.array(img)).set_duration(dialogue_duration)
    if cartoon_path:
        character = ImageClip(cartoon_path).set_duration(dialogue_duration).resize(height=300).set_position((padding, "center"))
        return CompositeVideoClip([background, character])
    return background

# Read texts
text_files = sorted([f for f in os.listdir(text_folder) if f.endswith(".txt")])
texts = [open(os.path.join(text_folder, f)).read().strip() for f in text_files]

# Build video
clips = []
for i, text in enumerate(texts):
    start_time = i * point_duration

    # Magnifier (placeholder as a red circle)
    magnifier = ColorClip((100, 100), color=(255, 0, 0)).set_opacity(0.5).set_duration(magnifier_duration)
    magnifier = magnifier.set_position((300 + i * 200, 200))  # placeholder positions

    # Dialogue box
    dialogue = create_dialogue_box(text, cartoon_path=None)

    # Blurred background
    blurred = blur_image(infographic).subclip(start_time, start_time + dialogue_duration)

    overlay = CompositeVideoClip([blurred, dialogue.set_start(0)]).set_duration(dialogue_duration)

    full = CompositeVideoClip([infographic, magnifier.set_start(0), overlay.set_start(magnifier_duration)]).set_duration(point_duration)
    clips.append(full)

final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile(output_path, fps=24)
