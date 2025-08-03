# Infographic+ Video Generator

A modular Python application for generating animated videos from SVG templates and JSON content data.

## Project Structure

```
.
├── assets/                 # Assets directory (fonts, images, templates)
├── content.json           # Content data file
├── config.py              # Configuration settings
├── main.py                # Main entry point
├── requirements.txt       # Python dependencies
├── core/                  # Core functionality modules
│   ├── __init__.py        # Package initializer
│   ├── audio_handler.py   # Audio handling functions
│   └── video_generator.py # Main video generation logic
└── video/                 # Video processing modules
    ├── __init__.py        # Package initializer
    ├── dialogue.py        # Dialogue clip generation
    ├── effects.py         # Image effects (wrapper)
    ├── effects_utils.py   # Visual effects implementation
    ├── gif_utils.py       # GIF processing utilities
    └── svg_utils.py       # SVG processing utilities
```

## Modules Overview

### Core Modules

- **`core/video_generator.py`** - Main video generation logic with `VideoGenerator` class
- **`core/audio_handler.py`** - Audio processing functions including TTS

### Video Modules

- **`video/dialogue.py`** - Dialogue clip generation with typewriter effects
- **`video/effects_utils.py`** - Visual effects implementation (click effects, blur)
- **`video/effects.py`** - Wrapper for image effects
- **`video/gif_utils.py`** - GIF processing and text wrapping utilities
- **`video/svg_utils.py`** - SVG template processing and content injection

### Utility Modules

- **`config.py`** - Configuration settings and file paths

## Usage

```bash
# Generate video with audio
python main.py

# Generate video without audio
python main.py --no-audio

# Specify output file
python main.py --output my_video.mp4
```

## Key Improvements

1. **Modular Design** - Separated concerns into distinct modules
2. **Improved Documentation** - Comprehensive docstrings for all functions
3. **Consistent API** - Unified interface for video generation
4. **Better Organization** - Logical grouping of related functionality

## Dependencies

See `requirements.txt` for the list of required Python packages.

