"""
Configuration Module - Centralized settings for all modules
This module contains all configuration settings for the Infography+ project
"""

import os

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))



# Module paths
MODULE_CONFIG = {
    "generate_infography_base": {
        "path": os.path.join(BASE_DIR, "generate_infography_base"),
        "functionalities": {
            "svg-parser": {
                "input": os.path.join(BASE_DIR, "generate_infography_base", "input", "5points_plant.svg"),
                "output_svg": os.path.join(BASE_DIR, "generate_infography_base", "output", "parsed.svg"),
                "output_json": os.path.join(BASE_DIR, "generate_infography_base", "output", "info.json"),
                'default_fill_color': 'black',
                'default_font_size': 16,
                'default_font_family': 'Arial',
                
                # Color values
                'colors': {
                    'black': '#000000',
                    'white': '#ffffff',
                    'text': 'black'
                }
            },
            "svg-replacer": {
                "input_svg": os.path.join(BASE_DIR, "generate_infography_base", "output", "parsed.svg"),
                "input_json": os.path.join(BASE_DIR, "generate_infography_base", "output", "info.json"),
                "output": os.path.join(BASE_DIR, "generate_infography_base", "output", "final.svg")
            }
        }
    },
    "generate_infography_video": {
        "path": os.path.join(BASE_DIR, "generate_infography_video"),
        "functionalities": {
            "video-generator": {
                "json_path": os.path.join(BASE_DIR, "generate_infography_video", "input", "content.json"),
                "svg_path": os.path.join(BASE_DIR, "assets", "templates", "4points_process.svg"),
                "cartoon_path": os.path.join(BASE_DIR, "assets", "images", "atom.gif"),
                "bullet_icon_path": os.path.join(BASE_DIR, "assets", "images", "bullet_spiral.gif"),
                "font_path": os.path.join(BASE_DIR, "assets", "fonts", "Cinzel-VariableFont_wght.ttf"),
                "converted_image_path": os.path.join(BASE_DIR, "generate_infography_video", "output", "final.png"),
                "audio_folder": os.path.join(BASE_DIR, "generate_infography_video", "output"),
                "output_path": os.path.join(BASE_DIR, "generate_infography_video", "output", "final_video.mp4"),
                "output_svg_path": os.path.join(BASE_DIR, "generate_infography_video", "output", "final.svg")
            }
        }
    },
    "generate_narration_video": {
        "path": os.path.join(BASE_DIR, "generate_narration_video"),
        "functionalities": {
            "narration-video": {
                "background": os.path.join(BASE_DIR, "generate_narration_video", "background.jpeg"),
                "audio": os.path.join(BASE_DIR, "generate_narration_video", "narration.wav"),
                "output_video": os.path.join(BASE_DIR, "generate_narration_video", "narration_video.mp4")
            }
        }
    }
}