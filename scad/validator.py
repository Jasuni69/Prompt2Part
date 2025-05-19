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

def validate_scad_code(scad_code, check_with_openscad=True):
    """
    Validate OpenSCAD code using syntax checks and optionally OpenSCAD rendering.
    Returns (is_valid, message)
    """
    # First do simple syntax validation
    syntax_valid, syntax_msg = is_valid_syntax(scad_code)
    if not syntax_valid:
        return False, syntax_msg
    
    # Check for common issues
    issues = check_for_common_issues(scad_code)
    
    # Optionally validate with OpenSCAD
    if check_with_openscad:
        render_valid, render_msg = validate_via_openscad(scad_code)
        if not render_valid:
            return False, render_msg
        
        # If there were issues but rendering worked, return a warning
        if issues:
            return True, f"Code renders but has issues: {'; '.join(issues)}"
            
        return True, "OpenSCAD validation passed"
    
    # If we have issues but didn't check rendering
    if issues:
        return True, f"Syntax valid but code has issues: {'; '.join(issues)}"
    
    return True, "Syntax check passed"

def fix_common_issues(code):
    """
    Fix common OpenSCAD syntax issues automatically.
    """
    # Replace common errors with correct syntax
    
    # Fix semicolons before closing braces (very common error)
    fixed_code = re.sub(r';\s*}', r'\n}', code)
    
    # Fix semicolons after module/function declarations
    fixed_code = re.sub(r'(module|function)\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*;(\s*{)', r'\1 \2(\3', fixed_code)
    
    # Fix illegal trailing semicolons
    fixed_code = re.sub(r';\s*$', '', fixed_code)
    
    # Fix semicolons after transformation functions before braces
    fixed_code = re.sub(r'(translate|rotate|scale|mirror|multmatrix|color|resize|offset|hull|minkowski|union|difference|intersection)\s*\([^)]*\)\s*;(\s*{)', r'\1(\2', fixed_code)
    
    # Remove stray semicolons at end of file
    fixed_code = fixed_code.rstrip().rstrip(';') + '\n'
    
    # Fix parameters in cylinder calls
    # Replace cylinder(r, h) with cylinder(h=h, r=r)
    cylinder_fixes = re.findall(r'cylinder\s*\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)', fixed_code)
    for match in cylinder_fixes:
        r, h = match
        old = f'cylinder({r}, {h})'
        new = f'cylinder(h={h}, r={r})'
        fixed_code = fixed_code.replace(old, new)
    
    # Fix parameters in translate calls
    # Replace translate(x, y, z) with translate([x, y, z])
    translate_fixes = re.findall(r'translate\s*\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)', fixed_code)
    for match in translate_fixes:
        x, y, z = match
        old = f'translate({x}, {y}, {z})'
        new = f'translate([{x}, {y}, {z}])'
        fixed_code = fixed_code.replace(old, new)
    
    # Fix parameters in rotate calls
    # Replace rotate(x, y, z) with rotate([x, y, z])
    rotate_fixes = re.findall(r'rotate\s*\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)', fixed_code)
    for match in rotate_fixes:
        x, y, z = match
        old = f'rotate({x}, {y}, {z})'
        new = f'rotate([{x}, {y}, {z}])'
        fixed_code = fixed_code.replace(old, new)
    
    # Fix vector definitions with spaces instead of commas
    # Replace [x y z] with [x, y, z]
    vector_fixes = re.findall(r'\[\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*\]', fixed_code)
    for match in vector_fixes:
        x, y, z = match
        old = f'[{x} {y} {z}]'
        new = f'[{x}, {y}, {z}]'
        fixed_code = fixed_code.replace(old, new)
    
    # Fix polygon calls where direct calculations are used
    # This is a common issue where people do polygon(points * scale) which is invalid
    polygon_calc_fixes = re.findall(r'polygon\s*\(\s*(\w+)\s*\*\s*(\w+|\d+(?:\.\d+)?)\s*\)', fixed_code)
    for match in polygon_calc_fixes:
        var_name, scale = match
        old = f'polygon({var_name} * {scale})'
        new = f'polygon([for (p = {var_name}) [p[0] * {scale}, p[1] * {scale}]])'
        fixed_code = fixed_code.replace(old, new)
    
    # Fix star point functions that were commonly generated incorrectly
    # This handles the case seen in the cookie cutter example where the function had syntax errors
    star_function_errors = re.findall(r'function\s+star_points\s*\([^)]*\)\s*=\s*\[\s*for\s*\(\s*i\s*=\s*\[\s*0\s*:\s*[^]]*\]\s*\)', fixed_code)
    if star_function_errors:
        # We found a likely broken star points generator, replace with a correct version
        star_pattern = re.compile(r'function\s+star_points\s*\([^{]*\{[^}]*\}')
        fixed_code = re.sub(star_pattern, """function star_points(points, outer_r, inner_r) = 
    [for (i = [0:2*points-1])
        let(angle = i * 180 / points)
        (i % 2 == 0) ? 
            [outer_r * cos(angle), outer_r * sin(angle)] : 
            [inner_r * cos(angle), inner_r * sin(angle)]
    ]""", fixed_code)
    
    # Add $fn if missing for models with curved surfaces
    if ('cylinder' in fixed_code or 'sphere' in fixed_code or 'circle' in fixed_code) and '$fn' not in fixed_code:
        # Find the first non-comment line to insert $fn
        lines = fixed_code.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('//') and not line.strip().startswith('/*'):
                insert_index = i
                break
        
        lines.insert(insert_index, '$fn = 100;  // Smoothness of curved surfaces')
        fixed_code = '\n'.join(lines)
    
    # Add missing comments for variables with numeric values
    lines = fixed_code.split('\n')
    for i, line in enumerate(lines):
        if re.match(r'^\s*\w+\s*=\s*\d+(?:\.\d+)?\s*;(?!\s*\/\/)', line):
            # This is a variable assignment without a comment
            lines[i] = line.rstrip() + '  // mm'
    
    fixed_code = '\n'.join(lines)
    
    # Fix transformation operations that have semicolons but should have blocks
    # Find transformations that end with semicolons instead of blocks
    for transform in ['translate', 'rotate', 'scale', 'mirror', 'color']:
        pattern = rf'({transform}\s*\([^)]*\))\s*;(?!\s*\/\/)'
        for match in re.finditer(pattern, fixed_code):
            # Make sure it's not within a module definition or another context where ; is valid
            context = fixed_code[max(0, match.start()-20):match.start()]
            if not re.search(r'function|module|return', context):
                repl = r'\1 {\n    // Add objects here\n}'
                fixed_code = fixed_code[:match.start()] + re.sub(pattern, repl, match.group(0)) + fixed_code[match.end():]
    
    # Add module documentation for undocumented modules
    module_pattern = r'(module\s+(\w+)\s*\([^)]*\)\s*{)'
    modules = re.finditer(module_pattern, fixed_code)
    
    offset = 0
    for match in modules:
        full_match = match.group(1)
        module_name = match.group(2)
        match_start = match.start(1) + offset
        
        # Check if there's already a comment before this module
        preceding_code = fixed_code[:match_start]
        last_newline = preceding_code.rfind('\n')
        if last_newline != -1:
            line_before = preceding_code[last_newline+1:].strip()
            # If no comment and not empty line, add documentation
            if not line_before.startswith('//') and line_before.strip():
                doc_comment = f"\n// {module_name}: Module for creating a component\n"
                fixed_code = fixed_code[:match_start] + doc_comment + fixed_code[match_start:]
                offset += len(doc_comment)
    
    # Fix function order issues
    # This is a simple fix that ensures functions are defined before they're used
    function_errors = check_function_call_before_definition(fixed_code)
    if function_errors:
        # Get functions that need to be moved
        functions_to_fix = {}
        for error in function_errors:
            func_match = re.search(r"Function '([^']+)'", error)
            if func_match:
                func_name = func_match.group(1)
                functions_to_fix[func_name] = True
        
        if functions_to_fix:
            # Extract function definitions
            function_defs = {}
            for func_name in functions_to_fix:
                pattern = rf'(function\s+{func_name}\s*\([^)]*\)\s*=[^;]*;)'
                match = re.search(pattern, fixed_code)
                if match:
                    function_defs[func_name] = match.group(1)
            
            # Remove original function definitions
            for func_name, definition in function_defs.items():
                fixed_code = fixed_code.replace(definition, '')
            
            # Add functions at the beginning after any initial comments
            lines = fixed_code.split('\n')
            insert_position = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('//') and not line.strip().startswith('/*'):
                    insert_position = i
                    break
            
            for func_name, definition in function_defs.items():
                lines.insert(insert_position, definition)
                insert_position += 1
            
            fixed_code = '\n'.join(lines)
    
    # Fix library imports - add missing ones if their functions are used
    library_errors = check_library_imports(fixed_code)
    if library_errors:
        library_imports_to_add = []
        for error in library_errors:
            lib_match = re.search(r"'([^']+)'", error)
            if lib_match:
                lib_name = lib_match.group(1)
                # Define the import statement for each library
                if lib_name == 'BOSL2':
                    library_imports_to_add.append('use <BOSL2/std.scad>;')
                elif lib_name == 'BOSL':
                    library_imports_to_add.append('use <BOSL/basics.scad>;')
                elif lib_name == 'Round-Anything':
                    library_imports_to_add.append('use <Round-Anything/polyround.scad>;')
                elif lib_name == 'threads':
                    library_imports_to_add.append('use <threads.scad>;')
                elif lib_name == 'MCAD':
                    library_imports_to_add.append('use <MCAD/involute_gears.scad>;')
        
        if library_imports_to_add:
            # Add library imports at the beginning after any initial comments
            import_block = '\n'.join(library_imports_to_add) + '\n\n'
            
            # Find the position to insert after comments
            lines = fixed_code.split('\n')
            insert_position = 0
            for i, line in enumerate(lines):
                if (line.strip() and not line.strip().startswith('//') and not line.strip().startswith('/*')
                    and not re.match(r'^\s*use\s*<', line)):
                    insert_position = i
                    break
            
            lines.insert(insert_position, import_block)
            fixed_code = '\n'.join(lines)
    
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