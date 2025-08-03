"""
Dialogue Clip Generator Module

This module contains functionality for creating animated dialogue clips
with typewriter effects for video generation.
"""

from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy.editor import VideoClip, CompositeVideoClip
from pathlib import Path
from video.gif_utils import gif_to_transparent_clip
from video.gif_utils import pixel_wrap
from config import font_path, bullet_icon_path


def create_typewriter_dialogue_clip(full_text, cartoon_path=None, background_clip=None,
                                    dialogue_duration=2, bullet_icon_path=bullet_icon_path, canvas_size=any):
    """
    Create a dialogue clip with a typewriter animation effect.
    
    This function generates a video clip that displays text with a typewriter
    animation, where characters appear one by one. It also supports displaying
    bullet points with icons and an optional cartoon character.
    
    Args:
        full_text (str): The complete text to display, with the first line as heading
                        and subsequent lines as bullet points
        cartoon_path (str, optional): Path to a GIF file for cartoon character
        background_clip (VideoClip, optional): Background clip to use
        dialogue_duration (float): Duration of the dialogue clip in seconds
        bullet_icon_path (str): Path to the bullet point icon image
        canvas_size (tuple): Size of the video canvas as (width, height)
        
    Returns:
        CompositeVideoClip: A MoviePy CompositeVideoClip with the dialogue animation
    """
    
    # Parse text into heading and bullet points
    heading, *points = full_text.strip().split("\n")
    total_chars = len(full_text.replace("\n", " "))  # for timing calc
    effective_duration = max(0.5, dialogue_duration - 4.0)
    typing_speed = total_chars / effective_duration
    duration = total_chars / typing_speed
    fps = 24

    # Load and prepare bullet icon
    bullet_icon = PILImage.open(bullet_icon_path).convert("RGBA")
    bullet_icon_size = (32, 32)
    bullet_icon = bullet_icon.resize(bullet_icon_size, PILImage.LANCZOS)

    # Calculate layout dimensions
    left_width = int(canvas_size[0] * 0.2)
    padding = int(canvas_size[0] * 0.06)
    
    desired_box_height = int(canvas_size[1] * 0.8)
    box_width = canvas_size[0] - left_width - 2 * padding
    box_x0 = left_width + padding
    box_x1 = box_x0 + box_width

    # Vertically center the box
    box_y0 = (canvas_size[1] - desired_box_height) // 2
    box_y1 = box_y0 + desired_box_height

    # Set font sizes
    heading_font_size = int(desired_box_height * 0.05)
    body_font_size = int(desired_box_height * 0.035)
    line_spacing = int(body_font_size * 1.6)

    heading_font = ImageFont.truetype(str(font_path), heading_font_size)
    body_font = ImageFont.truetype(str(font_path), body_font_size)

    def make_frame(t):
        """Generate a single frame of the typewriter animation."""
        chars_to_show = int((t / duration) * total_chars)
        shown_chars = 0

        # Get background frame and apply blur to dialogue area
        bg_frame = background_clip.get_frame(t)
        pil_bg = PILImage.fromarray(bg_frame).convert("RGBA")
        blur_region = pil_bg.crop((box_x0, box_y0, box_x1, box_y1)).filter(ImageFilter.GaussianBlur(50))
        pil_bg.paste(blur_region, (box_x0, box_y0))

        # Draw dialogue box
        draw = ImageDraw.Draw(pil_bg)
        draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=40, outline=(30, 30, 30, 255), width=5)

        y = box_y0 + padding

        # === Render Heading ===
        heading_wrapped = pixel_wrap(heading, heading_font, box_width - 2 * padding)
        for _, hline in heading_wrapped:
            if shown_chars >= chars_to_show:
                break
            chars_in_line = len(hline)
            text_to_draw = hline[:max(0, chars_to_show - shown_chars)]
            w = heading_font.getlength(text_to_draw)
            x = box_x0 + (box_width - w) / 2
            draw.text((x, y), text_to_draw, font=heading_font, fill="black")
            y += heading_font_size + 8
            shown_chars += chars_in_line + 1  # line break

        y += line_spacing // 2  # spacer

        # === Render Bullet Points ===
        for point in points:
            clean_point = point.lstrip("•- ").strip()
            wrapped = pixel_wrap(clean_point, body_font, box_width - 2 * padding - bullet_icon_size[0] - 10)
            for i, (_, line) in enumerate(wrapped):
                if shown_chars >= chars_to_show:
                    break
                chars_in_line = len(line)
                text_to_draw = line[:max(0, chars_to_show - shown_chars)]

                if i == 0:
                    # Add bullet icon only on first line
                    icon_x = box_x0 + padding
                    icon_y = y + (body_font_size - bullet_icon_size[1]) // 2
                    pil_bg.paste(bullet_icon, (icon_x, icon_y), bullet_icon)
                    text_x = icon_x + bullet_icon_size[0] + 10
                else:
                    text_x = box_x0 + padding + bullet_icon_size[0] + 10

                draw.text((text_x, y), text_to_draw, font=body_font, fill="black")
                y += line_spacing
                shown_chars += chars_in_line + 1

        return np.array(pil_bg.convert("RGB"))[:, :, :3]

    # Create the dialogue clip
    dialogue_clip = VideoClip(make_frame=make_frame, duration=dialogue_duration).set_fps(fps)

    # Add cartoon character if provided
    overlays = [dialogue_clip]
    if cartoon_path:
        character = gif_to_transparent_clip(cartoon_path, duration=dialogue_duration, resize_height=300)
        character = character.set_position((int(canvas_size[0] * 0.03), "center"))
        overlays.append(character)

    return CompositeVideoClip(overlays).set_duration(dialogue_duration)

