"""
Test script to generate a simple OpenSCAD model.
This will test the entire pipeline from RAG to model generation.
"""

import os
import time
from rag.retriever import retrieve_context
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Settings
OUTPUT_DIR = "generated"
MODEL_NAME = "simple_test_model.scad"
TEMPERATURE = 0.3  # Lower temperature for more precise output

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_scad_model(prompt, context, output_path):
    """Generate an OpenSCAD model using the OpenAI API and RAG context"""
    print(f"Generating model for: {prompt}")
    
    # Construct the full prompt
    system_prompt = """You are a 3D modeling expert specializing in OpenSCAD code.
Generate clean, valid OpenSCAD code for the described model.
Follow these guidelines:
1. Include clear comments
2. Use modules to organize code
3. Use variables for all dimensions
4. Ensure the code is syntactically correct
5. Avoid extra braces or syntax errors
6. Include a main module that calls all other modules
7. Call the main module at the end of the file
8. Keep code simple but functional"""

    user_prompt = f"""Create OpenSCAD code for: {prompt}

Use these code examples as reference:

{context}

Ensure your code is clean, well-commented, and has no syntax errors.
The code should be directly runnable in OpenSCAD."""

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    # Generate the model
    response = client.chat.completions.create(
        model="gpt-4",  # Use GPT-4 for best results
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=TEMPERATURE
    )
    
    # Extract the generated code
    generated_code = response.choices[0].message.content
    
    # Save the generated code
    with open(output_path, "w") as f:
        f.write(generated_code)
    
    print(f"Model generated and saved to: {output_path}")
    return generated_code

def main():
    # Simple test prompt
    prompt = "Create a simple cube with a sphere on top and a cylinder on the side. Include parameters for all dimensions."
    
    print("Starting test model generation...")
    start_time = time.time()
    
    # Step 1: Retrieve context using RAG
    print("\nRetrieving context from RAG...")
    context = retrieve_context(prompt)
    if not context:
        print("Failed to retrieve context")
        return
    
    print(f"Retrieved {len(context.split())} words of context")
    
    # Step 2: Generate the OpenSCAD model
    output_path = os.path.join(OUTPUT_DIR, MODEL_NAME)
    generated_code = generate_scad_model(prompt, context, output_path)
    
    # Step 3: Show a sample of the generated code
    print("\nSample of generated OpenSCAD code:")
    print("=" * 50)
    print(generated_code[:500] + "..." if len(generated_code) > 500 else generated_code)
    print("=" * 50)
    
    end_time = time.time()
    print(f"\nModel generation completed in {end_time - start_time:.2f} seconds")
    print(f"Full model saved to: {output_path}")

if __name__ == "__main__":
    main() 