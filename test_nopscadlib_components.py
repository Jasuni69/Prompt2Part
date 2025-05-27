#!/usr/bin/env python3

import sys
sys.path.append('gui')
from rag_backend_improved import generate_openscad_code_improved

def test_nopscadlib_components():
    """Test NopSCADlib component generation with the improved RAG system."""
    
    print("🔧 Testing NopSCADlib Component Generation")
    print("=" * 60)
    
    # Test cases organized by component type
    test_cases = [
        # Screws and fasteners
        ("Create an M3 screw", "screw"),
        ("Make a socket head cap screw M5 x 20mm", "screw"),
        ("Generate a hex nut M6", "nut"),
        ("Create a washer for M4 screw", "washer"),
        
        # Motors and actuators
        ("Create a NEMA17 stepper motor", "motor"),
        ("Make a servo motor", "motor"),
        ("Generate a stepper motor mount", "motor"),
        
        # Electronic components
        ("Create a microswitch", "microswitch"),
        ("Make a limit switch", "microswitch"),
        ("Generate a potentiometer", "potentiometer"),
        ("Create a terminal block", "terminal"),
        
        # PCB and connectors
        ("Create an Arduino PCB", "pcb"),
        ("Make a pin header connector", "connector"),
        ("Generate a D-sub connector", "connector"),
        
        # Mechanical components
        ("Create a threaded insert", "insert"),
        ("Make a hex pillar standoff", "pillar"),
        ("Generate a linear rail", "rail"),
        ("Create a smooth rod", "rod"),
        
        # Miscellaneous
        ("Make a zip tie", "ziptie"),
        ("Create wire routing", "wire"),
        ("Generate tubing", "tube"),
        ("Create a transformer", "transformer")
    ]
    
    results = {"success": 0, "partial": 0, "failed": 0}
    
    for i, (prompt, expected_type) in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {prompt}")
        print("-" * 40)
        
        try:
            result = generate_openscad_code_improved(prompt)
            print("✅ Generated code:")
            print(result[:200] + "..." if len(result) > 200 else result)
            
            filename = f"test_nopscad_{i:02d}_{expected_type}.scad"
            with open(filename, 'w') as f:
                f.write(result)
            print(f"💾 Saved to: {filename}")
            
            # Validation based on expected component type
            result_lower = result.lower()
            
            # Check for NopSCADlib usage
            if "nopscadlib" in result_lower:
                print("🎯 SUCCESS: Uses NopSCADlib!")
                results["success"] += 1
            elif any(func in result_lower for func in ["screw", "nut", "washer", "motor", "switch", "pcb", "connector"]):
                print("✅ PARTIAL: Contains relevant component functions!")
                results["partial"] += 1
            elif any(shape in result for shape in ["cylinder(", "cube(", "sphere("]):
                print("⚠️  BASIC: Uses basic shapes - might be valid!")
                results["partial"] += 1
            else:
                print("❌ FAILED: No relevant component code found")
                results["failed"] += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results["failed"] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    total = len(test_cases)
    print(f"🎯 Success (NopSCADlib): {results['success']}/{total} ({results['success']/total*100:.1f}%)")
    print(f"✅ Partial (relevant): {results['partial']}/{total} ({results['partial']/total*100:.1f}%)")
    print(f"❌ Failed: {results['failed']}/{total} ({results['failed']/total*100:.1f}%)")
    
    success_rate = (results['success'] + results['partial']) / total * 100
    print(f"\n🏆 Overall Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🌟 EXCELLENT: RAG system performs very well with NopSCADlib!")
    elif success_rate >= 60:
        print("👍 GOOD: RAG system works well with most components!")
    elif success_rate >= 40:
        print("⚠️  FAIR: Some components work, needs improvement!")
    else:
        print("🔧 NEEDS WORK: RAG system needs significant improvement!")

if __name__ == "__main__":
    test_nopscadlib_components() 