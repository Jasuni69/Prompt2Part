import os
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = 'data/chroma_db/'
COLLECTION_NAME = 'scad_chunks'
TOP_K = 10
MODEL = 'gpt-3.5-turbo'

SYSTEM_PROMPT = (
    "You are an expert OpenSCAD code generator. "
    "Use the provided code snippets as references. "
    "If a module or function in the references matches the user's intent (for example, a gear, bolt, bracket, or other part), use it—even if the user does not mention it by name. "
    "Prefer using advanced, parametric modules from the references over synthesizing code from primitives. "
    "If no relevant module is available, synthesize a plausible solution. "
    "Only output valid OpenSCAD code, with no explanations or comments."
)

def generate_openscad_code(user_query: str) -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('Please set the OPENAI_API_KEY environment variable.')
    client = OpenAI(api_key=api_key)
    client_chroma = chromadb.Client(Settings(persist_directory=CHROMA_DIR))
    collection = client_chroma.get_or_create_collection(COLLECTION_NAME)
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
    # Construct messages for OpenAI chat
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Reference code:\n{context}\n\nUser request: {user_query}\n\nOpenSCAD code:"}
    ]
    # Generate code
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=512
    )
    return completion.choices[0].message.content.strip() 