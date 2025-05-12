from rag.retriever import retrieve_context
from models.local_llm import generate_code

def generate_scad_code(prompt):
    context = retrieve_context(prompt)
    scad_code = generate_code(prompt, context=context)
    return scad_code 