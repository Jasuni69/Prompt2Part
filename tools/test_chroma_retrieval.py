"""
Test script to verify ChromaDB retrieval is working properly.
"""

from rag.retriever import retrieve_context, semantic_search
import time
import sys
import io

def main():
    print("Testing RAG retrieval with ChromaDB...")
    
    # Test with a simple query
    query = "Make a parametric phone stand with adjustable angle"
    
    # Start timing
    start_time = time.time()
    
    # Capture stdout to check for ChromaDB messages
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    # Test semantic_search directly
    print("\nTesting semantic_search function:")
    results = semantic_search(query, n_results=5)
    
    # Get captured output
    output = new_stdout.getvalue()
    sys.stdout = old_stdout
    print(output)
    
    # Check if it's using ChromaDB or the fallback
    if "Using Chroma DB collection" in output:
        print("✅ Using ChromaDB as expected")
    else:
        print("❌ Not using ChromaDB - using fallback")
    
    # Print result count
    if results and results["documents"] and results["documents"][0]:
        print(f"Found {len(results['documents'][0])} matching documents")
    else:
        print("No results found")
    
    # Test the retrieve_context function (full pipeline)
    print("\nTesting retrieve_context function:")
    context = retrieve_context(query)
    
    if context:
        context_lines = context.split('\n')
        word_count = len(context.split())
        print(f"Retrieved {word_count} words, {len(context_lines)} lines")
        print("\nSample of retrieved context:")
        print('\n'.join(context_lines[:15]))
    else:
        print("No context retrieved")
    
    # End timing
    end_time = time.time()
    print(f"\nQuery completed in {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main() 