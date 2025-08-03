#!/usr/bin/env python3
"""
Main Video Generation Script

This script generates videos from SVG templates and JSON content data.
It can generate videos with or without audio narration.
"""

import argparse
from core.video_generator import generate_video_with_audio, generate_video_without_audio


def main():
    """Main function to parse arguments and generate video."""
    parser = argparse.ArgumentParser(description="Generate videos from SVG templates and JSON content")
    parser.add_argument(
        "--no-audio", 
        action="store_true", 
        help="Generate video without audio narration"
    )
    parser.add_argument(
        "--output", 
        "-o", 
        type=str, 
        help="Output file path (default: uses path from config)"
    )
    
    args = parser.parse_args()
    
    if args.no_audio:
        print("Generating video without audio...")
        generate_video_without_audio(args.output)
    else:
        print("Generating video with audio...")
        generate_video_with_audio(args.output)


if __name__ == "__main__":
    print("Starting video generation...")
    main()
