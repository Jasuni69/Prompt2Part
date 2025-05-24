"""
Test script to generate a final OpenSCAD model without external dependencies.
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
MODEL_NAME = "final_test_model.scad"
TEMPERATURE = 0.3

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
8. DO NOT use any external libraries or imports
9. Use ONLY standard OpenSCAD built-in modules and functions
10. Implement any needed functionality directly rather than using libraries"""

    # Limit context size to approximately 4000 tokens
    max_context_words = 1500
    context_words = context.split()
    if len(context_words) > max_context_words:
        # Truncate context
        print(f"Truncating context from {len(context_words)} to {max_context_words} words to avoid token limits")
        context = ' '.join(context_words[:max_context_words])
    
    user_prompt = f"""Create OpenSCAD code for: {prompt}

Use these code examples as reference:

{context}

IMPORTANT REQUIREMENTS:
1. DO NOT use any external libraries (no includes or uses)
2. Use ONLY standard OpenSCAD built-in modules and functions
3. Implement rounded corners and other features directly
4. Ensure your code is clean, well-commented, and has no syntax errors
5. The code must be directly runnable in OpenSCAD without any dependencies"""

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    # Generate the model
    try:
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
    except Exception as e:
        print(f"Error generating model: {e}")
        # Try with even less context if we hit a token limit
        if "context_length_exceeded" in str(e):
            print("Token limit exceeded. Retrying with reduced context...")
            max_context_words = 800
            context = ' '.join(context_words[:max_context_words])
            
            user_prompt = f"""Create OpenSCAD code for: {prompt}

Use these code examples as reference:

{context}

IMPORTANT REQUIREMENTS:
1. DO NOT use any external libraries (no includes or uses)
2. Use ONLY standard OpenSCAD built-in modules and functions
3. Implement rounded corners and other features directly
4. Ensure your code is clean, well-commented, and has no syntax errors
5. The code must be directly runnable in OpenSCAD without any dependencies"""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=TEMPERATURE
            )
            
            generated_code = response.choices[0].message.content
        else:
            raise
    
    # Clean up code if needed
    if "```openscad" in generated_code.lower() or "```scad" in generated_code.lower():
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
            elif in_code_block:
                clean_lines.append(line)
        
        generated_code = '\n'.join(clean_lines)
    
    # Save the generated code
    with open(output_path, "w") as f:
        f.write(generated_code)
    
    print(f"Model generated and saved to: {output_path}")
    return generated_code

def main():
    # Final test prompt
    prompt = """Create a phone stand with adjustable angle.
The stand should have:
1. A base that's 80mm wide, 60mm deep, and 10mm tall
2. A phone holder that's 15mm tall and can fit phones of different widths
3. The holder should tilt between 45 and 75 degrees
4. Include a slot for cable management
5. Add rounded corners where appropriate
6. Use only built-in OpenSCAD functions (no libraries)"""
    
    print("Starting final model generation...")
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