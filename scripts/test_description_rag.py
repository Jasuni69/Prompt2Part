#!/usr/bin/env python3
"""
Test script to demonstrate the new description-based RAG system.
This script compares the old code-based embeddings with the new description-based approach.
"""

import time
from rag.retriever import retrieve_context as retrieve_old
from rag.description_retriever import retrieve_context as retrieve_descriptions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_query(query, max_results=5):
    """Test a query with both old and new retrieval systems."""
    print("="*80)
    print(f"TESTING QUERY: '{query}'")
    print("="*80)

    # Test new description-based approach
    print("\n🔍 NEW APPROACH: Description-based embeddings (text-embedding-3-large)")
    print("-" * 60)
    start_time = time.time()
    try:
        new_results = retrieve_descriptions(query, max_results=max_results)
        new_time = time.time() - start_time
        print(f"⏱️  Time: {new_time:.2f}s")
        print(f"📄 Results preview:")
        # Show first 500 characters of results
        preview = new_results[:500] + \
            "..." if len(new_results) > 500 else new_results
        print(preview)
    except Exception as e:
        print(f"❌ Error: {e}")
        new_results = None
        new_time = 0

    print("\n" + "="*60)

    # Test old code-based approach
    print("\n🔍 OLD APPROACH: Code-based embeddings (text-embedding-ada-002)")
    print("-" * 60)
    start_time = time.time()
    try:
        old_results = retrieve_old(query, max_results=max_results)
        old_time = time.time() - start_time
        print(f"⏱️  Time: {old_time:.2f}s")
        print(f"📄 Results preview:")
        # Show first 500 characters of results
        preview = old_results[:500] + \
            "..." if len(old_results) > 500 else old_results
        print(preview)
    except Exception as e:
        print(f"❌ Error: {e}")
        old_results = None
        old_time = 0

    print("\n" + "="*60)

    # Compare results
    print("\n📊 COMPARISON:")
    if new_results and old_results:
        print(f"  New approach time: {new_time:.2f}s")
        print(f"  Old approach time: {old_time:.2f}s")
        print(f"  New results length: {len(new_results)} chars")
        print(f"  Old results length: {len(old_results)} chars")

        # Count functions found
        new_functions = new_results.count(
            "// Module:") + new_results.count("// Function:")
        old_functions = old_results.count(
            "// Module:") + old_results.count("// Function:")
        print(f"  New approach found: {new_functions} functions/modules")
        print(f"  Old approach found: {old_functions} functions/modules")

    print("\n")


def main():
    """Run comprehensive tests of the description-based RAG system."""
    print("🚀 TESTING DESCRIPTION-BASED RAG SYSTEM")
    print("This script compares the new description-based approach with the old code-based approach.")
    print()

    # Test queries covering different domains
    test_queries = [
        "rounded cube with fillets",
        "gear with teeth for mechanical parts",
        "thread screw bolt fastener",
        "electronic PCB connector",
        "text font rendering",
        "bearing shaft joint",
        "box enclosure case",
        "smooth curved surface",
        "parametric design",
        "3D printing support"
    ]

    print(f"Running {len(test_queries)} test queries...\n")

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*20} TEST {i}/{len(test_queries)} {'='*20}")
        test_query(query, max_results=3)

        # Add a small delay between tests
        time.sleep(0.5)

    print("\n" + "="*80)
    print("🎉 TESTING COMPLETE!")
    print("="*80)
    print("\nKey improvements with description-based approach:")
    print("✅ Searches function descriptions instead of raw code")
    print("✅ Uses text-embedding-3-large (3072 dimensions vs 1536)")
    print("✅ Better semantic understanding of function purposes")
    print("✅ Returns complete function code as context")
    print("✅ Reduces noise from code syntax in embeddings")
    print("\nTo use the new system in your applications:")
    print("  from rag.description_retriever import retrieve_context")


if __name__ == "__main__":
    main()
