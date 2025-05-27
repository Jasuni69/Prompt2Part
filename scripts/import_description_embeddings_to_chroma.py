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
EMBEDDINGS_FILE = 'data/scad_description_embeddings_large.jsonl'
CHROMA_DIR = 'data/chroma_db_descriptions'
COLLECTION_NAME = 'scad_descriptions'

print(f"Embeddings file path: {os.path.abspath(EMBEDDINGS_FILE)}")
print(f"Chroma DB directory: {os.path.abspath(CHROMA_DIR)}")

# Ensure Chroma directory exists
os.makedirs(CHROMA_DIR, exist_ok=True)
print(f"Chroma directory exists: {os.path.exists(CHROMA_DIR)}")

try:
    # Check if the embeddings file exists
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"Error: Embeddings file not found: {EMBEDDINGS_FILE}")
        print("Please run 'python scripts/embed_scad_descriptions_large.py' first.")
        exit(1)

    # Count total embeddings for progress tracking
    total_embeddings = 0
    with open(EMBEDDINGS_FILE, 'r') as f:
        for _ in f:
            total_embeddings += 1

    print(f"Found {total_embeddings} description embeddings to import")

    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection if it exists
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")
    except:
        pass

    # Create new collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        # Use cosine similarity for better semantic matching
        metadata={"hnsw:space": "cosine"}
    )
    print(f"Created new collection '{COLLECTION_NAME}'")

    # Load embeddings and metadata
    print("Loading description embeddings...")
    embeddings = []
    metadatas = []
    documents = []  # This will store the code, not the description
    ids = []

    with open(EMBEDDINGS_FILE, 'r') as f:
        for i, line in enumerate(tqdm(f, total=total_embeddings, desc="Loading embeddings")):
            try:
                obj = json.loads(line)
                embeddings.append(obj['embedding'])
                metadatas.append({
                    "desc_id": obj["desc_id"],
                    "function_name": obj["function_name"],
                    "function_type": obj["function_type"],
                    "library": obj["library"],
                    "file": obj["file"],
                    "parameters": obj["parameters"]
                })
                # Store the code as the document (what gets retrieved)
                documents.append(obj['code'])
                ids.append(obj['desc_id'])
            except Exception as e:
                print(f"Error processing line {i}: {e}")
                print(f"Line content: {line[:100]}...")

    print(f"Loaded {len(embeddings)} embeddings, {len(metadatas)} metadata items, {len(documents)} code documents, and {len(ids)} ids")

    BATCH_SIZE = 1000

    print(
        f"Adding {len(embeddings)} description embeddings to Chroma DB in batches of {BATCH_SIZE}...")
    for i in range(0, len(embeddings), BATCH_SIZE):
        end_idx = min(i+BATCH_SIZE, len(embeddings))
        print(
            f"Adding batch {i//BATCH_SIZE + 1}/{(len(embeddings)-1)//BATCH_SIZE + 1}: items {i} to {end_idx-1}...")
        try:
            collection.add(
                embeddings=embeddings[i:end_idx],
                metadatas=metadatas[i:end_idx],
                documents=documents[i:end_idx],  # Code documents
                ids=ids[i:end_idx]
            )
            print(
                f"Successfully added batch. New collection count: {collection.count()}")
        except Exception as e:
            print(f"Error adding batch {i} to {end_idx}: {e}")
            traceback.print_exc()

    print("Done! Chroma DB is ready.")
    print(f"Final collection count: {collection.count()}")

    def get_openai_query_embedding(query):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise EnvironmentError(
                'Please set the OPENAI_API_KEY environment variable.')
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=[query],
            model="text-embedding-3-large"
        )
        return response.data[0].embedding

    # Simple retrieval test
    def test_retrieval(query, top_k=5):
        print(f"\nTesting retrieval for query: '{query}'")
        try:
            query_embedding = get_openai_query_embedding(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            print(f"Found {len(results['documents'][0])} results")
            for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
                similarity = 1 - dist
                print(f"\nRank {i+1} (similarity {similarity:.3f}):")
                print(
                    f"  Function: {meta['function_type']} {meta['function_name']}")
                print(f"  Library: {meta['library']}")
                print(f"  Parameters: {meta['parameters']}")
                print(f"  Code preview: {doc[:150]}...")
                print("  " + "-"*50)
        except Exception as e:
            print(f"Error during test retrieval: {e}")

    # Test with different queries
    test_queries = [
        "rounded cube module",
        "gear with teeth",
        "thread screw bolt",
        "electronic connector",
        "text font"
    ]

    for query in test_queries:
        test_retrieval(query, top_k=3)

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()

print(f"\nDescription-based RAG system is ready!")
print(f"- Embeddings model: text-embedding-3-large")
print(f"- Embedding dimension: 3072")
print(f"- Search approach: Description → Code retrieval")
print(f"- Collection: {COLLECTION_NAME}")
print(f"- Database: {CHROMA_DIR}")
