#!/usr/bin/env python3
"""
Fix common OpenSCAD syntax errors in generated model files.
This script can be used to automatically fix the most common OpenSCAD syntax issues.
"""

import os
import re
import sys
import glob
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

def find_openscad_files(directory="generated", extension=".scad"):
    """Find all OpenSCAD files in the specified directory"""
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist")
        return []
    
    pattern = os.path.join(directory, f"*{extension}")
    files = glob.glob(pattern)
    return files

def fix_extra_braces(content):
    """Fix extra curly braces that cause parse errors"""
    # Remove problematic markers for empty module and operation bodies
    content = re.sub(r'{\s*// Empty module body\s*}', '', content)
    content = re.sub(r'{\s*// Empty operation body\s*}', '', content)
    
    # Find instances of double opening braces with space between
    fixed = re.sub(r'{\s*{', '{', content)
    # Find instances of double closing braces with space between
    fixed = re.sub(r'}\s*}', '}', fixed)
    
    # Remove extra parentheses at the beginning
    fixed = re.sub(r'^\s*\(', '', fixed)
    
    # Fix missing closing braces
    open_count = fixed.count('{')
    close_count = fixed.count('}')
    
    if open_count > close_count:
        # Too many opening braces
        print(f"{Fore.YELLOW}Warning: {open_count - close_count} too many opening braces{Style.RESET_ALL}")
        # Add missing closing braces at the end
        fixed = fixed.rstrip() + '\n' + '}' * (open_count - close_count) + '\n'
    elif close_count > open_count:
        # Too many closing braces
        print(f"{Fore.YELLOW}Warning: {close_count - open_count} too many closing braces{Style.RESET_ALL}")
        # Remove extra closing braces
        for _ in range(close_count - open_count):
            last_close = fixed.rstrip().rfind('}')
            if last_close > 0:
                fixed = fixed[:last_close] + fixed[last_close+1:]
    
    return fixed

def fix_module_definitions(content):
    """Fix common issues with module definitions"""
    # Fix modules with empty bodies followed by implementation
    pattern = r'module\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*{\s*// Empty module body\s*}\s*{'
    
    def module_replacer(match):
        module_name = match.group(1)
        return f"module {module_name}("
    
    fixed = re.sub(pattern, module_replacer, content)
    
    # Fix function definitions with incorrect syntax
    function_pattern = r'function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*=\s*0;\s*// Default return value\s*=\s*\n\s*\['
    
    def function_replacer(match):
        function_name = match.group(1)
        return f"function {function_name}("
    
    fixed = re.sub(function_pattern, function_replacer, fixed)
    
    return fixed

def fix_polyhedron(content):
    """Fix common issues with polyhedron definitions"""
    # Look for polyhedron with points/faces issues
    polyhedron_pattern = r'polyhedron\s*\(\s*points\s*=\s*([^,]+),\s*faces\s*=\s*([^)]+)\)'
    
    def polyhedron_replacer(match):
        points_str = match.group(1)
        faces_str = match.group(2)
        
        # Make sure points are in the correct format [x,y,z]
        if '[[' not in points_str:
            points_str = '[' + points_str + ']'
            
        # Make sure faces are in the correct format [[index1,index2,index3], ...]
        if '[[' not in faces_str:
            faces_str = '[' + faces_str + ']'
        
        return f'polyhedron(points={points_str}, faces={faces_str})'
    
    fixed = re.sub(polyhedron_pattern, polyhedron_replacer, content)
    return fixed

def ensure_main_module_call(content):
    """Make sure the main module is defined and called at the end of the file"""
    # Check if there's a main module defined
    main_module_pattern = r'module\s+main\s*\('
    main_module_exists = re.search(main_module_pattern, content) is not None
    
    # Check if the main module is called at the end
    main_call_pattern = r'main\s*\([^)]*\)\s*;?\s*$'
    main_call_exists = re.search(main_call_pattern, content) is not None
    
    fixed = content
    
    if main_module_exists and not main_call_exists:
        # Main module exists but is not called at the end
        fixed = fixed.rstrip() + '\n\n// Call the main module\nmain();\n'
        print(f"{Fore.GREEN}Added main module call at the end{Style.RESET_ALL}")
    elif not main_module_exists:
        # No main module exists, wrap everything in a main module
        # This is a more complex transformation and should be done carefully
        print(f"{Fore.YELLOW}Warning: No main module found{Style.RESET_ALL}")
    
    return fixed

def fix_syntax_errors(file_path):
    """Fix common syntax errors in an OpenSCAD file"""
    print(f"Processing {file_path}...")
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Make a backup of the original file
        backup_path = file_path + '.bak'
        with open(backup_path, 'w') as backup:
            backup.write(content)
        
        # Apply fixes
        fixed = content
        fixed = fix_module_definitions(fixed)
        fixed = fix_extra_braces(fixed)
        fixed = fix_polyhedron(fixed)
        fixed = ensure_main_module_call(fixed)
        
        if fixed != content:
            with open(file_path, 'w') as file:
                file.write(fixed)
            print(f"{Fore.GREEN}✅ Fixed syntax errors in {file_path}{Style.RESET_ALL}")
        else:
            print(f"{Fore.BLUE}No syntax errors found in {file_path}{Style.RESET_ALL}")
            # Remove the backup file if no changes were made
            os.remove(backup_path)
        
        return True
    except Exception as e:
        print(f"{Fore.RED}Error processing {file_path}: {e}{Style.RESET_ALL}")
        return False

def main():
    """Main function to fix OpenSCAD syntax errors"""
    # Allow specifying a directory as a command-line argument
    target_dir = "generated"
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    
    print(f"Looking for OpenSCAD files in {target_dir}...")
    scad_files = find_openscad_files(target_dir)
    
    if not scad_files:
        print(f"No OpenSCAD files found in {target_dir}")
        return
    
    print(f"Found {len(scad_files)} OpenSCAD files")
    
    # Process each file
    success_count = 0
    for file_path in scad_files:
        if fix_syntax_errors(file_path):
            success_count += 1
    
    print(f"\nProcessed {len(scad_files)} files, fixed {success_count} files")

if __name__ == "__main__":
    main() 