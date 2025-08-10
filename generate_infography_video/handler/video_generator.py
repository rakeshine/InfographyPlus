"""
Video Generator Module

This module contains the core logic for generating videos from SVG templates
and JSON content data. It handles the composition of clips, application of
effects, and final video rendering.
"""

import os
import json
import cairosvg
from moviepy.editor import *
from pathlib import Path
from PIL import Image as PILImage

from config import *
from .audio_handler import generate_tts
from utils.effects_utils import create_click_effect_clip, blur_image
from utils.dialogue_utils import create_typewriter_dialogue_clip

# Import configuration variables
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MODULE_CONFIG

# Get paths from module configuration
svg_config = MODULE_CONFIG['generate_infography_video']['functionalities']['video-generator']
json_path = svg_config['json_path']
svg_path = svg_config['svg_path']
cartoon_path = svg_config['cartoon_path']

converted_image_path = svg_config['converted_image_path']
audio_folder = svg_config['audio_folder']
output_path = svg_config['output_path']
output_svg_path = svg_config['output_svg_path']

class VideoGenerator:
    """
    A class to generate videos from SVG templates and JSON content.
    
    This class handles the entire video generation process, from processing
    SVG templates to composing final video clips with effects and audio.
    """
    
    def __init__(self, with_audio=True):
        """
        Initialize the VideoGenerator.
        
        Args:
            with_audio (bool): Whether to generate video with audio narration
        """
        self.with_audio = with_audio
        self.canvas_size = None
        self.content_blocks = []
        
    def process_template(self):
        """Process SVG template and convert to PNG."""
        from utils.svg_utils import process_svg
        
        # Process SVG to update with content headers
        process_svg(svg_path, json_path, output_svg_path)
        
        # Convert SVG to PNG
        cairosvg.svg2png(url=output_svg_path, write_to=converted_image_path)
        
        # Get canvas size
        self.canvas_size = PILImage.open(converted_image_path).size
        
        # Load content blocks
        with open(json_path, "r", encoding="utf-8") as f:
            self.content_blocks = json.load(f)
            
        print(f"Processed template with {len(self.content_blocks)} content blocks")
    
    def generate_clips(self):
        """
        Generate video clips for each content block.
        
        Returns:
            list: List of MoviePy VideoClip objects
        """
        clips = []
        
        for block_index, block in enumerate(self.content_blocks):
            title = block.get("title", "")
            position = block.get("position", {})
            points = block.get("points", [])
            
            if not points:
                continue

            # Combine title + bullet points
            dialogue_text = f"{title}\n" + "\n".join([f"• {point}" for point in points])
            base_name = f"block{block_index+1}"
            audio_path = os.path.join(audio_folder, base_name + ".wav")

            # Handle audio generation if needed
            audio_clip = None
            if self.with_audio:
                if not os.path.exists(audio_path):
                    generate_tts(dialogue_text, audio_path)
                audio_clip = AudioFileClip(audio_path)
                dialogue_dur = audio_clip.duration
            else:
                dialogue_dur = 4  # Fixed duration without audio
                
            magnifier_dur = min(3.0, dialogue_dur * 0.4)
            total_dur = dialogue_dur + magnifier_dur

            # Create base infographic clip
            infographic_clip = ImageClip(converted_image_path).set_duration(total_dur).crossfadein(0.6)
            clips.append(CompositeVideoClip([infographic_clip], size=self.canvas_size).set_duration(3))
            
            # Create blurred background for dialogue
            blurred = blur_image(infographic_clip).subclip(0, dialogue_dur)

            # Create dialogue overlay
            dialogue = create_typewriter_dialogue_clip(
                dialogue_text,
                cartoon_path,
                background_clip=blurred,
                dialogue_duration=dialogue_dur,
                canvas_size=self.canvas_size
            ).crossfadein(0.6)

            overlay = CompositeVideoClip([blurred, dialogue])

            # Create scene with all elements
            scene = CompositeVideoClip([
                infographic_clip,
                create_click_effect_clip(
                    round(position.get("x", 0)), 
                    round(position.get("y", 0)) - 25, 
                    round(position.get("width", 0)),
                    round(position.get("height", 0)) + 25,
                    duration=2, 
                    canvas_size=self.canvas_size),
                overlay.set_start(magnifier_dur)
            ], size=self.canvas_size).set_duration(total_dur)
            
            # Add audio if needed
            if self.with_audio and audio_clip:
                scene = scene.set_audio(audio_clip)

            clips.append(scene)
            
        return clips
    
    def generate_video(self, output_file=None):
        """
        Generate the final video from all clips.
        
        Args:
            output_file (str, optional): Output file path. Uses config if not provided.
        """
        if output_file is None:
            output_file = output_path
            
        print('Processing template...')
        self.process_template()
        
        print('Generating clips...')
        clips = self.generate_clips()
        
        print('Concatenating clips...')
        final_video = concatenate_videoclips(clips)
        
        print(f'Writing video to {output_file}...')
        final_video.write_videofile(
            output_file, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac", 
            audio=True, 
            threads=4
        )
        
        print('Video generation complete!')


def generate_video_with_audio(output_file=None):
    """
    Generate a video with audio narration.
    
    Args:
        output_file (str, optional): Output file path. Uses config if not provided.
    """
    generator = VideoGenerator(with_audio=True)
    generator.generate_video(output_file)


def generate_video_without_audio(output_file=None):
    """
    Generate a video without audio narration.
    
    Args:
        output_file (str, optional): Output file path. Uses config if not provided.
    """
    generator = VideoGenerator(with_audio=False)
    generator.generate_video(output_file)
