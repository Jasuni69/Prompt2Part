import os
import json
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
import re
from openai import OpenAI

load_dotenv()

# Settings
CHROMA_DIR = 'data/chroma_db/'
COLLECTION_NAME = 'scad_chunks'
METADATA_FILE = 'data/scad_metadata.jsonl'
MAX_CHUNKS = 20
MIN_RELEVANCE_SCORE = 0.75  # Higher = stricter matching

# Get API key for embedding
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Warning: OPENAI_API_KEY not set. Using mock embeddings.")

# Load metadata for fast lookups
metadata_lookup = {}
if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                metadata_lookup[entry['chunk_id']] = entry
            except json.JSONDecodeError:
                continue

# Library/content specialization mapping
DOMAIN_LIBRARIES = {
    'thread': ['BOLTS_archive', 'threads-scad', 'NopSCADlib'],
    'gear': ['BOSL2', 'BOLTS_archive', 'BOSL'],
    'rounded': ['Round-Anything', 'BOSL2'],
    'mechanical': ['BOLTS_archive', 'NopSCADlib'],
    'electronic': ['NopSCADlib'],
    'case': ['YAPP_Box', 'constructive'],
    'enclosure': ['YAPP_Box', 'MarksEnclosureHelper'],
    'text': ['BOSL2', 'BOSL'],
}

def extract_entities(prompt):
    """Extract key entities and requirements from the prompt."""
    entities = {
        'shape_type': None,
        'parameters': [],
        'operations': [],
        'specific_modules': [],
        'target_libraries': [],
        'part_dimensions': {},
    }
    
    # Check for basic shapes
    basic_shapes = ['cube', 'sphere', 'cylinder', 'cone', 'text', 'polygon', 'polyhedron']
    for shape in basic_shapes:
        if re.search(r'\b' + shape + r'\b', prompt, re.IGNORECASE):
            entities['shape_type'] = shape
    
    # Check for operations
    operations = ['union', 'difference', 'intersection', 'translate', 'rotate', 'scale', 'mirror', 'extrude', 'hull', 'minkowski']
    for op in operations:
        if re.search(r'\b' + op + r'\b', prompt, re.IGNORECASE):
            entities['operations'].append(op)
    
    # Check for parameters and dimensions
    params = ['size', 'height', 'width', 'depth', 'diameter', 'radius', 'angle', 'thickness']
    for param in params:
        if re.search(r'\b' + param + r'\b', prompt, re.IGNORECASE):
            entities['parameters'].append(param)
    
    # Extract dimensions (like 5mm, 10cm, etc.)
    dim_pattern = r'(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in)'
    dim_matches = re.finditer(dim_pattern, prompt, re.IGNORECASE)
    for match in dim_matches:
        value = float(match.group(1))
        unit = match.group(2).lower()
        
        # Convert to mm for consistency
        if unit in ('cm'):
            value *= 10
        elif unit in ('m'):
            value *= 1000
        elif unit in ('inch', 'in'):
            value *= 25.4
            
        # Try to associate with nearby parameter
        text_before = prompt[:match.start()].lower()
        for param in ['height', 'width', 'depth', 'diameter', 'radius', 'length', 'thickness']:
            if param in text_before[-20:]:
                entities['part_dimensions'][param] = value
                break
        else:
            # If no specific parameter found, store as generic dimension
            if 'dimensions' not in entities['part_dimensions']:
                entities['part_dimensions']['dimensions'] = []
            entities['part_dimensions']['dimensions'].append(value)
    
    # Check for specialized domains and components
    
    # Threads, screws, bolts
    if any(term in prompt.lower() for term in ['thread', 'screw', 'bolt', 'nut', 'fastener']):
        entities['specific_modules'].append('thread')
        entities['target_libraries'].extend(DOMAIN_LIBRARIES['thread'])
        
        # Thread specific details
        thread_match = re.search(r'\bM(\d+)(?:x(\d+(?:\.\d+)?))?', prompt)
        if thread_match:
            diameter = int(thread_match.group(1))
            pitch = float(thread_match.group(2)) if thread_match.group(2) else None
            entities['part_dimensions']['thread_diameter'] = diameter
            if pitch:
                entities['part_dimensions']['thread_pitch'] = pitch
    
    # Gears
    if any(term in prompt.lower() for term in ['gear', 'cog', 'sprocket', 'rack', 'pinion']):
        entities['specific_modules'].append('gear')
        entities['target_libraries'].extend(DOMAIN_LIBRARIES['gear'])
        
        # Look for teeth count
        teeth_match = re.search(r'(\d+)\s*(?:tooth|teeth)', prompt, re.IGNORECASE)
        if teeth_match:
            entities['part_dimensions']['teeth'] = int(teeth_match.group(1))
    
    # Rounded shapes
    if any(term in prompt.lower() for term in ['round', 'rounded', 'fillet', 'chamfer']):
        entities['specific_modules'].append('rounded')
        entities['target_libraries'].extend(DOMAIN_LIBRARIES['rounded'])
    
    # Cases & enclosures
    if any(term in prompt.lower() for term in ['box', 'case', 'enclosure', 'housing', 'container']):
        entities['specific_modules'].append('enclosure')
        entities['target_libraries'].extend(DOMAIN_LIBRARIES['enclosure'])
    
    # Electronics
    if any(term in prompt.lower() for term in ['pcb', 'arduino', 'raspberry pi', 'electronic', 'board']):
        entities['specific_modules'].append('electronic')
        entities['target_libraries'].extend(DOMAIN_LIBRARIES['electronic'])
    
    # Text and labeling
    if any(term in prompt.lower() for term in ['text', 'label', 'letter', 'writing']):
        entities['specific_modules'].append('text')
        entities['target_libraries'].extend(DOMAIN_LIBRARIES['text'])
    
    # Remove duplicates from target libraries
    entities['target_libraries'] = list(set(entities['target_libraries']))
    
    return entities

def get_embedding(text):
    """Get embedding for text using OpenAI API."""
    if not api_key:
        # Mock embedding for testing
        return [0.1] * 1536
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.1] * 1536  # Mock embedding

def filter_results_by_library(results, target_libraries):
    """Filter results to prioritize chunks from specific libraries."""
    if not target_libraries:
        return results
    
    # Find chunks from target libraries
    prioritized = []
    for i, meta in enumerate(results["metadatas"][0]):
        chunk_id = meta.get("chunk_file", "").split("__")[0]
        if chunk_id in metadata_lookup:
            lib = metadata_lookup[chunk_id].get('library', '')
            if lib in target_libraries:
                prioritized.append(i)
    
    # If we have enough prioritized results, use only those
    if len(prioritized) >= 3:
        filtered_docs = [results["documents"][0][i] for i in prioritized]
        filtered_metas = [results["metadatas"][0][i] for i in prioritized]
        filtered_distances = [results["distances"][0][i] for i in prioritized]
        
        return {
            "documents": [filtered_docs],
            "metadatas": [filtered_metas],
            "distances": [filtered_distances]
        }
    
    return results

def semantic_search(query, n_results=MAX_CHUNKS, filter_libraries=None):
    """Perform semantic search using Chroma DB."""
    try:
        client = chromadb.Client(Settings(persist_directory=CHROMA_DIR))
        collection = client.get_or_create_collection(COLLECTION_NAME)
        
        query_embedding = get_embedding(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Apply library filtering if requested
        if filter_libraries:
            results = filter_results_by_library(results, filter_libraries)
            
        return results
    except Exception as e:
        print(f"Error in semantic search: {e}")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

def filter_by_examples(results, prefer_examples=True):
    """Filter results to prioritize chunks with usage examples."""
    if not prefer_examples:
        return results
    
    # Find chunks with examples
    has_examples = []
    for i, meta in enumerate(results["metadatas"][0]):
        chunk_id = meta.get("chunk_file", "").split("__")[0]  # Extract chunk_id from Chroma ID
        if chunk_id in metadata_lookup and metadata_lookup[chunk_id].get('has_examples', False):
            has_examples.append(i)
    
    # If we have examples, prioritize them
    if has_examples:
        filtered_docs = [results["documents"][0][i] for i in has_examples]
        filtered_metas = [results["metadatas"][0][i] for i in has_examples]
        filtered_distances = [results["distances"][0][i] for i in has_examples]
        
        # Make sure we have at least some minimum number of results
        if len(filtered_docs) >= 3:
            return {
                "documents": [filtered_docs],
                "metadatas": [filtered_metas],
                "distances": [filtered_distances]
            }
    
    return results

def create_enhanced_query(prompt, entities):
    """Create enhanced queries based on entity extraction."""
    queries = []
    
    # Add the main prompt as is
    queries.append(prompt)
    
    # Create specialized queries based on entity types
    if entities['shape_type']:
        shape_query = f"OpenSCAD code for {entities['shape_type']}"
        if entities['operations']:
            shape_query += f" with {', '.join(entities['operations'])}"
        queries.append(shape_query)
    
    # Add queries for specific modules
    for module in entities['specific_modules']:
        module_query = f"OpenSCAD {module} module example code"
        queries.append(module_query)
    
    # Add dimensions-based query
    if entities['part_dimensions']:
        dim_parts = []
        for key, value in entities['part_dimensions'].items():
            if key != 'dimensions':
                dim_parts.append(f"{key}={value}mm")
        
        if dim_parts:
            queries.append(f"OpenSCAD code with parameters {', '.join(dim_parts)}")
    
    return queries

def score_chunk_relevance(prompt, chunk_text, entities=None):
    """Score how relevant a chunk is to the prompt beyond vector similarity."""
    base_score = 1.0
    
    # If we have extracted entities, use them for scoring
    if entities:
        # Check for shape type matches
        if entities['shape_type'] and entities['shape_type'].lower() in chunk_text.lower():
            base_score += 0.5
            
        # Check for operations
        for op in entities['operations']:
            if op.lower() in chunk_text.lower():
                base_score += 0.2
                
        # Check for specific modules
        for module in entities['specific_modules']:
            pattern = r'module\s+\w*' + re.escape(module) + r'\w*\s*\('
            if re.search(pattern, chunk_text, re.IGNORECASE):
                base_score += 0.5
                
        # Bonus for examples
        if "example" in chunk_text.lower() or "// Usage:" in chunk_text:
            base_score += 0.3
            
        # Check for any dimensions mentioned in the chunk
        for key in entities['part_dimensions'].keys():
            if key != 'dimensions' and key in chunk_text.lower():
                base_score += 0.2
                
    # Check for direct keyword matches with the prompt
    prompt_keywords = set(re.findall(r'\b\w{3,}\b', prompt.lower()))
    chunk_keywords = set(re.findall(r'\b\w{3,}\b', chunk_text.lower()))
    keyword_matches = prompt_keywords.intersection(chunk_keywords)
    
    # Add score based on keyword matches
    keyword_score = len(keyword_matches) / max(len(prompt_keywords), 1) * 0.5
    base_score += keyword_score
    
    return base_score

def rerank_results(results, prompt, entities=None):
    """Rerank search results based on content analysis beyond vector similarity."""
    if not results or not results["documents"] or not results["documents"][0]:
        return results
        
    # Get current documents, metadatas, and distances
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0] if "distances" in results else [1.0] * len(docs)
    
    # Calculate content relevance scores
    content_scores = []
    for doc in docs:
        relevance = score_chunk_relevance(prompt, doc, entities)
        content_scores.append(relevance)
    
    # Create tuples with combined score (vector distance + content score)
    scored_results = []
    for i in range(len(docs)):
        # For vector distances, smaller is better, so we invert
        # Normalize both scores to 0-1 range
        normalized_distance = 1 - (distances[i] / 2)  # Typical distances are 0-2
        combined_score = (normalized_distance * 0.6) + (content_scores[i] * 0.4)
        scored_results.append((combined_score, docs[i], metas[i], distances[i]))
    
    # Sort by combined score (descending)
    scored_results.sort(reverse=True)
    
    # Extract sorted results
    sorted_docs = [item[1] for item in scored_results]
    sorted_metas = [item[2] for item in scored_results]
    sorted_distances = [item[3] for item in scored_results]
    
    # Return reranked results
    return {
        "documents": [sorted_docs],
        "metadatas": [sorted_metas],
        "distances": [sorted_distances]
    }

def retrieve_context(prompt, max_chunks=MAX_CHUNKS, selected_libraries=None):
    """
    Main function to retrieve relevant context for a prompt.
    Uses multi-query retrieval and reranking.
    
    Args:
        prompt (str): The user's prompt
        max_chunks (int): Maximum number of chunks to return
        selected_libraries (list): List of library names to focus on
        
    Returns:
        str: Formatted context with relevant code snippets
    """
    try:
        # Extract entities from the prompt
        entities = extract_entities(prompt)
        
        # If libraries were specified by the user, use those
        if selected_libraries:
            entities['target_libraries'] = selected_libraries
            
        # Create enhanced queries
        queries = create_enhanced_query(prompt, entities)
        
        # Perform searches with different queries and collect results
        all_results = []
        
        # Main query search
        main_results = semantic_search(prompt, n_results=max_chunks, 
                                      filter_libraries=entities['target_libraries'])
        if main_results and main_results["documents"] and main_results["documents"][0]:
            all_results.extend([(doc, meta) for doc, meta in 
                              zip(main_results["documents"][0], main_results["metadatas"][0])])
        
        # Run additional specialized queries
        for query in queries[1:]:  # Skip the first query which is the original prompt
            query_results = semantic_search(query, n_results=max(5, max_chunks // 3),
                                          filter_libraries=entities['target_libraries'])
            if query_results and query_results["documents"] and query_results["documents"][0]:
                all_results.extend([(doc, meta) for doc, meta in 
                                  zip(query_results["documents"][0], query_results["metadatas"][0])])
        
        # Deduplicate results
        seen_chunks = set()
        unique_results = []
        unique_metas = []
        
        for doc, meta in all_results:
            chunk_id = meta.get("chunk_file", "")
            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                unique_results.append(doc)
                unique_metas.append(meta)
                if len(unique_results) >= max_chunks:
                    break
        
        # Rerank the results
        combined_results = {
            "documents": [unique_results],
            "metadatas": [unique_metas]
        }
        
        reranked = rerank_results(combined_results, prompt, entities)
        
        # Format the top chunks into a context string
        context_parts = []
        
        # Add information about detected entities
        if entities['specific_modules'] or entities['target_libraries']:
            context_parts.append("// DESIGN CONSTRAINTS")
            if entities['specific_modules']:
                context_parts.append(f"// Specialized components: {', '.join(entities['specific_modules'])}")
            if entities['target_libraries']:
                context_parts.append(f"// Using libraries: {', '.join(entities['target_libraries'])}")
            if entities['part_dimensions']:
                dim_parts = []
                for key, value in entities['part_dimensions'].items():
                    if key != 'dimensions':
                        dim_parts.append(f"{key}={value}mm")
                if dim_parts:
                    context_parts.append(f"// Dimensions: {', '.join(dim_parts)}")
            context_parts.append("")
        
        # Add the code chunks with clear separation and metadata
        if reranked and reranked["documents"] and reranked["documents"][0]:
            context_parts.append("// REFERENCE CODE EXAMPLES")
            
            for i, (doc, meta) in enumerate(zip(reranked["documents"][0][:max_chunks], 
                                               reranked["metadatas"][0][:max_chunks])):
                # Extract useful metadata
                chunk_id = meta.get("chunk_file", "")
                library = ""
                file_path = ""
                
                if chunk_id in metadata_lookup:
                    library = metadata_lookup[chunk_id].get('library', '')
                    file_path = metadata_lookup[chunk_id].get('file_path', '')
                
                # Format metadata header for this chunk
                header = f"// EXAMPLE {i+1}: "
                if library:
                    header += f"from {library} library - "
                if file_path:
                    header += f"{file_path}"
                
                context_parts.append(header)
                context_parts.append(doc)
                context_parts.append("\n// -----------------------------------------------\n")
        
        # Format the full context string
        if context_parts:
            context_string = "\n".join(context_parts)
            return context_string
        
        return None
        
    except Exception as e:
        print(f"Error in retrieve_context: {e}")
        return None 