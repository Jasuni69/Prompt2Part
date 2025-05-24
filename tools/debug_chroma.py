import os
import chromadb
from chromadb.config import Settings
import time

CHROMA_DIR = os.path.abspath('data/chroma_db')
print(f"Chroma DB directory: {CHROMA_DIR}")

# Make sure the directory exists
os.makedirs(CHROMA_DIR, exist_ok=True)
print(f"Directory exists: {os.path.exists(CHROMA_DIR)}")

# Create a client with explicit persistence settings
client = chromadb.Client(Settings(
    persist_directory=CHROMA_DIR,
    anonymized_telemetry=False,
    allow_reset=True
))
print(f"Client created with version {chromadb.__version__}")

# Get or create a collection
collection = client.get_or_create_collection("test_collection")
print(f"Collection created or accessed: {collection.name}")
print(f"Initial collection count: {collection.count()}")

# Add some test data
print("Adding test data...")
collection.add(
    documents=["This is a test document", "This is another test document"],
    metadatas=[{"source": "test1"}, {"source": "test2"}],
    ids=["id1", "id2"]
)

# Force persistence
print("Testing if collection data persists...")
print(f"Collection count after adding: {collection.count()}")

# Let's explicitly persist if needed (some Chroma versions need this)
if hasattr(client, 'persist'):
    print("Explicitly calling persist()...")
    client.persist()

print(f"Final collection count: {collection.count()}")
print(f"Chroma DB directory listing: {os.listdir(CHROMA_DIR)}")

# Create a new client and check if data is still there
print("\nCreating a new client to test persistence...")
client2 = chromadb.Client(Settings(
    persist_directory=CHROMA_DIR,
    anonymized_telemetry=False,
    allow_reset=False
))

# Try to get the collection
try:
    collection2 = client2.get_collection("test_collection")
    print(f"Collection successfully retrieved with count: {collection2.count()}")
    if collection2.count() != 2:
        print("ERROR: Data didn't persist correctly!")
    else:
        print("SUCCESS: Data persisted correctly!")
except Exception as e:
    print(f"ERROR: Failed to retrieve collection: {e}")

# Wait for a moment and check directory again
time.sleep(2)
print(f"Final directory listing: {os.listdir(CHROMA_DIR)}") 