import xml.etree.ElementTree as ET
import json
import os
import re

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

# === SET FILE PATHS HERE ===
INPUT_SVG = "assets/templates/5points_plant.svg"
OUTPUT_SVG = "5points_plant.svg"
OUTPUT_JSON = "text_blocks.json"

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
            font_size = 16  # default font size
            font_size_match = re.search(r'font-size:\s*([+-]?\d*\.?\d+)', style)
            if font_size_match:
                font_size = float(font_size_match.group(1))
            
            # Get fill color from style attribute of text element
            fill_color = '#000000'  # default black
            fill_match = re.search(r'fill:\s*([^;]+)', style)
            if fill_match:
                fill_color = fill_match.group(1)
            
            # Extract tspans individually as separate text blocks
            tspans = elem.findall('svg:tspan', ns)
            if tspans:
                combined_text = ''
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
                    
                    # Estimate dimensions for tspan text
                    width = estimate_text_width(tspan_text, font_size)
                    height = estimate_text_height(tspan_text, font_size)
                    max_line_length = len(max(tspan_text.split('\n'), key=len)) if tspan_text else 0
                    
                    individual_blocks.append({
                        'id': f"text{block_id}",
                        'text': tspan_text,
                        'x': round(x, 2),
                        'y': round(y, 2),
                        'width': round(width, 2),
                        'height': round(height, 2),
                        'font_size': font_size,
                        'max_line_length': max_line_length,
                        'fill': fill_color
                    })
                    block_id += 1
                    combined_text += tspan_text + '\n'
                
                # Add combined text block for all tspans in this text element
                combined_text = combined_text.strip()
                if combined_text:
                    width = estimate_text_width(combined_text, font_size)
                    height = estimate_text_height(combined_text, font_size)
                    max_line_length = len(max(combined_text.split('\n'), key=len))
                    combined_blocks.append({
                        'id': f"combined{block_id}",
                        'text': combined_text,
                        'x': round(base_x, 2),
                        'y': round(base_y, 2),
                        'width': round(width, 2),
                        'height': round(height, 2),
                        'font_size': font_size,
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
                
                width = estimate_text_width(text_content, font_size)
                height = estimate_text_height(text_content, font_size)
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
    for i, block in enumerate(combined_blocks):
        block['id'] = f"combined{i + 1}"
    
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
    
    # Normalize text content for matching: remove whitespace and newlines
    def normalize_text(text):
        return ''.join(text.split()).lower() if text else ''
    
    # Create mappings of normalized text content to block data for matching
    individual_to_block = {normalize_text(block['text']): block for block in individual_blocks}
    combined_to_block = {normalize_text(block['text']): block for block in combined_blocks}
    
    # Create a mapping of combined block IDs to their block data for direct matching
    combined_id_to_block = {block['id']: block for block in combined_blocks}
    
    # Combine both mappings for comprehensive matching
    text_to_block = {**individual_to_block, **combined_to_block}
    
    # Print out the mapping for debugging
    print("Text to block mapping:")
    for text, block in text_to_block.items():
        print(f"  '{text}' -> {block['id']} (x:{block['x']}, y:{block['y']})")
    
    # Also print the original text for debugging
    print("Original texts in blocks:")
    all_blocks = individual_blocks + combined_blocks
    for block in all_blocks:
        print(f"  '{block['text']}' -> '{normalize_text(block['text'])}'")
    
    # Print specific blocks we're looking for
    print("Looking for specific blocks:")
    target_texts = ["KART NELA", "LOREM IPSUM", "SED AMAR", "ELIT ADIPI", "MIUS MAREA"]
    for target in target_texts:
        normalized = normalize_text(target)
        if normalized in text_to_block:
            print(f"  Found '{target}' -> '{normalized}' -> {text_to_block[normalized]['id']}")
        else:
            print(f"  Not found '{target}' -> '{normalized}'")
    
    # Create parent map to track parent-child relationships
    parent_map = {c: p for p in root.iter() for c in p}
    
    # Process each text element
    for i, text_elem in enumerate(text_elements):
        print(f"Processing text element {i+1}")
        
        # Find tspans inside the text element
        tspans = text_elem.findall('svg:tspan', ns)
        
        if tspans:
            # For text elements with tspans, we need to check if this represents a combined block
            # First, try to match the entire text content as a combined block
            full_text_content = extract_text_content(text_elem, ns)
            normalized_full_text = normalize_text(full_text_content)
            combined_block = text_to_block.get(normalized_full_text, None)
            
            if combined_block and combined_block['id'].startswith('combined'):
                print(f"  Found combined block for entire text element: {combined_block['id']} (x:{combined_block['x']}, y:{combined_block['y']})")
                # Create rectangle element with explicit fill attribute
                rect = ET.Element(f"{{{ns['svg']}}}rect")
                rect.set('x', str(combined_block['x']))
                rect.set('y', str(combined_block['y']))
                rect.set('width', str(combined_block['width']))
                rect.set('height', str(combined_block['height']))
                rect.set('fill', 'black')
                rect.set('id', combined_block['id'])
                
                # Add rectangle as sibling to the text element
                parent = parent_map.get(text_elem)
                if parent is not None:
                    # Insert rectangle after the text element
                    children = list(parent)
                    index = children.index(text_elem)
                    parent.insert(index + 1, rect)
                    print(f"    Added rectangle with id {combined_block['id']} at ({combined_block['x']}, {combined_block['y']})")
                
                # Remove the entire text element
                parent = parent_map.get(text_elem)
                if parent is not None:
                    parent.remove(text_elem)
                    print(f"    Removed entire text element")
            else:
                # Process individual tspans as before
                for j, tspan in enumerate(tspans):
                    tspan_text = tspan.text or ""
                    normalized_tspan_text = normalize_text(tspan_text)
                    print(f"  TSpan {j+1}: '{tspan_text}' (normalized: '{normalized_tspan_text}')")
                    block = text_to_block.get(normalized_tspan_text, None)
                    if block:
                        print(f"    Found matching block: {block['id']} (x:{block['x']}, y:{block['y']})")
                        # Create rectangle element with explicit fill attribute
                        rect = ET.Element(f"{{{ns['svg']}}}rect")
                        rect.set('x', str(block['x']))
                        rect.set('y', str(block['y']))
                        rect.set('width', str(block['width']))
                        rect.set('height', str(block['height']))
                        rect.set('fill', 'black')
                        rect.set('id', block['id'])
                        
                        # Add rectangle as sibling to the text element
                        parent = parent_map.get(text_elem)
                        if parent is not None:
                            # Insert rectangle after the text element
                            children = list(parent)
                            index = children.index(text_elem)
                            parent.insert(index + 1, rect)
                            print(f"    Added rectangle with id {block['id']} at ({block['x']}, {block['y']})")
                        
                        # Remove the tspan element
                        text_elem.remove(tspan)
                        print(f"    Removed tspan")
                    else:
                        print(f"    No matching block found")
                
                # Remove the text element if all tspans are removed
                # After removing tspans, check if the text element should be removed
                # We'll remove it if it has no meaningful child elements left and no text content
                # Check if all remaining tspans are just spaces
                remaining_tspans = [t for t in text_elem if strip_ns(t.tag) == 'tspan']
                meaningful_tspans = [t for t in remaining_tspans if t.text and t.text.strip()]
                
                if len(meaningful_tspans) == 0 and (not text_elem.text or text_elem.text.strip() == ""):
                    parent = parent_map.get(text_elem)
                    if parent is not None:
                        parent.remove(text_elem)
                        print(f"  Removed text element")
        else:
            # No tspans, replace whole text element
            text_content = extract_text_content(text_elem, ns)
            normalized_text_content = normalize_text(text_content)
            print(f"  Text content (no tspans): '{text_content}' (normalized: '{normalized_text_content}')")
            block = text_to_block.get(normalized_text_content, None)
            if block:
                print(f"    Found matching block: {block['id']} (x:{block['x']}, y:{block['y']})")
                # Create rectangle element with explicit fill attribute
                rect = ET.Element(f"{{{ns['svg']}}}rect")
                rect.set('x', str(block['x']))
                rect.set('y', str(block['y']))
                rect.set('width', str(block['width']))
                rect.set('height', str(block['height']))
                rect.set('fill', 'black')
                rect.set('id', block['id'])
                
                # Add rectangle as sibling to the text element
                parent = parent_map.get(text_elem)
                if parent is not None:
                    # Insert rectangle after the text element
                    children = list(parent)
                    index = children.index(text_elem)
                    parent.insert(index + 1, rect)
                    print(f"    Added rectangle with id {block['id']} at ({block['x']}, {block['y']})")
                    
                    # Remove the text element
                    parent.remove(text_elem)
                    print(f"    Removed text element")
            else:
                print(f"    No matching block found")
    
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
