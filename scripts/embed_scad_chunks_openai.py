import os
import glob
import json
import time
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv
import tiktoken

# Load environment variables from .env if present
load_dotenv()

# Settings
CHUNKS_DIR = 'data/scad_chunks/'
OUTPUT_FILE = 'data/scad_embeddings_openai.jsonl'
BATCH_SIZE = 100  # OpenAI API supports up to 2048 tokens per request, but we'll use 100 for safety
SLEEP_BETWEEN_BATCHES = 1  # seconds

# Get API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise EnvironmentError('Please set the OPENAI_API_KEY environment variable.')

client = OpenAI(api_key=api_key)

# Find all chunk files
chunk_files = sorted(glob.glob(os.path.join(CHUNKS_DIR, '*.txt')))

# Resume support: find already embedded chunks
embedded_files = set()
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                embedded_files.add(obj['chunk_file'])
            except Exception:
                continue

# Filter out already embedded
to_embed = [f for f in chunk_files if os.path.basename(f) not in embedded_files]

print(f"Found {len(chunk_files)} chunks, {len(to_embed)} to embed.")

# Tokenizer setup for OpenAI models
tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")
MAX_TOKENS = 2000
OVERLAP = 100
MAX_BATCH_TOKENS = 1500  # New: max tokens per batch for safety

def split_by_tokens(text, max_tokens=MAX_TOKENS, overlap=OVERLAP):
    tokens = tokenizer.encode(text)
    sub_chunks = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        sub_chunk_tokens = tokens[start:end]
        sub_chunk_text = tokenizer.decode(sub_chunk_tokens)
        sub_chunks.append((sub_chunk_text, idx))
        idx += 1
        start += max_tokens - overlap
    return sub_chunks

def batch_by_token_limit(sub_chunks, tokenizer, max_batch_tokens=MAX_BATCH_TOKENS):
    batches = []
    current_batch = []
    current_tokens = 0
    for sub_text, sub_idx, file in sub_chunks:
        tokens = tokenizer.encode(sub_text)
        if current_tokens + len(tokens) > max_batch_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append((sub_text, sub_idx, file))
        current_tokens += len(tokens)
    if current_batch:
        batches.append(current_batch)
    return batches

with open(OUTPUT_FILE, 'a') as out_f:
    all_sub_chunks = []
    for file in to_embed:
        with open(file, 'r') as f:
            text = f.read()
            sub_chunks = split_by_tokens(text)
            for sub_text, sub_idx in sub_chunks:
                all_sub_chunks.append((sub_text, sub_idx, file))
    batches = batch_by_token_limit(all_sub_chunks, tokenizer)
    for batch_i, batch in enumerate(tqdm(batches)):
        batch_texts = [sub_text for (sub_text, sub_idx, file) in batch]
        batch_indices = [(file, sub_idx, sub_text) for (sub_text, sub_idx, file) in batch]
        try:
            response = client.embeddings.create(
                input=batch_texts,
                model="text-embedding-ada-002"
            )
            for (file, sub_idx, sub_text), emb in zip(batch_indices, response.data):
                obj = {
                    "chunk_file": os.path.basename(file),
                    "sub_chunk_index": sub_idx,
                    "text": sub_text,
                    "embedding": emb.embedding
                }
                out_f.write(json.dumps(obj) + '\n')
                out_f.flush()
        except Exception as e:
            print(f"Batch {batch_i} failed: {e}\nFalling back to single sub-chunk embedding.")
            for (file, sub_idx, sub_text) in batch_indices:
                try:
                    response = client.embeddings.create(
                        input=[sub_text],
                        model="text-embedding-ada-002"
                    )
                    emb = response.data[0]
                    obj = {
                        "chunk_file": os.path.basename(file),
                        "sub_chunk_index": sub_idx,
                        "text": sub_text,
                        "embedding": emb.embedding
                    }
                    out_f.write(json.dumps(obj) + '\n')
                    out_f.flush()
                except Exception as e2:
                    print(f"  Skipped {os.path.basename(file)} (sub-chunk {sub_idx}): {e2}")
            continue
        time.sleep(SLEEP_BETWEEN_BATCHES)
print("Embedding complete.") 