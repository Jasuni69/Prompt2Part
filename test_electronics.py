#!/usr/bin/env python3

import sys
sys.path.append('gui')
from rag_backend_improved import generate_openscad_code_improved

def test_electronics():
    """Test electronic component generation with the improved RAG system."""
    
    print("🔧 Testing Electronic Component Generation")
    print("=" * 50)
    
    prompts = [
        "Create a resistor",
        "Make a transistor",
        "Generate an LED",
        "Create a capacitor",
        "Make a diode component"
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n🔍 Test {i}: {prompt}")
        print("-" * 30)
        
        try:
            result = generate_openscad_code_improved(prompt)
            print("✅ Generated code:")
            print(result)
            
            filename = f"test_electronics_{i}.scad"
            with open(filename, 'w') as f:
                f.write(result)
            print(f"💾 Saved to: {filename}")
            
            # Quick validation
            if any(comp in result for comp in ["Resistor", "Transistor", "Led_01"]):
                print("🎯 SUCCESS: Uses correct electronic component function!")
            elif any(shape in result for shape in ["cylinder(", "cube(", "sphere("]):
                print("✅ Uses basic shapes - could be a valid electronic component!")
            else:
                print("⚠️  Check generated code manually")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_electronics() 