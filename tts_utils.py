import os
from gtts import gTTS

def generate_tts(text, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        tts = gTTS(text)
        tts.save(out_path)
        print(f"✅ TTS saved: {out_path}")
    except Exception as e:
        print(f"❌ TTS error: {e}")