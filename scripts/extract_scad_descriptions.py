import os
import re
import json
from pathlib import Path

RAW_DIR = Path('data/scad_raw')
DESCRIPTIONS_DIR = Path('data/scad_descriptions')
DESCRIPTIONS_METADATA_FILE = Path('data/scad_descriptions_metadata.jsonl')

DESCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)

# Clear out old description files before writing new ones
for f in DESCRIPTIONS_DIR.glob("*.json"):
    f.unlink()

description_counter = 1
metadata = []

# Enhanced regex patterns for OpenSCAD modules, functions, and comment blocks
defs_pattern = re.compile(
    r'^(module|function)\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)
comment_block_pattern = re.compile(r'/\*.*?\*/', re.MULTILINE | re.DOTALL)
single_line_comment_pattern = re.compile(r'//.*$', re.MULTILINE)


def extract_function_description(code, start_pos, func_name, func_type):
    """Extract comprehensive description for a function/module including comments, parameters, and usage."""

    # Find the start of the line containing the function definition
    line_start = code.rfind('\n', 0, start_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1

    # Look for comments before this position
    code_before = code[:line_start].strip()
    description_parts = []

    # Extract preceding comment blocks (both // and /* */)
    lines = code_before.split('\n')
    comment_lines = []

    # Look backwards for consecutive comment lines
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith('//'):
            comment_lines.insert(0, stripped[2:].strip())
        elif stripped == '':
            # Allow empty lines within comment blocks
            if comment_lines:
                comment_lines.insert(0, '')
        else:
            # Stop when we hit non-comment, non-empty line
            break

    # Also check for block comments immediately before
    block_matches = list(comment_block_pattern.finditer(code_before))
    if block_matches:
        last_block = block_matches[-1]
        # Check if the block comment is close to our function
        if code_before[last_block.end():].strip() == '':
            block_content = last_block.group(0)[2:-2].strip()  # Remove /* */
            comment_lines.insert(0, block_content)

    # Clean up comment lines and create description
    if comment_lines:
        # Remove empty lines at start and end
        while comment_lines and comment_lines[0].strip() == '':
            comment_lines.pop(0)
        while comment_lines and comment_lines[-1].strip() == '':
            comment_lines.pop()

        if comment_lines:
            description_parts.append('\n'.join(comment_lines))

    # Extract function signature for context
    func_match = re.search(
        rf'^({func_type})\s+({func_name})\s*\(([^)]*)\)', code[start_pos:], re.MULTILINE)
    if func_match:
        full_signature = func_match.group(0)
        params = func_match.group(3).strip()

        # Create a readable parameter description
        if params:
            param_desc = f"Parameters: {params}"
            description_parts.append(param_desc)

        # Add function type and name
        type_desc = f"{func_type.capitalize()}: {func_name}"
        description_parts.insert(0, type_desc)

    # If no comments found, create a basic description from the function name and parameters
    if len(description_parts) <= 2:  # Only type and params, no actual description
        # Try to infer purpose from function name
        name_words = re.findall(r'[A-Z][a-z]*|[a-z]+', func_name)
        if name_words:
            inferred_desc = f"OpenSCAD {func_type} for {' '.join(name_words).lower()}"
            description_parts.insert(-1 if len(description_parts)
                                     > 1 else 0, inferred_desc)

    return '\n\n'.join(description_parts) if description_parts else f"{func_type.capitalize()}: {func_name}"


def extract_full_function_code(code, start_pos, end_pos):
    """Extract the complete function/module code including any preceding comments."""

    # Find preceding comments
    line_start = code.rfind('\n', 0, start_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1

    code_before = code[:line_start].strip()
    lines = code_before.split('\n')

    # Find the start of the comment block
    comment_start = line_start
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith('//') or stripped == '':
            # Move start position back to include this line
            comment_start = code.rfind(
                '\n' + line) + 1 if '\n' + line in code else 0
        else:
            break

    # Also check for block comments
    block_matches = list(comment_block_pattern.finditer(code_before))
    if block_matches:
        last_block = block_matches[-1]
        if code_before[last_block.end():].strip() == '':
            comment_start = min(comment_start, last_block.start())

    # Extract the full code from comment start to function end
    full_code = code[comment_start:end_pos].strip()
    return full_code


# Process all SCAD files
for root, _, files in os.walk(RAW_DIR):
    for file in files:
        if file.endswith('.scad'):
            lib = Path(root).relative_to(
                RAW_DIR).parts[0] if Path(root) != RAW_DIR else ''
            file_path = Path(root) / file

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()

                # Find all module/function definitions
                matches = list(defs_pattern.finditer(code))

                for i, match in enumerate(matches):
                    start = match.start()
                    end = matches[i+1].start() if i + \
                        1 < len(matches) else len(code)

                    func_type = match.group(1)  # module or function
                    func_name = match.group(2)  # function name
                    func_params = match.group(3)  # parameters

                    # Extract description (for embedding)
                    description = extract_function_description(
                        code, start, func_name, func_type)

                    # Extract full code (the value)
                    full_code = extract_full_function_code(code, start, end)

                    # Create description file
                    desc_id = f"desc_{description_counter:05d}"
                    desc_file = DESCRIPTIONS_DIR / f"{desc_id}.json"

                    # Store as key-value pair
                    desc_data = {
                        "id": desc_id,
                        "description": description,  # This will be embedded
                        "code": full_code,          # This is the retrieved value
                        "function_name": func_name,
                        "function_type": func_type,
                        "parameters": func_params,
                        "library": lib,
                        "file": str(file_path.relative_to(RAW_DIR))
                    }

                    with open(desc_file, 'w') as df:
                        json.dump(desc_data, df, indent=2)

                    # Store metadata
                    metadata.append({
                        'desc_id': desc_id,
                        'library': lib,
                        'file': str(file_path.relative_to(RAW_DIR)),
                        'function_type': func_type,
                        'function_name': func_name,
                        'parameters': func_params,
                        'description_preview': description[:200] + "..." if len(description) > 200 else description,
                        'code_length': len(full_code)
                    })

                    description_counter += 1

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

# Write metadata
with open(DESCRIPTIONS_METADATA_FILE, 'w') as mf:
    for entry in metadata:
        mf.write(json.dumps(entry) + '\n')

print(f"Extracted {description_counter-1} function/module descriptions.")
print(f"Description files saved to: {DESCRIPTIONS_DIR}")
print(f"Metadata saved to: {DESCRIPTIONS_METADATA_FILE}")

# Create summary statistics
module_count = sum(
    1 for entry in metadata if entry['function_type'] == 'module')
function_count = sum(
    1 for entry in metadata if entry['function_type'] == 'function')
libraries = set(entry['library'] for entry in metadata if entry['library'])

print(f"\nSummary:")
print(f"- Modules: {module_count}")
print(f"- Functions: {function_count}")
print(f"- Libraries: {len(libraries)}")
print(f"- Total descriptions: {len(metadata)}")
