import os
import sys
import gc
import whisper
import pysrt
from moviepy.editor import (
    TextClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ImageClip,
    AudioFileClip,
)

# Add project root to sys.path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MODULE_CONFIG


def typing_clip_by_chars(text, duration, fontsize, font, video_size, text_width):
    chars = list(text)
    n = max(1, len(chars))
    per_char = duration / n

    subclips = []
    for i in range(1, n + 1):
        part = "".join(chars[:i])

        txt = TextClip(
            part,
            fontsize=fontsize,
            font=font,
            color="white",
            method="caption",
            size=(text_width, video_size[1]),  # adjustable width, full video height
            align="center",
            stroke_color="black",
            stroke_width=2,
        ).set_duration(per_char).set_position(("center", "center"))

        subclips.append(txt)

    seg_clip = concatenate_videoclips(subclips, method="compose")
    for c in subclips:
        try:
            c.close()
        except:
            pass
    gc.collect()
    return seg_clip


def to_srt_time(t: float) -> str:
    hrs = int(t // 3600)
    mins = int((t % 3600) // 60)
    secs = int(t % 60)
    ms = int((t * 1000) % 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


def main():
    svg_config = MODULE_CONFIG["generate_narration_video"]["functionalities"]["narration-video"]
    BACKGROUND_IMAGE = svg_config["background"]
    NARRATION_AUDIO = svg_config["audio"]
    OUTPUT_VIDEO = svg_config["output_video"]

    FONT_SIZE = 50
    VIDEO_SIZE = (1280, 720)
    FONT = "Arial-Bold"
    TEXT_WIDTH = 900

    srt_path = "transcript.srt"
    if not os.path.exists(srt_path):
        print("Transcribing audio with Whisper...")
        model = whisper.load_model("small")
        result = model.transcribe(NARRATION_AUDIO, word_timestamps=True)
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result["segments"], start=1):
                start = segment["start"]
                end = segment["end"]
                f.write(f"{i}\n{to_srt_time(start)} --> {to_srt_time(end)}\n{segment['text'].strip()}\n\n")
        del model, result
        gc.collect()
    else:
        print("Using existing transcript.srt file...")

    subs = pysrt.open(srt_path)
    audio = AudioFileClip(NARRATION_AUDIO)
    audio_duration = audio.duration

    bg_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE).set_duration(audio_duration)

    clips = []
    for idx, sub in enumerate(subs, start=1):
        seg_text = sub.text.strip()
        start_time = sub.start.ordinal / 1000
        end_time = sub.end.ordinal / 1000
        seg_duration = max(0.1, end_time - start_time)

        print(f"Segment {idx}: '{seg_text}' [{start_time:.2f}s → {end_time:.2f}s]")

        try:
            seg_clip = typing_clip_by_chars(seg_text, seg_duration, FONT_SIZE, FONT, VIDEO_SIZE, TEXT_WIDTH)
            seg_clip = seg_clip.set_start(start_time)
            clips.append(seg_clip)
        except Exception as e:
            print(f"  Fallback for segment {idx}: {e}")
            fallback = TextClip(
                seg_text,
                fontsize=FONT_SIZE,
                font=FONT,
                color="white",
                method="caption",
                size=(VIDEO_SIZE[0] - 100, None),
                align="center",
                stroke_color="black",
                stroke_width=2,
            )
            # Force render to get height for center position
            _ = fallback.get_frame(0)
            center_y = (VIDEO_SIZE[1] - fallback.h) / 2
            fallback = fallback.set_start(start_time).set_duration(seg_duration).set_position(("center", center_y))
            clips.append(fallback)

        gc.collect()

    final = CompositeVideoClip([bg_clip] + clips, size=VIDEO_SIZE).set_audio(audio)
    final = final.set_duration(audio_duration)

    final.write_videofile(
        OUTPUT_VIDEO,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=1,
        logger=None,
    )

    final.close()
    audio.close()
    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    bg_clip.close()
    gc.collect()
    print(f"✅ Done! Saved to {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
