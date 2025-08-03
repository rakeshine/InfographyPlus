"""
Configuration Module

This module contains configuration settings for the video generation system,
including file paths for input templates, assets, and output files.
"""

from pathlib import Path

# Input file paths
json_path = "content.json"                    # Content data file
svg_path = "assets/templates/4points_process.svg"  # SVG template file
cartoon_path = "assets/images/atom.gif"       # Cartoon character GIF
bullet_icon_path = "assets/images/bullet_spiral.gif"  # Bullet point icon
font_path = "assets/fonts/Cinzel-VariableFont_wght.ttf"  # Font file

# Output file paths
converted_image_path = "output/final.png"     # Converted SVG to PNG
audio_folder = "output"                        # Folder for audio files
output_path = "output/final_video.mp4"         # Final video output
output_svg_path = 'output/final.svg'          # Processed SVG output
