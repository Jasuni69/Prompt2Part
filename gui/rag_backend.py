import os
import chromadb
import json
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
import glob
import re

load_dotenv()

CHROMA_DIR = 'data/chroma_db'
COLLECTION_NAME = 'scad_chunks'
TOP_K = 10
MODEL = 'gpt-3.5-turbo'

SYSTEM_PROMPT = (
    "You are an expert OpenSCAD code generator. "
    "For any prompt, if the user prompt is a simple primitive (cube, sphere, etc.), generate minimal valid OpenSCAD code using any dimensions or parameters provided in the prompt. "
    "For more complex or composite prompts, use best practices and the provided code examples as context. "
    "Strictly follow these rules: "
    "Only use standard OpenSCAD primitives and syntax. "
    "Never invent or use functions that are not part of OpenSCAD. "
    "For spheres: if the user specifies a diameter, use sphere(d=...); if a radius, use sphere(r=...). "
    "Output only the minimal valid OpenSCAD code for the user's request, with no explanations or comments."
)

class ChromaRAG:
    def __init__(self):
        """Initialize ChromaDB connection."""
        self.client = None
        self.collection = None
        self.ensure_connection()
    
    def ensure_connection(self):
        """Ensure connection to ChromaDB."""
        try:
            # Initialize Chroma with persistent client
            self.client = chromadb.PersistentClient(path=CHROMA_DIR)
            
            # Get collection if it exists, otherwise fall back to mock
            collections = self.client.list_collections()
            if any(c.name == COLLECTION_NAME for c in collections):
                self.collection = self.client.get_collection(COLLECTION_NAME)
                print(f"Connected to ChromaDB collection: {COLLECTION_NAME}")
                print(f"Collection has {self.collection.count()} items")
            else:
                print(f"Warning: Collection {COLLECTION_NAME} not found")
                self.collection = None
            
            return self.collection is not None
        except Exception as e:
            print(f"Error connecting to ChromaDB: {e}")
            return False

def get_all_scad_library_uses(library_dirs=["scad_library"]):
    use_lines = []
    for lib_dir in library_dirs:
        for scad_file in glob.glob(f"{lib_dir}/**/*.scad", recursive=True):
            use_lines.append(f'use <{scad_file}>;')
    return '\n'.join(use_lines)

def verify_scad_library_modules(library_dirs=["scad_library"]):
    print("Verifying all .scad modules in:", library_dirs)
    scad_files = []
    for lib_dir in library_dirs:
        for scad_file in glob.glob(f"{lib_dir}/**/*.scad", recursive=True):
            scad_files.append(scad_file)
    print(f"Found {len(scad_files)} .scad files:")
    for scad_file in scad_files:
        print(f"  {scad_file}")
    print("\nCorresponding use <...>; lines:")
    for scad_file in scad_files:
        print(f'use <{scad_file}>;')

def load_symbol_index(index_file="available_modules.json"):
    try:
        with open(index_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load symbol index: {e}")
        return {"modules": [], "functions": []}

def extract_called_symbols(code):
    # Find all module and function calls in the code
    module_calls = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code))
    return module_calls

def filter_rag_context_by_modules(context, relevant_modules):
    # Only keep code examples that use at least one relevant module
    if not relevant_modules:
        return context
    filtered = []
    for block in context.split('\n\n'):
        if any(f'{mod}(' in block for mod in relevant_modules):
            filtered.append(block)
    return '\n\n'.join(filtered) if filtered else context

def find_closest_symbol(requested, symbol_index):
    # Simple case-insensitive match, fallback to fuzzy match if needed
    requested_lower = requested.lower()
    all_symbols = symbol_index["modules"] + symbol_index["functions"]
    # Exact case-insensitive match
    for sym in all_symbols:
        if sym.lower() == requested_lower:
            return sym
    # Fuzzy: startswith or contains
    for sym in all_symbols:
        if requested_lower in sym.lower() or sym.lower() in requested_lower:
            return sym
    # Fallback: return None
    return None

def generate_openscad_code(user_query: str) -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('Please set the OPENAI_API_KEY environment variable.')
    client = OpenAI(api_key=api_key)
    client_chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client_chroma.get_collection(COLLECTION_NAME)
    # Embed the query
    response = client.embeddings.create(
        input=[user_query],
        model="text-embedding-ada-002"
    )
    query_embedding = response.data[0].embedding
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
    # Multi-layer RAG: select relevant modules for the prompt
    symbol_index = load_symbol_index()
    relevant_modules = select_libraries_for_prompt(user_query, symbol_index)
    # --- Symbol suggestion logic ---
    # If the prompt requests a common object, suggest the closest available symbol
    entities = extract_entities_from_prompt(user_query)
    suggestions = {}
    for ent in entities:
        closest = find_closest_symbol(ent, symbol_index)
        if closest and closest != ent:
            suggestions[ent] = closest
    # If suggestions exist, add to system prompt
    suggestion_text = ""
    if suggestions:
        suggestion_text = ("\nFor this prompt, use the following available modules/functions instead of the requested names: " +
            ", ".join(f"'{k}' → '{v}'" for k, v in suggestions.items()) + ". ")
    # Filter RAG context to only include code using relevant modules
    filtered_context = filter_rag_context_by_modules(context, relevant_modules)
    # Dynamic system prompt
    if relevant_modules:
        system_prompt = (
            "You are an expert OpenSCAD code generator. "
            f"For this prompt, you may use only the following modules/functions: {', '.join(sorted(relevant_modules))}. "
            "If you need to use other features, use only built-in OpenSCAD primitives. "
            "Never invent or use functions that are not part of OpenSCAD or the allowed modules. "
            "Output only the minimal valid OpenSCAD code for the user's request, with no explanations or comments."
            + suggestion_text
        )
    else:
        system_prompt = (
            "You are an expert OpenSCAD code generator. "
            "For this prompt, use only built-in OpenSCAD primitives. "
            "Never invent or use functions that are not part of OpenSCAD. "
            "Output only the minimal valid OpenSCAD code for the user's request, with no explanations or comments."
            + suggestion_text
        )
    # Construct messages for OpenAI chat
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Reference code:\n{filtered_context}\n\nUser request: {user_query}\n\nOpenSCAD code:"}
    ]
    # Generate code
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=512
    )
    code = completion.choices[0].message.content.strip()
    # Post-generation validation
    available = set(symbol_index["modules"]) | set(symbol_index["functions"])
    called = extract_called_symbols(code)
    undefined = [sym for sym in called if sym not in available and sym not in {"module", "function"}]
    # --- Minimal use statement logic ---
    # Map symbol to file(s) using symbol_index
    symbol_to_file = {}
    for entry in symbol_index.get("module_files", []) + symbol_index.get("function_files", []):
        symbol_to_file.setdefault(entry["name"], set()).add(entry["file"])
    needed_files = set()
    for sym in called:
        if sym in symbol_to_file:
            needed_files.update(symbol_to_file[sym])
    # Only prepend use statements for needed files
    use_block = "\n".join(f'use <{scad_file}>;' for scad_file in sorted(needed_files))
    full_code = f'{use_block}\n\n{code}' if use_block else code
    if undefined:
        warning = f"// WARNING: The following modules/functions are not available in your libraries: {', '.join(undefined)}\n"
        return warning + full_code
    return full_code

def extract_entities_from_prompt(prompt):
    # Simple keyword/entity extraction (can be improved with LLM)
    # Extract words that could be module/function names
    words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', prompt.lower()))
    # Remove common English words (stopwords)
    stopwords = {"a", "the", "with", "for", "and", "to", "of", "in", "on", "at", "by", "is", "as", "an", "from", "that", "it", "this", "be", "or", "use", "using", "make", "create", "generate", "model", "part", "object", "module", "function", "scad", "parametric", "simple", "complex", "shape", "3d", "print", "printer", "design"}
    entities = [w for w in words if w not in stopwords]
    return entities

def find_relevant_libraries(entities, symbol_index):
    # Map module/function to file (from symbol index)
    # For now, just match module/function names
    relevant = set()
    for entity in entities:
        if entity in symbol_index["modules"] or entity in symbol_index["functions"]:
            relevant.add(entity)
    return relevant

def select_libraries_for_prompt(prompt, symbol_index=None):
    if symbol_index is None:
        symbol_index = load_symbol_index()
    entities = extract_entities_from_prompt(prompt)
    relevant = find_relevant_libraries(entities, symbol_index)
    return relevant 