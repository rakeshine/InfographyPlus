from PIL import Image as PILImage, ImageDraw
import numpy as np
from moviepy.editor import VideoClip


def create_magnifier_zoom(base_clip, start_pos, end_pos, zoom_factor=2.0, size=(150, 150),
                          border_color="white", border_width=4, pulse_duration=3.5, fps=24):
    total_duration = base_clip.duration + pulse_duration

    def make_frame(t):
        if t < base_clip.duration:
            interp = t / base_clip.duration
            pos_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * interp)
            pos_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * interp)
            scale = 1.0
        else:
            interp = (t - base_clip.duration) / pulse_duration
            pos_x, pos_y = end_pos
            scale = 1 + 0.05 * np.sin(2 * np.pi * 2 * interp)

        frame = base_clip.get_frame(0)
        crop_size = int(size[0] / zoom_factor), int(size[1] / zoom_factor)
        crop_x0 = max(pos_x - crop_size[0] // 2, 0)
        crop_y0 = max(pos_y - crop_size[1] // 2, 0)
        crop_x1 = min(crop_x0 + crop_size[0], frame.shape[1])
        crop_y1 = min(crop_y0 + crop_size[1], frame.shape[0])
        cropped = frame[crop_y0:crop_y1, crop_x0:crop_x1]

        final_size = (int(size[0] * scale), int(size[1] * scale))
        resized = np.array(PILImage.fromarray(cropped).resize(final_size, resample=PILImage.BICUBIC))

        img = PILImage.new("RGBA", final_size, (0, 0, 0, 0))
        img.paste(PILImage.fromarray(resized), (0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([border_width // 2, border_width // 2, final_size[0] - border_width // 2, final_size[1] - border_width // 2], outline=border_color, width=border_width)

        shadow = PILImage.new("RGBA", (final_size[0]+10, final_size[1]+10), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((5, 5, final_size[0]+5, final_size[1]+5), fill=(0, 0, 0, 80))
        shadow.paste(img, (5, 5), img)

        return np.array(shadow.convert("RGB"))

    def make_mask(t):
        if t < base_clip.duration:
            scale = 1.0
        else:
            interp = (t - base_clip.duration) / pulse_duration
            scale = 1 + 0.05 * np.sin(2 * np.pi * 2 * interp)
        final_size = (int((size[0]+10) * scale), int((size[1]+10) * scale))
        mask_img = PILImage.new("L", final_size, 0)
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse((0, 0, final_size[0], final_size[1]), fill=255)
        return np.array(mask_img).astype(np.float32) / 255.0

    clip = VideoClip(make_frame=make_frame, duration=total_duration).set_fps(fps)
    mask = VideoClip(make_frame=make_mask, ismask=True, duration=total_duration).set_fps(fps)
    clip = clip.set_mask(mask)

    return clip.set_position(lambda t: (
        int(start_pos[0] + (end_pos[0] - start_pos[0]) * min(t / base_clip.duration, 1.0)),
        int(start_pos[1] + (end_pos[1] - start_pos[1]) * min(t / base_clip.duration, 1.0))
    ))