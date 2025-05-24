import os
import tempfile
import subprocess
import re
import json
from pathlib import Path

def is_valid_syntax(scad_code):
    """Check if the syntax of the OpenSCAD code is valid."""
    # Basic syntax checks
    # Check for balanced braces/parentheses
    if scad_code.count('{') != scad_code.count('}'):
        return False, "Unbalanced curly braces"
    if scad_code.count('(') != scad_code.count(')'):
        return False, "Unbalanced parentheses"
    if scad_code.count('[') != scad_code.count(']'):
        return False, "Unbalanced square brackets"
    
    # Check for semicolons (most OpenSCAD statements need them)
    if not re.search(r';', scad_code):
        return False, "Missing semicolons"
    
    # Check for common OpenSCAD keywords
    if not any(keyword in scad_code for keyword in ['cube', 'sphere', 'cylinder', 'union', 'difference', 'polygon', 'linear_extrude']):
        return False, "No basic OpenSCAD primitives found"
    
    # Check for variable usage before definition
    var_decls = {}
    for match in re.finditer(r'(\w+)\s*=\s*[^;]+;', scad_code):
        var_name = match.group(1)
        var_decls[var_name] = match.start()
    
    for var_name, decl_pos in var_decls.items():
        # Look for usage of the variable before its declaration
        pattern = r'\b' + re.escape(var_name) + r'\b'
        for match in re.finditer(pattern, scad_code):
            if match.start() < decl_pos and not re.match(r'\s*' + re.escape(var_name) + r'\s*=', scad_code[match.start():match.start()+len(var_name)+10]):
                return False, f"Variable '{var_name}' used before declaration"
    
    # Check for mismatched transform parameters
    transform_patterns = [
        (r'translate\s*\([^)]*\)', r'translate\s*\(\s*\[\s*[^]]*\]\s*\)'),
        (r'rotate\s*\([^)]*\)', r'rotate\s*\(\s*\[\s*[^]]*\]\s*\)'),
        (r'scale\s*\([^)]*\)', r'scale\s*\(\s*\[\s*[^]]*\]\s*\)'),
    ]
    
    for pattern, correct_pattern in transform_patterns:
        for match in re.finditer(pattern, scad_code):
            transform_code = match.group(0)
            if not re.match(correct_pattern, transform_code):
                transform_name = transform_code.split('(')[0].strip()
                return False, f"Incorrect {transform_name} syntax - should use vector [x,y,z] format"
    
    # Check for invalid cylinder parameters
    for match in re.finditer(r'cylinder\s*\(([^)]*)\)', scad_code):
        params = match.group(1)
        # Check for old syntax (cylinder(r, h) or cylinder(h, r))
        if re.match(r'\s*\d+\s*,\s*\d+\s*', params) and not re.search(r'[rh]=', params):
            return False, "Invalid cylinder syntax - use named parameters: cylinder(h=h, r=r)"
    
    # Check for function/module definitions and calls
    function_errors = check_function_call_before_definition(scad_code)
    if function_errors:
        return False, "; ".join(function_errors)
    
    # Check for library usage
    library_errors = check_library_imports(scad_code)
    if library_errors:
        return False, "; ".join(library_errors)
    
    # Check for data structure errors
    data_errors = check_data_structures(scad_code)
    if data_errors:
        return False, "; ".join(data_errors)
    
    # Check for operation nesting errors
    nesting_errors = check_operation_nesting(scad_code)
    if nesting_errors:
        return False, "; ".join(nesting_errors)
    
    return True, "Syntax appears valid"

def validate_via_openscad(scad_code):
    """
    Validate OpenSCAD code by attempting to render it using the OpenSCAD CLI.
    Returns (is_valid, message).
    """
    # Check if OpenSCAD is installed
    try:
        result = subprocess.run(['openscad', '--version'], 
                              capture_output=True, 
                              text=True, 
                              check=False)
        if result.returncode != 0:
            return False, "OpenSCAD not found or not working"
    except FileNotFoundError:
        return False, "OpenSCAD CLI not found"
    
    # Create a temporary .scad file
    with tempfile.NamedTemporaryFile(suffix='.scad', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(scad_code.encode('utf-8'))
    
    # Create an output STL path
    tmp_stl = tmp_path.replace('.scad', '.stl')
    
    try:
        # Run OpenSCAD to check if it can render the file
        result = subprocess.run(
            ['openscad', '-o', tmp_stl, tmp_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=15  # Timeout in seconds
        )
        
        # Check the result
        if result.returncode == 0:
            if os.path.exists(tmp_stl) and os.path.getsize(tmp_stl) > 0:
                return True, "OpenSCAD rendered successfully"
            else:
                return False, "OpenSCAD did not create output"
        else:
            # Parse error messages from OpenSCAD
            error_msg = result.stderr
            if 'ERROR:' in error_msg:
                error_lines = [line for line in error_msg.split('\n') if 'ERROR:' in line]
                cleaned_errors = '\n'.join(error_lines)
                return False, f"OpenSCAD render error: {cleaned_errors}"
            else:
                return False, f"OpenSCAD error with no details: {error_msg}"
    
    except subprocess.TimeoutExpired:
        return False, "OpenSCAD render timed out (15s)"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
    finally:
        # Clean up temporary files
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if os.path.exists(tmp_stl):
            os.unlink(tmp_stl)

def check_for_common_issues(scad_code):
    """
    Check for common issues in OpenSCAD code and return a list of issues found.
    """
    issues = []
    
    # Check for missing $fn
    if ('cylinder' in scad_code or 'sphere' in scad_code or 'circle' in scad_code) and '$fn' not in scad_code:
        issues.append("Missing $fn parameter for curved surfaces")
    
    # Check for missing variable units in comments
    var_declarations = re.findall(r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*;(?!\s*\/\/)', scad_code)
    for var_name, var_value in var_declarations:
        issues.append(f"Variable '{var_name}' is missing a unit comment (e.g. // mm)")
    
    # Check for inconsistent indentation
    lines = scad_code.split('\n')
    prev_indent = 0
    brace_stack = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('//'):
            continue
            
        # Count leading spaces
        indent = len(line) - len(line.lstrip())
        
        # Track brace level
        if '{' in line:
            brace_stack.append(indent)
        
        # Check if indentation matches brace level
        if brace_stack and indent < brace_stack[-1]:
            if not stripped.startswith('}'):
                issues.append(f"Line {i+1}: Inconsistent indentation")
                
        if '}' in line and brace_stack:
            brace_stack.pop()
            
        prev_indent = indent
    
    # Check for potentially problematic names (reserved words, etc.)
    reserved_words = ['if', 'for', 'let', 'each', 'function', 'module']
    for word in reserved_words:
        pattern = r'\b' + word + r'\s*='
        if re.search(pattern, scad_code):
            issues.append(f"Using reserved word '{word}' as a variable name")
    
    # Check for missing module documentation
    module_defs = re.findall(r'module\s+(\w+)\s*\([^)]*\)\s*{', scad_code)
    for module_name in module_defs:
        # Look for a comment line before the module definition
        module_match = re.search(r'(\/\/[^\n]*\n)*\s*module\s+' + re.escape(module_name), scad_code)
        if module_match:
            preceding_text = module_match.group(0)
            if '//' not in preceding_text:
                issues.append(f"Module '{module_name}' is missing documentation comments")
    
    # Check for overlarge models (potential errors)
    large_values = re.findall(r'\b(\d{4,})\b', scad_code)
    if large_values:
        issues.append(f"Very large numeric values found: {', '.join(large_values)}")
    
    return issues

def validate_preview(scad_code, output_dir=None):
    """
    Validate by generating a preview image - ensuring visual correctness
    
    Args:
        scad_code (str): The OpenSCAD code to validate
        output_dir (str): Optional directory to save the preview image
        
    Returns:
        tuple: (success, result_path_or_message)
    """
    # Create temporary directory if none provided
    if not output_dir:
        temp_dir = tempfile.mkdtemp()
    else:
        temp_dir = output_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    # Create a temporary SCAD file
    with tempfile.NamedTemporaryFile(suffix='.scad', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(scad_code.encode('utf-8'))
    
    # Create a PNG preview
    png_path = os.path.join(temp_dir, 'preview.png')
    try:
        result = subprocess.run(
            ['openscad', '-o', png_path, '--imgsize=800,600', '--colorscheme=Tomorrow', tmp_path],
            check=False, capture_output=True, timeout=20
        )
        
        if result.returncode == 0 and os.path.exists(png_path) and os.path.getsize(png_path) > 100:
            return True, png_path
        else:
            error_msg = result.stderr.decode() if result.stderr else "Unknown error rendering preview"
            return False, error_msg
    except subprocess.TimeoutExpired:
        return False, "OpenSCAD preview generation timed out (20s)"
    except Exception as e:
        return False, str(e)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        # Don't clean up temp_dir if it was provided by the caller

def validate_scad_code(scad_code, check_with_openscad=True, generate_preview=False, preview_dir=None):
    """
    Validate OpenSCAD code using syntax checks and optionally OpenSCAD rendering.
    
    Args:
        scad_code (str): The OpenSCAD code to validate
        check_with_openscad (bool): Whether to validate with OpenSCAD CLI
        generate_preview (bool): Whether to generate a preview image
        preview_dir (str): Directory to save the preview image if generated
        
    Returns:
        tuple: (is_valid, message, preview_path) if generate_preview=True else (is_valid, message)
    """
    # First do simple syntax validation
    syntax_valid, syntax_msg = is_valid_syntax(scad_code)
    if not syntax_valid:
        return (False, syntax_msg, None) if generate_preview else (False, syntax_msg)
    
    # Check for common issues
    issues = check_for_common_issues(scad_code)
    
    # Optionally validate with OpenSCAD
    if check_with_openscad:
        render_valid, render_msg = validate_via_openscad(scad_code)
        if not render_valid:
            return (False, render_msg, None) if generate_preview else (False, render_msg)
    
    # Generate preview if requested
    preview_path = None
    if generate_preview:
        preview_valid, preview_result = validate_preview(scad_code, preview_dir)
        if preview_valid:
            preview_path = preview_result
        else:
            # Preview failed but rendering succeeded - still valid but with warning
            warning_msg = f"Warning: Preview generation failed: {preview_result}"
            if issues:
                issues.append(warning_msg)
            else:
                issues = [warning_msg]
    
    # If there were issues but rendering worked, return a warning
    if issues:
        message = f"Code renders but has issues: {'; '.join(issues)}"
        return (True, message, preview_path) if generate_preview else (True, message)
    
    success_msg = "OpenSCAD validation passed"
    return (True, success_msg, preview_path) if generate_preview else (True, success_msg)

def fix_common_issues(scad_code):
    """
    Fix common issues in OpenSCAD code that could cause rendering problems.
    
    Args:
        scad_code (str): Input OpenSCAD code
        
    Returns:
        str: Fixed OpenSCAD code
    """
    # Fix syntax errors
    fixed_code = scad_code
    
    # Fix broken module closures
    braces_open = fixed_code.count('{')
    braces_close = fixed_code.count('}')
    
    if braces_open > braces_close:
        # Add missing closing braces
        fixed_code += '\n' + ('}' * (braces_open - braces_close))
    
    # Fix missing semicolons in variable assignments
    # This regex finds variable assignments without semicolons
    fixed_code = re.sub(r'(\$?\w+\s*=\s*[^;{]+)(?=\n)', r'\1;', fixed_code)
    
    # Fix use of uninitialized variables by giving them reasonable defaults
    # Identify used but undefined variables
    var_pattern = r'(?<!\$)(?<!function\s)(?<!module\s)(\w+)\s*='
    defined_vars = set(re.findall(var_pattern, fixed_code))
    
    # Look for variable uses
    used_vars = set()
    for match in re.finditer(r'[^\$\w](\w+)\s*[\(\[\+\-\*\/]', fixed_code):
        var = match.group(1)
        if var not in ['if', 'for', 'let', 'module', 'function', 'use', 'include', 'echo', 'assert', 'sin', 'cos', 'tan']:
            used_vars.add(var)
    
    # List of OpenSCAD operation keywords
    operation_keywords = [
        'union', 'difference', 'intersection', 'translate', 'rotate', 'scale', 
        'mirror', 'hull', 'minkowski', 'linear_extrude', 'rotate_extrude', 'color',
        'cube', 'sphere', 'cylinder', 'square', 'circle', 'text', 'polygon', 'polyhedron'
    ]
    
    # Remove operation keywords from used vars
    used_vars = used_vars - set(operation_keywords)
    
    # Remove numeric values from used vars (numbers shouldn't be variables)
    used_vars = {var for var in used_vars if not re.match(r'^\d+$', var)}
    
    # Find variables used before defined
    undefined_vars = used_vars - defined_vars
    
    # Common dimensions and their defaults
    dimension_defaults = {
        'width': '100',
        'height': '50', 
        'depth': '20',
        'thickness': '2',
        'radius': '10',
        'diameter': '20',
        'length': '100',
        'angle': '45',
        'size': '10',
        'wall_thickness': '1.2',
        'base_height': '5',
        'base_width': '100',
        'base_depth': '60',
        'support_height': '40',
        'support_width': '20',
        'vent_hole_diameter': '5',
        'cable_hole_diameter': '10',
        'fillet_radius': '2',
        'tolerance': '0.2',
        'clearance': '0.3'
    }
    
    # Add defaults for undefined variables
    declarations = []
    for var in undefined_vars:
        # Skip loop variables
        if var in ['i', 'j', 'k', 'x', 'y', 'z']:
            continue
            
        if var in dimension_defaults:
            default = dimension_defaults[var]
        else:
            # Generic default
            default = '10'
            
        declarations.append(f'{var} = {default}; // Auto-defined parameter')
    
    if declarations:
        # Add declarations at the beginning after any existing comments or $fn declaration
        lines = fixed_code.split('\n')
        
        # First find if there are already parameter blocks
        param_section_found = False
        insert_pos = 0
        
        for i, line in enumerate(lines):
            # If we find "// Parameters" or similar, add our declarations after that block
            if re.match(r'//.*[Pp]arameters', line):
                # Find the end of this parameter block
                for j in range(i+1, len(lines)):
                    if not lines[j].strip() or not re.match(r'^\s*[\w$]', lines[j]):
                        insert_pos = j
                        param_section_found = True
                        break
                if param_section_found:
                    break
        
        # If no parameter section found, insert after comments at the top
        if not param_section_found:
            # Skip past comments at the beginning
            for i, line in enumerate(lines):
                if not line.strip().startswith('//') and line.strip():
                    insert_pos = i
                    break
        
        # Add our declarations
        lines.insert(insert_pos, '\n// Auto-defined parameters')
        insert_pos += 1
        for decl in declarations:
            lines.insert(insert_pos, decl)
            insert_pos += 1
        lines.insert(insert_pos, '')
        
        fixed_code = '\n'.join(lines)

    # Fix missing modules that may be referenced
    # Find module calls without definitions
    module_pattern = r'module\s+(\w+)'
    defined_modules = set(re.findall(module_pattern, fixed_code))
    
    call_pattern = r'(\w+)\s*\('
    for match in re.finditer(call_pattern, fixed_code):
        name = match.group(1)
        if name not in ['if', 'for', 'translate', 'rotate', 'scale', 'mirror', 'color', 
                       'union', 'difference', 'intersection', 'hull', 'minkowski', 'echo',
                       'cube', 'sphere', 'cylinder', 'polyhedron', 'square', 'circle', 'polygon']:
            if name not in defined_modules and name not in fixed_code[:match.start()]:
                # Add a basic implementation for the missing module
                basic_module = f"""
// Auto-generated placeholder module
module {name}() {{
    echo("Placeholder for {name}");
    cube([10, 10, 10], center=true);
}}
"""
                # Add to the beginning of the file
                fixed_code = basic_module + fixed_code
                defined_modules.add(name)
    
    # Fix empty module and operation bodies
    fixed_code = re.sub(r'(module\s+\w+\s*\([^)]*\))\s*{\s*}', r'\1 {\n    cube([1, 1, 1], center=true); // Placeholder\n}', fixed_code)
    
    # Fix operations with empty bodies
    ops = ['union', 'difference', 'intersection', 'translate', 'rotate', 'scale', 'mirror', 'color']
    for op in ops:
        fixed_code = re.sub(rf'({op}\s*\([^)]*\))\s*{{\s*}}', r'\1 {\n    cube([1, 1, 1], center=true); // Placeholder\n}', fixed_code)
    
    # Fix variables used in the wrong context (e.g., array when scalar expected)
    # This is a complex check, but we can do some simple fixes
    
    # Fix broken for loops
    # Look for for loops with incorrect syntax
    for_pattern = r'for\s*\(([^)]+)\)'
    for match in re.finditer(for_pattern, fixed_code):
        loop_expr = match.group(1)
        
        # Check if it's using Python-style range
        if 'range' in loop_expr:
            # Fix: for(i in range(0, 10)) -> for(i = [0:1:9])
            range_pattern = r'(\w+)\s+in\s+range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
            range_match = re.search(range_pattern, loop_expr)
            if range_match:
                var, start, end = range_match.groups()
                replacement = f'{var} = [{start}:1:{end}-1]'
                fixed_code = fixed_code.replace(loop_expr, replacement)
        
        # Check for Python-style 'in' for iteration
        elif ' in ' in loop_expr:
            # Fix: for(i in array) -> for(i = array)
            in_pattern = r'(\w+)\s+in\s+(\[.*?\]|\w+)'
            in_match = re.search(in_pattern, loop_expr)
            if in_match:
                var, array = in_match.groups()
                replacement = f'{var} = {array}'
                fixed_code = fixed_code.replace(loop_expr, replacement)
                
    # Add main call if none exists
    # Check if there are any modules defined but none called at the end
    if 'module' in fixed_code and not re.search(r'\w+\(\)\s*;?\s*$', fixed_code):
        # Find the last defined module
        module_matches = list(re.finditer(r'module\s+(\w+)', fixed_code))
        if module_matches:
            # Get the last defined module
            last_module = module_matches[-1].group(1)
            # Add a call to it at the end
            fixed_code += f'\n\n// Render the model\n{last_module}();'
                
    return fixed_code

def analyze_model_complexity(scad_code):
    """
    Analyze the complexity of the model and provide feedback.
    Returns a dictionary with analysis results.
    """
    result = {
        "primitives_count": 0,
        "operations_count": 0,
        "modules_count": 0,
        "variables_count": 0,
        "complexity_score": 0,
        "render_time_estimate": "quick",
        "recommendations": []
    }
    
    # Count primitives
    primitives = ['cube', 'sphere', 'cylinder', 'polyhedron', 'square', 'circle', 'polygon']
    for primitive in primitives:
        pattern = r'\b' + primitive + r'\s*\('
        matches = re.findall(pattern, scad_code)
        result["primitives_count"] += len(matches)
    
    # Count operations
    operations = ['union', 'difference', 'intersection', 'minkowski', 'hull']
    for op in operations:
        pattern = r'\b' + op + r'\s*\('
        matches = re.findall(pattern, scad_code)
        result["operations_count"] += len(matches)
    
    # Count modules
    modules = re.findall(r'module\s+\w+\s*\(', scad_code)
    result["modules_count"] = len(modules)
    
    # Count variables
    variables = re.findall(r'\b\w+\s*=\s*[^;]+;', scad_code)
    result["variables_count"] = len(variables)
    
    # Calculate complexity score
    result["complexity_score"] = (
        result["primitives_count"] * 1 + 
        result["operations_count"] * 2 + 
        result["modules_count"] * 1.5
    )
    
    # Estimate render time
    if result["complexity_score"] < 10:
        result["render_time_estimate"] = "quick"
    elif result["complexity_score"] < 30:
        result["render_time_estimate"] = "moderate"
    else:
        result["render_time_estimate"] = "slow"
    
    # Add recommendations
    if result["primitives_count"] > 20 and result["modules_count"] < 3:
        result["recommendations"].append("Consider organizing repeated elements into modules")
    
    if '$fn' in scad_code:
        fn_values = re.findall(r'\$fn\s*=\s*(\d+)', scad_code)
        if fn_values and int(fn_values[0]) > 200:
            result["recommendations"].append("High $fn value may cause slow rendering. Consider reducing for development.")
    
    if 'minkowski' in scad_code and result["complexity_score"] > 15:
        result["recommendations"].append("Minkowski operations are computationally expensive. Consider simplifying.")
    
    if result["complexity_score"] > 30:
        result["recommendations"].append("Complex model detected. Consider breaking into separate files or modules.")
    
    return result

def check_function_call_before_definition(scad_code):
    """Check if functions or modules are called before they are defined."""
    lines = scad_code.split('\n')
    defined_functions = {}
    defined_modules = {}
    line_content = {}
    
    # First pass: Find all function and module definitions
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        line_content[line_num] = line
        
        # Find function definitions
        func_match = re.search(r'function\s+(\w+)\s*\(', line)
        if func_match:
            func_name = func_match.group(1)
            defined_functions[func_name] = line_num
            
        # Find module definitions
        module_match = re.search(r'module\s+(\w+)\s*\(', line)
        if module_match:
            module_name = module_match.group(1)
            defined_modules[module_name] = line_num
    
    # Second pass: Check for calls before definition
    errors = []
    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith('//') or line.strip().startswith('/*'):
            continue
        
        # Check for function calls
        for func_name, def_line in defined_functions.items():
            pattern = r'\b' + re.escape(func_name) + r'\s*\('
            if re.search(pattern, line) and line_num < def_line:
                # Ensure it's not the definition itself
                if not re.search(r'function\s+' + re.escape(func_name), line):
                    errors.append(f"Function '{func_name}' called on line {line_num} but defined on line {def_line}")
        
        # Check for module calls
        for module_name, def_line in defined_modules.items():
            pattern = r'\b' + re.escape(module_name) + r'\s*\('
            if re.search(pattern, line) and line_num < def_line:
                # Ensure it's not the definition itself
                if not re.search(r'module\s+' + re.escape(module_name), line):
                    errors.append(f"Module '{module_name}' called on line {line_num} but defined on line {def_line}")
    
    return errors

def check_library_imports(scad_code):
    """Check if libraries are properly imported and used."""
    errors = []
    
    # Check for libraries mentioned in comments but not imported
    libraries = {
        'BOSL2': r'use\s*<BOSL2/',
        'BOSL': r'use\s*<BOSL/',
        'Round-Anything': r'use\s*<Round-Anything/',
        'threads': r'use\s*<threads.scad>',
        'MCAD': r'use\s*<MCAD/'
    }
    
    # Look for library function usage patterns
    usage_patterns = {
        'BOSL2': [r'cuboid\s*\(', r'cylindroid\s*\(', r'attach\s*\('],
        'BOSL': [r'cube_center\s*\(', r'hollow_cylinder\s*\('],
        'Round-Anything': [r'polyround\s*\(', r'round_corners\s*\('],
        'threads': [r'metric_thread\s*\(', r'english_thread\s*\('],
        'MCAD': [r'gear\s*\(', r'involute_gear\s*\(']
    }
    
    # Check for each library
    for lib_name, import_pattern in libraries.items():
        has_import = re.search(import_pattern, scad_code)
        has_usage = any(re.search(pattern, scad_code) for pattern in usage_patterns.get(lib_name, []))
        
        if has_usage and not has_import:
            errors.append(f"Library functions from '{lib_name}' used but library not imported")
    
    return errors

def check_data_structures(scad_code):
    """Check for common errors in data structure definitions."""
    errors = []
    
    # Check for missing commas in array/vector definitions
    vector_pattern = r'\[\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*\]'
    # This pattern finds [x y z] without commas
    for match in re.finditer(vector_pattern, scad_code):
        errors.append(f"Vector/array missing commas: {match.group(0)}")
    
    # Check for malformed array of points
    point_array_pattern = r'\[\s*(\[\s*\d+(?:\.\d+)?,\s*\d+(?:\.\d+)?\s*\])'
    for match in re.finditer(point_array_pattern, scad_code):
        next_char = scad_code[match.end():match.end()+1]
        if next_char and next_char not in ',]':
            errors.append(f"Array of points missing comma after: {match.group(1)}")
    
    # Check for mismatched function return with expected data
    if 'polygon(' in scad_code:
        # If polygon is used, check if any function returning a list is called directly
        polygon_function_calls = re.finditer(r'polygon\s*\(\s*(\w+)\s*\(', scad_code)
        for match in polygon_function_calls:
            func_name = match.group(1)
            # Check if function is defined
            func_def = re.search(rf'function\s+{func_name}\s*\([^)]*\)\s*=', scad_code)
            if func_def:
                # Check if the function returns a list/vector
                if not re.search(r'\[\s*for\s*\(', func_def.group(0)) and not re.search(r'concat\s*\(', func_def.group(0)):
                    errors.append(f"Function '{func_name}' might not return proper point list for polygon")
    
    return errors

def check_operation_nesting(scad_code):
    """Check for improper nesting of operations."""
    errors = []
    
    # Check for boolean operations with missing children
    boolean_ops = ['union', 'difference', 'intersection', 'hull', 'minkowski']
    for op in boolean_ops:
        pattern = rf'{op}\s*\(\s*\)\s*\{{'
        for match in re.finditer(pattern, scad_code):
            errors.append(f"{op}() has no arguments")
    
    # Check for transform operations without child objects
    transform_ops = ['translate', 'rotate', 'scale', 'mirror', 'color']
    for op in transform_ops:
        pattern = rf'{op}\s*\([^)]*\)\s*;'
        for match in re.finditer(pattern, scad_code):
            # Skip if part of a module definition
            if not re.search(r'function|module', scad_code[max(0, match.start()-20):match.start()]):
                errors.append(f"{op}() has no child operation; it needs {{ }} with objects inside")
    
    return errors 