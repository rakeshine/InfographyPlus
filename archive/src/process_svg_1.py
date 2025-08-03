from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Setup your webdriver - ensure chromedriver is installed and in PATH
service = Service('/opt/homebrew/bin/chromedriver')  # Provide correct path
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Run headlessly if you want

driver = webdriver.Chrome(service=service, options=options)

# Load your SVG file locally or hosted URL
svg_file = 'file:////Users/rakeshvijayakumar/Documents/Business/SmartSolutions/InfogrpahyPlus/assets/templates/4points_process.svg'  # Change to your file path or URL
driver.get(svg_file)

# Wait for SVG load/render if needed
time.sleep(1)

# Find all <text> elements within SVG using XPath for SVG
text_elements = driver.find_elements(By.XPATH, "//*[local-name()='text']")

elements_data = []

for elem in text_elements:
    # Get bounding box and text content via JS
    rect = driver.execute_script("""
    var el = arguments[0];
    var r = el.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height};
    """, elem)
    
    text_content = elem.text.strip()

    # Optionally get font size for header identification
    font_size = driver.execute_script("""
    var el = arguments[0];
    var style = window.getComputedStyle(el);
    return parseFloat(style.fontSize);
    """, elem)

    elements_data.append({
        'element': elem,
        'text': text_content,
        'x': rect['x'],
        'y': rect['y'],
        'width': rect['width'],
        'height': rect['height'],
        'font_size': font_size
    })

# Sort elements by vertical (y) then horizontal (x) position to get reading order
elements_data.sort(key=lambda e: (e['y'], e['x']))

# Print the inferred visual order
for i, e in enumerate(elements_data, 1):
    print(f"{i}: \"{e['text']}\" at ({e['x']:.2f}, {e['y']:.2f}) font size: {e['font_size']}")

driver.quit()