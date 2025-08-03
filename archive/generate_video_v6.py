from moviepy.editor import *
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter, ImageSequence
import numpy as np
import os

# Paths
image_path = "assets/infographic.png"
cartoon_path = "assets/man.gif"
text_folder = "assets/texts"
audio_folder = "assets/audio"
output_path = "output/final_video.mp4"

# Get actual image dimensions
original_image = PILImage.open(image_path)
canvas_size = original_image.size  # (width, height)

def gif_to_transparent_clip(gif_path, duration, resize_height=None, position=("left", "center")):
    gif = PILImage.open(gif_path)
    frames = []
    durations = []

    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        np_frame = np.array(rgba)
        frames.append(np_frame)
        durations.append(frame.info.get("duration", 100))
    
    avg_duration_ms = sum(durations) / len(durations)
    fps = 1000 / avg_duration_ms  # convert ms to fps
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

def create_magnifier_zoom(base_clip, start_pos, end_pos, zoom_factor=2.0, size=(150, 150), border_color="white", border_width=4):
    def make_frame(t):
        pos_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * (t / base_clip.duration))
        pos_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * (t / base_clip.duration))
        frame = base_clip.get_frame(0)
        crop_size = int(size[0] / zoom_factor), int(size[1] / zoom_factor)
        crop_x0 = max(pos_x - crop_size[0] // 2, 0)
        crop_y0 = max(pos_y - crop_size[1] // 2, 0)
        crop_x1 = min(crop_x0 + crop_size[0], frame.shape[1])
        crop_y1 = min(crop_y0 + crop_size[1], frame.shape[0])
        cropped = frame[crop_y0:crop_y1, crop_x0:crop_x1]
        resized = np.array(PILImage.fromarray(cropped).resize(size, resample=PILImage.BICUBIC))
        img = PILImage.new("RGBA", size, (0, 0, 0, 0))
        img.paste(PILImage.fromarray(resized), (0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([
            border_width // 2, border_width // 2,
            size[0] - border_width // 2, size[1] - border_width // 2
        ], outline=border_color, width=border_width)
        shadow = PILImage.new("RGBA", (size[0]+10, size[1]+10), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((5, 5, size[0]+5, size[1]+5), fill=(0, 0, 0, 80))
        shadow.paste(img, (5, 5), img)
        return np.array(shadow.convert("RGB"))

    def make_mask(t):
        mask_img = PILImage.new("L", (size[0]+10, size[1]+10), 0)
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse((5, 5, size[0]+5, size[1]+5), fill=255)
        return np.array(mask_img).astype(np.float32) / 255.0

    image_clip = VideoClip(make_frame=make_frame, duration=base_clip.duration)
    mask_clip = VideoClip(make_frame=make_mask, ismask=True, duration=base_clip.duration)
    image_clip = image_clip.set_mask(mask_clip)

    return image_clip.set_position(lambda t: (
        int(start_pos[0] + (end_pos[0] - start_pos[0]) * (t / base_clip.duration)),
        int(start_pos[1] + (end_pos[1] - start_pos[1]) * (t / base_clip.duration))
    ))

def create_dialogue_box(text, cartoon_path=None, duration=2.0):
    img = PILImage.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    left_width = int(canvas_size[0] * 0.2)
    padding = int(canvas_size[0] * 0.03)
    box_x0 = left_width + padding
    box_y0 = padding
    box_x1 = canvas_size[0] - padding
    box_y1 = canvas_size[1] - padding
    radius = 30

    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=radius, fill=(255, 255, 255, 240))

    text_x = box_x0 + padding
    text_y = box_y0 + padding

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((text_x, text_y), text, fill="black", font=font)
    base_clip = ImageClip(np.array(img)).set_duration(duration)

    if cartoon_path:
        if cartoon_path.endswith(".gif"):
            character = gif_to_transparent_clip(cartoon_path, duration=duration, resize_height=300)
        else:
            character = ImageClip(cartoon_path).resize(height=300)
        character = character.set_position((padding, "center"))
        return CompositeVideoClip([base_clip.set_duration(duration), character])
    return base_clip

# Generate video parts
text_files = sorted([f for f in os.listdir(text_folder) if f.endswith(".txt")])
clips = []

for i, text_file in enumerate(text_files):
    text_path = os.path.join(text_folder, text_file)
    base_name = os.path.splitext(text_file)[0]  # e.g., point1
    audio_path = os.path.join(audio_folder, base_name + ".wav")

    if not os.path.exists(audio_path):
        print(f"Skipping {text_file} — matching audio file not found: {audio_path}")
        continue

    with open(text_path) as f:
        text = f.read().strip()

    audio_clip = AudioFileClip(audio_path)
    dialogue_dur = audio_clip.duration
    magnifier_dur = min(3.0, dialogue_dur * 0.5)
    total_dur = dialogue_dur + magnifier_dur

    infographic_clip = ImageClip(image_path).set_duration(total_dur)
    end_pos = (300 + i * 200, 300)
    start_pos = (-200, 100)

    magnifier = create_magnifier_zoom(
        base_clip=infographic_clip.set_duration(magnifier_dur),
        start_pos=start_pos,
        end_pos=end_pos,
        zoom_factor=2.0
    )

    blurred = blur_image(infographic_clip).subclip(0, dialogue_dur)
    dialogue = create_dialogue_box(text, cartoon_path, duration=dialogue_dur)
    overlay = CompositeVideoClip([blurred, dialogue])

    scene = CompositeVideoClip([
        infographic_clip,
        magnifier.set_start(0),
        overlay.set_start(magnifier_dur)
    ], size=canvas_size).set_duration(total_dur).set_audio(audio_clip)

    clips.append(scene)

if not clips:
    raise ValueError("No video clips generated. Check your assets/texts and assets/audio folders.")

final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", audio=True)
