from rag.retriever import retrieve_context

def test_retrieve_context():
    prompt = "Create a cylinder with a hole."
    context = retrieve_context(prompt)
    assert isinstance(context, str)
    assert "OpenSCAD" in context or "//" in context 