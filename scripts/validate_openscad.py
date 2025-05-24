#!/usr/bin/env python3
"""
Validate OpenSCAD models by checking for syntax errors.
This script uses the OpenSCAD command-line interface to check for syntax errors in .scad files.
"""

import os
import subprocess
import argparse
import glob
import sys

def find_openscad_executable():
    """Find the OpenSCAD executable path"""
    # Common locations for the OpenSCAD executable
    possible_paths = [
        "openscad",  # If in PATH
        "/usr/bin/openscad",
        "/usr/local/bin/openscad",
        "C:/Program Files/OpenSCAD/openscad.exe",
        os.path.expanduser("~/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    ]
    
    for path in possible_paths:
        try:
            # Try running 'openscad --version' to check if it works
            result = subprocess.run([path, "--version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True)
            if result.returncode == 0:
                print(f"Found OpenSCAD at: {path}")
                return path
        except Exception:
            continue
    
    return None

def validate_scad_file(openscad_exe, file_path):
    """Validate a single OpenSCAD file for syntax errors"""
    print(f"Validating {file_path}...")
    
    # Create a temporary output path for STL
    temp_output = os.path.splitext(file_path)[0] + "_validate.stl"
    
    try:
        # Run OpenSCAD in command-line mode to check for syntax errors
        result = subprocess.run(
            [openscad_exe, "-o", temp_output, file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=30  # Timeout after 30 seconds
        )
        
        # Check if there were errors
        if result.returncode != 0:
            print(f"❌ Error in {file_path}:")
            error_lines = result.stderr.split('\n')
            for line in error_lines:
                if line.strip():
                    print(f"   {line}")
            return False
        else:
            print(f"✅ {file_path} - No syntax errors")
            return True
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout while validating {file_path}")
        return False
    except Exception as e:
        print(f"❌ Error validating {file_path}: {e}")
        return False
    finally:
        # Clean up temporary file
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="Validate OpenSCAD models for syntax errors")
    parser.add_argument("--dir", "-d", default="generated", help="Directory containing .scad files")
    parser.add_argument("--file", "-f", help="Single .scad file to validate")
    parser.add_argument("--openscad", help="Path to OpenSCAD executable")
    
    args = parser.parse_args()
    
    # Find the OpenSCAD executable
    openscad_exe = args.openscad or find_openscad_executable()
    if not openscad_exe:
        print("Error: Could not find OpenSCAD executable. Please install OpenSCAD or specify the path with --openscad.")
        return 1
    
    # Get the list of files to validate
    files_to_validate = []
    if args.file:
        if os.path.exists(args.file) and args.file.endswith(".scad"):
            files_to_validate.append(args.file)
        else:
            print(f"Error: {args.file} is not a valid .scad file")
            return 1
    else:
        # Find all .scad files in the specified directory
        if not os.path.exists(args.dir):
            print(f"Error: Directory {args.dir} does not exist")
            return 1
        
        files_to_validate = glob.glob(os.path.join(args.dir, "*.scad"))
        if not files_to_validate:
            print(f"No .scad files found in {args.dir}")
            return 0
    
    print(f"Found {len(files_to_validate)} .scad files to validate")
    
    # Validate each file
    success_count = 0
    for file_path in files_to_validate:
        if validate_scad_file(openscad_exe, file_path):
            success_count += 1
    
    # Print summary
    print(f"\nValidation complete: {success_count}/{len(files_to_validate)} files are valid")
    
    # Return success if all files passed validation
    return 0 if success_count == len(files_to_validate) else 1

if __name__ == "__main__":
    sys.exit(main()) 