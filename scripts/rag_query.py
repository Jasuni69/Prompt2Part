import os
import sys
import numpy as np
import json
import chromadb
from dotenv import load_dotenv
import openai
import argparse

# Load environment variables
load_dotenv()

# Constants
CHROMA_DIR = 'data/chroma_db'
COLLECTION_NAME = 'scad_chunks'
TOP_K = 10
MODEL = 'gpt-3.5-turbo'  # Change to 'gpt-4' if you have access

SYSTEM_PROMPT = (
    "You are an expert OpenSCAD code generator. "
    "Use the provided code snippets as references. "
    "If a relevant module (such as for gears) is available in the references, use it. "
    "Generate valid OpenSCAD code that fulfills the user's request. "
    "Only output code, no explanations."
)

# Get user query
if len(sys.argv) < 2:
    print("Usage: python scripts/rag_query.py \"<your query>\"")
    sys.exit(1)
user_query = sys.argv[1]

def get_embedding(query):
    """Get OpenAI embedding for a query."""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        # Use mock embedding (this is for demo purposes)
        return [0.0] * 1536
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=query,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.0] * 1536

def query_chroma(query):
    """Query ChromaDB for similar code snippets."""
    try:
        # Initialize Chroma
        client_chroma = chromadb.PersistentClient(path=CHROMA_DIR)
        
        # Get collection
        collection = client_chroma.get_collection(COLLECTION_NAME)
        
        # Get embedding for query
        query_embedding = get_embedding(query)
        
        # Retrieve top-k relevant chunks
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K,
            include=["documents", "metadatas"]
        )

        # Build context string
        context = "\n\n".join(
            f"// Reference {i+1}: {meta['chunk_file']} [sub-chunk {meta['sub_chunk_index']}]:\n{doc}"
            for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]))
        )

        # Construct messages for OpenAI chat
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Reference code:\n{context}\n\nUser request: {query}\n\nOpenSCAD code:"}
        ]

        # Generate code
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=512
        )

        # Print only the generated code
        print(completion.choices[0].message.content.strip())
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")

query_chroma(user_query) 