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

# Regex patterns for OpenSCAD modules and functions
defs_pattern = re.compile(r'^(module|function)\s+(\w+)\s*\(', re.MULTILINE)

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
                    chunk_spans.append((start, end, match.group(1), match.group(2)))

                # If no modules/functions, chunk by 50 lines
                if not chunk_spans:
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
                            'text': chunk_text[:1000]  # preview
                        })
                        chunk_counter += 1
                else:
                    for start, end, def_type, def_name in chunk_spans:
                        chunk_text = code[start:end].strip()
                        chunk_id = f"chunk_{chunk_counter:05d}"
                        chunk_file = CHUNKS_DIR / f"{chunk_id}.txt"
                        with open(chunk_file, 'w') as cf:
                            cf.write(chunk_text)
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
                            'text': chunk_text[:1000]  # preview
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