import os
import json
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
import re
from openai import OpenAI
import uuid
import numpy as np

load_dotenv()

# Settings
CHROMA_DIR = 'data/chroma_db_descriptions/'
COLLECTION_NAME = 'scad_descriptions'
METADATA_FILE = 'data/scad_descriptions_metadata.jsonl'
MAX_RESULTS = 20
MIN_RELEVANCE_SCORE = 0.3  # Adjusted for description-based search
EMBEDDINGS_FILE = 'data/scad_description_embeddings_large.jsonl'

# Get API key for embedding
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Warning: OPENAI_API_KEY not set. Using mock embeddings.")

# Flag to track if memory vectors have been loaded
MEMORY_LOADED = False

# Load metadata for fast lookups
metadata_lookup = {}
if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                metadata_lookup[entry['desc_id']] = entry
            except json.JSONDecodeError:
                continue

# Domain specialization mapping for descriptions
DOMAIN_KEYWORDS = {
    'thread': ['thread', 'screw', 'bolt', 'nut', 'fastener'],
    'gear': ['gear', 'tooth', 'teeth', 'cog', 'wheel'],
    'rounded': ['round', 'fillet', 'chamfer', 'smooth', 'curve'],
    'mechanical': ['bearing', 'shaft', 'joint', 'hinge', 'mechanical'],
    'electronic': ['pcb', 'circuit', 'electronic', 'connector', 'wire'],
    'case': ['case', 'box', 'enclosure', 'housing', 'container'],
    'text': ['text', 'font', 'letter', 'character', 'string'],
}

# In-memory database for fast retrieval
MEMORY_VECTORS = []
MEMORY_DESCRIPTIONS = []
MEMORY_CODES = []
MEMORY_METADATA = []
MEMORY_IDS = []


def load_memory_vectors():
    """Load description embeddings into memory for fast retrieval."""
    global MEMORY_VECTORS, MEMORY_DESCRIPTIONS, MEMORY_CODES, MEMORY_METADATA, MEMORY_IDS, MEMORY_LOADED

    # Skip if already loaded
    if MEMORY_LOADED:
        return True

    # Load from embeddings file
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"WARNING: Embeddings file not found: {EMBEDDINGS_FILE}")
        return False

    print(f"Loading description vectors into memory from {EMBEDDINGS_FILE}...")

    try:
        MEMORY_VECTORS = []
        MEMORY_DESCRIPTIONS = []
        MEMORY_CODES = []
        MEMORY_METADATA = []
        MEMORY_IDS = []

        with open(EMBEDDINGS_FILE, 'r') as f:
            for line in f:
                obj = json.loads(line)
                MEMORY_VECTORS.append(obj['embedding'])
                MEMORY_DESCRIPTIONS.append(obj['description'])
                MEMORY_CODES.append(obj['code'])
                MEMORY_METADATA.append({
                    "desc_id": obj["desc_id"],
                    "function_name": obj["function_name"],
                    "function_type": obj["function_type"],
                    "library": obj["library"],
                    "file": obj["file"],
                    "parameters": obj["parameters"]
                })
                MEMORY_IDS.append(obj['desc_id'])

        print(
            f"Successfully loaded {len(MEMORY_VECTORS)} description vectors into memory")
        MEMORY_LOADED = True
        return True
    except Exception as e:
        print(f"Error loading vectors into memory: {e}")
        return False


def memory_semantic_search(query, n_results=MAX_RESULTS):
    """Perform semantic search using in-memory description vectors."""
    global MEMORY_VECTORS, MEMORY_DESCRIPTIONS, MEMORY_CODES, MEMORY_METADATA, MEMORY_IDS

    # Load vectors if not already loaded
    if not MEMORY_VECTORS:
        load_memory_vectors()
        if not MEMORY_VECTORS:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    # Get query embedding
    query_embedding = get_embedding(query)

    # Compute cosine similarity
    similarities = []
    for vec in MEMORY_VECTORS:
        # Normalize vectors
        query_norm = np.linalg.norm(query_embedding)
        vec_norm = np.linalg.norm(vec)

        # Compute dot product
        if query_norm > 0 and vec_norm > 0:
            dot_product = np.dot(query_embedding, vec)
            similarity = dot_product / (query_norm * vec_norm)
            # Convert similarity to distance (0-2 range like Chroma)
            distance = 1 - similarity
            similarities.append(distance)
        else:
            similarities.append(2.0)  # Maximum distance

    # Sort by similarity (lowest distance first)
    sorted_indices = np.argsort(similarities)[:n_results]

    # Build result object like Chroma - but return codes instead of descriptions
    result_docs = [MEMORY_CODES[i]
                   for i in sorted_indices]  # Return the code, not description
    result_metas = [MEMORY_METADATA[i] for i in sorted_indices]
    result_distances = [similarities[i] for i in sorted_indices]

    return {
        "documents": [result_docs],
        "metadatas": [result_metas],
        "distances": [result_distances]
    }


def get_embedding(text):
    """Get embedding for text using OpenAI text-embedding-3-large model."""
    if not api_key:
        # Mock embedding for testing (3072 dimensions for text-embedding-3-large)
        return [0.1] * 3072

    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-3-large"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.1] * 3072  # Mock embedding


def semantic_search(query, n_results=MAX_RESULTS, filter_libraries=None):
    """Perform semantic search using description embeddings with reliable fallback to in-memory search."""
    # First try to preload memory vectors in case we need to fall back
    load_memory_vectors()

    try:
        # Try to use Chroma DB first
        try:
            # Create Chroma client with explicit persistence settings
            client = chromadb.PersistentClient(path=CHROMA_DIR)

            # Check if collection exists and has data
            collections = client.list_collections()
            collection_exists = any(
                c.name == COLLECTION_NAME for c in collections)

            if not collection_exists:
                print(
                    f"Collection {COLLECTION_NAME} not found, falling back to in-memory search")
                return memory_semantic_search(query, n_results)

            # Get the collection
            collection = client.get_collection(COLLECTION_NAME)

            # Verify collection has data
            count = collection.count()
            if count == 0:
                print(
                    f"Collection {COLLECTION_NAME} is empty, falling back to in-memory search")
                return memory_semantic_search(query, n_results)

            print(f"Using Chroma DB collection with {count} entries")

            # Get embedding for the query
            query_embedding = get_embedding(query)

            # Perform the query
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            return results

        except Exception as e:
            print(f"Chroma DB error: {e}, falling back to in-memory search")
            return memory_semantic_search(query, n_results)

    except Exception as e:
        print(f"Search error: {e}")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}


def filter_by_relevance(results, min_score=MIN_RELEVANCE_SCORE):
    """Filter results by relevance score."""
    if not results["distances"] or not results["distances"][0]:
        return results

    filtered_docs = []
    filtered_metas = []
    filtered_distances = []

    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        # Convert distance to similarity (1 - distance)
        similarity = 1 - dist
        if similarity >= min_score:
            filtered_docs.append(doc)
            filtered_metas.append(meta)
            filtered_distances.append(dist)

    return {
        "documents": [filtered_docs],
        "metadatas": [filtered_metas],
        "distances": [filtered_distances]
    }


def enhance_query_with_domain_keywords(query):
    """Enhance query with domain-specific keywords for better matching."""
    enhanced_query = query.lower()

    # Add relevant domain keywords
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in enhanced_query for keyword in keywords):
            # Add related keywords to improve matching
            related_keywords = [
                kw for kw in keywords if kw not in enhanced_query]
            if related_keywords:
                enhanced_query += " " + \
                    " ".join(related_keywords[:2])  # Add top 2 related

    return enhanced_query


def retrieve_context(query, max_results=MAX_RESULTS, filter_libraries=None):
    """
    Main retrieval function that searches descriptions and returns code.

    Args:
        query: User's search query
        max_results: Maximum number of results to return
        filter_libraries: Optional list of libraries to filter by

    Returns:
        String containing the retrieved code context
    """
    # Enhance query for better domain matching
    enhanced_query = enhance_query_with_domain_keywords(query)

    # Perform semantic search
    results = semantic_search(
        enhanced_query, n_results=max_results, filter_libraries=filter_libraries)

    # Filter by relevance
    filtered_results = filter_by_relevance(results)

    if not filtered_results["documents"] or not filtered_results["documents"][0]:
        return "No relevant OpenSCAD code found for your query."

    # Build context from retrieved code
    context_parts = []
    seen_functions = set()

    for i, (code, meta, distance) in enumerate(zip(
        filtered_results["documents"][0],
        filtered_results["metadatas"][0],
        filtered_results["distances"][0]
    )):
        # Avoid duplicates
        func_key = f"{meta.get('function_name', 'unknown')}_{meta.get('function_type', 'unknown')}"
        if func_key in seen_functions:
            continue
        seen_functions.add(func_key)

        # Add code with metadata
        similarity = 1 - distance
        context_parts.append(
            f"// {meta.get('function_type', 'unknown').capitalize()}: {meta.get('function_name', 'unknown')}")
        context_parts.append(f"// Library: {meta.get('library', 'unknown')}")
        context_parts.append(f"// Relevance: {similarity:.2f}")
        context_parts.append(
            f"// Parameters: {meta.get('parameters', 'none')}")
        context_parts.append("")
        context_parts.append(code.strip())
        context_parts.append("")
        context_parts.append("// " + "="*50)
        context_parts.append("")

    return "\n".join(context_parts)


# Initialize memory vectors on import
load_memory_vectors()
