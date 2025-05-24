import os
import re
import json
from pathlib import Path
from rag.retriever import retrieve_context
from models.local_llm import generate_code, extract_scad_code
from scad.validator import validate_scad_code, fix_common_issues, analyze_model_complexity
import datetime

class ScadGenerator:
    def __init__(self, output_dir='generated', model=None, temperature=0.2):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.model = model
        self.temperature = temperature
        
    def preprocess_prompt(self, prompt):
        """
        Clean up and enhance the user prompt with manufacturing considerations.
        Extract key parameters, standardize units, etc.
        """
        # Extract goals and purpose from the prompt
        design_purpose = "general purpose"
        if "for" in prompt.lower():
            purpose_match = re.search(r'for\s+(\w+(?:\s+\w+){0,3})', prompt.lower())
            if purpose_match:
                design_purpose = purpose_match.group(1)
                
        # Add manufacturing method if not specified
        manufacturing_methods = ["3d printing", "3d printed", "cnc", "laser cut", "injection molded", "cast"]
        has_manufacturing = any(method in prompt.lower() for method in manufacturing_methods)
        
        if not has_manufacturing:
            # Default to 3D printing if not specified
            enhanced_prompt = f"{prompt} (designed for 3D printing)"
        else:
            enhanced_prompt = prompt
        
        # Add units if numbers without units are found
        # E.g., "Create a box 10x20x5" -> "Create a box 10mm x 20mm x 5mm"
        def add_units(match):
            value = match.group(1)
            return f"{value}mm"
            
        # Look for dimensions without units
        pattern = r'(\d+(?:\.\d+)?)\s*(?=x|\s|$)(?![a-zA-Z])'
        enhanced_prompt = re.sub(pattern, add_units, enhanced_prompt)
        
        # Extract specific mechanical requirements
        mechanical_features = []
        if "strong" in enhanced_prompt.lower() or "strength" in enhanced_prompt.lower():
            mechanical_features.append("structural strength")
        if "water" in enhanced_prompt.lower() or "waterproof" in enhanced_prompt.lower():
            mechanical_features.append("water resistance")
        if "snap" in enhanced_prompt.lower() or "clip" in enhanced_prompt.lower():
            mechanical_features.append("snap-fit connections")
        if "thread" in enhanced_prompt.lower() or "screw" in enhanced_prompt.lower():
            mechanical_features.append("threaded connections")
            
        # Return the enhanced prompt along with extracted features
        return {
            "prompt": enhanced_prompt,
            "design_purpose": design_purpose,
            "mechanical_features": mechanical_features
        }
    
    def craft_design_prompt(self, prompt_info, use_rag=True):
        """Create a comprehensive design prompt with manufacturing considerations."""
        base_prompt = prompt_info["prompt"]
        design_purpose = prompt_info["design_purpose"]
        mechanical_features = prompt_info["mechanical_features"]
        
        # Start with the base prompt
        enhanced_prompt = f"Design task: {base_prompt}\n\n"
        
        # Add purpose section
        enhanced_prompt += f"Purpose: Create a functional, manufacturable design for {design_purpose}.\n\n"
        
        # Add mechanical considerations
        enhanced_prompt += "Design considerations:\n"
        
        if "3d print" in base_prompt.lower():
            enhanced_prompt += """
- Design for 3D printing with appropriate wall thickness (minimum 1.2mm)
- Avoid overhangs greater than 45° without supports
- Add fillets to stress points (min 0.5mm radius) and sharp corners
- Consider print orientation in the design
"""
        elif "cnc" in base_prompt.lower():
            enhanced_prompt += """
- Design for CNC machining with accessible features
- Avoid internal sharp corners (use fillets of minimum 1mm)
- Consider tool access and fixturing in the design
- Maintain uniform wall thickness where possible
"""
        elif "injection" in base_prompt.lower():
            enhanced_prompt += """
- Design for injection molding with draft angles (1-2°)
- Maintain uniform wall thickness (ideally 1.5-3mm)
- Avoid thick sections that may cause sink marks
- Add appropriate fillets to all edges
"""
        else:
            # Default manufacturing considerations
            enhanced_prompt += """
- Use appropriate wall thickness for structural integrity
- Add fillets to stress points and sharp corners
- Design for ease of manufacturing and assembly
- Consider material properties in the design
"""
        
        # Add specific mechanical requirements
        if mechanical_features:
            enhanced_prompt += "\nSpecific mechanical requirements:\n"
            for feature in mechanical_features:
                if feature == "structural strength":
                    enhanced_prompt += "- Reinforce structure with ribs or gussets where needed\n"
                elif feature == "water resistance":
                    enhanced_prompt += "- Include proper sealing features and overlapping joints\n"
                elif feature == "snap-fit connections":
                    enhanced_prompt += "- Design appropriate snap features with correct interference\n"
                elif feature == "threaded connections":
                    enhanced_prompt += "- Include thread features with standard sizes and proper clearances\n"
        
        # Add parametric design guidance
        enhanced_prompt += """
Implementation requirements:
- Use a fully parametric approach with all dimensions as variables
- Include clear comments explaining design decisions
- Organize code with logical module hierarchy
- Use appropriate OpenSCAD features efficiently
"""
        
        return enhanced_prompt
    
    def postprocess_code(self, code):
        """
        Clean up and enhance the generated code.
        Fix common issues and ensure best practices.
        """
        # Apply the fix_common_issues function
        cleaned_code = fix_common_issues(code)
        
        # Analyze the complexity of the model
        complexity_analysis = analyze_model_complexity(cleaned_code)
        
        # Add header comment with complexity information and recommendations
        header = f"""// OpenSCAD Model
// Generated with AI assistance
// Complexity: {complexity_analysis["complexity_score"]:.1f} ({complexity_analysis["render_time_estimate"]} render)
// Structure: {complexity_analysis["modules_count"]} modules, {complexity_analysis["primitives_count"]} primitives, {complexity_analysis["operations_count"]} boolean operations

"""
        
        # Add recommendations as comments
        if complexity_analysis["recommendations"]:
            header += "// Recommendations:\n"
            for rec in complexity_analysis["recommendations"]:
                header += f"// - {rec}\n"
            header += "\n"
            
        # Add the clean code
        result = header + cleaned_code
        
        # Remove empty union blocks
        result = re.sub(r'union\s*\(\s*\)\s*;?', '', result)
        result = re.sub(r'union\s*\{\s*\}', '', result)
        
        return result
    
    def balance_delimiters(self, code):
        """
        Balance delimiters (braces, parentheses, brackets) in the code.
        This is a last-resort fix for unbalanced delimiters that completely break the code.
        """
        # Track opening and closing counts
        delimiters = {
            '{': '}',
            '[': ']',
            '(': ')'
        }
        
        # Count each delimiter
        counts = {c: 0 for c in delimiters.keys()}
        counts.update({c: 0 for c in delimiters.values()})
        
        for char in code:
            if char in counts:
                counts[char] += 1
            
        # Check for imbalance
        fixed_code = code
        for opener, closer in delimiters.items():
            # Add missing closing delimiters
            while counts[opener] > counts[closer]:
                fixed_code += closer
                counts[closer] += 1
            
            # Add missing opening delimiters at the beginning
            # This is a bit risky but better than unbalanced code
            while counts[closer] > counts[opener]:
                fixed_code = opener + fixed_code
                counts[opener] += 1
        
        return fixed_code

    def ensure_valid_structure(self, code):
        """
        Ensure the generated code has the minimum required structure
        and fix common errors that might cause rendering issues.
        
        Args:
            code (str): The generated OpenSCAD code
            
        Returns:
            str: Corrected OpenSCAD code
        """
        # If the code is completely empty or minimal, replace with a fallback
        if not code or len(code.strip()) < 10:
            return """
            // Fallback simple model
            $fn = 100;
            cylinder(h=10, r=5);
            """
        
        # Create a copy for modifications
        fixed_code = code
        
        # Fix empty modules - add empty body if completely missing
        module_pattern = r'(module\s+\w+\s*\([^)]*\))\s*;'
        fixed_code = re.sub(module_pattern, r'\1 {}', fixed_code)
        
        # Fix modules with missing body opening brace
        module_pattern = r'(module\s+\w+\s*\([^)]*\))\s*(?!\{)'
        fixed_code = re.sub(module_pattern, r'\1 {', fixed_code)
        
        # Function pattern - fix functions without return values
        function_pattern = r'(function\s+\w+\s*\([^)]*\))\s*;\s*(?!\=)'
        fixed_code = re.sub(function_pattern, r'\1 = 0;', fixed_code)
        
        # Add closing braces where needed - count opening and closing
        braces_open = fixed_code.count('{')
        braces_close = fixed_code.count('}')
        
        if braces_open > braces_close:
            # Add missing closing braces
            fixed_code += '\n' + ('}' * (braces_open - braces_close))
            
        # Fix incorrect vector syntax often used by LLMs <1,2,3> -> [1,2,3]
        vector_pattern = r'<([^<>]+),\s*([^<>]+),\s*([^<>]+)>'
        
        for match in re.finditer(vector_pattern, fixed_code):
            old = match.group(0)
            x, y, z = match.group(1), match.group(2), match.group(3)
            new = f'[{x}, {y}, {z}]'
            fixed_code = fixed_code.replace(old, new)
            
        # Fix incorrect angle bracket syntax in conditional expressions
        fixed_code = re.sub(r'(\w+)\s*<\s*(\w+)', r'\1 < \2', fixed_code)
        fixed_code = re.sub(r'(\w+)\s*>\s*(\w+)', r'\1 > \2', fixed_code)
        
        # Fix partial vector definitions in translations and rotations
        fixed_code = re.sub(r'(translate|rotate)\s*\(\[([^,\]]+)\]\)', r'\1([\2, 0, 0])', fixed_code)
        fixed_code = re.sub(r'(translate|rotate)\s*\(\[([^,\]]+),\s*([^,\]]+)\]\)', r'\1([\2, \3, 0])', fixed_code)
        
        # Fix incorrect loop syntax that LLMs sometimes generate
        # Fix Python-style for loops: for i in range(0, 10) -> for(i=[0:1:9])
        range_pattern = r'for\s*\(\s*(\w+)\s+in\s+range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*\)'
        fixed_code = re.sub(range_pattern, r'for(\1 = [\2 : 1 : \3-1])', fixed_code)
        
        # Fix for var in array -> for(var=array)
        in_pattern = r'for\s*\(\s*(\w+)\s+in\s+(\[.*?\]|\w+)\s*\)'
        fixed_code = re.sub(in_pattern, r'for(\1 = \2)', fixed_code)
        
        # Fix for loops with missing parentheses
        for_pattern = r'for\s+(\w+)\s*=\s*(\[[^\]]+\])'
        fixed_code = re.sub(for_pattern, r'for(\1 = \2)', fixed_code)
        
        # Fix Python-like list comprehensions in OpenSCAD
        list_comp_pattern = r'\[\s*([^:\[\]]+)\s+for\s+(\w+)\s+in\s+(\[[^\]]+\])\s*\]'
        
        for match in re.finditer(list_comp_pattern, fixed_code):
            expr, var, range_expr = match.groups()
            replacement = f'[for ({var} = {range_expr}) {expr}]'
            fixed_code = fixed_code.replace(match.group(0), replacement)
        
        # Remove comments that repeat immediately - common in LLM output
        fixed_code = re.sub(r'(\/\/[^\n]*)\n\1', r'\1', fixed_code)
        
        # Ensure we have $fn parameter for models with curved surfaces
        if ('cylinder' in fixed_code or 'sphere' in fixed_code or 'circle' in fixed_code) and '$fn' not in fixed_code:
            fixed_code = '$fn = 100; // Smoothness of curved surfaces\n\n' + fixed_code
            
        # Fix missing semicolons at the end of assignments
        fixed_code = re.sub(r'(\$?\w+\s*=\s*[^;{]+)(?=\n)', r'\1;', fixed_code)
        
        # Fix common variable name issues
        if 'heigth' in fixed_code:
            fixed_code = fixed_code.replace('heigth', 'height')
        if 'widht' in fixed_code:
            fixed_code = fixed_code.replace('widht', 'width')
        if 'lenght' in fixed_code:
            fixed_code = fixed_code.replace('lenght', 'length')
        
        # Fix missing module calls at end of file
        # If no module is called, try to find the main module and call it
        main_modules = ['main', 'assemble', 'render_model']
        has_module_call = False
        
        for line in fixed_code.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not any(keyword in stripped for keyword in ['module', 'function', '=', 'include', 'use']):
                has_module_call = True
                break
                
        if not has_module_call:
            # Try to find the main module
            for module_name in main_modules:
                if re.search(rf'module\s+{module_name}\s*\(', fixed_code):
                    fixed_code += f'\n\n// Render the model\n{module_name}();'
                    break
            else:
                # Fallback: find the last defined module and call it 
                module_defs = re.findall(r'module\s+(\w+)\s*\([^)]*\)', fixed_code)
                if module_defs:
                    last_module = module_defs[-1]
                    fixed_code += f'\n\n// Render the model\n{last_module}();'
        
        # Final cleanup - remove trailing descriptions
        lines = fixed_code.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that look like prose descriptions
            if re.match(r'^[A-Z].*\.$', line.strip()):
                continue
            filtered_lines.append(line)
        
        fixed_code = '\n'.join(filtered_lines)
        
        # Ensure the code ends with a newline
        if not fixed_code.endswith('\n'):
            fixed_code += '\n'
        
        # Remove empty union blocks
        fixed_code = re.sub(r'union\s*\(\s*\)\s*;?', '', fixed_code)
        fixed_code = re.sub(r'union\s*\{\s*\}', '', fixed_code)
        
        return fixed_code

    def generate_improved_code(self, prompt, context, max_attempts=3, selected_libraries=None, output_file=None):
        """Generate code with improvement loop based on validation feedback."""
        last_code = None
        attempt = 0
        
        while attempt < max_attempts:
            # Add information about specific libraries if provided
            library_info = ""
            if selected_libraries:
                libraries = ", ".join(selected_libraries)
                library_info = f"\nPlease focus on using modules from these libraries: {libraries}.\n"
            
            # Generate initial code
            if attempt == 0:
                scad_code = generate_code(
                    prompt + library_info, 
                    context, 
                    model=self.model, 
                    temperature=self.temperature
                )
            else:
                # For subsequent attempts, create more specific feedback based on error type
                is_valid, message = validate_scad_code(last_code)
                
                # Customize feedback based on error type for more targeted improvements
                if "Unbalanced" in message:
                    feedback = f"The previous code had syntax errors: {message}\nPlease ensure all parentheses (), braces {{}}, and brackets [] are properly balanced and matched."
                elif "used before declaration" in message:
                    var_name = re.search(r"'([^']+)'", message)
                    var_name = var_name.group(1) if var_name else "variables"
                    feedback = f"The variable '{var_name}' was used before it was defined. Please ensure all variables are defined at the top of the file before they are used."
                elif "cylinder" in message and "syntax" in message:
                    feedback = "Incorrect cylinder syntax. Use named parameters: cylinder(h=height, r=radius) or cylinder(h=height, d=diameter), never just cylinder(radius, height)."
                elif "transform" in message or "translate" in message:
                    feedback = "Incorrect transform syntax. Use vector format: translate([x,y,z]), rotate([x,y,z]), etc. Never use translate(x,y,z) without brackets."
                elif "semicolon" in message:
                    feedback = "Syntax error with semicolons. End statements with semicolons, but don't place semicolons after function/module declarations before the opening brace."
                elif "No basic OpenSCAD primitives" in message:
                    feedback = "The code doesn't contain any basic OpenSCAD primitives (cube, sphere, cylinder, etc). Please include actual 3D shapes in the design."
                elif "function call before definition" in message:
                    feedback = "Function or module was called before it was defined. Make sure all functions and modules are defined before they are used."
                elif "OpenSCAD render error" in message:
                    feedback = f"The code failed to render in OpenSCAD with error: {message}\nPlease fix the syntax issues and ensure the code will run correctly."
                else:
                    feedback = f"The previous code had issues: {message}\nPlease fix and regenerate focusing on manufacturability, clean syntax, and best practices."
                
                # Add examples for common issues
                if "star_points" in last_code and ("star" in prompt.lower() or "points" in prompt.lower()):
                    feedback += "\n\nHere's a correct star_points function example:\n"
                    feedback += """function star_points(points, outer_r, inner_r) = 
    [for (i = [0:2*points-1])
        let(angle = i * 180 / points)
        (i % 2 == 0) ? 
            [outer_r * cos(angle), outer_r * sin(angle)] : 
            [inner_r * cos(angle), inner_r * sin(angle)]
    ];"""
                
                scad_code = generate_code(
                    prompt + library_info + "\n\n" + feedback, 
                    context, 
                    model=self.model, 
                    temperature=self.temperature
                )
            
            # Extract code from response if needed
            scad_code = extract_scad_code(scad_code)
            
            # Apply structural fixes before validation
            scad_code = self.ensure_valid_structure(scad_code)
            
            # Create preview directory if output file is specified
            preview_dir = None
            if output_file:
                # If output_file is a path, get the directory
                output_path = Path(output_file)
                if output_path.parent.exists():
                    preview_dir = str(output_path.parent)
                else:
                    preview_dir = str(self.output_dir)
            
            # Validate the generated code with preview on the final attempt
            generate_preview = (attempt == max_attempts - 1) or (attempt == 0)  # First and last attempts
            if generate_preview:
                is_valid, message, preview_path = validate_scad_code(
                    scad_code, 
                    check_with_openscad=True, 
                    generate_preview=True, 
                    preview_dir=preview_dir
                )
            else:
                is_valid, message = validate_scad_code(scad_code)
                preview_path = None
            
            # If valid or final attempt, apply common fixes and return
            if is_valid or attempt == max_attempts - 1:
                # Fix common issues automatically
                scad_code = self.postprocess_code(scad_code)
                
                # Save to file if path provided
                if output_file:
                    self.save_to_file(scad_code, output_file)
                    
                    # Save preview metadata
                    if preview_path:
                        preview_meta = {
                            "preview_image": preview_path,
                            "generated_at": str(datetime.datetime.now()),
                            "is_valid": is_valid
                        }
                        meta_path = Path(output_file).with_suffix('.preview.json')
                        with open(meta_path, 'w') as f:
                            json.dump(preview_meta, f, indent=2)
                
                result_message = message
                if preview_path:
                    result_message = f"{message} (Preview generated at {preview_path})"
                
                return scad_code, is_valid, result_message
            
            # Store code for feedback in next iteration
            last_code = scad_code
            attempt += 1
        
        # Should not reach here, but just in case
        return scad_code, False, "Max attempts reached without valid code."
        
    def generate_schema_representation(self, prompt):
        """
        Generate a structured JSON schema representation of the 3D model requirements.
        This intermediate step helps bridge user intent and implementation details.
        """
        schema_prompt = f"""
Based on this description: \"{prompt}\"
Generate a detailed structured JSON representation with these fields:
- object_type: Primary object to create (e.g., "box", "phone stand", "gear", etc.)
- dimensions: Key measurements in mm with sensible defaults
- features: List of specific features
- assembly_relationships: How parts connect to each other
- mechanical_properties: Structural considerations
- manufacturing_constraints: 3D printing constraints
- placement: Information about how parts should be positioned relative to each other
- physical_constraints: Required clearances, tolerances, and other physical properties

Format as valid JSON only. Do not include explanations outside the JSON.
Ensure dimensions have physically reasonable relationships (e.g., thickness < width).
"""
        # Generate the schema using an LLM
        schema_response = generate_code(
            schema_prompt, 
            context=None, 
            model=self.model, 
            temperature=0.1
        )
        # Extract JSON from the response
        try:
            # Find JSON in the response
            json_pattern = r'({[\s\S]*})'
            json_match = re.search(json_pattern, schema_response)
            if json_match:
                schema_json = json_match.group(1)
                schema = json.loads(schema_json)
                if not isinstance(schema, dict):
                    raise ValueError("Parsed schema is not a dict")
                # Ensure required fields exist and are dicts/lists as expected
                if 'dimensions' not in schema or not isinstance(schema['dimensions'], dict):
                    schema['dimensions'] = {}
                if 'features' not in schema or not isinstance(schema['features'], list):
                    schema['features'] = []
                if 'assembly_relationships' not in schema or not isinstance(schema['assembly_relationships'], list):
                    schema['assembly_relationships'] = []
                if 'physical_constraints' not in schema or not isinstance(schema['physical_constraints'], dict):
                    schema['physical_constraints'] = {
                        "min_wall_thickness": 1.2,
                        "clearance": 0.3,
                        "fillet_radius": 0.5
                    }
                return schema
        except Exception as e:
            print(f"Error parsing schema: {e}")
        # If we fail to parse JSON or no match was found, return a basic structure
        return {
            "object_type": "generic",
            "dimensions": {},
            "features": ["parametric"],
            "assembly_relationships": [],
            "mechanical_properties": ["solid"],
            "manufacturing_constraints": ["3D printable"],
            "placement": {},
            "physical_constraints": {
                "min_wall_thickness": 1.2,
                "clearance": 0.3,
                "fillet_radius": 0.5
            }
        }
    
    def schema_to_enhanced_prompt(self, original_prompt, schema):
        """
        Convert a schema representation to an enhanced prompt with explicit structure.
        """
        # Format the schema as a structured part of the prompt
        dimensions_text = ""
        if schema.get("dimensions"):
            dims = []
            for k, v in schema["dimensions"].items():
                dims.append(f"{k}: {v}mm")
            dimensions_text = ", ".join(dims)
        
        features_text = ", ".join(schema.get("features", []))
        constraints_text = ", ".join(schema.get("manufacturing_constraints", []))
        
        # Extract physical relationship information 
        placement_info = ""
        if schema.get("placement"):
            placement = []
            for k, v in schema.get("placement", {}).items():
                placement.append(f"{k}: {v}")
            if placement:
                placement_info = "\nPart placements: " + "; ".join(placement)
        
        # Extract assembly relationships
        assembly_info = ""
        if schema.get("assembly_relationships"):
            assembly_info = "\nAssembly relationships: " + "; ".join(schema.get("assembly_relationships", []))
        
        # Extract physical constraints
        physical_constraints = ""
        if schema.get("physical_constraints"):
            constraints = []
            for k, v in schema.get("physical_constraints", {}).items():
                constraints.append(f"{k}: {v}")
            if constraints:
                physical_constraints = "\nPhysical constraints: " + "; ".join(constraints)
        
        enhanced_prompt = f"""Design task: {original_prompt}

STRUCTURED DESIGN PARAMETERS:
Object type: {schema.get("object_type", "3D object")}
Dimensions: {dimensions_text if dimensions_text else "Use appropriate scaling"}
Required features: {features_text if features_text else "parametric, customizable"}
Manufacturing constraints: {constraints_text if constraints_text else "3D printable with min 1.2mm wall thickness"}{placement_info}{assembly_info}{physical_constraints}

Key requirements:
1. Generate complete, functional OpenSCAD code that can be rendered directly
2. Ensure all parts are properly positioned in 3D space with correct transforms
3. Use a clean, modular structure with separated components
4. Include common parameters that can be easily adjusted
5. Validate all dimensional relationships make physical sense
6. DO NOT include empty operation bodies or placeholder comments

Generate OpenSCAD code that implements this design with clean syntax and structure.
"""
        return enhanced_prompt
    
    def generate_scad_code(self, prompt, use_rag=True, selected_libraries=None, output_file=None, max_attempts=3):
        """
        Generate OpenSCAD code from a natural language prompt.
        
        Args:
            prompt (str): The user's prompt describing the 3D model
            use_rag (bool): Whether to use RAG for improved generation
            selected_libraries (list): Optional list of libraries to prioritize in retrieval
            output_file (str): Optional filename to save the generated code
            max_attempts (int): Maximum number of generation attempts
            
        Returns:
            tuple: (scad_code, is_valid, message)
        """
        try:
            # First generate a schema representation to better understand the design intent
            schema = self.generate_schema_representation(prompt)
            
            # Defensive: ensure schema is a dict
            if not isinstance(schema, dict):
                schema = {}

            # Create an enhanced prompt using the schema
            schema_enhanced_prompt = self.schema_to_enhanced_prompt(prompt, schema)
            
            # Preprocess the prompt with manufacturing considerations
            prompt_info = self.preprocess_prompt(schema_enhanced_prompt)
            
            # Create an enhanced design prompt
            enhanced_prompt = self.craft_design_prompt(prompt_info, use_rag)
            
            # Retrieve relevant context if RAG is enabled
            context = None
            if use_rag:
                # Add specific libraries from the schema 
                inferred_libraries = []
                obj_type = schema.get("object_type", "").lower() if isinstance(schema, dict) else ""
                features = [f.lower() for f in schema.get("features", [])] if isinstance(schema, dict) and isinstance(schema.get("features", []), list) else []
                
                # Infer libraries based on object type and features
                if "gear" in obj_type or "gear" in features:
                    inferred_libraries.extend(["MCAD", "BOSL2"])
                if "rounded" in features or "fillet" in features:
                    inferred_libraries.append("Round-Anything")
                if "thread" in features or "screw" in obj_type:
                    inferred_libraries.append("threads")
                if "case" in obj_type or "box" in obj_type or "enclosure" in obj_type:
                    inferred_libraries.append("YAPP_Box")
                
                # Combine with user-specified libraries
                if selected_libraries:
                    all_libraries = list(set(selected_libraries + inferred_libraries))
                else:
                    all_libraries = inferred_libraries
                
                context = retrieve_context(enhanced_prompt, selected_libraries=all_libraries if all_libraries else None)
            
            # Generate code with multiple attempts and feedback
            scad_code, is_valid, message = self.generate_improved_code(
                enhanced_prompt, 
                context, 
                max_attempts=max_attempts,
                selected_libraries=selected_libraries,
                output_file=output_file
            )
            
            # Save to file if requested
            if output_file:
                if not output_file.endswith('.scad'):
                    output_file += '.scad'
                
                file_path = self.output_dir / output_file
                with open(file_path, 'w') as f:
                    f.write(scad_code)
                
                # Also save metadata about the generation
                metadata = {
                    "original_prompt": prompt,
                    "enhanced_prompt": enhanced_prompt,
                    "schema": schema,
                    "libraries": selected_libraries,
                    "validation": {"is_valid": is_valid, "message": message},
                    "complexity": analyze_model_complexity(scad_code)
                }
                
                meta_path = file_path.with_suffix('.json')
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            return scad_code, is_valid, message
            
        except Exception as e:
            # Handle any unexpected errors during generation
            error_msg = str(e)
            print(f"Error in generate_scad_code: {error_msg}")
            
            # Create a basic fallback model with error information
            fallback_code = f"""// Error occurred during generation
// Error: {error_msg}
// Original prompt: {prompt}

// Fallback basic shape
$fn = 100;
cube(20, center=true);
"""
            return fallback_code, False, f"Generation error: {error_msg}"

# For backward compatibility
def generate_scad_code(prompt, use_rag=True, selected_libraries=None, output_file=None):
    """Legacy function for backwards compatibility."""
    generator = ScadGenerator()
    scad_code, is_valid, message = generator.generate_scad_code(prompt, use_rag, selected_libraries, output_file)
    return scad_code 