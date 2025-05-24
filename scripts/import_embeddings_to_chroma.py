import os
import json
import chromadb
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Paths
EMBEDDINGS_FILE = 'data/scad_embeddings_openai.jsonl'
CHROMA_DIR = 'data/chroma_db'
COLLECTION_NAME = 'scad_chunks'

print(f"Embeddings file path: {os.path.abspath(EMBEDDINGS_FILE)}")
print(f"Chroma DB directory: {os.path.abspath(CHROMA_DIR)}")

# Ensure Chroma directory exists
os.makedirs(CHROMA_DIR, exist_ok=True)
print(f"Chroma directory exists: {os.path.exists(CHROMA_DIR)}")

try:
    # Check if the embeddings file exists
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"Error: Embeddings file not found: {EMBEDDINGS_FILE}")
        exit(1)
    
    # Count total embeddings for progress tracking
    total_embeddings = 0
    with open(EMBEDDINGS_FILE, 'r') as f:
        for _ in f:
            total_embeddings += 1
    
    print(f"Found {total_embeddings} embeddings to import")
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # Create collection
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' created/accessed. Count: {collection.count()}")

    # Load embeddings and metadata
    print("Loading embeddings...")
    embeddings = []
    metadatas = []
    documents = []
    ids = []

    with open(EMBEDDINGS_FILE, 'r') as f:
        for i, line in enumerate(tqdm(f)):
            try:
                obj = json.loads(line)
                embeddings.append(obj['embedding'])
                metadatas.append({
                    "chunk_file": obj["chunk_file"],
                    "sub_chunk_index": obj.get("sub_chunk_index", 0)
                })
                documents.append(obj['text'])
                ids.append(f"{obj['chunk_file']}__{obj.get('sub_chunk_index', 0)}")
            except Exception as e:
                print(f"Error processing line {i}: {e}")
                print(f"Line content: {line[:100]}...")

    print(f"Loaded {len(embeddings)} embeddings, {len(metadatas)} metadata items, {len(documents)} documents, and {len(ids)} ids")

    BATCH_SIZE = 1000

    print(f"Adding {len(embeddings)} embeddings to Chroma DB in batches of {BATCH_SIZE}...")
    for i in range(0, len(embeddings), BATCH_SIZE):
        end_idx = min(i+BATCH_SIZE, len(embeddings))
        print(f"Adding batch {i} to {end_idx}...")
        try:
            collection.add(
                embeddings=embeddings[i:end_idx],
                metadatas=metadatas[i:end_idx],
                documents=documents[i:end_idx],
                ids=ids[i:end_idx]
            )
            print(f"Successfully added batch. New collection count: {collection.count()}")
        except Exception as e:
            print(f"Error adding batch {i} to {end_idx}: {e}")
            traceback.print_exc()
            
    print("Done! Chroma DB is ready.")
    print(f"Final collection count: {collection.count()}")

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
        print(f"Found {len(results['documents'][0])} results")
        for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
            print(f"Rank {i+1} (distance {dist:.4f}): {meta['chunk_file']} [sub-chunk {meta['sub_chunk_index']}]\n{doc[:200]}\n---")

    if __name__ == "__main__":
        # Example usage
        test_query = "rounded cube module"
        test_retrieval(test_query)
        
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc() 