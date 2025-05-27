#!/usr/bin/env python3

import sys
sys.path.append('gui')

from rag_backend_improved import generate_openscad_code_improved

def test_comprehensive_rag():
    """Test the improved RAG system with various component types."""
    
    print("🔧 Comprehensive RAG System Test")
    print("=" * 50)
    
    test_cases = [
        # Gear tests
        ("Create a gear with 20 teeth and 5mm module", "gear"),
        ("Make a simple spur gear with 15 teeth", "gear"),
        ("Generate an involute gear with 30 teeth", "gear"),
        
        # Simple primitives
        ("Create a 30mm cube", "primitive"),
        ("Make a sphere with radius 15mm", "primitive"),
        ("Generate a cylinder 50mm tall and 10mm diameter", "primitive"),
        
        # Complex shapes
        ("Create a hexagonal prism 20mm tall", "complex"),
        ("Make a torus with major radius 20mm and minor radius 5mm", "complex"),
    ]
    
    results = []
    
    for i, (prompt, category) in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {prompt}")
        print("-" * 40)
        
        try:
            code = generate_openscad_code_improved(prompt)
            
            # Save to file
            filename = f"test_comprehensive_{i}.scad"
            with open(filename, 'w') as f:
                f.write(code)
            
            print(f"✅ Generated code:")
            print(code)
            print(f"💾 Saved to: {filename}")
            
            # Quick validation
            success_indicators = []
            if category == "gear":
                if "gear(" in code and "use <scad_library/BOSL/involute_gears.scad>" in code:
                    success_indicators.append("✅ Uses correct gear() function and BOSL library")
                if "mm_per_tooth" in code and "number_of_teeth" in code:
                    success_indicators.append("✅ Uses correct parameter names")
                if "A(" not in code:
                    success_indicators.append("✅ No invalid A() function")
            elif category == "primitive":
                if any(prim in code for prim in ["cube(", "sphere(", "cylinder("]):
                    success_indicators.append("✅ Uses correct primitive functions")
            
            if success_indicators:
                for indicator in success_indicators:
                    print(indicator)
            else:
                print("⚠️  No specific validation criteria met")
            
            results.append((prompt, "SUCCESS", len(code)))
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((prompt, "ERROR", 0))
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 50)
    successful = sum(1 for _, status, _ in results if status == "SUCCESS")
    total = len(results)
    print(f"Success rate: {successful}/{total} ({successful/total*100:.1f}%)")
    
    for prompt, status, length in results:
        status_icon = "✅" if status == "SUCCESS" else "❌"
        print(f"{status_icon} {prompt[:50]}... ({length} chars)")

if __name__ == "__main__":
    test_comprehensive_rag() 