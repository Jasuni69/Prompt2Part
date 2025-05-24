import glob
import re
import os
import json

EXCLUDE_DIRS = {"tests", "examples"}
LIBRARY_ROOT = "scad_library"  # relative to project root
OUTPUT_FILE = "available_modules.json"

modules = set()
functions = set()

# Add OpenSCAD built-in math functions and primitives
BUILTIN_FUNCTIONS = [
    'abs', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'clamp', 'cos', 'cross', 'degrees', 'exp', 'floor', 'ln', 'log', 'lookup', 'max', 'min', 'norm', 'pow', 'rands', 'round', 'sign', 'sin', 'sqrt', 'tan', 'len', 'str', 'version', 'version_num', 'parent_module', 'parent_module_idx', 'is_undef', 'is_list', 'is_num', 'is_bool', 'is_string', 'is_function', 'is_path', 'is_polygon', 'is_object', 'is_inf', 'is_nan', 'concat', 'chr', 'ord', 'search', 'replace', 'split', 'join', 'sort', 'reverse', 'unique', 'sum', 'product', 'for', 'let', 'assert', 'echo', 'import', 'dxf_linear_extrude', 'dxf_rotate_extrude', 'surface', 'text', 'projection', 'hull', 'minkowski', 'render', 'color', 'offset', 'resize', 'mirror', 'multmatrix', 'scale', 'rotate', 'translate', 'union', 'difference', 'intersection', 'children', 'cube', 'cylinder', 'sphere', 'polyhedron', 'square', 'circle', 'polygon', 'linear_extrude', 'rotate_extrude', 'import_stl', 'import_off', 'import_dxf', 'import_svg', 'import_obj', 'import_amf', 'import_3mf', 'import_png', 'import_jpg', 'import_bmp', 'import_gcode', 'import_zip', 'import_zipfile', 'import_zipdir', 'import_zipfiledir', 'import_zipfilefile', 'import_zipfiledirfile', 'import_zipfilefiledir', 'import_zipfilefilefile', 'import_zipfiledirfiledir', 'import_zipfiledirfilefile', 'import_zipfilefiledirfile', 'import_zipfilefilefiledir', 'import_zipfilefilefilefile', 'import_zipfiledirfilefiledir', 'import_zipfiledirfilefilefile', 'import_zipfilefiledirfiledir', 'import_zipfilefiledirfilefile', 'import_zipfilefilefiledirfile', 'import_zipfilefilefilefiledir', 'import_zipfilefilefilefilefile', 'import_zipfiledirfilefilefiledir', 'import_zipfiledirfilefilefilefile', 'import_zipfilefiledirfilefiledir', 'import_zipfilefiledirfilefilefile', 'import_zipfilefilefiledirfiledir', 'import_zipfilefilefiledirfilefile', 'import_zipfilefilefilefiledirfile', 'import_zipfilefilefilefilefiledir', 'import_zipfilefilefilefilefilefile'
]

BUILTIN_MODULES = [
    'cube', 'cylinder', 'sphere', 'polyhedron', 'square', 'circle', 'polygon', 'linear_extrude', 'rotate_extrude', 'import', 'projection', 'hull', 'minkowski', 'render', 'color', 'offset', 'resize', 'mirror', 'multmatrix', 'scale', 'rotate', 'translate', 'union', 'difference', 'intersection', 'children', 'surface', 'text', 'dxf_linear_extrude', 'dxf_rotate_extrude'
]

for root, dirs, files in os.walk(LIBRARY_ROOT):
    # Skip excluded directories
    if any(ex in root for ex in EXCLUDE_DIRS):
        continue
    for file in files:
        if file.endswith(".scad"):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        m = re.match(r'\s*module\s+([a-zA-Z0-9_]+)\s*\(', line)
                        if m:
                            modules.add(m.group(1))
                        f_m = re.match(r'\s*function\s+([a-zA-Z0-9_]+)\s*\(', line)
                        if f_m:
                            functions.add(f_m.group(1))
            except Exception as e:
                print(f"Error reading {path}: {e}")

modules.update(BUILTIN_MODULES)
functions.update(BUILTIN_FUNCTIONS)

index = {
    "modules": sorted(list(modules)),
    "functions": sorted(list(functions))
}

with open(OUTPUT_FILE, "w") as out:
    json.dump(index, out, indent=2)

print(f"Extracted {len(modules)} modules and {len(functions)} functions.")
print(f"Saved to {OUTPUT_FILE}") 