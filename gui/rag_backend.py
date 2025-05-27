import os
import chromadb
import json
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
import glob
import re
# Import the new description-based retriever
from rag.description_retriever import retrieve_context

load_dotenv()

# Updated to use description-based system
CHROMA_DIR = 'data/chroma_db_descriptions/'
COLLECTION_NAME = 'scad_descriptions'
TOP_K = 10
MODEL = 'gpt-3.5-turbo'

SYSTEM_PROMPT = (
    "You are an expert OpenSCAD code generator. "
    "You will be provided with relevant OpenSCAD functions and modules as context. "
    "Use these provided functions when they match the user's request. "
    "For simple primitives (cube, sphere, etc.), you may use standard OpenSCAD syntax. "
    "Strictly follow these rules: "
    "Only use the provided functions or standard OpenSCAD primitives. "
    "Never invent functions that are not provided in the context. "
    "For spheres: if the user specifies a diameter, use sphere(d=...); if a radius, use sphere(r=...). "
    "Output only the minimal valid OpenSCAD code for the user's request, with no explanations or comments."
)

# Threading function mappings for proper library selection
THREADING_FUNCTIONS = {
    'trapezoidal_threaded_rod': 'BOSL2',
    'trapezoidal_threaded_nut': 'BOSL2',
    'metric_trapezoidal_threaded_rod': 'BOSL',
    'metric_trapezoidal_threaded_nut': 'BOSL',
    'threaded_rod': 'BOSL2',  # Available in both, but BOSL2 is preferred
    'threaded_nut': 'BOSL2',
    'acme_threaded_rod': 'BOSL2',
    'acme_threaded_nut': 'BOSL2',
    'square_threaded_rod': 'BOSL2',
    'square_threaded_nut': 'BOSL2',
    'ball_screw_rod': 'BOSL2',
    'generic_threaded_rod': 'BOSL2',
    'npt_threaded_rod': 'BOSL2',
    'buttress_threaded_rod': 'BOSL2',
    'buttress_threaded_nut': 'BOSL2'
}


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
    """Generate OpenSCAD code using the new description-based RAG system."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError(
            'Please set the OPENAI_API_KEY environment variable.')

    client = OpenAI(api_key=api_key)

    # Use the new description-based retrieval system
    context = retrieve_context(user_query, max_results=TOP_K)

    # If no relevant context found, use basic system prompt
    if context == "No relevant OpenSCAD code found for your query.":
        system_prompt = (
            "You are an expert OpenSCAD code generator. "
            "Use only built-in OpenSCAD primitives and syntax. "
            "Never invent functions that are not part of OpenSCAD. "
            "Output only the minimal valid OpenSCAD code for the user's request, with no explanations or comments."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User request: {user_query}\n\nOpenSCAD code:"}
        ]
    else:
        # Use the enhanced system prompt with retrieved context
        system_prompt = (
            "You are an expert OpenSCAD code generator. "
            "You will be provided with relevant OpenSCAD functions and modules as context. "
            "Use these provided functions when they match the user's request. "
            "For simple primitives (cube, sphere, etc.), you may use standard OpenSCAD syntax. "
            "IMPORTANT THREADING RULES: "
            "- For trapezoidal_threaded_rod, trapezoidal_threaded_nut: these are from BOSL library "
            "- For threaded_rod, acme_threaded_rod, square_threaded_rod: these are from BOSL2 library "
            "- Always use the exact function names provided in the context "
            "Strictly follow these rules: "
            "Only use the provided functions or standard OpenSCAD primitives. "
            "Never invent functions that are not provided in the context. "
            "Output only the minimal valid OpenSCAD code for the user's request, with no explanations or comments."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Available OpenSCAD functions and modules:\n{context}\n\nUser request: {user_query}\n\nOpenSCAD code:"}
        ]

    # Generate code
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=512
    )

    code = completion.choices[0].message.content.strip()

    # Clean up the code (remove markdown formatting if present)
    code = re.sub(r'```[a-zA-Z]*\n?', '', code)
    code = code.replace('```', '')

    # Extract libraries from context and add use statements
    libraries_used = extract_libraries_from_context(context)
    use_statements = generate_use_statements(libraries_used, code)

    # Combine use statements with generated code
    if use_statements:
        full_code = f"{use_statements}\n\n{code.strip()}"
    else:
        full_code = code.strip()

    return full_code


def extract_libraries_from_context(context):
    """Extract library names from the retrieved context."""
    libraries = set()
    lines = context.split('\n')

    for line in lines:
        if line.startswith('// Library: '):
            library = line.replace('// Library: ', '').strip()
            if library and library != 'unknown':
                libraries.add(library)

    return libraries


def generate_use_statements(libraries, generated_code=""):
    """Generate use statements for the given libraries, with special handling for threading functions."""
    use_statements = []

    # Check for threading functions in the generated code
    threading_libs_needed = set()
    for func_name, lib in THREADING_FUNCTIONS.items():
        if func_name in generated_code:
            threading_libs_needed.add(lib)

    # Add threading libraries to the libraries set
    libraries = libraries.union(threading_libs_needed)

    # Handle BOSL/BOSL2 conflicts - if BOSL is needed for threading, remove BOSL2
    if 'BOSL' in libraries and 'BOSL2' in libraries:
        # Check if BOSL is needed for threading functions
        bosl_threading_needed = any(
            func_name in generated_code and THREADING_FUNCTIONS[func_name] == 'BOSL'
            for func_name in THREADING_FUNCTIONS
        )
        if bosl_threading_needed:
            libraries.discard('BOSL2')  # Remove BOSL2 to avoid conflicts
        else:
            # Remove BOSL if not needed for threading
            libraries.discard('BOSL')

    # Map library names to their use statements
    library_map = {
        'BOSL2': 'use <BOSL2/std.scad>',
        'BOSL': ['include <BOSL/constants.scad>', 'use <BOSL/threading.scad>'],
        'NopSCADlib': 'use <NopSCADlib/lib.scad>',
        'MCAD': 'use <MCAD/boxes.scad>',
        'dotSCAD': 'use <dotSCAD/src/util/util.scad>',
        'threads-scad': 'use <threads-scad/threads.scad>',
        'Round-Anything': 'use <Round-Anything/polyround.scad>',
        'OpenSCAD-Snippet': 'use <OpenSCAD-Snippet/main.scad>',
        # Add more mappings as needed
    }

    for library in libraries:
        if library in library_map:
            mapping = library_map[library]
            if isinstance(mapping, list):
                use_statements.extend(mapping)
            else:
                use_statements.append(mapping)
        else:
            # For unknown libraries, try a generic approach
            use_statements.append(
                f'// use <{library}/...>;  // Add appropriate {library} include')

    return '\n'.join(use_statements)


def extract_entities_from_prompt(prompt):
    # Simple keyword/entity extraction (can be improved with LLM)
    # Extract words that could be module/function names
    words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', prompt.lower()))
    # Remove common English words (stopwords)
    stopwords = {"a", "the", "with", "for", "and", "to", "of", "in", "on", "at", "by", "is", "as", "an", "from", "that", "it", "this", "be", "or", "use", "using", "make",
                 "create", "generate", "model", "part", "object", "module", "function", "scad", "parametric", "simple", "complex", "shape", "3d", "print", "printer", "design"}
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
