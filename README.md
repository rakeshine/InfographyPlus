# Infography+ Project

A comprehensive infographics and video generation system with multiple specialized modules.

## 🎯 Project Overview

Infography+ is a modular system designed to create engaging infographics and videos from SVG templates and content data. The system consists of three main modules:

1. **generate_infography_base** - SVG processing and manipulation
2. **generate_infography_video** - Video generation from infographics
3. **generate_narration_video** - Narration-based video creation

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Chrome/Chromium browser (for Selenium support)
- Required Python packages (see requirements.txt)

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run the main application
python main.py
```

### Usage
The system provides a menu-driven interface:
1. Run `python main.py`
2. Select the desired module and functionality
3. Follow the prompts to execute

## 📁 Project Structure

```
InfographyPlus/
├── main.py                 # Central entry point
├── config.py              # Global configuration
├── README.md              # This file
├── requirements.txt        # Python dependencies
├── content.json           # Sample content data
├── assets/                # Shared assets
│   ├── fonts/            # Font files
│   ├── images/           # Image assets
│   └── templates/        # SVG templates
├── generate_infography_base/
│   ├── __init__.py
│   ├── input/            # SVG input files
│   ├── output/           # Processed output files
│   └── utils/
│       ├── __init__.py
│       ├── svg-parser.py  # SVG text extraction
│       └── svg-replacer.py # SVG text replacement
├── generate_infography_video/
│   ├── __init__.py
│   ├── main.py          # Video generation entry
│   ├── handler/         # Video processing handlers
│   └── utils/           # Utility functions
├── generate_narration_video/
│   ├── __init__.py
│   ├── execute.py       # Narration video creation
│   └── [module files]   # Narration-specific utilities
```

## 🔧 Modules & Functionalities

### 1. generate_infography_base
**Purpose**: SVG processing and manipulation

**Functionalities**:
- **SVG Parser**: Extract text elements from SVG files with coordinates
- **SVG Replacer**: Replace text elements in SVG with new content

**Usage**:
```bash
# Run from main.py and select:
# 1.1 SVG Parser
# 1.2 SVG Replacer
```

**Input/Output**:
- **Input**: SVG files in `generate_infography_base/input/`
- **Output**: Processed SVG and JSON files in `generate_infography_base/output/`

### 2. generate_infography_video
**Purpose**: Create videos from infographics

**Functionalities**:
- **Video Generator**: Generate animated videos from SVG infographics
- **Audio Handler**: Process and synchronize audio with visuals

**Usage**:
```bash
# Run from main.py and select:
# 2.1 Video Generator
```

**Input/Output**:
- **Input**: SVG templates and content data
- **Output**: MP4 video files

### 3. generate_narration_video
**Purpose**: Create narration-based videos

**Functionalities**:
- **Narration Video**: Generate videos with voice-over narration

**Usage**:
```bash
# Run from main.py and select:
# 3.1 Narration Video
```

## 📊 Configuration

All configuration is centralized in `config.py` with the following sections:

- **SVG_PARSER**: SVG processing settings
- **SVG_REPLACER**: Text replacement parameters
- **VIDEO_GENERATOR**: Video creation settings
- **NARRATION_VIDEO**: Narration-specific settings

## 🎨 Supported Formats

### Input Formats
- **SVG**: Scalable Vector Graphics templates
- **JSON**: Content data files
- **GIF**: Animated graphics
- **PNG/JPG**: Static images

### Output Formats
- **SVG**: Processed vector graphics
- **MP4**: High-quality video files
- **JSON**: Metadata and configuration
- **PNG**: Rasterized graphics

## 🛠️ Development

### Adding New Modules
1. Create module directory with `__init__.py`
2. Add input/output folders
3. Update `config.py` with new settings
4. Add functionality to `main.py` menu

### Customization
- Modify `config.py` for behavior changes
- Add new templates to `assets/templates/`
- Update fonts in `assets/fonts/`
- Add images to `assets/images/`

## 🐛 Troubleshooting

### Common Issues

**SVG Parser Not Found**
```bash
# Ensure you're in the project root
cd /path/to/InfographyPlus
python main.py
```

**Chrome Driver Issues**
- Install Chrome/Chromium browser
- Ensure ChromeDriver is in PATH
- Use Selenium fallback if needed

**Path Issues**
- All paths are now absolute and calculated from script location
- No need to change working directory

## 📞 Support

For issues or questions:
1. Check this README first
2. Verify configuration in `config.py`
3. Ensure all dependencies are installed
4. Check module-specific documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 License

This project is proprietary software. All rights reserved.


## Prompt
# Youtube Shorts
Rephrase the above information into a format below with proper punctuations and text length not more than the text in below format. [ {"text": "5 quick tips to instantly improve your presentations.", "duration": 2.0}, {"text": "1) Open with a strong hook—state a bold result or question.", "duration": 2.0}, {"text": "2) Use one key idea per slide. Remove anything that doesn’t support it.", "duration": 2.0}, {"text": "3) Tell a story—set up, conflict, resolution. Keep momentum.", "duration": 2.0}, {"text": "4) Use large text and high contrast. Design for the back row.", "duration": 2.0}, {"text": "5) Rehearse out loud. Time yourself and trim ruthlessly.", "duration": 2.0}, {"text": "Follow for more concise comms tips!", "duration": 2.0}, ]

# Youtube Video
Same as above except change duration to 10 to 12 seconds