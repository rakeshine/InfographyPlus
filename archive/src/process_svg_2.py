import xml.etree.ElementTree as ET
import json

SVG_NS = '{http://www.w3.org/2000/svg}'
INKSCAPE_NS = '{http://www.inkscape.org/namespaces/inkscape}'

def strip_ns(tag):
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def estimate_word_width(word, font_size=16, char_width_factor=0.6):
    # Approximate the width of a word in pixels assuming average char width ~0.6 * font_size
    return len(word) * font_size * char_width_factor

def wrap_text(text, max_width, font_size=16):
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
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    ET.register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
    
    tree = ET.parse(svg_file)
    root = tree.getroot()
    
    with open(headers_file, 'r', encoding='utf-8') as hf:
        data = json.load(hf)
    headers = [obj.get('title', '') for obj in data]

    label_names = ['rect1', 'rect2', 'rect3', 'rect4']
    header_map = {label: headers[i] if i < len(headers) else "" for i, label in enumerate(label_names)}
    
    rects_to_replace = []
    
    for elem in root.iter():
        if strip_ns(elem.tag) == 'rect':
            label = elem.attrib.get(f'{INKSCAPE_NS}label')
            if label in label_names:
                rects_to_replace.append(elem)
    
    FONT_SIZE = 42
    LINE_HEIGHT = FONT_SIZE * 1.2
    
    for rect in rects_to_replace:
        label = rect.attrib.get(f'{INKSCAPE_NS}label')
        header_text = header_map.get(label, '')
        if not header_text:
            continue
        
        x = float(rect.attrib.get('x', '0'))
        y = float(rect.attrib.get('y', '0'))
        width = float(rect.attrib.get('width', '100'))
        
        # Determine parent element
        parent = None
        for p in root.iter():
            if rect in list(p):
                parent = p
                break
        if parent is None:
            parent = root
        
        parent.remove(rect)
        
        right_align = label in ['rect2', 'rect4']
        
        add_wrapped_text(parent, x, y, header_text, FONT_SIZE, width, LINE_HEIGHT, right_align=right_align)
    
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"Processed SVG saved to {output_file}")

if __name__ == "__main__":
    svg_path = '../assets/templates/4points_process_new.svg'  # Change to your file path or URL
    headers_path = '../assets/content.json' 
    output_svg_path = '../output/final.svg'
    
    process_svg(svg_path, headers_path, output_svg_path)
