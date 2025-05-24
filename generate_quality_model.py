#!/usr/bin/env python3
"""
Generate high-quality OpenSCAD code using improved prompt engineering.
This script focuses on producing syntactically correct, clean code without manual intervention.
"""

import os
import time
import json
from rag.retriever import retrieve_context
import openai
from dotenv import load_dotenv
import argparse
from gui.rag_backend import generate_openscad_code

# Load environment variables
load_dotenv()

# Settings
OUTPUT_DIR = "generated"
DEFAULT_TEMP = 0.2  # Lower temperature for precise output

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_code_examples(prompt, max_examples=3):
    """Get highly relevant code examples instead of using all retrieved context"""
    context = retrieve_context(prompt)
    if not context:
        return ""
        
    # Extract the examples from the RAG context
    examples = []
    current_example = None
    current_lines = []
    
    for line in context.split('\n'):
        if line.startswith('// EXAMPLE '):
            # Save previous example if it exists
            if current_example and current_lines:
                examples.append('\n'.join(current_lines))
                current_lines = []
            
            # Start new example
            current_example = line
        elif current_example is not None:
            current_lines.append(line)
    
    # Add the last example if it exists
    if current_example and current_lines:
        examples.append('\n'.join(current_lines))
    
    # Select the most relevant examples (limit to max_examples)
    selected_examples = examples[:max_examples]
    
    return '\n\n'.join(selected_examples)

def generate_quality_scad(prompt, output_path, temperature=DEFAULT_TEMP):
    """Generate high-quality OpenSCAD code with improved prompt engineering"""
    print(f"Generating model for: {prompt}")

    # Get high-quality examples (RAG context)
    examples = get_code_examples(prompt)
    print(f"Retrieved {len(examples.split())} words of focused examples")

    # Improved system prompt
    system_prompt = """You are an expert OpenSCAD code generator specializing in 3D models with clean, standard syntax.\n\nFor simple primitive shapes (cube, sphere, cylinder, etc.), generate minimal valid OpenSCAD code using any dimensions or parameters provided in the user prompt.\nFor more complex or composite prompts, use best practices and the provided code examples as context.\n\nStrictly follow these rules:\n- Only use standard OpenSCAD primitives and syntax.\n- Never invent or use functions that are not part of OpenSCAD.\n- For spheres: if the user specifies a diameter, use sphere(d=...); if a radius, use sphere(r=...).\n- Ensure the code is directly runnable without syntax errors.\n- ONLY return the code, no explanations or markdown.\n"""

    user_prompt = f"""Create OpenSCAD code for the following 3D model:\n\n{prompt}\n\nOpenSCAD code examples for reference:\n\n{examples}\n\nRemember:\n- NO external libraries or includes\n- ONLY standard OpenSCAD built-in modules and functions\n- Ensure the code is directly runnable without syntax errors\n- ONLY return the code, no explanations or markdown"""

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)

    # Generate the model with improved prompt
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature
    )

    # Extract the generated code
    generated_code = response.choices[0].message.content

    # Clean up any remaining markdown code blocks
    if "```" in generated_code:
        # Extract code from markdown code blocks
        lines = generated_code.split('\n')
        clean_lines = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_code_block:
                in_code_block = True
                continue
            elif line.strip().startswith("```") and in_code_block:
                in_code_block = False
                continue
            elif in_code_block or not line.strip().startswith("```"):
                clean_lines.append(line)
        generated_code = '\n'.join(clean_lines)

    # Save the generated code
    with open(output_path, "w") as f:
        f.write(generated_code)

    print(f"Model generated and saved to: {output_path}")
    return generated_code

def test_model_generation(output_path):
    """Test if the generated model has syntax errors"""
    try:
        import subprocess
        result = subprocess.run(
            ["openscad", "-o", "/dev/null", "--check-parameters", "true", output_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ OpenSCAD syntax validation successful")
            return True
        else:
            print(f"❌ OpenSCAD syntax validation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing model: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="OpenSCAD Quality Generator")
    parser.add_argument('--prompt', type=str, help='Prompt for non-interactive code generation')
    args = parser.parse_args()

    if args.prompt:
        prompt = args.prompt
        timestamp = int(time.time())
        output_file = f"model_{timestamp}.scad"
        output_path = os.path.join(OUTPUT_DIR, output_file)
        # Use the unified backend
        generated_code = generate_openscad_code(prompt)
        with open(output_path, "w") as f:
            f.write(generated_code)
        print("\nGenerated OpenSCAD code:\n" + "=" * 50)
        print(generated_code)
        print("=" * 50)
        is_valid = test_model_generation(output_path)
        print(f"\nModel saved to: {output_path}")
        return

    while True:
        print("\n=== OpenSCAD Quality Generator ===")
        prompt = input("Enter a description of the 3D model you want to create (or 'q' to quit): ")
        if prompt.lower() in ('q', 'quit', 'exit'):
            break
        timestamp = int(time.time())
        output_file = f"model_{timestamp}.scad"
        output_path = os.path.join(OUTPUT_DIR, output_file)
        generated_code = generate_openscad_code(prompt)
        with open(output_path, "w") as f:
            f.write(generated_code)
        print("\nSample of generated OpenSCAD code:")
        print("=" * 50)
        print(generated_code[:500] + "..." if len(generated_code) > 500 else generated_code)
        print("=" * 50)
        is_valid = test_model_generation(output_path)
        print(f"\nModel generation completed in {time.time() - timestamp:.2f} seconds")
        print(f"Full model saved to: {output_path}")
        
        # Render options
        if is_valid:
            render = input("Would you like to render the model? (y/n): ")
            if render.lower() == 'y':
                try:
                    # Render to STL and PNG
                    stl_path = output_path.replace('.scad', '.stl')
                    png_path = output_path.replace('.scad', '.png')
                    
                    print("Rendering to STL...")
                    subprocess.run(["openscad", "-o", stl_path, output_path], check=True)
                    
                    print("Rendering image preview...")
                    subprocess.run(["openscad", "-o", png_path, "--imgsize=800,600", output_path], check=True)
                    
                    print(f"Rendered STL saved to: {stl_path}")
                    print(f"Preview image saved to: {png_path}")
                except Exception as e:
                    print(f"Error during rendering: {e}")
                    
if __name__ == "__main__":
    main() 