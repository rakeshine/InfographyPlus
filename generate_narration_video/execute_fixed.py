import whisper
import pysrt
from moviepy.editor import *
# Import configuration variables
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MODULE_CONFIG

# Get paths from module configuration
svg_config = MODULE_CONFIG['generate_narration_video']['functionalities']['narration-video']
BACKGROUND_IMAGE = svg_config['background']
NARRATION_AUDIO = svg_config['audio']
OUTPUT_VIDEO = svg_config['output_video']

FONT_SIZE = 50
VIDEO_SIZE = (1280, 720)  # match background or desired output
FONT = "Arial-Bold"

# Check if transcript already exists to skip transcription
srt_path = "transcript.srt"
if not os.path.exists(srt_path):
    print("Transcribing audio with Whisper...")
    model = whisper.load_model("small")
    result = model.transcribe(NARRATION_AUDIO, word_timestamps=False)

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(result["segments"], start=1):
            start = segment["start"]
            end = segment["end"]

            def to_srt_time(t):
                hrs = int(t // 3600)
                mins = int((t % 3600) // 60)
                secs = int(t % 60)
                ms = int((t * 1000) % 1000)
                return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

            f.write(f"{i}\n{to_srt_time(start)} --> {to_srt_time(end)}\n{segment['text'].strip()}\n\n")
else:
    print("Using existing transcript.srt file...")

# Step 2: Load SRT
print("Loading subtitles...")
subs = pysrt.open(srt_path)

# Step 3: Prepare background image
print("Preparing background...")
img_clip = ImageClip(BACKGROUND_IMAGE).resize(VIDEO_SIZE)

# Step 4: Build highlight clips
print("Creating video clips...")
clips = []
WINDOW_SIZE = 5  # number of subtitles to show around current

for idx, sub in enumerate(subs):
    print(f"Processing subtitle {idx+1}/{len(subs)}")
    start_time = sub.start.ordinal / 1000
    duration = sub.duration.seconds + sub.duration.milliseconds / 1000

    text_clips = []
    start_idx = max(0, idx - WINDOW_SIZE)
    end_idx = min(len(subs), idx + WINDOW_SIZE + 1)

    for i in range(start_idx, end_idx):
        s = subs[i]
        if i == idx:
            color = "yellow"
        else:
            color = "gray"

        txt_clip = TextClip(
            s.text.strip(),
            fontsize=FONT_SIZE,
            color=color,
            font=FONT,
            method="caption",
            size=(VIDEO_SIZE[0] - 100, None),
            align="center",
            stroke_color="black",
            stroke_width=2
        ).set_position(("center", VIDEO_SIZE[1]//2 + (i - idx) * (FONT_SIZE + 10)))

        text_clips.append(txt_clip)

    clips.append(CompositeVideoClip([img_clip] + text_clips)
                 .set_start(start_time)
                 .set_duration(duration))

# Step 5: Combine into final video
final_video = CompositeVideoClip(clips, size=VIDEO_SIZE)

# Step 6: Add audio
print("Adding audio...")
audio = AudioFileClip(NARRATION_AUDIO)
final_video = final_video.set_audio(audio)

# Step 7: Export
print("Exporting video...")
final_video.write_videofile(OUTPUT_VIDEO, fps=24, codec="libx264", audio_codec="aac")
print(f"✅ Done! Saved to {OUTPUT_VIDEO}")
