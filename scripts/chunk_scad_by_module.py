import os
import re
import json
from glob import glob

SCAD_DIR = 'data/scad_raw/'  # Directory with .scad files
OUTPUT_FILE = 'data/scad_semantic_chunks.jsonl'

# Regex to match modules and functions with leading comments
def extract_chunks_from_scad(code):
    # Match /* ... */ or // ... comments before module/function
    pattern = re.compile(r'((?:/\*.*?\*/\s*|//.*\n\s*)*)(module|function)\s+(\w+)\s*\(([^)]*)\)\s*\{((?:[^{}]*|\{[^{}]*\})*)\}', re.DOTALL)
    for match in pattern.finditer(code):
        leading_comments, kind, name, params, body = match.groups()
        docstring = ''
        # Extract docstring from leading comments if present
        if leading_comments:
            docstring = leading_comments.strip()
        chunk_text = match.group(0)
        yield {
            'type': kind,
            'name': name,
            'params': params.strip(),
            'docstring': docstring,
            'code': chunk_text
        }

def main():
    with open(OUTPUT_FILE, 'w') as out_f:
        for scad_file in glob(os.path.join(SCAD_DIR, '**', '*.scad'), recursive=True):
            with open(scad_file, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            for chunk in extract_chunks_from_scad(code):
                chunk['filename'] = os.path.relpath(scad_file, SCAD_DIR)
                out_f.write(json.dumps(chunk) + '\n')
    print(f"Chunks written to {OUTPUT_FILE}")

if __name__ == '__main__':
    main() 