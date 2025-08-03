from moviepy.editor import *
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
from PIL import ImageSequence
import numpy as np
import os

# Paths
image_path = "assets/infographic.png"
cartoon_path = "assets/man.gif"
text_folder = "assets/texts"
output_path = "output/final_video.mp4"

# Get actual image dimensions
original_image = PILImage.open(image_path)
canvas_size = original_image.size  # (width, height)
magnifier_duration = 3.0
dialogue_duration = 2.0
point_duration = magnifier_duration + dialogue_duration

# Load infographic without resizing
infographic = ImageClip(image_path).set_duration(point_duration * 4)

def gif_to_transparent_clip(gif_path, duration, resize_height=None, position=("left", "center")):
    gif = PILImage.open(gif_path)
    frames = []

    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        np_frame = np.array(rgba)
        frames.append(np_frame)

    clip = ImageSequenceClip(frames, fps=len(frames) / duration)

    if resize_height:
        clip = clip.resize(height=resize_height)

    return clip.set_duration(duration).set_position(position)


# Blurred background generator
def blur_image(image_clip, sigma=10):
    frame = image_clip.get_frame(0)
    pil_image = PILImage.fromarray(frame)
    blurred = pil_image.filter(ImageFilter.GaussianBlur(radius=sigma))
    return ImageClip(np.array(blurred)).set_duration(image_clip.duration).set_position("center")

# Magnifier effect
def create_magnifier_zoom(base_clip, start_pos, end_pos, zoom_factor=2.0, size=(150, 150)):
    def make_frame(t):
        pos_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * (t / magnifier_duration))
        pos_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * (t / magnifier_duration))

        frame = base_clip.get_frame(0)

        crop_size = int(size[0] / zoom_factor), int(size[1] / zoom_factor)
        crop_x0 = max(pos_x - crop_size[0] // 2, 0)
        crop_y0 = max(pos_y - crop_size[1] // 2, 0)
        crop_x1 = min(crop_x0 + crop_size[0], frame.shape[1])
        crop_y1 = min(crop_y0 + crop_size[1], frame.shape[0])

        cropped = frame[crop_y0:crop_y1, crop_x0:crop_x1]
        resized = np.array(PILImage.fromarray(cropped).resize(size, resample=PILImage.BICUBIC))

        if resized.shape[2] == 4:
            resized = resized[:, :, :3]

        mask_img = PILImage.new("L", size, 0)
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

    return image_clip.set_position(lambda t: (
        int(start_pos[0] + (end_pos[0] - start_pos[0]) * (t / magnifier_duration)),
        int(start_pos[1] + (end_pos[1] - start_pos[1]) * (t / magnifier_duration))
    ))

# Dialogue overlay
def create_dialogue_box(text, cartoon_path=None):
    W, H = canvas_size
    dialogue_box_width = int(W * 0.65)  # slightly less than 70% to leave margin
    dialogue_box_height = int(H * 0.6)
    padding = int(W * 0.03)

    # Create transparent canvas
    img = PILImage.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw white rounded dialogue box on right side
    box_x0 = int(W * 0.32)
    box_y0 = int((H - dialogue_box_height) / 2)
    box_x1 = box_x0 + dialogue_box_width
    box_y1 = box_y0 + dialogue_box_height
    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=40, fill=(255, 255, 255, 240))

    # Load font
    try:
        font = ImageFont.truetype("arial.ttf", int(H * 0.04))
    except:
        font = ImageFont.load_default()

    # Word wrap text
    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.getbbox(test_line)[2] > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
        return lines

    lines = wrap_text(text, font, dialogue_box_width - 2 * padding)
    text_y = box_y0 + padding

    for line in lines:
        draw.text((box_x0 + padding, text_y), line, font=font, fill="black")
        text_y += font.getbbox(line)[3] + 10

    # Convert to clip
    base_clip = ImageClip(np.array(img)).set_duration(dialogue_duration)

    # Add character image (optional)
    if cartoon_path and cartoon_path.endswith(".gif"):
        character = gif_to_transparent_clip(cartoon_path, duration=dialogue_duration, resize_height=300)
    else:
        character = ImageClip(cartoon_path).set_duration(dialogue_duration).resize(height=300).set_position((padding, "center"))

    if cartoon_path:
        character = character.set_position((int(W * 0.03), "center"))
        return CompositeVideoClip([base_clip, character])
    return base_clip


# Read texts
text_files = sorted([f for f in os.listdir(text_folder) if f.endswith(".txt")])
texts = [open(os.path.join(text_folder, f)).read().strip() for f in text_files]

# Generate scenes
clips = []

for i, text in enumerate(texts):
    start_time = i * point_duration

    end_pos = (300 + i * 200, 300)
    start_pos = (-200, 100)

    magnifier = create_magnifier_zoom(
        base_clip=infographic,
        start_pos=start_pos,
        end_pos=end_pos,
        zoom_factor=2.0
    )

    blurred = blur_image(infographic).subclip(start_time, start_time + dialogue_duration)
    dialogue = create_dialogue_box(text, cartoon_path)
    overlay = CompositeVideoClip([blurred, dialogue.set_start(0)]).set_duration(dialogue_duration)

    full_scene = CompositeVideoClip([
        infographic.set_start(0),
        magnifier.set_start(0),
        overlay.set_start(magnifier_duration)
    ], size=canvas_size).set_duration(point_duration)

    clips.append(full_scene)

# Final output
final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile(output_path, fps=24)
