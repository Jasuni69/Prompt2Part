import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import tempfile
import requests
import re

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
10. NEVER include empty operation body placeholders - use actual geometry

PHYSICAL RELATIONSHIPS & POSITIONING:
1. When combining parts, understand their physical relationships:
   - For bases and supports, ensure they connect properly with correct Z-positions
   - Use proper coordinate transforms for rotations around the right axis
   - When nesting parts inside others, use the correct dimensions and offsets
2. Placement guidelines:
   - Translate objects to logical positions that make physical sense
   - For parts that need to be on top of others, use the proper height offsets
   - Center objects at origin when possible for easier manipulation
   - For assemblies, use parent-child relationships logically: base→support→feature
3. Dimension relationships:
   - Keep physical relationships between dimensions consistent, e.g., thickness ≪ width
   - Use scaled relationships (e.g., height = base_height * 2) rather than arbitrary numbers
   - Apply proper clearances for parts that need to fit together (0.1-0.4mm)

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
8. Never nest blocks unnecessarily: translate(...) { } { } - this is invalid syntax
9. Don't leave empty block bodies or comments like "// Empty operation body"

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
- Phone stand: Base with proper support angle (30-75°) and cable management

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
    # Include few-shot examples for common designs
    few_shot_examples = """
# FEW-SHOT EXAMPLES

## EXAMPLE 1: Box with lid
```openscad
// Parameters
$fn = 100; // Smoothness for curved surfaces
width = 80;  // mm, outer width
depth = 50;  // mm, outer depth
height = 30; // mm, outer height
wall = 2;    // mm, wall thickness
corner_radius = 5; // mm, radius for rounded corners

// Box base
module rounded_box(w, d, h, r) {
    hull() {
        for (x = [-1, 1], y = [-1, 1], z = [-1, 1]) {
            translate([x * (w/2 - r), y * (d/2 - r), z * (h/2 - r)])
                sphere(r = r);
        }
    }
}

// Main body
difference() {
    rounded_box(width, depth, height * 0.7, corner_radius);
    // Hollow out the inside
    translate([0, 0, wall])
        rounded_box(width - 2*wall, depth - 2*wall, height, corner_radius);
}

// Lid (positioned for demonstration)
translate([0, depth + 10, 0])
difference() {
    rounded_box(width, depth, height * 0.4, corner_radius);
    translate([0, 0, -wall])
        rounded_box(width - 2*wall, depth - 2*wall, height * 0.4, corner_radius);
}
```

## EXAMPLE 2: Gear with customizable teeth
```openscad
// Import required library
use <MCAD/involute_gears.scad>

// Parameters
$fn = 100;    // Smoothness for curved surfaces
teeth = 20;   // Number of teeth
thickness = 5; // mm, gear thickness
shaft_d = 5;  // mm, center hole diameter

// Create the gear
difference() {
    // Main gear body
    gear(number_of_teeth = teeth,
         circular_pitch = 5,
         pressure_angle = 20,
         clearance = 0.2,
         gear_thickness = thickness);
    // Center hole
    translate([0,0,-1]) cylinder(d=shaft_d, h=thickness+2, center=false);
}
```

## EXAMPLE 3: Parametric bolt using BOSL2
```openscad
// Import BOSL2 standard library
use <BOSL2/std.scad>;

// Parameters
bolt_diameter = 8; // mm
bolt_length = 30;  // mm
thread_pitch = 1.25; // mm

// Generate the bolt
bolt(d=bolt_diameter, l=bolt_length, pitch=thread_pitch);
```

## EXAMPLE 4: Phone stand with adjustable angle
```openscad
// Parameters
$fn = 100;  // Smoothness for curved surfaces
base_width = 80; // mm, width of the base
base_depth = 60; // mm, depth of the base
base_height = 5; // mm, height of the base
support_width = 60; // mm, width of the support
support_height = 80; // mm, height of the support
wall = 2;    // mm, wall thickness
angle = 70;  // Angle of inclination in degrees

// Base with slot
module base() {
    difference() {
        // Base plate
        cube([base_width, base_depth, base_height], center = true);
        
        // Slot for the support
        translate([0, 0, 1])
            cube([support_width + 1, wall * 3, base_height + 2], center = true);
    }
}

// Adjustable support
module support() {
    difference() {
        // Main support plate
        cube([support_width, wall, support_height], center = true);
        
        // Cutout for phone
        translate([0, 0, support_height/4])
            cube([support_width * 0.7, wall * 2, support_height/2], center = true);
    }
}

// Assemble the stand
base();
translate([0, -base_depth/4, support_height/2])
    rotate([angle, 0, 0])
        support();
```

"""

    if not context:
        formatted_context = f"""
# DESIGN TASK
Generate OpenSCAD code for: {prompt}

{few_shot_examples}

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

{few_shot_examples}

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
    print("[DEBUG] Entered generate_code_with_openai", flush=True)
    try:
        # Get API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
            return generate_code_fallback(prompt, context)
            
        # Format context and prompt
        formatted_prompt = format_context_for_prompt(context, prompt)

        # DEBUG: Print the system and user prompt being sent to the LLM
        print("\n================ SYSTEM PROMPT ================\n")
        print(OPENSCAD_SYSTEM_PROMPT)
        print("\n================ USER PROMPT / CONTEXT ================\n")
        print(formatted_prompt)
        print("\n=======================================================\n")
        
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

def final_code_cleanup(code):
    """
    Final cleanup pass to fix common structural issues that might remain after extraction.
    """
    # First fix all modules with empty bodies
    code = re.sub(r'(module\s+\w+\s*\([^)]*\))\s*{\s*}\s*{', r'\1 {', code)
    
    # Fix syntax and structural issues
    
    # Fix empty blocks in modules with double closing braces pattern
    module_pattern = r'(module\s+\w+\s*\([^)]*\))\s*{\s*}\s*{(.*?)}\s*}'
    code = re.sub(module_pattern, r'\1 {\2}', code, flags=re.DOTALL)
    
    # Fix modules where there's a closing brace before the module body starts
    code = re.sub(r'(module\s+\w+\s*\([^)]*\))\s*}\s*{', r'\1 {', code)
    
    # Remove any empty blocks that are followed by valid blocks
    code = re.sub(r'}\s*{\s*}', r'}', code)
    
    # Fix empty blocks in modules
    pattern = r'(module\s+\w+\s*\([^)]*\))\s*{\s*}(\s*{)'
    while re.search(pattern, code):
        code = re.sub(pattern, r'\1\2', code)
    
    # Operations list for patterns
    operations = ['union', 'difference', 'intersection', 'translate', 'rotate', 'scale', 'mirror', 'hull', 'minkowski']
    
    # Fix empty operation bodies - replace with just the operation
    for op in operations:
        # Fix pattern where there's an empty block followed by a valid block
        pattern = rf'({op}\s*\([^)]*\))\s*{{\s*}}\s*{{(.*?)}}(\s*}})?'
        code = re.sub(pattern, r'\1 {\2}', code, flags=re.DOTALL)
        
        # Fix nested transforms with } { pattern
        pattern = rf'({op}\s*\([^)]*\))\s*}}\s*{{(.*?)}}'
        code = re.sub(pattern, r'\1 {\2}', code, flags=re.DOTALL)
    
    # Fix operations that have empty blocks - one more targeted fix 
    for op in operations:
        pattern = rf'({op}\s*\([^)]*\))\s*{{\s*}}\s*'
        code = re.sub(pattern, r'\1 {}\n', code)
    
    # Fix module definitions with empty bodies followed by content blocks
    pattern = r'(module\s+\w+\s*\([^)]*\))\s*{\s*}\s*(\{)'
    code = re.sub(pattern, r'\1 \2', code)
    
    # Fix operation bodies without braces on same line
    for op in operations:
        pattern = rf'({op}\s*\([^)]*\))\s*\n\s*(\{{)'
        code = re.sub(pattern, r'\1 \2', code)
    
    # Fix any leftover "{\n}" patterns
    code = re.sub(r'{\s*}', '{\n}', code)
    
    # Fix module definitions with empty body comments
    code = re.sub(r'(module\s+\w+\s*\([^)]*\))\s*{\s*//[^{]*\s*}\s*{', r'\1 {', code)
    
    # Fix nested transform operation with empty body
    pattern = r'(\w+\s*\([^)]*\))\s*{\s*}\s*(\w+\s*\([^)]*\))'
    code = re.sub(pattern, r'\1 \2', code)
    
    # Fix incorrect for loop syntax in OpenSCAD
    code = re.sub(r'for\s*\((\w+)\s*=\s*\[([^]]+)\]\)\s*{', r'for (\1 = [\2]) {', code)
    
    # Fix missing semicolons after variable assignments
    code = re.sub(r'(\$?\w+\s*=\s*[^;{]+)(?=\n)', r'\1;', code)
    
    # Fix incorrect bracket placement in for loops
    code = re.sub(r'for\s*\((.+?)\)\s*{(.+?)}\s*{', r'for (\1) {\2}', code, flags=re.DOTALL)
    
    # Fix incomplete rotations/translations
    code = re.sub(r'(rotate|translate)\s*\(\[([^,\]]+)(?:,\s*[^,\]]+)?\]\)', r'\1([\2, 0, 0])', code)
    code = re.sub(r'(rotate|translate)\s*\(\[([^,\]]+),\s*([^,\]]+)\]\)', r'\1([\2, \3, 0])', code)
    
    # Fix the "} {" pattern which should be just "{"
    code = re.sub(r'}\s*{', '{\n', code)
    
    # Fix trailing descriptions and comments
    code = re.sub(r'\n\nThis OpenSCAD code.*$', '', code, flags=re.DOTALL)
    
    # Ensure we have proper semicolons after vector/array definitions
    code = re.sub(r'(\$?\w+\s*=\s*\[[^\]]*\])(?=\n)', r'\1;', code)
    
    return code

def extract_scad_code(text):
    """Extract valid OpenSCAD code from a potentially mixed text."""
    # First, remove obvious non-code sections
    # Remove markdown formatting completely
    text = re.sub(r'```(?:openscad|scad)?|\s*```', '', text)
    
    # Remove any debug/error message lines
    lines = text.split('\n')
    cleaned_lines = []
    skip_line = False
    
    # Patterns that indicate non-code content
    non_code_patterns = [
        r'previous code had issues',
        r'empty (?:module|operation) body',
        r'the code',
        r'please fix',
        r'regenerate',
        r'focusing on',
        r'implementation requirements',
        r'openscad code',
        r'design task',
        r'purpose:',
        r'considerations:',
        r'this openscad code defines',
        r'this is a 3d model',
        r'let me know if you',
        r'this design',
        r'parameters can be',
        r'you can modify',
        r'the parameters',
        r'customizable parameters',
        r'here is an implementation',
        r'this (?:creates|generates|implements)',
        r'important notes',
        r'note:',
        r'explanation:',
        r'instructions:',
        r'implementation details',
        r'usage:',
    ]
    
    # Skip header lines that match these patterns
    for line in lines:
        # Skip lines that look like prompts or feedback for the LLM
        if any(re.search(pattern, line.lower()) for pattern in non_code_patterns):
            continue
            
        # Skip module/file hierarchy comments 
        if re.match(r'^(?:module|file) hierarchy', line.strip()):
            continue
            
        # Skip lines that are just dashes/bullets or purely descriptive
        if re.match(r'^[-•*]|^\d+\.\s', line.strip()):
            continue
            
        # Skip lines that look like prose (sentences with periods)
        if re.match(r'^[A-Z][^.;{]*\.$', line.strip()):
            continue
            
        # Keep the line if it passed all filters
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Remove any explanatory text blocks at the beginning or end
    # These often contain phrases like "design task" or explanations
    explanation_patterns = [
        r'^.*design task:.*?\n\n',
        r'^.*purpose:.*?\n\n',
        r'^.*considerations:.*?\n\n',
        r'\n\nThis OpenSCAD code.*$',
        r'^.*I\'ve created.*?\n\n',
        r'^.*Here\'s the.*?\n\n',
        r'^.*First, let\'s.*?\n\n',
        r'^.*Let me create.*?\n\n',
    ]
    
    for pattern in explanation_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any empty module/operation body comments that were inserted
    text = re.sub(r'{\s*//\s*Empty (?:module|operation) body\s*}', '{\n}', text)
    
    # Ensure the top of the file looks like OpenSCAD code
    if not (text.strip().startswith("//") or 
            text.strip().startswith("/*") or 
            text.strip().startswith("module") or 
            text.strip().startswith("function") or
            text.strip().startswith("use") or
            text.strip().startswith("include") or
            text.strip().startswith("$fn")):
        
        # Try to find where the actual code starts
        code_markers = ["module", "function", "$fn", "use <", "include <", "// Parameters"]
        for marker in code_markers:
            if marker in text:
                text = text[text.find(marker):]
                break
    
    # Add $fn parameter if missing for models with curved surfaces
    if ('cylinder' in text or 'sphere' in text or 'circle' in text) and '$fn' not in text:
        text = '$fn = 100; // Smoothness for curved surfaces\n\n' + text
    
    # Fix module definitions with "module" keyword repeated
    text = re.sub(r'module\s+module\s+', 'module ', text)
    
    # Fix operation names used as variable names - this breaks OpenSCAD
    operation_keywords = ['union', 'difference', 'intersection', 'translate', 'rotate', 'scale', 
                         'mirror', 'hull', 'minkowski', 'linear_extrude', 'rotate_extrude', 'color']
    
    for keyword in operation_keywords:
        # Find variable assignments for operation keywords
        pattern = rf'(\b{keyword}\s*=\s*[^;]+;)'
        for match in re.finditer(pattern, text):
            # Replace with a prefixed version
            old = match.group(1)
            new = old.replace(f"{keyword} =", f"var_{keyword} =")
            text = text.replace(old, new)
    
    # Final cleanup: remove any trailing prose description
    lines = text.split('\n')
    last_code_line = 0
    
    # Find the last line that looks like code
    for i, line in enumerate(lines):
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("//") and any(char in cleaned for char in ";{}()[]"):
            last_code_line = i
            
    # If we found a sensible last code line, truncate there
    if last_code_line > 0 and last_code_line < len(lines) - 1:
        lines = lines[:last_code_line + 1]
        
    # Collect remaining code that looks valid
    text = '\n'.join(lines)
    
    # Fix remaining syntax issues
    
    # Fix pairs of parentheses/brackets/braces
    open_close_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
    for open_char, close_char in open_close_pairs:
        # Count occurrences
        open_count = text.count(open_char)
        close_count = text.count(close_char)
        
        # Fix missing closing parentheses/brackets
        if open_count > close_count:
            text += '\n' + (close_char * (open_count - close_count))
    
    # Apply the final cleanup to fix structural issues
    return final_code_cleanup(text) 
    return final_code_cleanup(text) 