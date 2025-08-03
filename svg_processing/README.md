# SVG Processing Tools

This directory contains tools for processing SVG files, specifically for extracting text elements and replacing rectangles with text.

## Directory Structure

```
svg_processing/
├── README.md          # This documentation file
├── input/             # Input SVG files
│   ├── 5points_plant.svg
│   ├── output_with_texts.svg
│   └── test_tspan_font_sizes.svg
├── output/            # Output files
│   ├── 5points_plant.svg
│   ├── text_blocks.json
│   └── output_with_texts.svg
└── utils/             # Processing utilities
    ├── svg-parser.py
    └── svg-replacer.py
```

## Tools

### svg-parser.py

This tool extracts text elements from an SVG file and replaces them with rectangles. It generates a JSON file with the text block information.

**Usage:**
```bash
cd utils
python svg-parser.py
```

**Input:** `../input/5points_plant.svg`
**Outputs:** 
- `../output/5points_plant.svg` (SVG with rectangles instead of text)
- `../output/text_blocks.json` (Text block information)

### svg-replacer.py

This tool takes the output from svg-parser.py and replaces the rectangles with text elements, preserving the original text content and formatting.

**Usage:**
```bash
cd utils
python svg-replacer.py
```

**Inputs:**
- `../output/5points_plant.svg` (SVG with rectangles)
- `../output/text_blocks.json` (Text block information)

**Output:** `../output/output_with_texts.svg` (Final SVG with text restored)

## Workflow

1. Run `svg-parser.py` to extract text and generate rectangles
2. Run `svg-replacer.py` to restore text using the generated JSON data
