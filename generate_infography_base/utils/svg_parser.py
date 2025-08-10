import xml.etree.ElementTree as ET
import json
import os
import re
import statistics

# Try to import Selenium for fallback coordinate extraction
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    import time
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available, will use direct extraction only")

# Import configuration variables
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MODULE_CONFIG

# Get paths from module configuration
svg_config = MODULE_CONFIG['generate_infography_base']['functionalities']['svg-parser']
INPUT_SVG = svg_config['input']
OUTPUT_SVG = svg_config['output_svg']
OUTPUT_JSON = svg_config['output_json']

def setup_selenium():
    """Set up Selenium WebDriver with headless Chrome"""
    if not SELENIUM_AVAILABLE:
        return None
        
    # Setup Chrome options
    options = Options()
    options.add_argument('--headless')  # Run headlessly
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Try to use ChromeDriver
    try:
        # Try to find chromedriver in PATH
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        # Try with specific path if needed
        try:
            service = Service('/opt/homebrew/bin/chromedriver')  # Common path on macOS
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e2:
            # Try with Chromium if Chrome not available
            try:
                options.binary_location = "/usr/bin/chromium-browser"
                driver = webdriver.Chrome(options=options)
            except:
                print(f"Failed to setup Selenium: {e}")
                return None
    
    return driver

def get_text_elements_with_selenium(svg_path):
    """Use Selenium to get text elements with accurate coordinates"""
    if not SELENIUM_AVAILABLE:
        return []
        
    driver = setup_selenium()
    if driver is None:
        return []
    
    try:
        # Load SVG file directly in browser
        file_url = f"file://{os.path.abspath(svg_path)}"
        driver.get(file_url)
        
        # Wait for SVG to load
        time.sleep(1)
        
        # Find all <text> elements within SVG using XPath
        text_elements = driver.find_elements(By.XPATH, "//*[local-name()='text']")
        
        elements_data = []
        
        for i, elem in enumerate(text_elements):
            try:
                # Get bounding box and text content via JS
                rect = driver.execute_script("""
                var el = arguments[0];
                var r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, width: r.width, height: r.height};
                """, elem)
                
                text_content = elem.text.strip()
                
                # Get font size for header identification
                font_size = driver.execute_script("""
                var el = arguments[0];
                var style = window.getComputedStyle(el);
                return parseFloat(style.fontSize);
                """, elem)
                
                # Get fill color
                fill_color = driver.execute_script("""
                var el = arguments[0];
                var style = window.getComputedStyle(el);
                return style.fill || style.color || '#000000';
                """, elem)
                
                elements_data.append({
                    'id': f"text{i + 1}",
                    'text': text_content,
                    'x': round(rect['x'], 2),
                    'y': round(rect['y'], 2),
                    'width': round(rect['width'], 2),
                    'height': round(rect['height'], 2),
                    'font_size': font_size,
                    'max_line_length': len(max(text_content.split('\n'), key=len)) if text_content else 0,
                    'fill': fill_color
                })
            except Exception as e:
                print(f"Error processing text element {i}: {e}")
                continue
        
        # Sort elements by vertical (y) then horizontal (x) position to get reading order
        elements_data.sort(key=lambda e: (e['y'], e['x']))
        
        # Reassign IDs based on sorted order
        for i, block in enumerate(elements_data):
            block['id'] = f"text{i + 1}"
        
        return elements_data
        
    finally:
        driver.quit()

def strip_ns(tag):
    """Strip namespace from XML tag"""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def parse_transform_matrix(transform):
    """Parse transform matrix to extract x, y translation values"""
    if not transform:
        return 0, 0
    
    # Match matrix(a b c d e f) where e and f are translation values
    # This pattern extracts the content between parentheses and splits by spaces
    matrix_match = re.search(r'matrix\((.*?)\)', transform)
    if matrix_match:
        content = matrix_match.group(1)
        numbers = content.split()
        if len(numbers) >= 6:
            # e (5th number) and f (6th number) are the translation values
            x = float(numbers[4])
            y = float(numbers[5])
            return x, y
    
    # Match translate(x, y) or translate(x y)
    translate_match = re.search(r'translate\((.*?)\)', transform)
    if translate_match:
        content = translate_match.group(1)
        # Split by comma or space
        numbers = re.split(r'[, ]+', content.strip())
        if len(numbers) >= 1:
            x = float(numbers[0])
            y = float(numbers[1]) if len(numbers) > 1 and numbers[1] else 0
            return x, y
    
    return 0, 0

def extract_text_content(elem, ns):
    """Extract text content from text element, including tspans"""
    text_content = ""
    tspans = elem.findall('svg:tspan', ns)
    if tspans:
        # Combine all tspan texts
        text_content = ''.join(t.text or '' for t in tspans)
    else:
        text_content = elem.text or ""
    return text_content.strip()

def estimate_text_width(text, font_size):
    """Estimate text width in pixels"""
    lines = text.split('\n')
    avg_char_width = font_size * 0.6
    # Calculate width as the maximum width of any line
    max_width = max(len(line) for line in lines) * avg_char_width if lines else 0
    return max_width

def estimate_text_height(text, font_size):
    """Estimate text height in pixels"""
    lines = text.split('\n')
    line_count = len(lines)
    # Calculate height as sum of line heights
    return line_count * font_size * 1.2

def calculate_rectangle_dimensions_for_text(text_content, font_size):
    """Calculate rectangle dimensions for text without tspans"""
    width = estimate_text_width(text_content, font_size)
    height = estimate_text_height(text_content, font_size)
    return width, height

def get_tspan_font_size(tspan, parent_font_size):
    """Get font size from tspan, fallback to parent font size if not specified"""
    # Get font size from style attribute of tspan
    style = tspan.attrib.get('style', '')
    font_size = parent_font_size  # default to parent font size
    font_size_match = re.search(r'font-size:\s*([+-]?\d*\.?\d+)', style)
    if font_size_match:
        font_size = float(font_size_match.group(1))
    return font_size

def calculate_rectangle_dimensions_for_tspans(tspans, parent_font_size):
    """Calculate rectangle dimensions for text with tspans
    - Width: width of any one tspan (using the widest)
    - Height: sum of the height of all tspans
    Returns:
    - width: calculated width
    - height: calculated height
    - max_font_size: maximum font size among tspans (for JSON output)
    """
    tspan_data = []
    
    # Calculate dimensions for each tspan
    for tspan in tspans:
        tspan_text = tspan.text or ""
        tspan_text = tspan_text.strip()
        if not tspan_text:
            continue
         
        # Get font size for this tspan (may be different from parent)
        font_size = get_tspan_font_size(tspan, parent_font_size)
        width = estimate_text_width(tspan_text, font_size)
        height = estimate_text_height(tspan_text, font_size)
        tspan_data.append({
            'width': width,
            'height': height,
            'font_size': font_size
        })
    
    # For texts with tspans:
    # - Width should be the width of any one tspan (using the widest)
    # - Height should be the sum of the height of all tspans
    if tspan_data:
        width = max(tspan['width'] for tspan in tspan_data)
        height = sum(tspan['height'] for tspan in tspan_data)
        # Use the font size of the widest tspan for the combined block
        max_width_tspan = max(tspan_data, key=lambda x: x['width'])
        max_font_size = max_width_tspan['font_size']
    else:
        width = 0
        height = 0
        max_font_size = parent_font_size
    
    return width, height, max_font_size

def classify_text_blocks(blocks):
    """Classify text blocks into numbers, headers, and descriptions"""
    # Calculate median font size and median area
    font_sizes = [b["font_size"] for b in blocks if "font_size" in b]
    areas = [b["width"] * b["height"] for b in blocks if "width" in b and "height" in b]

    # Handle case where we might not have enough data for statistics
    if not font_sizes or not areas:
        # Fallback: assign "unknown" to all blocks
        for block in blocks:
            block["type"] = "unknown"
        return blocks

    median_font = statistics.median(font_sizes)
    median_area = statistics.median(areas)

    classified = []

    for block in blocks:
        text = block["text"].strip().replace("\n", " ")
        font_size = block.get("font_size", 16)  # Default to 16 if not present
        area = block.get("width", 0) * block.get("height", 0)
        word_count = len(text.split())

        # Rule 1: If text looks like a number (1, 01, 1.), and is short
        if re.fullmatch(r'(0?[1-9]|[1-9][0-9])\.?', text):
            category = "number"
        
        # Rule 2: Headers - medium length, high font size, above median area
        elif font_size >= median_font and area >= median_area * 0.75 and word_count <= 5:
            category = "header"

        # Rule 3: Descriptions - lower font size, higher area, more words
        elif font_size <= median_font and area >= median_area and word_count >= 5:
            category = "description"

        # Fallbacks
        elif word_count <= 3 and font_size >= median_font:
            category = "header"
        elif word_count >= 5:
            category = "description"
        else:
            category = "unknown"

        block["type"] = category
        classified.append(block)

    return classified

def get_text_elements_from_svg(svg_path):
    """Extract text elements and their properties directly from SVG"""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    # Find all text elements in the SVG tree
    text_elements = root.findall('.//svg:text', ns)
    
    individual_blocks = []
    combined_blocks = []
    block_id = 1
    
    for elem in text_elements:
        try:
            # Get transform attribute to extract position of the text element
            transform = elem.attrib.get('transform', '')
            base_x, base_y = parse_transform_matrix(transform)
            
            # Get font size from style attribute of text element
            style = elem.attrib.get('style', '')
            font_size = svg_config['default_font_size']  # Use config value
            font_size_match = re.search(r'font-size:\s*([+-]?\d*\.?\d+)', style)
            if font_size_match:
                font_size = float(font_size_match.group(1))
            
            # Get fill color from style attribute of text element
            fill_color = svg_config['colors']['text']  # Use config value
            fill_match = re.search(r'fill:\s*([^;]+)', style)
            if fill_match:
                fill_color = fill_match.group(1)
            
            # Extract tspans individually as separate text blocks
            tspans = elem.findall('svg:tspan', ns)
            if tspans:
                combined_text = ''
                
                # Calculate dimensions for individual tspans
                for tspan in tspans:
                    tspan_text = tspan.text or ""
                    tspan_text = tspan_text.strip()
                    if not tspan_text:
                        continue
                    
                    # Get tspan transform attribute if any, else use base transform
                    tspan_transform = tspan.attrib.get('transform', '')
                    if tspan_transform:
                        x, y = parse_transform_matrix(tspan_transform)
                    else:
                        # Get x and y coordinates from tspan attributes
                        x = tspan.attrib.get('x')
                        y = tspan.attrib.get('y')
                        if x is not None and y is not None:
                            try:
                                x = float(x)
                                y = float(y)
                            except ValueError:
                                x, y = base_x, base_y
                        else:
                            x, y = base_x, base_y
                    
                    # Get font size for this tspan (may be different from parent)
                    tspan_font_size = get_tspan_font_size(tspan, font_size)
                    
                    # Estimate dimensions for tspan text
                    width = estimate_text_width(tspan_text, tspan_font_size)
                    height = estimate_text_height(tspan_text, tspan_font_size)
                    max_line_length = len(max(tspan_text.split('\n'), key=len)) if tspan_text else 0
                    
                    individual_blocks.append({
                        'id': f"text{block_id}",
                        'text': tspan_text,
                        'x': round(x, 2),
                        'y': round(y, 2),
                        'width': round(width, 2),
                        'height': round(height, 2),
                        'font_size': tspan_font_size,
                        'max_line_length': max_line_length,
                        'fill': fill_color
                    })
                    block_id += 1
                    combined_text += tspan_text + '\n'
                
                # Add combined text block for all tspans in this text element
                combined_text = combined_text.strip()
                if combined_text:
                    # For combined blocks with tspans:
                    # - Width should be the width of any one tspan (using the widest)
                    # - Height should be the sum of the height of all tspans
                    width, height, max_font_size = calculate_rectangle_dimensions_for_tspans(tspans, font_size)
                    
                    max_line_length = len(max(combined_text.split('\n'), key=len))
                    combined_blocks.append({
                        'id': f"combined{block_id}",
                        'text': combined_text,
                        'x': round(base_x, 2),
                        'y': round(base_y, 2),
                        'width': round(width, 2),
                        'height': round(height, 2),
                        'font_size': max_font_size,
                        'max_line_length': max_line_length,
                        'fill': fill_color
                    })
                    block_id += 1
            else:
                # No tspans, treat whole text element as one block
                text_content = elem.text or ""
                text_content = text_content.strip()
                if not text_content:
                    continue
                
                # Use externalized function for calculating dimensions
                width, height = calculate_rectangle_dimensions_for_text(text_content, font_size)
                max_line_length = len(max(text_content.split('\n'), key=len)) if text_content else 0
                
                combined_blocks.append({
                    'id': f"combined{block_id}",
                    'text': text_content,
                    'x': round(base_x, 2),
                    'y': round(base_y, 2),
                    'width': round(width, 2),
                    'height': round(height, 2),
                    'font_size': font_size,
                    'max_line_length': max_line_length,
                    'fill': fill_color
                })
                block_id += 1
        except Exception as e:
            print(f"Error processing text element: {e}")
            continue
    
    # Sort individual blocks by vertical (y) then horizontal (x) position to get reading order
    individual_blocks.sort(key=lambda e: (e['y'], e['x']))
    for i, block in enumerate(individual_blocks):
        block['id'] = f"text{i + 1}"
    
    # Sort combined blocks by vertical (y) then horizontal (x) position to get reading order
    combined_blocks.sort(key=lambda e: (e['y'], e['x']))
    
    # Classify text blocks
    combined_blocks = classify_text_blocks(combined_blocks)
    
    # Generate new IDs based on classification
    type_counters = {"number": 0, "header": 0, "description": 0, "unknown": 0}
    
    for block in combined_blocks:
        block_type = block.get("type", "unknown")
        type_counters[block_type] += 1
        block['id'] = f"{block_type}{type_counters[block_type]}"
    
    return individual_blocks, combined_blocks

def get_text_elements_with_fallback(svg_path):
    """Extract text elements with direct method, fallback to Selenium if needed"""
    # Try direct extraction first
    print("Attempting direct extraction...")
    individual_blocks, combined_blocks = get_text_elements_from_svg(svg_path)
    
    # Check if we got valid coordinates (not all zeros)
    has_valid_coordinates = any(block['x'] != 0 or block['y'] != 0 for block in individual_blocks)
    
    if not has_valid_coordinates and SELENIUM_AVAILABLE:
        print("Direct extraction failed or returned invalid coordinates, trying Selenium fallback...")
        individual_blocks = get_text_elements_with_selenium(svg_path)
        combined_blocks = individual_blocks  # fallback returns single list
    
    return individual_blocks, combined_blocks

def replace_text_with_rectangles_in_tree(tree, individual_blocks, combined_blocks):
    """Replace text elements with rectangles in the original SVG tree"""
    root = tree.getroot()
    
    # Register namespaces to preserve them
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    ET.register_namespace('', ns['svg'])
    
    # Find all text elements in the SVG tree
    text_elements = root.findall('.//svg:text', ns)
    
    # Create a mapping of combined block IDs to their block data for direct matching
    combined_id_to_block = {block['id']: block for block in combined_blocks}
    
    # Create parent map to track parent-child relationships
    parent_map = {c: p for p in root.iter() for c in p}
    
    # Process each text element
    for i, text_elem in enumerate(text_elements):
        print(f"Processing text element {i+1}")
        
        # Get transform attribute to extract position of the text element
        transform = text_elem.attrib.get('transform', '')
        base_x, base_y = parse_transform_matrix(transform)
        
        # Find tspans inside the text element
        tspans = text_elem.findall('svg:tspan', ns)
        
        if tspans:
            # For text elements with tspans, we need to find the matching combined block
            # based on the position of the text element
            matching_combined_block = None
            for block in combined_blocks:
                # Check if the block position matches the text element position
                if (abs(block['x'] - base_x) < 1.0 and 
                    abs(block['y'] - base_y) < 1.0):
                    matching_combined_block = block
                    break
            
            if matching_combined_block:
                print(f"  Found combined block for entire text element: {matching_combined_block['id']} (x:{matching_combined_block['x']}, y:{matching_combined_block['y']})")
                # Create rectangle element with explicit fill attribute
                rect = ET.Element(f"{{{ns['svg']}}}rect")
                rect.set('x', str(matching_combined_block['x']))
                rect.set('y', str(matching_combined_block['y']))
                rect.set('width', str(matching_combined_block['width']))
                rect.set('height', str(matching_combined_block['height']))
                rect.set('fill', 'black')
                rect.set('id', matching_combined_block['id'])
                
                # Add rectangle as sibling to the text element
                parent = parent_map.get(text_elem)
                if parent is not None:
                    # Insert rectangle after the text element
                    children = list(parent)
                    index = children.index(text_elem)
                    parent.insert(index + 1, rect)
                    print(f"    Added rectangle with id {matching_combined_block['id']} at ({matching_combined_block['x']}, {matching_combined_block['y']})")
                
                # Remove the entire text element
                parent = parent_map.get(text_elem)
                if parent is not None:
                    parent.remove(text_elem)
                    print(f"    Removed entire text element")
            else:
                print(f"  No matching combined block found for text element at ({base_x}, {base_y})")
                # Remove the text element if no matching combined block is found
                parent = parent_map.get(text_elem)
                if parent is not None:
                    parent.remove(text_elem)
                    print(f"    Removed text element")
        else:
            # No tspans, replace whole text element
            # Find matching combined block based on text content
            text_content = extract_text_content(text_elem, ns)
            matching_combined_block = None
            for block in combined_blocks:
                if block['text'].strip() == text_content.strip():
                    matching_combined_block = block
                    break
            
            if matching_combined_block:
                print(f"    Found matching block: {matching_combined_block['id']} (x:{matching_combined_block['x']}, y:{matching_combined_block['y']})")
                # Create rectangle element with explicit fill attribute
                rect = ET.Element(f"{{{ns['svg']}}}rect")
                rect.set('x', str(matching_combined_block['x']))
                rect.set('y', str(matching_combined_block['y']))
                rect.set('width', str(matching_combined_block['width']))
                rect.set('height', str(matching_combined_block['height']))
                rect.set('fill', 'black')
                rect.set('id', matching_combined_block['id'])
                
                # Add rectangle as sibling to the text element
                parent = parent_map.get(text_elem)
                if parent is not None:
                    # Insert rectangle after the text element
                    children = list(parent)
                    index = children.index(text_elem)
                    parent.insert(index + 1, rect)
                    print(f"    Added rectangle with id {matching_combined_block['id']} at ({matching_combined_block['x']}, {matching_combined_block['y']})")
                    
                    # Remove the text element
                    parent.remove(text_elem)
                    print(f"    Removed text element")
            else:
                print(f"    No matching block found for text: '{text_content}'")
                # Remove the text element if no matching combined block is found
                parent = parent_map.get(text_elem)
                if parent is not None:
                    parent.remove(text_elem)
                    print(f"    Removed text element")
    
    return tree

def parse_and_replace(svg_path):
    """Parse SVG directly, extract text blocks, replace with rectangles, and sort"""
    # Extract individual and combined text elements with accurate coordinates using direct method with Selenium fallback
    individual_blocks, combined_blocks = get_text_elements_with_fallback(svg_path)
    
    if not individual_blocks:
        print("No text elements found")
        return None, [], []
    
    # Parse the original SVG to preserve its structure
    tree = ET.parse(svg_path)
    
    # Replace text elements with rectangles in the original SVG tree using both individual and combined blocks
    tree = replace_text_with_rectangles_in_tree(tree, individual_blocks, combined_blocks)
    
    return tree, individual_blocks, combined_blocks

def save_outputs(tree, individual_blocks, combined_blocks, svg_out, json_out):
    """Save the processed SVG and JSON files"""
    # Save SVG
    tree.write(svg_out, encoding='utf-8', xml_declaration=True)
    
    # Save JSON with combined blocks (grouped tspans)
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump(combined_blocks, f, indent=2, ensure_ascii=False)
    print(f"✅ SVG saved to: {svg_out}")
    print(f"✅ JSON saved to: {json_out}")

def run_parser(svg_in, svg_out, json_out):
    """Main function to run the parser"""
    if not os.path.exists(svg_in):
        print(f"❌ SVG not found: {svg_in}")
        return
    tree, individual_blocks, combined_blocks = parse_and_replace(svg_in)
    if tree is not None and individual_blocks:
        save_outputs(tree, individual_blocks, combined_blocks, svg_out, json_out)
    else:
        print("❌ Failed to process SVG")

if __name__ == "__main__":
    run_parser(INPUT_SVG, OUTPUT_SVG, OUTPUT_JSON)
