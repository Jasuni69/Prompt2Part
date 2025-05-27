import os
import chromadb
import json
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
import glob
import re
from typing import Dict, List, Tuple, Set

load_dotenv()

CHROMA_DIR = 'data/chroma_db'
COLLECTION_NAME = 'scad_chunks'
TOP_K = 15  # Increased for better context
MODEL = 'gpt-3.5-turbo'

# Enhanced library mappings with specific function names
LIBRARY_MAPPINGS = {
    'gear': {
        'libraries': ['BOSL/involute_gears.scad'],
        'functions': ['gear', 'gear2d'],
        'keywords': ['gear', 'tooth', 'teeth', 'involute', 'spur', 'module', 'pitch']
    },
    'thread': {
        'libraries': ['BOSL2/threading.scad', 'threads-scad/threads.scad'],
        'functions': ['threaded_rod', 'threaded_nut', 'metric_thread', 'thread_helix'],
        'keywords': ['thread', 'bolt', 'screw', 'metric', 'M8', 'M10', 'threaded']
    },
    'bearing': {
        'libraries': ['NopSCADlib/vitamins/bearing.scad', 'BOSL2/bearings.scad'],
        'functions': ['bearing', 'ball_bearing', 'thrust_bearing'],
        'keywords': ['bearing', 'ball', 'thrust', 'race', 'inner', 'outer']
    },
    'pulley': {
        'libraries': ['BOSL2/pulleys.scad', 'NopSCADlib/vitamins/pulley.scad'],
        'functions': ['pulley', 'timing_pulley', 'GT2_pulley'],
        'keywords': ['pulley', 'belt', 'timing', 'GT2', 'tooth']
    },
    'spring': {
        'libraries': ['BOSL2/springs.scad', 'NopSCADlib/vitamins/spring.scad'],
        'functions': ['spring', 'coil_spring', 'compression_spring'],
        'keywords': ['spring', 'coil', 'compression', 'tension', 'helical']
    },
    'electronic': {
        'libraries': ['OpenSCAD-Snippet/Asset_SCAD/Resistor.scad', 'OpenSCAD-Snippet/Asset_SCAD/Transistor.scad', 'OpenSCAD-Snippet/Asset_SCAD/Led_01.scad'],
        'functions': ['Resistor', 'Transistor', 'Led_01'],
        'keywords': ['resistor', 'transistor', 'led', 'electronic', 'component', 'circuit', 'capacitor', 'diode']
    },
    'screw': {
        'libraries': ['NopSCADlib/vitamins/screw.scad'],
        'functions': ['screw', 'screw_and_washer', 'screw_countersink'],
        'keywords': ['screw', 'bolt', 'fastener', 'cap', 'socket', 'hex', 'countersink', 'M3', 'M4', 'M5', 'M6', 'M8']
    },
    'nut': {
        'libraries': ['NopSCADlib/vitamins/nut.scad'],
        'functions': ['nut', 'nut_and_washer', 'wing_nut'],
        'keywords': ['nut', 'hex', 'wing', 'nyloc', 'lock', 'fastener']
    },
    'washer': {
        'libraries': ['NopSCADlib/vitamins/washer.scad'],
        'functions': ['washer', 'penny_washer', 'star_washer'],
        'keywords': ['washer', 'penny', 'star', 'spring', 'flat']
    },
    'microswitch': {
        'libraries': ['NopSCADlib/vitamins/microswitch.scad'],
        'functions': ['microswitch', 'microswitch_hole_positions'],
        'keywords': ['microswitch', 'switch', 'limit', 'button', 'lever', 'endstop']
    },
    'motor': {
        'libraries': ['NopSCADlib/vitamins/stepper_motor.scad', 'NopSCADlib/vitamins/servo_motor.scad'],
        'functions': ['stepper_motor', 'servo_motor', 'NEMA'],
        'keywords': ['motor', 'stepper', 'servo', 'NEMA', 'NEMA17', 'NEMA23', 'actuator']
    },
    'pcb': {
        'libraries': ['NopSCADlib/vitamins/pcb.scad'],
        'functions': ['pcb', 'pcb_component', 'pcb_hole_positions'],
        'keywords': ['pcb', 'board', 'circuit', 'arduino', 'raspberry', 'pi', 'breadboard']
    },
    'connector': {
        'libraries': ['NopSCADlib/vitamins/d_connector.scad', 'NopSCADlib/vitamins/pin_header.scad'],
        'functions': ['d_connector', 'pin_header', 'box_header'],
        'keywords': ['connector', 'header', 'pin', 'socket', 'plug', 'jack', 'usb', 'hdmi']
    },
    'terminal': {
        'libraries': ['NopSCADlib/vitamins/terminal.scad', 'NopSCADlib/vitamins/green_terminals.scad'],
        'functions': ['terminal', 'green_terminal', 'terminal_block'],
        'keywords': ['terminal', 'block', 'screw', 'wire', 'connection']
    },
    'potentiometer': {
        'libraries': ['NopSCADlib/vitamins/potentiometer.scad'],
        'functions': ['potentiometer', 'pot'],
        'keywords': ['potentiometer', 'pot', 'variable', 'resistor', 'knob', 'dial']
    },
    'transformer': {
        'libraries': ['NopSCADlib/vitamins/transformer.scad'],
        'functions': ['transformer'],
        'keywords': ['transformer', 'power', 'supply', 'voltage', 'ac', 'dc']
    },
    'insert': {
        'libraries': ['NopSCADlib/vitamins/insert.scad'],
        'functions': ['insert', 'insert_hole', 'threaded_insert'],
        'keywords': ['insert', 'threaded', 'brass', 'heat', 'set']
    },
    'pillar': {
        'libraries': ['NopSCADlib/vitamins/pillar.scad'],
        'functions': ['pillar', 'hex_pillar', 'nylon_pillar'],
        'keywords': ['pillar', 'standoff', 'spacer', 'hex', 'nylon', 'support']
    },
    'rail': {
        'libraries': ['NopSCADlib/vitamins/rail.scad', 'NopSCADlib/vitamins/sbr_rail.scad'],
        'functions': ['rail', 'sbr_rail', 'linear_rail'],
        'keywords': ['rail', 'linear', 'guide', 'sbr', 'mgn', 'carriage']
    },
    'rod': {
        'libraries': ['NopSCADlib/vitamins/rod.scad'],
        'functions': ['rod', 'smooth_rod', 'threaded_rod'],
        'keywords': ['rod', 'smooth', 'shaft', 'linear', 'guide']
    },
    'tube': {
        'libraries': ['NopSCADlib/vitamins/tubing.scad'],
        'functions': ['tubing', 'tube'],
        'keywords': ['tube', 'tubing', 'pipe', 'hose', 'pneumatic']
    },
    'wire': {
        'libraries': ['NopSCADlib/vitamins/wire.scad'],
        'functions': ['wire', 'ribbon_cable'],
        'keywords': ['wire', 'cable', 'ribbon', 'conductor', 'insulation']
    },
    'ziptie': {
        'libraries': ['NopSCADlib/vitamins/ziptie.scad'],
        'functions': ['ziptie', 'ziptie_holes'],
        'keywords': ['ziptie', 'cable', 'tie', 'strap', 'fastener']
    }
}

def preprocess_prompt(user_prompt: str) -> str:
    """Enhanced prompt preprocessing with better library mapping."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Warning: No OpenAI API key found, skipping prompt preprocessing")
        return user_prompt
    
    # Enhanced system prompt with more specific mappings
    system_prompt = f"""You are a prompt preprocessor for an OpenSCAD code generation system.

Transform prompts into technical terms that match OpenSCAD library functions.

CRITICAL LIBRARY MAPPINGS:
{chr(10).join([f"- {k.title()}: use {v['libraries'][0]} with functions {v['functions'][:2]}" for k, v in LIBRARY_MAPPINGS.items()])}

Rules:
1. Keep output under 30 words
2. Use exact function names when possible
3. Mention specific libraries (BOSL, BOSL2, NopSCADlib)
4. Preserve dimensions and parameters
5. Focus on geometric/mechanical terms

Examples:
"gear with 20 teeth" → "gear(mm_per_tooth, 20) using BOSL involute_gears"
"M8 bolt" → "threaded_rod M8 using BOSL2 threading"
"timing belt pulley" → "timing_pulley GT2 using BOSL2 pulleys"
"ball bearing" → "ball_bearing using NopSCADlib vitamins"
"resistor" → "Resistor() using OpenSCAD-Snippet electronic components"
"30mm cube" → "cube(30)" (already correct)
"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=80,
            temperature=0.1
        )
        processed_prompt = response.choices[0].message.content.strip()
        
        print(f"🔄 Enhanced preprocessing:")
        print(f"   Original: {user_prompt}")
        print(f"   Optimized: {processed_prompt}")
        
        return processed_prompt
        
    except Exception as e:
        print(f"Warning: Prompt preprocessing failed ({e}), using original prompt")
        return user_prompt

def identify_component_type(prompt: str) -> str:
    """Identify the main component type from the prompt."""
    prompt_lower = prompt.lower()
    
    for component_type, config in LIBRARY_MAPPINGS.items():
        if any(keyword in prompt_lower for keyword in config['keywords']):
            return component_type
    
    return 'generic'

def get_preferred_libraries(component_type: str) -> List[str]:
    """Get preferred libraries for a component type."""
    if component_type in LIBRARY_MAPPINGS:
        return LIBRARY_MAPPINGS[component_type]['libraries']
    return []

def get_preferred_functions(component_type: str) -> List[str]:
    """Get preferred functions for a component type."""
    if component_type in LIBRARY_MAPPINGS:
        return LIBRARY_MAPPINGS[component_type]['functions']
    return []

def load_symbol_index(index_file="available_modules.json"):
    """Load the symbol index with enhanced error handling."""
    try:
        with open(index_file, "r") as f:
            data = json.load(f)
            print(f"📚 Loaded symbol index: {len(data.get('modules', []))} modules, {len(data.get('functions', []))} functions")
            return data
    except Exception as e:
        print(f"Could not load symbol index: {e}")
        return {"modules": [], "functions": [], "module_files": [], "function_files": []}

def filter_context_by_component(context: str, component_type: str, preferred_functions: List[str]) -> str:
    """Filter RAG context to prioritize relevant component examples."""
    if component_type == 'generic':
        return context
    
    blocks = context.split('\n\n')
    relevant_blocks = []
    fallback_blocks = []
    
    for block in blocks:
        block_lower = block.lower()
        
        # High priority: contains preferred functions
        if any(func in block_lower for func in preferred_functions):
            relevant_blocks.append(block)
        # Medium priority: contains component keywords
        elif component_type in LIBRARY_MAPPINGS and any(keyword in block_lower for keyword in LIBRARY_MAPPINGS[component_type]['keywords']):
            fallback_blocks.append(block)
    
    # Return relevant blocks first, then fallback blocks if needed
    filtered_blocks = relevant_blocks + fallback_blocks[:3]  # Limit fallback
    
    if filtered_blocks:
        result = '\n\n'.join(filtered_blocks)
        print(f"🎯 Filtered context: {len(relevant_blocks)} relevant + {len(fallback_blocks[:3])} fallback blocks")
        return result
    else:
        print("⚠️  No component-specific context found, using original")
        return context

def extract_called_symbols(code: str) -> Set[str]:
    """Extract all function/module calls from generated code."""
    # Find all module and function calls
    pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    calls = set(re.findall(pattern, code))
    return calls

def validate_symbols_against_index(code: str, symbol_index: Dict) -> Tuple[Set[str], Set[str]]:
    """Validate that called symbols exist in the symbol index."""
    called_symbols = extract_called_symbols(code)
    available_symbols = set(symbol_index.get("modules", [])) | set(symbol_index.get("functions", []))
    
    # OpenSCAD built-in primitives (always available)
    builtin_primitives = {
        'cube', 'sphere', 'cylinder', 'polyhedron', 'polygon', 'circle', 'square',
        'linear_extrude', 'rotate_extrude', 'hull', 'minkowski', 'union', 'difference', 'intersection',
        'translate', 'rotate', 'scale', 'mirror', 'resize', 'color', 'echo', 'assert'
    }
    
    valid_symbols = (called_symbols & available_symbols) | (called_symbols & builtin_primitives)
    invalid_symbols = called_symbols - available_symbols - builtin_primitives
    
    return valid_symbols, invalid_symbols

def generate_use_statements(code: str, symbol_index: Dict, component_type: str) -> str:
    """Generate minimal use statements based on called functions and component type."""
    called_symbols = extract_called_symbols(code)
    
    # Build symbol-to-file mapping
    symbol_to_files = {}
    for entry in symbol_index.get("module_files", []) + symbol_index.get("function_files", []):
        symbol_name = entry.get("name", "")
        file_path = entry.get("file", "")
        if symbol_name and file_path:
            if symbol_name not in symbol_to_files:
                symbol_to_files[symbol_name] = []
            symbol_to_files[symbol_name].append(file_path)
    
    needed_files = set()
    
    # Add files for called symbols
    for symbol in called_symbols:
        if symbol in symbol_to_files:
            # Prefer component-specific libraries
            files = symbol_to_files[symbol]
            preferred_libs = get_preferred_libraries(component_type)
            
            # Try to find a preferred library first
            preferred_file = None
            for lib in preferred_libs:
                for file_path in files:
                    if lib in file_path:
                        preferred_file = file_path
                        break
                if preferred_file:
                    break
            
            if preferred_file:
                needed_files.add(preferred_file)
            else:
                # Fall back to first available file
                needed_files.add(files[0])
    
    # Generate use statements
    use_statements = []
    for file_path in sorted(needed_files):
        # Ensure proper scad_library/ prefix
        if not file_path.startswith('scad_library/'):
            file_path = f'scad_library/{file_path}'
        use_statements.append(f'use <{file_path}>;')
    
    return '\n'.join(use_statements)

def generate_openscad_code_improved(user_query: str) -> str:
    """Improved OpenSCAD code generation with better component handling."""
    
    # Step 1: Enhanced preprocessing
    optimized_query = preprocess_prompt(user_query)
    
    # Step 2: Identify component type
    component_type = identify_component_type(optimized_query)
    preferred_functions = get_preferred_functions(component_type)
    
    print(f"🔍 Component type: {component_type}")
    if preferred_functions:
        print(f"🎯 Preferred functions: {preferred_functions}")
    
    # Step 3: RAG retrieval
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('Please set the OPENAI_API_KEY environment variable.')
    
    client = OpenAI(api_key=api_key)
    client_chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client_chroma.get_collection(COLLECTION_NAME)
    
    # Embed optimized query
    response = client.embeddings.create(
        input=[optimized_query],
        model="text-embedding-ada-002"
    )
    query_embedding = response.data[0].embedding
    
    # Retrieve relevant chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas"]
    )
    
    # Build and filter context
    context = "\n\n".join(
        f"// Reference {i+1}: {meta['chunk_file']} [sub-chunk {meta['sub_chunk_index']}]:\n{doc}"
        for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]))
    )
    
    filtered_context = filter_context_by_component(context, component_type, preferred_functions)
    
    # Step 4: Enhanced system prompt
    symbol_index = load_symbol_index()
    
    if component_type != 'generic' and preferred_functions:
        system_prompt = f"""You are an expert OpenSCAD code generator specializing in {component_type} components.

CRITICAL: For {component_type} components, you MUST use these functions: {', '.join(preferred_functions[:3])}

Available libraries for {component_type}:
{chr(10).join([f"- {lib}" for lib in get_preferred_libraries(component_type)[:3]])}

Rules:
1. Use ONLY the specified functions for {component_type} components
2. Never use generic functions like A() or undefined functions
3. Follow the exact syntax from the reference code
4. Output only valid OpenSCAD code with no explanations
5. Preserve all user-specified parameters (teeth, module, dimensions)

Example for gear: gear(mm_per_tooth=5, number_of_teeth=20) NOT A(teeth, module)
"""
    else:
        system_prompt = """You are an expert OpenSCAD code generator.
Use only built-in OpenSCAD primitives or functions shown in the reference code.
Never invent functions. Output only valid OpenSCAD code with no explanations."""
    
    # Step 5: Generate code
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Reference code:\n{filtered_context}\n\nUser request: {user_query}\n\nOpenSCAD code:"}
    ]
    
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,  # Lower temperature for more consistent results
        max_tokens=512
    )
    
    generated_code = completion.choices[0].message.content.strip()
    
    # Step 6: Validation and use statement generation
    valid_symbols, invalid_symbols = validate_symbols_against_index(generated_code, symbol_index)
    
    if invalid_symbols:
        print(f"⚠️  Invalid symbols detected: {invalid_symbols}")
        # Try to suggest corrections
        suggestions = []
        for invalid_sym in invalid_symbols:
            if component_type in LIBRARY_MAPPINGS:
                preferred = LIBRARY_MAPPINGS[component_type]['functions']
                if preferred:
                    suggestions.append(f"// Consider using {preferred[0]}() instead of {invalid_sym}()")
        
        if suggestions:
            generated_code = '\n'.join(suggestions) + '\n\n' + generated_code
    
    # Step 7: Generate appropriate use statements
    use_statements = generate_use_statements(generated_code, symbol_index, component_type)
    
    # Step 8: Combine final code
    if use_statements:
        final_code = f"{use_statements}\n\n{generated_code}"
    else:
        final_code = generated_code
    
    print(f"✅ Generated {len(final_code)} characters of code")
    return final_code

# Backward compatibility
def generate_openscad_code(user_query: str) -> str:
    """Wrapper for backward compatibility."""
    return generate_openscad_code_improved(user_query) 