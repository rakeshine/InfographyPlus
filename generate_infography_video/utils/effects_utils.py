"""
Visual Effects Utilities Module

This module contains various visual effects functions used in video generation,
including click effects, highlights, and other animations.
"""

from PIL import Image as PILImage, ImageDraw
import numpy as np
from moviepy.editor import VideoClip

# Import configuration variables
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MODULE_CONFIG

# Get paths from module configuration
svg_config = MODULE_CONFIG['generate_infography_video']['functionalities']['video-generator']
converted_image_path = svg_config['converted_image_path']


def create_click_effect_clip(x, y, w, h, duration, canvas_size, fps=24):
    """ 
    Creates an animated rectangular highlight ripple effect.
    
    This function generates a pulsing blue rectangle animation that highlights
    a specific area of the video, typically used to draw attention to content blocks.
    
    Args:
        x (int): X-coordinate of the rectangle's top-left corner
        y (int): Y-coordinate of the rectangle's top-left corner
        w (int): Width of the rectangle
        h (int): Height of the rectangle
        duration (float): Duration of the effect in seconds
        canvas_size (tuple): Size of the video canvas as (width, height)
        fps (int, optional): Frames per second for the animation. Defaults to 24.
        
    Returns:
        VideoClip: A MoviePy VideoClip object with the animated effect
    """
    base_img = PILImage.open(converted_image_path).convert("RGBA")

    def make_frame(t):
        """Generate a single frame of the click effect animation."""
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


def blur_image(image_clip, sigma=50):
    """
    Apply Gaussian blur to an image clip.
    
    Args:
        image_clip (ImageClip): MoviePy ImageClip to blur
        sigma (int, optional): Blur intensity. Higher values = more blur. Defaults to 50.
        
    Returns:
        ImageClip: Blurred version of the input clip
    """
    from PIL import ImageFilter
    import numpy as np
    from moviepy.editor import ImageClip
    
    frame = image_clip.get_frame(0)
    pil_image = PILImage.fromarray(frame)
    blurred = pil_image.filter(ImageFilter.GaussianBlur(radius=sigma))
    return ImageClip(np.array(blurred)).set_duration(image_clip.duration).set_position("center")
