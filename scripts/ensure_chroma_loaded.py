#!/usr/bin/env python3
"""
Ensure ChromaDB is properly initialized with embeddings.
This script verifies that embeddings are loaded either in Chroma DB or in memory.
"""

import os
import json
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
EMBEDDINGS_FILE = 'data/scad_embeddings_openai.jsonl'
CHROMA_DIR = 'data/chroma_db/'
COLLECTION_NAME = 'scad_chunks'

def ensure_chroma_directory():
    """Ensure the Chroma DB directory exists and is writable"""
    chroma_path = os.path.abspath(CHROMA_DIR)
    print(f"Checking Chroma DB directory: {chroma_path}")
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(chroma_path, exist_ok=True)
        
        # Check if the directory is writable
        test_file = os.path.join(chroma_path, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        print(f"✅ Chroma directory is valid and writable")
        return True
    except Exception as e:
        print(f"❌ Error with Chroma directory: {e}")
        return False

def check_embeddings_file():
    """Check if the embeddings file exists and is valid"""
    print(f"Checking embeddings file: {EMBEDDINGS_FILE}")
    
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"❌ Embeddings file not found: {EMBEDDINGS_FILE}")
        return False
    
    try:
        # Check if the file is valid JSON lines
        count = 0
        with open(EMBEDDINGS_FILE, 'r') as f:
            for line in f:
                json.loads(line)
                count += 1
                if count > 5:  # Just check the first few lines
                    break
        
        print(f"✅ Embeddings file is valid with data")
        return True
    except Exception as e:
        print(f"❌ Error validating embeddings file: {e}")
        return False

def check_chroma_collection():
    """Check if the Chroma collection exists and has data"""
    print(f"Checking Chroma collection: {COLLECTION_NAME}")
    
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        
        collections = client.list_collections()
        collection_exists = any(c.name == COLLECTION_NAME for c in collections)
        
        if not collection_exists:
            print(f"❌ Collection {COLLECTION_NAME} does not exist")
            return False
        
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        
        if count == 0:
            print(f"❌ Collection {COLLECTION_NAME} exists but is empty")
            return False
        
        print(f"✅ Collection {COLLECTION_NAME} exists with {count} entries")
        return True
    except Exception as e:
        print(f"❌ Error checking Chroma collection: {e}")
        return False

def import_embeddings_to_chroma():
    """Import embeddings from file to Chroma DB"""
    print(f"Importing embeddings to Chroma DB...")
    
    try:
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        
        # Create a new collection
        collection = client.get_or_create_collection(COLLECTION_NAME)
        
        # Load embeddings
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
        
        # Add embeddings in batches
        BATCH_SIZE = 1000
        for i in range(0, len(embeddings), BATCH_SIZE):
            end_idx = min(i+BATCH_SIZE, len(embeddings))
            print(f"Adding batch {i} to {end_idx}...")
            
            collection.add(
                embeddings=embeddings[i:end_idx],
                metadatas=metadatas[i:end_idx],
                documents=documents[i:end_idx],
                ids=ids[i:end_idx]
            )
        
        # Verify
        count = collection.count()
        print(f"✅ Successfully imported {count} embeddings to Chroma DB")
        return True
    except Exception as e:
        print(f"❌ Error importing embeddings to Chroma: {e}")
        traceback.print_exc()
        return False

def main():
    """Main function to ensure ChromaDB is properly loaded"""
    print("=== Checking RAG System ===")
    
    # Step 1: Check directory
    dir_ok = ensure_chroma_directory()
    if not dir_ok:
        print("Failed to validate Chroma directory")
        return False
    
    # Step 2: Check embeddings file
    embeddings_ok = check_embeddings_file()
    if not embeddings_ok:
        print("Failed to validate embeddings file")
        return False
    
    # Step 3: Check Chroma collection
    collection_ok = check_chroma_collection()
    
    # Step 4: Import embeddings if needed
    if not collection_ok:
        print("Chroma collection not ready, attempting to import embeddings...")
        import_ok = import_embeddings_to_chroma()
        if not import_ok:
            print("Failed to import embeddings to Chroma")
            print("The system will fall back to in-memory vector search")
        else:
            print("Successfully imported embeddings to Chroma")
    
    print("\n=== RAG System Check Complete ===")
    print("Your system will use:")
    if collection_ok or (not collection_ok and import_ok):
        print("✅ ChromaDB for vector search (preferred)")
    else:
        print("✅ In-memory vector search (fallback)")
    
    return True

if __name__ == "__main__":
    main() 