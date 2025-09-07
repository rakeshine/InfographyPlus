"""
Audio Handler Module

This module contains functionality for handling audio in video generation,
including text-to-speech conversion and audio file management.
"""

import os
import tempfile
import shutil
from gtts import gTTS


def generate_tts(text, out_path):
    """
    Generate text-to-speech audio file from input text.
    
    Args:
        text (str): Text to convert to speech
        out_path (str): Output file path for the audio file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    try:
        tts = gTTS(text, slow=False, lang="en", tld="co.in")
        tts.save(out_path)
        print(f"✅ TTS saved: {out_path}")
    except Exception as e:
        print(f"❌ TTS error: {e}")

def get_audio_duration(audio_path):
    """
    Get the duration of an audio file.
    
    Args:
        audio_path (str): Path to the audio file
        
    Returns:
        float: Duration of the audio file in seconds, or None if file doesn't exist
    """
    try:
        if os.path.exists(audio_path):
            from moviepy.editor import AudioFileClip
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            audio_clip.close()
            return duration
        return None
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return None