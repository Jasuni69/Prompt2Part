from rag.retriever import retrieve_context

def main():
    print("Testing RAG functionality...")
    
    # Test retrieving context for a simple query
    print("\n1. Testing basic retrieval:")
    prompt = "A cube with a ball on top and a pyramid on top of the ball"
    
    context = retrieve_context(prompt)
    if context:
        print(f"Retrieved {len(context.split())} words")
        print("First 1000 characters of context:")
        print(context[:1000])
    else:
        print("No context retrieved")
    
    # Test with another query
    print("\n2. Testing more specific retrieval:")
    prompt = "A phone stand with adjustable angle"
    
    context = retrieve_context(prompt)
    if context:
        print(f"Retrieved {len(context.split())} words")
        print("First 1000 characters of context:")
        print(context[:1000])
    else:
        print("No context retrieved")
    
if __name__ == "__main__":
    main() 