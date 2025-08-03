"""
SVG Utilities Module

This module contains functionality for processing SVG templates and injecting
content from JSON data files.
"""

import xml.etree.ElementTree as ET
import json
from config import json_path

# Namespace constants
SVG_NS = '{http://www.w3.org/2000/svg}'
INKSCAPE_NS = '{http://www.inkscape.org/namespaces/inkscape}'


def strip_ns(tag):
    """
    Strip namespace from XML tag.
    
    Args:
        tag (str): XML tag that may contain namespace
        
    Returns:
        str: Tag without namespace
    """
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def estimate_word_width(word, font_size=16, char_width_factor=0.6):
    """
    Estimate the width of a word in pixels.
    
    Args:
        word (str): Word to estimate width for
        font_size (int): Font size in pixels
        char_width_factor (float): Average character width factor
        
    Returns:
        float: Estimated width in pixels
    """
    # Approximate the width of a word in pixels assuming average char width ~0.6 * font_size
    return len(word) * font_size * char_width_factor


def wrap_text(text, max_width, font_size=16):
    """
    Wrap text to fit within a specified width.
    
    Args:
        text (str): Text to wrap
        max_width (float): Maximum width in pixels
        font_size (int): Font size in pixels
        
    Returns:
        list: List of wrapped lines
    """
    words = text.split()
    lines = []
    current_line = ''
    current_width = 0.0
    
    for w in words:
        word_width = estimate_word_width(w, font_size)
        space_width = estimate_word_width(' ', font_size)
        
        # If current_line is empty, no space width added
        additional_width = word_width if not current_line else (space_width + word_width)
        
        if current_width + additional_width <= max_width:
            if current_line:
                current_line += ' '
            current_line += w
            current_width += additional_width
        else:
            if current_line:
                lines.append(current_line)
            current_line = w
            current_width = word_width
    
    if current_line:
        lines.append(current_line)
    return lines


def add_wrapped_text(parent, x, y, text, font_size, box_width, line_height=None, right_align=False):
    """
    Add wrapped text to an SVG element.
    
    Args:
        parent (Element): Parent SVG element to add text to
        x (float): X coordinate for text
        y (float): Y coordinate for text
        text (str): Text to add
        font_size (int): Font size in pixels
        box_width (float): Maximum width for text wrapping
        line_height (float, optional): Height between lines
        right_align (bool): Whether to right-align text
    """
    if line_height is None:
        line_height = font_size * 1.2
    
    text_attribs = {
        'y': str(y),
        'font-size': str(font_size),
        'font-family': 'Arial',
        'fill': 'black',
        'style': 'dominant-baseline:hanging'  # Align y coordinate at top of first line
    }
    
    if right_align:
        text_attribs['text-anchor'] = 'end'
        text_x = x + box_width
    else:
        text_x = x
    
    text_attribs['x'] = str(text_x)
    
    text_elem = ET.Element(f'{SVG_NS}text', text_attribs)
    
    wrapped_lines = wrap_text(text, box_width, font_size)
    
    for i, line in enumerate(wrapped_lines):
        tspan_attrib = {
            'x': str(text_x),
        }
        tspan_attrib['dy'] = '0' if i == 0 else str(line_height)
        
        tspan = ET.Element(f'{SVG_NS}tspan', tspan_attrib)
        tspan.text = line
        text_elem.append(tspan)
    
    parent.append(text_elem)


def process_svg(svg_file, headers_file, output_file):
    """
    Process SVG template and inject content from JSON data.
    
    This function reads an SVG template, replaces labeled rectangles with
    wrapped text content from JSON data, and updates the JSON with position
    information for video generation.
    
    Args:
        svg_file (str): Path to input SVG template
        headers_file (str): Path to JSON file with content data
        output_file (str): Path to output processed SVG file
    """
    # Register namespaces
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    ET.register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
    
    # Parse SVG
    tree = ET.parse(svg_file)
    root = tree.getroot()
    
    # Load content data
    with open(headers_file, 'r', encoding='utf-8') as hf:
        data = json.load(hf)

    # Map headers to labels
    headers = [obj.get('title', '') for obj in data]
    label_names = ['header1', 'header2', 'header3', 'header4']
    header_map = {label: headers[i] if i < len(headers) else "" for i, label in enumerate(label_names)}
    
    # Find rectangles to replace
    rects_to_replace = []
    label_positions = {}  # Will hold x,y positions for each label

    for elem in root.iter():
        if strip_ns(elem.tag) == 'rect':
            label = elem.attrib.get(f'{INKSCAPE_NS}label')
            if label in label_names:
                rects_to_replace.append(elem)
                # Store x, y for content.json
                x = float(elem.attrib.get('x', '0'))
                y = float(elem.attrib.get('y', '0'))
                width = float(elem.attrib.get('width', '0'))
                height = float(elem.attrib.get('height', '0'))
                label_positions[label] = {'x': x, 'y': y, 'width': width, 'height': height}
    
    # Text formatting constants
    FONT_SIZE = 42
    LINE_HEIGHT = FONT_SIZE * 1.2

    # Replace rectangles with text
    for rect in rects_to_replace:
        label = rect.attrib.get(f'{INKSCAPE_NS}label')
        header_text = header_map.get(label, '')
        if not header_text:
            continue
        
        x = float(rect.attrib.get('x', '0'))
        y = float(rect.attrib.get('y', '0'))
        width = float(rect.attrib.get('width', '100'))
        
        # Find parent element of rect
        parent = next((p for p in root.iter() if rect in list(p)), root)
        parent.remove(rect)
        
        right_align = label in ['header2', 'header4']
        
        add_wrapped_text(parent, x, y, header_text, FONT_SIZE, width, LINE_HEIGHT, right_align=right_align)

    # 🔁 Inject position info into content.json data
    for i, label in enumerate(label_names):
        if i < len(data) and label in label_positions:
            data[i]['position'] = label_positions[label]

    # 💾 Save updated JSON
    with open(headers_file, 'w', encoding='utf-8') as hf:
        json.dump(data, hf, indent=2, ensure_ascii=False)
        print(f"Updated JSON saved to {headers_file}")

    # 💾 Save processed SVG
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"Processed SVG saved to {output_file}")

