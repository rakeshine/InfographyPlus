from moviepy.editor import ImageClip
from PIL import Image as PILImage, ImageFilter
import numpy as np

def blur_image(image_clip, sigma=50):
    frame = image_clip.get_frame(0)
    pil_image = PILImage.fromarray(frame)
    blurred = pil_image.filter(ImageFilter.GaussianBlur(radius=sigma))
    return ImageClip(np.array(blurred)).set_duration(image_clip.duration).set_position("center")