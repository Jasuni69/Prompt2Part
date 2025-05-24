import chromadb
import os

# Constants
CHROMA_DIR = 'data/chroma_db'
COLLECTION_NAME = 'scad_chunks'

# Initialize ChromaDB
client = chromadb.PersistentClient(path=CHROMA_DIR)

# List collections
print("Collections in ChromaDB:")
collections = client.list_collections()
for collection in collections:
    print(f"- {collection.name}")

# Check the scad_chunks collection
try:
    collection = client.get_collection(COLLECTION_NAME)
    count = collection.count()
    print(f"\nCollection '{COLLECTION_NAME}' contains {count} embeddings")
    
    # Get some sample data
    if count > 0:
        print("\nSample data from collection:")
        results = collection.peek(5)
        
        for i, (id, doc) in enumerate(zip(results['ids'], results['documents'])):
            print(f"\n{i+1}. ID: {id}")
            print(f"Text: {doc[:150]}...")
except Exception as e:
    print(f"Error accessing collection: {e}") 