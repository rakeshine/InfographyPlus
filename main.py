#!/usr/bin/env python3
"""
Main entry point for the Infography+ project
Allows selection of which module and functionality to run
"""

import os
import sys
import json
from config import MODULE_CONFIG

def display_menu():
    """Display the main menu for module and functionality selection"""
    print("\n" + "="*50)
    print("INFGRAPHY+ - MAIN MENU")
    print("="*50)
    
    modules = list(MODULE_CONFIG.keys())
    
    for i, module_name in enumerate(modules, 1):
        print(f"\n{i}. {module_name}")
        functionalities = MODULE_CONFIG[module_name]['functionalities']
        for j, func_name in enumerate(functionalities.keys(), 1):
            print(f"   {i}.{j} {func_name}")
    
    print("\n0. Exit")
    print("="*50)

def get_user_choice():
    """Get user selection for module and functionality"""
    try:
        choice = input("\nEnter your choice (e.g., '1.1' for module 1, functionality 1): ").strip()
        
        if choice == '0':
            return None, None
            
        parts = choice.split('.')
        if len(parts) == 2:
            module_idx = int(parts[0]) - 1
            func_idx = int(parts[1]) - 1
            
            modules = list(MODULE_CONFIG.keys())
            if 0 <= module_idx < len(modules):
                module_name = modules[module_idx]
                functionalities = list(MODULE_CONFIG[module_name]['functionalities'].keys())
                if 0 <= func_idx < len(functionalities):
                    return module_name, functionalities[func_idx]
        
        print("❌ Invalid choice. Please use format like '1.1'")
        return None, None
        
    except (ValueError, IndexError):
        print("❌ Invalid input format")
        return None, None

def run_functionality(module_name, functionality_name):
    """Execute the selected functionality"""
    try:
        config = MODULE_CONFIG[module_name]['functionalities'][functionality_name]
        
        print(f"\n🚀 Running {module_name} - {functionality_name}")
        print("-" * 40)
        
        if module_name == "generate_infography_base":
            if functionality_name == "svg-parser":
                from generate_infography_base.utils.svg_parser import run_parser
                run_parser(config['input'], config['output_svg'], config['output_json'])
                
            elif functionality_name == "svg-replacer":
                from generate_infography_base.utils.svg_replacer import replace_rects_in_order
                replace_rects_in_order(config['input_svg'], config['input_json'], config['output'])
                
        elif module_name == "generate_infography_video":
            if functionality_name == "video-generator":
                import sys
                import os
                # Add the generate_infography_video directory to Python path
                video_path = os.path.join(os.path.dirname(__file__), "generate_infography_video")
                if video_path not in sys.path:
                    sys.path.insert(0, video_path)
                
                from main import main as video_main
                video_main()
                
        elif module_name == "generate_narration_video":
            if functionality_name == "narration-video":
                from generate_narration_video.execute_fixed import main as narration_main
                narration_main()
                
    except Exception as e:
        print(f"❌ Error running {functionality_name}: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main application loop"""
    print("🎨 Welcome to Infography+ Project")
    
    while True:
        display_menu()
        module_name, functionality_name = get_user_choice()
        
        if module_name is None and functionality_name is None:
            if input("Are you sure you want to exit? (y/n): ").lower() == 'y':
                print("👋 Goodbye!")
                break
            continue
            
        run_functionality(module_name, functionality_name)
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
