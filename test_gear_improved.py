#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'gui'))

from rag_backend_improved import generate_openscad_code_improved

def test_gear_improved():
    """Test the improved RAG system specifically for gear generation"""
    
    gear_prompts = [
        "Create a gear with 20 teeth and 5mm module",
        "Make a simple spur gear with 15 teeth",
        "Generate an involute gear with 30 teeth",
    ]
    
    print("🔧 Testing Improved RAG System - Gear Focus")
    print("=" * 50)
    
    for i, prompt in enumerate(gear_prompts, 1):
        print(f"\n🔍 Test {i}: {prompt}")
        print("-" * 40)
        
        try:
            result = generate_openscad_code_improved(prompt)
            print(f"✅ Generated code:")
            print(result)
            
            # Save result
            filename = f"test_gear_improved_{i}.scad"
            with open(filename, 'w') as f:
                f.write(result)
            print(f"💾 Saved to: {filename}")
            
            # Quick validation
            if 'gear(' in result and 'BOSL' in result:
                print("🎯 SUCCESS: Uses correct gear() function and BOSL library!")
            elif 'A(' in result:
                print("❌ FAILED: Still using incorrect A() function")
            else:
                print("⚠️  UNCLEAR: Check generated code manually")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == "__main__":
    test_gear_improved() 