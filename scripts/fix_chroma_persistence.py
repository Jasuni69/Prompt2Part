#!/usr/bin/env python3
"""
Fix ChromaDB persistence issues.
This script ensures ChromaDB properly persists data to disk.
"""

import os
import shutil
import json
from tqdm import tqdm
import chromadb
from chromadb.config import Settings
import time

# Constants
EMBEDDINGS_FILE = 'data/scad_embeddings_openai.jsonl'
CHROMA_DIR = 'data/chroma_db'
COLLECTION_NAME = 'scad_chunks'

def clean_chroma_directory():
    """Completely remove and recreate the ChromaDB directory"""
    print(f"Cleaning ChromaDB directory: {CHROMA_DIR}")
    
    # Backup existing directory if it exists
    if os.path.exists(CHROMA_DIR):
        backup_dir = f"{CHROMA_DIR}_backup_{int(time.time())}"
        print(f"Creating backup at: {backup_dir}")
        shutil.copytree(CHROMA_DIR, backup_dir, dirs_exist_ok=True)
        
        # Remove existing directory
        print("Removing existing ChromaDB directory")
        shutil.rmtree(CHROMA_DIR)
    
    # Create fresh directory
    os.makedirs(CHROMA_DIR, exist_ok=True)
    print(f"Created fresh ChromaDB directory at: {CHROMA_DIR}")
    
    # Ensure directory is writable
    test_file = os.path.join(CHROMA_DIR, "test_write.tmp")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Directory is writable")
        return True
    except Exception as e:
        print(f"❌ Error: Directory is not writable: {e}")
        return False

def get_embeddings_count():
    """Get the count of embeddings in the file"""
    count = 0
    try:
        with open(EMBEDDINGS_FILE, 'r') as f:
            for _ in f:
                count += 1
        return count
    except Exception as e:
        print(f"Error counting embeddings: {e}")
        return 0

def import_embeddings():
    """Import embeddings to ChromaDB with proper persistence"""
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"❌ Error: Embeddings file not found: {EMBEDDINGS_FILE}")
        return False
    
    print(f"Importing embeddings from: {EMBEDDINGS_FILE}")
    
    # Get count for progress tracking
    total_embeddings = get_embeddings_count()
    print(f"Found {total_embeddings} embeddings to import")
    
    try:
        # Initialize ChromaDB with explicit settings for persistence
        client = chromadb.PersistentClient(
            path=CHROMA_DIR
        )
        
        # Create collection with optimal settings
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # Load and add embeddings in batches
        batch_size = 500
        batch_embeddings = []
        batch_metadatas = []
        batch_documents = []
        batch_ids = []
        
        # Keep track of a sample embedding for testing
        sample_embedding = None
        sample_id = None
        
        with open(EMBEDDINGS_FILE, 'r') as f:
            for i, line in enumerate(tqdm(f, total=total_embeddings)):
                try:
                    obj = json.loads(line)
                    
                    # Store sample embedding for testing
                    if sample_embedding is None:
                        sample_embedding = obj['embedding']
                        sample_id = f"{obj['chunk_file']}__{obj.get('sub_chunk_index', 0)}"
                    
                    batch_embeddings.append(obj['embedding'])
                    batch_documents.append(obj['text'])
                    batch_metadatas.append({
                        "chunk_file": obj["chunk_file"],
                        "sub_chunk_index": obj.get("sub_chunk_index", 0)
                    })
                    batch_ids.append(f"{obj['chunk_file']}__{obj.get('sub_chunk_index', 0)}")
                    
                    # Process in batches
                    if len(batch_embeddings) >= batch_size or i == total_embeddings - 1:
                        print(f"Adding batch of {len(batch_embeddings)} embeddings...")
                        
                        # Add the batch
                        collection.add(
                            embeddings=batch_embeddings,
                            documents=batch_documents,
                            metadatas=batch_metadatas,
                            ids=batch_ids
                        )
                        
                        # Clear the batches
                        batch_embeddings = []
                        batch_documents = []
                        batch_metadatas = []
                        batch_ids = []
                        
                        # Explicitly wait for persistence
                        time.sleep(0.1)
                
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {i}: {e}")
                except Exception as e:
                    print(f"Error processing line {i}: {e}")
        
        # Verify the collection has data
        count = collection.count()
        print(f"✅ Successfully imported {count} embeddings")
        
        # Perform a test query to verify functionality
        if count > 0 and sample_embedding is not None:
            print("Testing retrieval with a sample embedding...")
            try:
                query_results = collection.query(
                    query_embeddings=[sample_embedding],
                    n_results=1
                )
                
                if query_results and query_results["documents"] and query_results["documents"][0]:
                    print("✅ Retrieval is working")
                    print(f"Sample result: {query_results['documents'][0][0][:100]}...")
                    return True
                else:
                    print("❌ Retrieval test failed - no results")
                    return False
            except Exception as e:
                print(f"❌ Error during test query: {e}")
                return False
        
        return count > 0
    
    except Exception as e:
        print(f"❌ Error importing embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to fix ChromaDB persistence"""
    print("=== Fixing ChromaDB Persistence ===")
    
    # Step 1: Clean the ChromaDB directory
    if not clean_chroma_directory():
        print("Failed to prepare ChromaDB directory")
        return False
    
    # Step 2: Import embeddings with proper persistence
    if not import_embeddings():
        print("Failed to import embeddings to ChromaDB")
        return False
    
    print("\n=== ChromaDB Persistence Fix Complete ===")
    print("RAG system should now be using ChromaDB with proper persistence")
    return True

if __name__ == "__main__":
    main() 