import os
import json
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv

# Paths
EMBEDDINGS_FILE = 'data/scad_embeddings_openai.jsonl'
CHROMA_DIR = 'data/chroma_db/'

# Chroma setup
client = chromadb.Client(Settings(persist_directory=CHROMA_DIR))
collection = client.get_or_create_collection("scad_chunks")

# Load embeddings and metadata
print("Loading embeddings...")
embeddings = []
metadatas = []
documents = []
ids = []

with open(EMBEDDINGS_FILE, 'r') as f:
    for i, line in enumerate(tqdm(f)):
        obj = json.loads(line)
        embeddings.append(obj['embedding'])
        metadatas.append({
            "chunk_file": obj["chunk_file"],
            "sub_chunk_index": obj.get("sub_chunk_index", 0)
        })
        documents.append(obj['text'])
        ids.append(f"{obj['chunk_file']}__{obj.get('sub_chunk_index', 0)}")

BATCH_SIZE = 1000

print(f"Adding {len(embeddings)} embeddings to Chroma DB in batches of {BATCH_SIZE}...")
for i in range(0, len(embeddings), BATCH_SIZE):
    collection.add(
        embeddings=embeddings[i:i+BATCH_SIZE],
        metadatas=metadatas[i:i+BATCH_SIZE],
        documents=documents[i:i+BATCH_SIZE],
        ids=ids[i:i+BATCH_SIZE]
    )
print("Done! Chroma DB is ready.")

def get_openai_query_embedding(query):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('Please set the OPENAI_API_KEY environment variable.')
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        input=[query],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

# Simple retrieval test
def test_retrieval(query, top_k=5):
    print(f"\nRetrieving for query: {query}")
    query_embedding = get_openai_query_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
        print(f"Rank {i+1} (distance {dist:.4f}): {meta['chunk_file']} [sub-chunk {meta['sub_chunk_index']}]\n{doc[:200]}\n---")

if __name__ == "__main__":
    # Example usage
    test_query = "rounded cube module"
    test_retrieval(test_query) 