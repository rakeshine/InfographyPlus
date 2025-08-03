from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os

# Paths
image_path = "assets/infographic.png"
text_folder = "assets/texts"
output_path = "output/final_video.mp4"

# Settings
canvas_size = (1280, 720)
magnifier_duration = 3.0
dialogue_duration = 2.0
point_duration = magnifier_duration + dialogue_duration

# Load infographic
infographic = ImageClip(image_path).resize(height=canvas_size[1]).set_duration(point_duration * 4)

# Create blurred background
def blur_image(image_clip, sigma=10):
    frame = image_clip.get_frame(0)
    pil_image = Image.fromarray(frame)
    blurred = pil_image.filter(ImageFilter.GaussianBlur(radius=sigma))
    return ImageClip(np.array(blurred)).set_duration(image_clip.duration).set_position("center")

# Create magnifier zoom effect
def create_magnifier_zoom(base_clip, start_pos, end_pos, zoom_factor=2.0, size=(150, 150)):
    def make_frame(t):
        # Calculate position based on t
        pos_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * (t / magnifier_duration))
        pos_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * (t / magnifier_duration))

        frame = base_clip.get_frame(0)  # Use base image clip, not the magnifier itself

        # Crop region
        crop_size = int(size[0] / zoom_factor), int(size[1] / zoom_factor)
        crop_x0 = max(pos_x - crop_size[0] // 2, 0)
        crop_y0 = max(pos_y - crop_size[0] // 2, 0)
        crop_x1 = min(crop_x0 + crop_size[0], frame.shape[1])
        crop_y1 = min(crop_y0 + crop_size[1], frame.shape[0])

        cropped = frame[crop_y0:crop_y1, crop_x0:crop_x1]
        resized = np.array(Image.fromarray(cropped).resize(size, resample=Image.BICUBIC))

        # Ensure RGB only
        if resized.shape[2] == 4:
            resized = resized[:, :, :3]

        # Circular alpha mask
        mask_img = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        mask_np = np.array(mask_img).astype(np.float32) / 255.0

        return resized, mask_np

    def make_image(t):
        image, _ = make_frame(t)
        return image

    def make_mask(t):
        _, mask = make_frame(t)
        return mask

    image_clip = VideoClip(make_frame=make_image, duration=magnifier_duration)
    mask_clip = VideoClip(make_frame=make_mask, ismask=True, duration=magnifier_duration)

    image_clip = image_clip.set_mask(mask_clip)

    # Positioning animation
    return image_clip.set_position(lambda t: (
        int(start_pos[0] + (end_pos[0] - start_pos[0]) * (t / magnifier_duration)),
        int(start_pos[1] + (end_pos[1] - start_pos[1]) * (t / magnifier_duration))
    ))


# Dialogue box with 30% left for cartoon
def create_dialogue_box(text, cartoon_path=None):
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    character_width = int(canvas_size[0] * 0.3)
    padding = int(canvas_size[0] * 0.05)

    box_x0, box_y0 = padding, padding
    box_x1, box_y1 = canvas_size[0] - padding, canvas_size[1] - padding
    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=30, fill=(255, 255, 255, 240))

    # Text area
    text_x = character_width + 2 * padding
    text_y = box_y0 + padding

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((text_x, text_y), text, fill="black", font=font)

    base_clip = ImageClip(np.array(img)).set_duration(dialogue_duration)

    if cartoon_path:
        character = ImageClip(cartoon_path).set_duration(dialogue_duration).resize(height=300).set_position((padding, "center"))
        return CompositeVideoClip([base_clip, character])
    return base_clip

# Read input texts
text_files = sorted([f for f in os.listdir(text_folder) if f.endswith(".txt")])
texts = [open(os.path.join(text_folder, f)).read().strip() for f in text_files]

# Generate video clips
clips = []

for i, text in enumerate(texts):
    start_time = i * point_duration

    # Placeholder target coordinates on infographic (adjust or detect later)
    end_pos = (300 + i * 200, 300)
    start_pos = (-200, 100)

    # Magnifier zoom effect
    magnifier = create_magnifier_zoom(
        base_clip=infographic,  # pass base static image clip here
        start_pos=(100, 100),
        end_pos=(300, 300),
        zoom_factor=2.0)


    # Blurred background and dialogue
    blurred = blur_image(infographic).subclip(start_time, start_time + dialogue_duration)
    dialogue = create_dialogue_box(text, cartoon_path=None)

    overlay = CompositeVideoClip([blurred, dialogue.set_start(0)]).set_duration(dialogue_duration)

    full_scene = CompositeVideoClip([
        infographic.set_start(0),
        magnifier.set_start(0),
        overlay.set_start(magnifier_duration)
    ], size=canvas_size).set_duration(point_duration)

    clips.append(full_scene)

# Final video
final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile(output_path, fps=24)
