import os
import re
import json
from pathlib import Path

RAW_DIR = Path('data/scad_raw')
CHUNKS_DIR = Path('data/scad_chunks')
METADATA_FILE = Path('data/scad_metadata.jsonl')
FULL_CORPUS_FILE = Path('data/scad_full_corpus.txt')

CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

chunk_counter = 1
metadata = []
full_corpus = []

# Enhanced regex patterns for OpenSCAD modules, functions, and comment blocks
defs_pattern = re.compile(r'^(module|function)\s+(\w+)\s*\(', re.MULTILINE)
comment_block_pattern = re.compile(r'/\*.*?\*/|//.*$', re.MULTILINE|re.DOTALL)
usage_example_pattern = re.compile(r'example|usage|demo', re.IGNORECASE)

def extract_leading_comments(code, start_pos):
    """Extract comment blocks preceding the current position."""
    line_start = code.rfind('\n', 0, start_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    
    # Look for comments before this position
    code_before = code[:line_start].strip()
    comments = []
    
    # Look for up to 10 lines of comments before
    lines = code_before.split('\n')
    for line in reversed(lines[-10:]):
        stripped = line.strip()
        if stripped.startswith('//'):
            comments.insert(0, stripped)
        else:
            # Stop when we hit non-comment line
            break
    
    # Also check for block comments
    block_match = re.search(r'/\*.*?\*/\s*$', code_before, re.DOTALL)
    if block_match:
        comments.insert(0, block_match.group(0))
    
    return '\n'.join(comments)

for root, _, files in os.walk(RAW_DIR):
    for file in files:
        if file.endswith('.scad'):
            lib = Path(root).relative_to(RAW_DIR).parts[0] if Path(root) != RAW_DIR else ''
            file_path = Path(root) / file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
                full_corpus.append(f"// --- {file_path} ---\n" + code + "\n\n")

                # Find all module/function definitions
                matches = list(defs_pattern.finditer(code))
                chunk_spans = []
                
                for i, match in enumerate(matches):
                    start = match.start()
                    end = matches[i+1].start() if i+1 < len(matches) else len(code)
                    
                    # Extract any comments preceding this definition
                    leading_comments = extract_leading_comments(code, start)
                    
                    # Determine if this chunk has usage examples
                    has_examples = bool(usage_example_pattern.search(code[start:end]))
                    
                    chunk_spans.append((
                        start, 
                        end, 
                        match.group(1),  # type (module/function)
                        match.group(2),  # name
                        leading_comments,
                        has_examples
                    ))

                # If no modules/functions, use semantic chunking (paragraphs or logical sections)
                if not chunk_spans:
                    # Try to split by comment headers or multiple blank lines
                    section_breaks = re.split(r'(^//\s*[-=]{3,}.*$)|(^\s*$\s*^\s*$)', code, flags=re.MULTILINE)
                    
                    if len(section_breaks) <= 1:
                        # Fall back to chunking by ~50 lines if no clear sections
                        lines = code.splitlines()
                        for i in range(0, len(lines), 50):
                            chunk_lines = lines[i:i+50]
                            chunk_text = '\n'.join(chunk_lines)
                            chunk_id = f"chunk_{chunk_counter:05d}"
                            chunk_file = CHUNKS_DIR / f"{chunk_id}.txt"
                            with open(chunk_file, 'w') as cf:
                                cf.write(chunk_text)
                            metadata.append({
                                'chunk_id': chunk_id,
                                'library': lib,
                                'file': str(file_path.relative_to(RAW_DIR)),
                                'type': 'lines',
                                'name': None,
                                'start_line': i+1,
                                'end_line': i+len(chunk_lines),
                                'text': chunk_text[:1000],  # preview
                                'has_examples': bool(usage_example_pattern.search(chunk_text))
                            })
                            chunk_counter += 1
                    else:
                        # Process each section as its own chunk
                        current_pos = 0
                        for section in section_breaks:
                            if section and section.strip():
                                chunk_text = section.strip()
                                if len(chunk_text) > 10:  # Avoid empty chunks
                                    chunk_id = f"chunk_{chunk_counter:05d}"
                                    chunk_file = CHUNKS_DIR / f"{chunk_id}.txt"
                                    with open(chunk_file, 'w') as cf:
                                        cf.write(chunk_text)
                                    
                                    # Calculate line numbers
                                    start_line = code[:current_pos].count('\n') + 1
                                    current_pos += len(section)
                                    end_line = code[:current_pos].count('\n') + 1
                                    
                                    metadata.append({
                                        'chunk_id': chunk_id,
                                        'library': lib,
                                        'file': str(file_path.relative_to(RAW_DIR)),
                                        'type': 'section',
                                        'name': None,
                                        'start_line': start_line,
                                        'end_line': end_line,
                                        'text': chunk_text[:1000],  # preview
                                        'has_examples': bool(usage_example_pattern.search(chunk_text))
                                    })
                                    chunk_counter += 1
                else:
                    for start, end, def_type, def_name, comments, has_examples in chunk_spans:
                        # Include leading comments with the chunk
                        if comments:
                            full_chunk = comments + "\n" + code[start:end].strip()
                        else:
                            full_chunk = code[start:end].strip()
                            
                        chunk_id = f"chunk_{chunk_counter:05d}"
                        chunk_file = CHUNKS_DIR / f"{chunk_id}.txt"
                        with open(chunk_file, 'w') as cf:
                            cf.write(full_chunk)
                            
                        # Calculate line numbers
                        start_line = code[:start].count('\n') + 1
                        end_line = code[:end].count('\n') + 1
                        
                        metadata.append({
                            'chunk_id': chunk_id,
                            'library': lib,
                            'file': str(file_path.relative_to(RAW_DIR)),
                            'type': def_type,
                            'name': def_name,
                            'start_line': start_line,
                            'end_line': end_line,
                            'text': full_chunk[:1000],  # preview
                            'has_comments': bool(comments),
                            'has_examples': has_examples
                        })
                        chunk_counter += 1

# Write metadata
with open(METADATA_FILE, 'w') as mf:
    for entry in metadata:
        mf.write(json.dumps(entry) + '\n')

# Write full corpus
with open(FULL_CORPUS_FILE, 'w') as fc:
    fc.write('\n'.join(full_corpus))

print(f"Extracted {chunk_counter-1} chunks. Metadata in {METADATA_FILE}. Full corpus in {FULL_CORPUS_FILE}.") 