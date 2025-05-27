#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'gui'))

# Import both versions
from rag_backend import generate_openscad_code as generate_original
from rag_backend_improved import generate_openscad_code_improved

def test_improved_rag():
    """Test the improved RAG system against various component types"""
    
    test_cases = [
        # Gears (the main problem case)
        "Create a gear with 20 teeth and 5mm module",
        "Make a simple spur gear with 15 teeth",
        "Generate an involute gear",
        
        # Other mechanical components
        "Create an M8 threaded bolt",
        "Make a ball bearing",
        "Design a timing belt pulley",
        "Create a compression spring",
        
        # Simple primitives (should work in both)
        "Make a 30mm cube",
        "Create a sphere with 25mm diameter",
    ]
    
    print("🔧 Testing Improved RAG System")
    print("=" * 60)
    
    for i, prompt in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {prompt}")
        print("-" * 50)
        
        # Test improved version
        print("🚀 IMPROVED VERSION:")
        try:
            improved_result = generate_openscad_code_improved(prompt)
            print(f"✅ Generated code ({len(improved_result)} chars):")
            print(improved_result)
            
            # Save improved result
            filename = f"test_improved_{i}.scad"
            with open(filename, 'w') as f:
                f.write(improved_result)
            print(f"💾 Saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Improved version error: {e}")
        
        print("\n" + "="*50)
        
        # Test original version for comparison
        print("📜 ORIGINAL VERSION:")
        try:
            original_result = generate_original(prompt)
            print(f"Generated code ({len(original_result)} chars):")
            print(original_result[:200] + "..." if len(original_result) > 200 else original_result)
            
            # Save original result
            filename = f"test_original_{i}.scad"
            with open(filename, 'w') as f:
                f.write(original_result)
            print(f"💾 Saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Original version error: {e}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    test_improved_rag() 