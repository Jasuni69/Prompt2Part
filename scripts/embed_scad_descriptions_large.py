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
DESCRIPTIONS_DIR = 'data/scad_descriptions/'
OUTPUT_FILE = 'data/scad_description_embeddings_large.jsonl'
BATCH_SIZE = 100  # Process descriptions in batches
SLEEP_BETWEEN_BATCHES = 1  # seconds

# Get API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise EnvironmentError(
        'Please set the OPENAI_API_KEY environment variable.')

client = OpenAI(api_key=api_key)

# Find all description files
description_files = sorted(glob.glob(os.path.join(DESCRIPTIONS_DIR, '*.json')))

# Resume support: find already embedded descriptions
embedded_ids = set()
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                embedded_ids.add(obj['desc_id'])
            except Exception:
                continue

print(f"Found {len(description_files)} description files, {len(embedded_ids)} already embedded.")

# Tokenizer setup for OpenAI models
tokenizer = tiktoken.encoding_for_model("text-embedding-3-large")
MAX_TOKENS = 8000  # text-embedding-3-large supports up to 8191 tokens
MAX_BATCH_TOKENS = 6000  # Conservative limit for batch processing


def truncate_description(description, max_tokens=MAX_TOKENS):
    """Truncate description if it exceeds token limit."""
    tokens = tokenizer.encode(description)
    if len(tokens) <= max_tokens:
        return description

    # Truncate and decode back to text
    truncated_tokens = tokens[:max_tokens]
    return tokenizer.decode(truncated_tokens)


def batch_by_token_limit(descriptions, max_batch_tokens=MAX_BATCH_TOKENS):
    """Group descriptions into batches that don't exceed token limits."""
    batches = []
    current_batch = []
    current_tokens = 0

    for desc_data in descriptions:
        description = desc_data['description']
        tokens = tokenizer.encode(description)

        if current_tokens + len(tokens) > max_batch_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(desc_data)
        current_tokens += len(tokens)

    if current_batch:
        batches.append(current_batch)

    return batches


# Load all descriptions to embed
descriptions_to_embed = []
for desc_file in description_files:
    try:
        with open(desc_file, 'r') as f:
            desc_data = json.load(f)

        # Skip if already embedded
        if desc_data['id'] in embedded_ids:
            continue

        # Truncate description if needed
        desc_data['description'] = truncate_description(
            desc_data['description'])
        descriptions_to_embed.append(desc_data)

    except Exception as e:
        print(f"Error loading {desc_file}: {e}")
        continue

print(f"Processing {len(descriptions_to_embed)} new descriptions...")

# Group into batches
batches = batch_by_token_limit(descriptions_to_embed)
print(f"Created {len(batches)} batches for processing")

# Process batches
with open(OUTPUT_FILE, 'a') as out_f:
    for batch_i, batch in enumerate(tqdm(batches, desc="Processing batches")):
        batch_descriptions = [desc_data['description'] for desc_data in batch]

        try:
            # Create embeddings for the batch
            response = client.embeddings.create(
                input=batch_descriptions,
                model="text-embedding-3-large"
            )

            # Save embeddings
            for desc_data, embedding_obj in zip(batch, response.data):
                output_obj = {
                    "desc_id": desc_data['id'],
                    "function_name": desc_data['function_name'],
                    "function_type": desc_data['function_type'],
                    "library": desc_data['library'],
                    "file": desc_data['file'],
                    # The embedded text
                    "description": desc_data['description'],
                    "code": desc_data['code'],  # The full code (value)
                    "parameters": desc_data['parameters'],
                    "embedding": embedding_obj.embedding
                }
                out_f.write(json.dumps(output_obj) + '\n')
                out_f.flush()

        except Exception as e:
            print(f"Batch {batch_i} failed: {e}")
            print("Falling back to individual description embedding...")

            # Fall back to individual processing
            for desc_data in batch:
                try:
                    response = client.embeddings.create(
                        input=[desc_data['description']],
                        model="text-embedding-3-large"
                    )

                    output_obj = {
                        "desc_id": desc_data['id'],
                        "function_name": desc_data['function_name'],
                        "function_type": desc_data['function_type'],
                        "library": desc_data['library'],
                        "file": desc_data['file'],
                        "description": desc_data['description'],
                        "code": desc_data['code'],
                        "parameters": desc_data['parameters'],
                        "embedding": response.data[0].embedding
                    }
                    out_f.write(json.dumps(output_obj) + '\n')
                    out_f.flush()

                except Exception as e2:
                    print(
                        f"  Skipped {desc_data['function_name']} ({desc_data['id']}): {e2}")
                    continue

        # Rate limiting
        time.sleep(SLEEP_BETWEEN_BATCHES)

print("Embedding complete.")
print(f"Embeddings saved to: {OUTPUT_FILE}")

# Print summary statistics
total_embeddings = 0
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r') as f:
        for _ in f:
            total_embeddings += 1

print(f"Total embeddings in file: {total_embeddings}")

# Analyze the embeddings
modules = 0
functions = 0
libraries = set()

if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj['function_type'] == 'module':
                    modules += 1
                elif obj['function_type'] == 'function':
                    functions += 1
                if obj['library']:
                    libraries.add(obj['library'])
            except:
                continue

print(f"\nEmbedding Summary:")
print(f"- Modules: {modules}")
print(f"- Functions: {functions}")
print(f"- Libraries: {len(libraries)}")
print(f"- Model used: text-embedding-3-large")
print(f"- Embedding dimension: 3072")
