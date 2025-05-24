#!/usr/bin/env python3
"""
Update project dependencies.
This script ensures all required packages are installed.
"""

import subprocess
import sys
import os
import platform

def get_python_executable():
    """Get the appropriate Python executable"""
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # We're in a virtual environment
        return sys.executable
    else:
        # Try to use python3 explicitly
        return 'python3'

def update_dependencies():
    """Install or update dependencies from requirements.txt"""
    python_exe = get_python_executable()
    req_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
    
    if not os.path.exists(req_file):
        print(f"Error: requirements.txt not found at {req_file}")
        return False
    
    print(f"Installing dependencies from {req_file}...")
    
    try:
        # Upgrade pip first
        subprocess.run([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        
        # Install requirements
        subprocess.run([python_exe, '-m', 'pip', 'install', '-r', req_file], check=True)
        
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def main():
    """Main function"""
    print("=== Updating Project Dependencies ===")
    
    # Update dependencies
    success = update_dependencies()
    
    print("\n=== Dependency Update Complete ===")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 