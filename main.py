import sys
import os
from scripts.initialize_rag import initialize_rag
from demo import main as run_demo

if __name__ == "__main__":
    # Initialize the RAG system
    print("Initializing RAG system...")
    initialize_rag()
    
    # Run the demonstration
    run_demo() 