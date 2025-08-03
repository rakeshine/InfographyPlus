"""
GIF Utilities Module

This module contains functionality for processing GIF files and text wrapping
for video generation.
"""

from moviepy.editor import ImageSequenceClip
from PIL import Image as PILImage, ImageSequence
import numpy as np


def gif_to_transparent_clip(gif_path, duration, resize_height=None, position=("left", "center")):
    """
    Convert a GIF file to a transparent MoviePy clip.
    
    This function processes a GIF file, converts frames to RGBA format,
    crops the frames, and creates a looped video clip with specified duration.
    
    Args:
        gif_path (str): Path to the GIF file
        duration (float): Duration of the output clip in seconds
        resize_height (int, optional): Height to resize the clip to
        position (tuple): Position of the clip in the final video
        
    Returns:
        ImageSequenceClip: Processed MoviePy clip
    """
    # Open GIF file
    gif = PILImage.open(gif_path)
    frames = []
    durations = []
    
    # Process each frame
    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        w, h = rgba.size
        cropped = rgba.crop((50, 0, w - 20, h))  # Manual crop

        np_frame = np.array(cropped)

        frames.append(np_frame)
        durations.append(frame.info.get("duration", 100))
        
    # Calculate FPS from frame durations
    fps = 1000 / (sum(durations) / len(durations))
    
    # Create clip
    clip = ImageSequenceClip(frames, fps=fps)
    
    # Resize if needed
    if resize_height:
        clip = clip.resize(height=resize_height)
        
    # Loop for specified duration
    looped = clip.loop(duration=duration)
    return looped.set_position(position)


def pixel_wrap(text, font, max_width):
    """
    Wrap text to fit within a specified pixel width.
    
    This function wraps text based on actual pixel width rather than character count,
    providing more accurate text wrapping for video generation.
    
    Args:
        text (str): Text to wrap
        font (ImageFont): Font object for measuring text width
        max_width (int): Maximum width in pixels
        
    Returns:
        list: List of tuples (is_first_line, line_text) for wrapped lines
    """
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
