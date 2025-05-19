import os
import re
import json
from pathlib import Path
from rag.retriever import retrieve_context
from models.local_llm import generate_code, extract_scad_code
from scad.validator import validate_scad_code, fix_common_issues, analyze_model_complexity

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
        Perform a final validation pass to ensure the code has a valid structure.
        This fixes obvious syntax errors that would cause OpenSCAD to fail.
        """
        # First, balance all delimiters
        fixed_code = self.balance_delimiters(code)
        
        # Check for and fix incomplete module definitions
        # This pattern finds module declarations without a body
        module_pattern = r'(module\s+\w+\s*\([^)]*\)\s*(?!{))'
        fixed_code = re.sub(module_pattern, r'\1 {\n    // Empty module body\n}', fixed_code)
        
        # Fix incomplete function declarations
        function_pattern = r'(function\s+\w+\s*\([^)]*\)\s*(?!=))'
        fixed_code = re.sub(function_pattern, r'\1 = 0; // Default return value', fixed_code)
        
        # Fix dangling operations (transform or boolean ops without body)
        ops = ['union', 'difference', 'intersection', 'translate', 'rotate', 'scale', 'mirror', 'color', 'hull', 'minkowski']
        for op in ops:
            pattern = rf'({op}\s*\([^)]*\)\s*(?!{{)(?!;))'
            fixed_code = re.sub(pattern, r'\1 {\n    // Empty operation body\n}', fixed_code)
        
        # Ensure the code ends with a newline
        if not fixed_code.endswith('\n'):
            fixed_code += '\n'
        
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
                # For subsequent attempts, add feedback from validation
                is_valid, message = validate_scad_code(last_code)
                feedback = f"\nThe previous code had issues: {message}\nPlease fix and regenerate focusing on manufacturability, clean syntax, and best practices."
                scad_code = generate_code(
                    prompt + library_info + feedback, 
                    context, 
                    model=self.model, 
                    temperature=self.temperature
                )
            
            # Extract code from response if needed
            scad_code = extract_scad_code(scad_code)
            
            # Apply structural fixes before validation
            scad_code = self.ensure_valid_structure(scad_code)
            
            # Validate the generated code
            is_valid, message = validate_scad_code(scad_code)
            
            # If valid or final attempt, apply common fixes and return
            if is_valid or attempt == max_attempts - 1:
                # Fix common issues automatically
                scad_code = self.postprocess_code(scad_code)
                
                # Save to file if path provided
                if output_file:
                    self.save_to_file(scad_code, output_file)
                
                return scad_code, is_valid, message
            
            # Store code for feedback in next iteration
            last_code = scad_code
            attempt += 1
        
        # Should not reach here, but just in case
        return scad_code, False, "Max attempts reached without valid code."
        
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
            # Preprocess the prompt with manufacturing considerations
            prompt_info = self.preprocess_prompt(prompt)
            
            # Create an enhanced design prompt
            enhanced_prompt = self.craft_design_prompt(prompt_info, use_rag)
            
            # Retrieve relevant context if RAG is enabled
            context = retrieve_context(enhanced_prompt, selected_libraries=selected_libraries) if use_rag else None
            
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