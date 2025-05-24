#!/usr/bin/env python3
"""
OpenSCAD RAG Demo Script
A demonstration script for showcasing the Text-to-CAD system in an educational setting.
"""

import os
import time
from generate_quality_model import generate_quality_scad, test_model_generation
from rag.retriever import retrieve_context

def print_section(title):
    """Print a formatted section title"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def demonstrate_rag(prompt):
    """Demonstrate the RAG system's retrieval capabilities"""
    print_section("RAG System Demonstration")
    print(f"Query: {prompt}")
    
    context = retrieve_context(prompt)
    if context:
        print("\nRetrieved relevant OpenSCAD examples:")
        print("-" * 40)
        print(context[:1000] + "..." if len(context) > 1000 else context)
        print("-" * 40)
    else:
        print("No relevant examples found in the knowledge base.")

def generate_and_validate_model(prompt, output_dir="generated"):
    """Generate and validate an OpenSCAD model"""
    print_section("Model Generation")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = int(time.time())
    output_file = f"demo_model_{timestamp}.scad"
    output_path = os.path.join(output_dir, output_file)
    
    # Generate the model
    start_time = time.time()
    generated_code = generate_quality_scad(prompt, output_path)
    
    # Print sample of generated code
    print("\nGenerated OpenSCAD Code Preview:")
    print("-" * 40)
    print(generated_code[:500] + "..." if len(generated_code) > 500 else generated_code)
    print("-" * 40)
    
    # Validate the model
    is_valid = test_model_generation(output_path)
    
    # Report results
    end_time = time.time()
    print(f"\nGeneration completed in {end_time - start_time:.2f} seconds")
    print(f"Model saved to: {output_path}")
    print(f"Syntax validation: {'✅ Success' if is_valid else '❌ Failed'}")
    
    return output_path, is_valid

def main():
    print_section("OpenSCAD RAG System Demo")
    print("This demonstration will show how the system:")
    print("1. Uses RAG to retrieve relevant OpenSCAD examples")
    print("2. Generates high-quality OpenSCAD code from natural language")
    print("3. Validates the generated code for syntax correctness")
    
    # Example prompts for demonstration
    demo_prompts = [
        "A simple phone stand with adjustable angle and cable management",
        "A parametric gear with 20 teeth and 2mm module",
        "A wall-mounted tool holder with honeycomb pattern"
    ]
    
    for i, prompt in enumerate(demo_prompts, 1):
        print(f"\nDemo {i}/{len(demo_prompts)}")
        demonstrate_rag(prompt)
        output_path, is_valid = generate_and_validate_model(prompt)
        
        if is_valid:
            print("\nWould you like to:")
            print("1. Continue to next demo")
            print("2. Render this model")
            print("3. Exit demonstration")
            
            choice = input("\nEnter your choice (1-3): ")
            if choice == "2":
                os.system(f"openscad {output_path}")
            elif choice == "3":
                break
    
    print_section("Demonstration Complete")
    print("Thank you for watching the OpenSCAD RAG System demonstration!")

if __name__ == "__main__":
    main() 