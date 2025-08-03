import xml.etree.ElementTree as ET
import json
import textwrap

# === Set file paths ===
SVG_INPUT = "../output/parsed.svg"
JSON_INPUT = "../output/info.json"
SVG_OUTPUT = "../output/final.svg"

def wrap_text(text, max_chars):
    """Wrap text to specified maximum characters per line"""
    # Handle None or empty text
    if not text:
        return []
    return textwrap.wrap(text, width=max_chars)

def replace_rects_in_order(svg_file, json_file, output_file):
    """Replace rectangles with text elements in order using actual coordinates"""
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    tree = ET.parse(svg_file)
    root = tree.getroot()

    ns = {'svg': 'http://www.w3.org/2000/svg'}

    with open(json_file, 'r', encoding='utf-8') as f:
        blocks = json.load(f)

    # Create a mapping of rectangle IDs to text blocks
    block_map = {block['id']: block for block in blocks}

    # Find all rectangles with text IDs and replace them
    rect_elements = root.findall('.//svg:rect', ns)
    
    for rect in rect_elements:
        rect_id = rect.attrib.get('id', '')
        if rect_id in block_map:
            block = block_map[rect_id]
            
            text_content = block.get('text', '').strip()
            if not text_content:
                continue

            # Get text properties from JSON
            x = float(block.get('x', 0))
            y = float(block.get('y', 0))
            font_size = float(block.get('font_size', 16))
            fill = block.get('fill', 'black')
            font_family = block.get('font_family', 'Arial')
            max_chars = block.get('max_line_length', 40)

            # Build <text> with <tspan> wrapped lines
            text_elem = ET.Element('text', {
                'x': str(x),
                'y': str(y),
                'font-size': str(font_size),
                'fill': fill,
                'id': rect_id,
                'font-family': font_family
            })

            # Wrap text and create tspans
            lines = wrap_text(text_content, max_chars)
            for line_num, line in enumerate(lines):
                tspan = ET.Element('tspan', {
                    'x': str(x),
                    'dy': str(font_size * 1.2 if line_num > 0 else 0)
                })
                tspan.text = line
                text_elem.append(tspan)

            # Replace rectangle with text element
            # Find parent element
            parent_map = {c: p for p in root.iter() for c in p}
            parent = parent_map.get(rect)
            if parent is not None:
                parent.remove(rect)
                parent.append(text_elem)

    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"✅ SVG updated and saved to: {output_file}")

if __name__ == "__main__":
    replace_rects_in_order(SVG_INPUT, JSON_INPUT, SVG_OUTPUT)
