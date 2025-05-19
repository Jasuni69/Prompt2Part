import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import tempfile
import requests

# Load environment variables
load_dotenv()

# Check for available local LLM interfaces
OLLAMA_AVAILABLE = False
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    pass

# Default model settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "mistral")
OPENSCAD_SYSTEM_PROMPT = """You are an expert OpenSCAD programmer and mechanical engineer specializing in creating precise, functional, and manufacturable 3D models.

CRITICAL REQUIREMENTS FOR OPENSCAD CODE:
1. Write ONLY executable OpenSCAD code - no markdown or explanations outside the code
2. Use proper syntax for ALL function calls:
   - cylinder(h=height, r=radius) or cylinder(h=height, d=diameter) - never just cylinder(radius, height)
   - translate([x,y,z]) - never just translate(x,y,z)
   - Always use semicolons at the end of statements
   - All blocks must have matching { and } braces
3. Avoid syntax errors:
   - No trailing semicolons after function/module blocks
   - No semicolons after module/function definitions before the opening brace
   - Always separate array elements with commas: [x, y, z]
4. Consistent units - use mm for all dimensions
5. Ensure variables are defined before they're used
6. Only call modules AFTER they are defined 
7. When a model requires several parts, create separate modules for each part
8. Add comprehensive comments explaining design decisions and logic
9. Always generate complete, self-contained code that can be directly executed

PARAMETER DEFINITIONS:
- Define variables at the top of the file, grouped by component or function
- Use descriptive names: wall_thickness instead of wt
- Include explicit units in comments: wall_thickness = 2; // mm
- Define $fn for circles/curved surfaces (usually 100 for final models)
- Group related parameters together with explanatory comments
- For parameterized designs, expose ALL critical dimensions as variables
- Use ranges and constraints to ensure valid parameters (min/max values)

FUNCTION DEFINITION EXAMPLES:
- Function that returns a value: function calc_radius(diameter) = diameter / 2;
- Function returning a vector: function center_point(points) = [for (p = points) sum(p)] / len(points);
- Function returning a list: function fibonacci(n) = n <= 1 ? [0] : n == 2 ? [0, 1] : concat(fibonacci(n-1), [fibonacci(n-1)[n-2] + fibonacci(n-1)[n-3]]);
- Point generation function: 
  function generate_points(count, radius) = [for (i = [0:count-1]) [radius * cos(i * 360 / count), radius * sin(i * 360 / count)]];

CORRECT POLYGON EXAMPLES:
// Square points (clockwise order)
square_points = [[0, 0], [10, 0], [10, 10], [0, 10]];
polygon(square_points);

// Star shape using function
function star_points(points, outer_r, inner_r) = 
    [for (i = [0:2*points-1])
        let(angle = i * 180 / points)
        (i % 2 == 0) ? 
            [outer_r * cos(angle), outer_r * sin(angle)] : 
            [inner_r * cos(angle), inner_r * sin(angle)]
    ];
// Use with:
polygon(star_points(5, 20, 10));

MANUFACTURING CONSIDERATIONS:
- Consider wall thickness for 3D printing (minimum 1.2mm for strength)
- Design for printability: avoid overhangs greater than 45° without supports
- Add fillets/chamfers to stress points (minimum 0.5mm radius)
- For moving parts, ensure proper tolerances (0.2-0.4mm clearance)
- Include assembly instructions in comments
- For injection molding, consider draft angles (minimum 1-2°)

OPENSCAD SYNTAX SPECIFICS:
- For boolean operations, use syntax like: difference() { sphere(10); cube(15, center=true); }
- For transformations, use syntax like: translate([10, 0, 0]) rotate([0, 90, 0]) cube([10, 20, 30]);
- For iterations, use syntax like: for(i = [0:5]) { translate([i*10, 0, 0]) cube(5); }
- For holes and subtractions, use difference() { base_shape(); translate([...]) hole_shape(); }
- For rounded edges, use minkowski() { cube([10, 20, 5]); sphere(2); }
- For advanced shapes, use hull() to connect objects smoothly

LIBRARY USAGE:
- When using BOSL/BOSL2: Include "use <BOSL2/std.scad>;" at the top of your code
- When using threads: Include "use <threads.scad>;" for threading functions
- When using NopSCADlib: Include specific imports like "use <NopSCADlib/vitamins/pcb.scad>;"
- For gears: Include "use <MCAD/involute_gears.scad>;" when using MCAD gear functions
- For rounded shapes/fillets: "use <Round-Anything/polyround.scad>;" 
- For enclosures: "use <YAPP_Box/library/YAPPgenerator_v21.scad>;"

ERROR-PRONE PATTERNS TO AVOID:
1. Never call a function/variable before it's defined
2. Don't mix named and positional parameters: use cylinder(h=10, r=5) not cylinder(10, r=5)
3. Avoid creating recursive functions that don't terminate
4. Don't use the same name for both a function and a variable
5. Avoid reserved words as variables: module, function, for, if, else
6. Don't confuse module calls and function calls: modules use (), functions use =
7. Always ensure proper nesting of transformation operations

OPTIMIZATION TECHNIQUES:
- Use modules for repeated elements to reduce code redundancy
- Create higher-order parametric modules for complex shapes
- Employ recursion for fractal or repetitive patterns
- Use mathematical functions to generate complex curves
- Implement conditional logic for adaptive features

CODE STRUCTURE:
- Start with clear header comments explaining the model purpose and parameters
- Group parameters as variables (with descriptive comments)
- Define modules with clear names describing what they create
- End with the actual rendering commands
- Include appropriate $fn value for smooth curves (typically 100 for final renders)
- Organize complex designs with hierarchical module structure

COMMON STRUCTURES AND THEIR IMPLEMENTATIONS:
- Cookie cutter: Linear extrude a 2D shape, then make hollow with difference()
- Threaded container: Use thread library or create a helix with for() and rotate/translate
- Enclosure with lid: Create base and lid as separate modules, add snap features
- Gear mechanism: Use gear library or create involute profile with mathematical functions
- Adjustable bracket: Use for() loop with rotate() to create multiple positions

IMPORTANT: Double-check your code for syntax errors before completing it. Ensure all functions are defined before they are used, all geometric operations have proper syntax, and all parameter types match their expected usage.
"""

def check_ollama():
    """Check if Ollama is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except:
        return False

def format_context_for_prompt(context, prompt):
    """Format the context and prompt for the LLM."""
    if not context:
        formatted_context = f"""
# DESIGN TASK
Generate OpenSCAD code for: {prompt}

# DESIGN REQUIREMENTS
- The code must be fully functional and executable in OpenSCAD
- All parameter values should be in millimeters (mm)
- Use clear variable and module names
- Include detailed comments explaining key design decisions
- Expose important parameters as variables at the top
- Ensure all syntax is correct with proper parameter naming
- Use appropriate modules to organize and structure your code
- Make dimensions parameterized for easy modification
- Set $fn to an appropriate value (100) for smooth curved surfaces
- Consider manufacturing constraints (3D printing, CNC, etc.)
- Add fillets or chamfers to sharp edges for better mechanical properties
- Include material recommendations if applicable
- Optimize the design for both functionality and aesthetics

# IMPLEMENTATION
Write complete OpenSCAD code:
"""
        return formatted_context
        
    # Use the context provided by the retriever
    formatted_context = f"""
# DESIGN TASK
Generate OpenSCAD code for: {prompt}

# CODE REFERENCES
{context}

# IMPLEMENTATION GUIDELINES
- Study the reference code examples above carefully, especially syntax patterns and specialized functions
- Adapt the most relevant examples to create your solution
- Create a complete, functional implementation that will work in OpenSCAD
- Include necessary library imports if you're using specialized functions
- Use ONLY valid OpenSCAD syntax for all function calls and operations
- Ensure all blocks have matching {{ and }} braces
- Make the design fully parametric with variables at the top
- Check that all modules and variables are defined before use
- Set $fn to an appropriate value (100) for smooth curved surfaces
- Apply best practices for manufacturability (adequate wall thickness, proper tolerances)
- Add fillets/chamfers to sharp edges for better mechanical properties
- Include detailed comments explaining your design decisions
- Consider both aesthetics and functionality in your implementation

# IMPLEMENTATION
Write complete OpenSCAD code:
"""
    return formatted_context

def generate_code_with_ollama(prompt, context=None, model=DEFAULT_MODEL, temperature=0.2):
    """Generate OpenSCAD code using Ollama."""
    if not OLLAMA_AVAILABLE or not check_ollama():
        print("Ollama not available. Using OpenAI integration.")
        return generate_code_with_openai(prompt, context, temperature)
    
    try:
        # Format context and prompt
        formatted_prompt = format_context_for_prompt(context, prompt)
        
        # Generate response
        response = ollama.generate(
            model=model,
            prompt=formatted_prompt,
            system=OPENSCAD_SYSTEM_PROMPT,
            temperature=temperature
        )
        
        # Extract code from the response
        code = response['response']
        
        # Ensure it starts with OpenSCAD code
        if not code.startswith("//") and not code.startswith("/*") and not code.startswith("module"):
            code = "// " + prompt + "\n\n" + code
            
        return code
    except Exception as e:
        print(f"Error generating code with Ollama: {e}")
        return generate_code_with_openai(prompt, context, temperature)

def generate_code_with_openai(prompt, context=None, temperature=0.2):
    """Generate OpenSCAD code using OpenAI API."""
    try:
        # Get API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
            return generate_code_fallback(prompt, context)
            
        # Format context and prompt
        formatted_prompt = format_context_for_prompt(context, prompt)
        
        # Initialize OpenAI client
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Generate with OpenAI API - switch to GPT-4 for better CAD generation
        try:
            model = "gpt-4-turbo"
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": OPENSCAD_SYSTEM_PROMPT},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=temperature,
                max_tokens=4000
            )
        except Exception as e:
            print(f"Error with GPT-4, falling back to GPT-3.5: {e}")
            model = "gpt-3.5-turbo"
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": OPENSCAD_SYSTEM_PROMPT},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=temperature,
                max_tokens=3000
            )
        
        # Extract code from response
        code = response.choices[0].message.content.strip()
        
        # Clean up code if it contains markdown code fences
        if code.startswith("```") and code.endswith("```"):
            code = code.strip("```").strip()
            if code.startswith("openscad") or code.startswith("scad"):
                code = code[code.find("\n"):].strip()
        
        # Ensure it starts with OpenSCAD code - add a comment if needed
        if not code.startswith("//") and not code.startswith("/*") and not code.startswith("module"):
            code = f"// OpenSCAD model: {prompt}\n\n" + code
            
        return code
        
    except Exception as e:
        print(f"Error generating code with OpenAI: {e}")
        return generate_code_fallback(prompt, context)

def generate_code_fallback(prompt, context=None):
    """Fallback method when no API is available."""
    print("Using fallback code generation method.")
    
    # Simple template-based fallback
    base_code = f"""// Auto-generated OpenSCAD model for: {prompt}
// Note: This is a fallback template. Configure OpenAI API for better results.

// Parameters
$fn = 100;  // Smoothness of curved surfaces
height = 10;  // mm
width = 20;   // mm
depth = 15;   // mm

// Main module
module main_shape() {{
    difference() {{
        cube([width, depth, height], center=true);
        
        // Add some rounded corners using minkowski
        translate([0, 0, height/4]) {{
            minkowski() {{
                cube([width-4, depth-4, height/2], center=true);
                sphere(2);
            }}
        }}
    }}
}}

// Render the shape
main_shape();
"""
    return base_code

def generate_code(prompt, context=None, model=DEFAULT_MODEL, temperature=0.2):
    """
    Generate OpenSCAD code from a prompt using a local LLM.
    Optionally use context (from RAG).
    """
    # Try to use OpenAI API first (better quality for CAD)
    if os.getenv('OPENAI_API_KEY'):
        return generate_code_with_openai(prompt, context, temperature)
    
    # Try to use Ollama next
    if OLLAMA_AVAILABLE and check_ollama():
        return generate_code_with_ollama(prompt, context, model, temperature)
    
    # Fallback
    return generate_code_fallback(prompt, context)

def extract_scad_code(text):
    """Extract valid OpenSCAD code from a potentially mixed text."""
    # If it looks like pure code, return it
    if text.startswith("//") or text.startswith("module") or text.startswith("function"):
        return text
        
    # Look for code blocks
    import re
    code_blocks = re.findall(r'```(?:scad|openscad)?\s*([\s\S]+?)```', text)
    if code_blocks:
        return code_blocks[0]
        
    # Look for code-like sections (lines with brackets, semicolons)
    lines = text.split('\n')
    code_lines = []
    in_code_section = False
    
    for line in lines:
        # Detect code-like lines
        if ('{' in line or '}' in line or ';' in line or 
            line.strip().startswith('module') or
            line.strip().startswith('function') or
            line.strip().startswith('//') or
            ('=' in line and not line.strip().startswith('#'))):
            in_code_section = True
            code_lines.append(line)
        # Handle continuation of code blocks
        elif in_code_section and line.strip() and not line.strip().startswith('#'):
            code_lines.append(line)
        # Skip explanatory text
        elif line.strip().startswith('#') or 'example' in line.lower() or 'explanation' in line.lower():
            in_code_section = False
    
    if code_lines:
        return '\n'.join(code_lines)
    
    # If we couldn't extract code, return the original text
    return text 