import chromadb
CHROMA_DIR = "data/chroma_db"  # NO trailing slash!
COLLECTION_NAME = "scad_chunks"

client = chromadb.PersistentClient(path=CHROMA_DIR)
collections = client.list_collections()
print("Collections:", [c.name for c in collections])
if any(c.name == COLLECTION_NAME for c in collections):
    collection = client.get_collection(COLLECTION_NAME)
    print("Collection count:", collection.count())
else:
    print("Collection not found!") 