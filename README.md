# Advanced Text-to-CAD Generator (AI + OpenSCAD)

## Overview
Transform natural language descriptions into professional-grade 3D models with this advanced AI-powered CAD generator. The system uses state-of-the-art large language models (LLMs) combined with Retrieval-Augmented Generation (RAG) to produce high-quality OpenSCAD code that follows engineering best practices and considers manufacturing constraints.

## Key Features
- **Natural Language Input**: Simply describe what you want to create in plain language
- **Manufacturing-Aware Design**: Automatically optimizes designs for 3D printing, CNC machining, or injection molding
- **Parametric Models**: All generated models are fully parametric for easy customization
- **Engineering Best Practices**: Applies design guidelines for structural integrity and manufacturability
- **Code Quality Validation**: Validates and automatically fixes common OpenSCAD syntax issues
- **Multi-Model Support**: Works with GPT-4, GPT-3.5, local models via Ollama, and more
- **Rich Documentation**: Generated code includes detailed comments explaining design decisions
- **Complexity Analysis**: Evaluates model complexity and provides optimization recommendations
- **Intuitive CLI & GUI**: Choose between command-line or graphical interfaces
- **RAG-Enhanced Generation**: Uses a library of OpenSCAD code examples to improve code quality

## Manufacturing Considerations
The system automatically tailors the generated model based on manufacturing constraints:

- **3D Printing**
  - Appropriate wall thickness (min 1.2mm)
  - Avoids overhangs greater than 45° without supports
  - Adds chamfers/fillets to improve strength
  - Considers print orientation

- **CNC Machining**
  - Designs for accessibility of cutting tools
  - Avoids internal sharp corners
  - Includes fixturing considerations
  - Maintains uniform wall thickness

- **Injection Molding**
  - Adds proper draft angles (1-2°)
  - Maintains uniform wall thickness
  - Avoids thick sections that could cause sink marks
  - Includes appropriate fillets on all edges

## Enhanced CLI Usage

```bash
# Basic usage
python main.py generate --prompt "A phone stand with adjustable angle"

# Specify manufacturing method
python main.py generate --prompt "A phone stand" --manufacturing 3dprint

# Use specific libraries
python main.py generate --prompt "A gear mechanism" -l BOSL2 -l MCAD

# Export directly to STL
python main.py generate --prompt "A simple enclosure" --export-stl --open

# Analyze an existing SCAD file
python main.py analyze path/to/model.scad
```

## Example Prompts

Try these prompts to see the system's capabilities:

1. "A phone stand with rounded edges that can hold a phone at a 45-degree angle"
2. "A parametric enclosure for a Raspberry Pi with ventilation holes and mounting points"
3. "A gear mechanism with a 3:1 ratio and 30 teeth on the larger gear"
4. "A wall-mountable holder for tools with honeycomb pattern for strength"
5. "A threaded container with screw-on lid, waterproof seal, and knurled edges for grip"

## How It Works

1. **Prompt Analysis**: The system analyzes your request to identify key parameters, manufacturing constraints, and design requirements
2. **RAG Retrieval**: Relevant OpenSCAD code examples are retrieved from the knowledge base
3. **Design Generation**: The LLM generates a parametric design optimized for your requirements
4. **Validation & Refinement**: The code is validated, fixed, and enhanced with best practices
5. **Complexity Analysis**: The model is analyzed for complexity and optimization opportunities
6. **Export & Visualization**: The model is saved as .scad and optionally exported to .stl

## Advanced Features

### Multi-Query RAG System
The system uses a sophisticated multi-query approach for retrieving relevant examples:
- Extracts entities and design requirements from your prompt
- Generates specialized retrieval queries for each component
- Re-ranks results based on both semantic similarity and design context
- Formats a comprehensive context for the LLM with the most relevant code examples

### Engineering Parameter Extraction
Automatically extracts and applies:
- Dimensional requirements
- Material constraints
- Structural features
- Connection methods
- Manufacturing tolerances

### Intelligent Error Recovery
- Self-healing code generation with automatic syntax correction
- Multi-attempt generation with feedback loop
- Graceful fallback for challenging designs

## Setup
1. Install Python 3.10+
2. Install dependencies: `pip install -r requirements.txt`
3. Optional: Set up OpenAI API key in `.env` file for best results
4. Optional: Install OpenSCAD for STL export and visualization

## Project Structure
- `data/` - OpenSCAD docs and code snippets for RAG
- `models/` - LLM integrations (local and API-based)
- `rag/` - Retrieval-augmented generation system
- `scad/` - OpenSCAD code generation, validation, and export
- `ui/` - CLI and GUI interfaces
- `generated/` - Output directory for generated models
- `tests/` - Unit and integration tests
- `scripts/` - Utility scripts for setup and maintenance

## License
MIT License

# OpenSCAD RAG Data Pipeline

This project provides a workflow for using OpenSCAD libraries in Retrieval-Augmented Generation (RAG) systems. Below are the steps and scripts to set up and process your OpenSCAD codebase for RAG.

---

## Folder Structure

```
data/
├── scad_raw/                # All original .scad files, organized by library
├── scad_chunks/             # Preprocessed, chunked .scad code for RAG
├── scad_metadata.jsonl      # Metadata for each chunk (file, library, chunk index, etc.)
├── scad_full_corpus.txt     # (Optional) All .scad code concatenated for reference
```

---

## 1. Clone OpenSCAD Libraries

Use the provided script to clone popular OpenSCAD libraries into a folder (ignored by git):

```bash
bash scripts/clone_scad_libs.sh
```

This will create a `scad_library/` directory with all the libraries as subfolders.

---

## 2. Copy All .scad Files for Processing

Copy all `.scad` files from `scad_library/` to `data/scad_raw/`, preserving the directory structure:

```bash
rsync -av --include '*/' --include '*.scad' --exclude '*' scad_library/ data/scad_raw/
```

---

## 3. Extract and Chunk SCAD Code

Run the extraction script to process all `.scad` files:

```bash
python scripts/extract_scad_chunks.py
```

This will:
- Create `data/scad_chunks/` with chunked `.txt` files
- Generate `data/scad_metadata.jsonl` with metadata for each chunk
- Create `data/scad_full_corpus.txt` with all code concatenated

---

## 4. Example Workflow

1. Clone libraries: `bash scripts/clone_scad_libs.sh`
2. Copy .scad files: `rsync -av --include '*/' --include '*.scad' --exclude '*' scad_library/ data/scad_raw/`
3. Extract and chunk: `python scripts/extract_scad_chunks.py`

---

## Scripts

- `scripts/clone_scad_libs.sh`: Clones a set of popular OpenSCAD libraries from GitHub.
- `scripts/extract_scad_chunks.py`: Extracts and chunks code from `.scad` files for RAG, and generates metadata.

---

## Notes
- All utility scripts are now in the `scripts/` directory.
- The `scad_library/` directory is added to `.gitignore` to avoid bloating your repository.
- You can add or remove libraries by editing `scripts/clone_scad_libs.sh`.
- The chunking script can be adapted for different chunk sizes or strategies as needed.

## Embedding SCAD Chunks with OpenAI

To generate vector embeddings for your SCAD code chunks using OpenAI's `text-embedding-ada-002` model:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your OpenAI API key:**
   - Place your key in a `.env` file at the project root (recommended):
     ```env
     OPENAI_API_KEY=your-api-key-here
     ```
   - The embedding script will automatically load this file. Alternatively, you can export the variable manually if you prefer.

3. **Run the embedding script:**
   ```bash
   python scripts/embed_scad_chunks_openai.py
   ```
   - This will read all `.txt` files in `data/scad_chunks/`, generate embeddings, and write them to `data/scad_embeddings_openai.jsonl`.
   - The script supports resuming if interrupted and logs progress.

4. **Output:**
   - Each line in `data/scad_embeddings_openai.jsonl` is a JSON object with:
     - `chunk_file`: the chunk filename
     - `text`: the SCAD code
     - `embedding`: the embedding vector

You can later import these embeddings into a vector database for retrieval-augmented generation.

## Importing Embeddings into Chroma and Retrieval

To load your OpenAI SCAD embeddings into a Chroma vector database and test retrieval:

1. **Install Chroma (if not already):**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the import script:**
   ```bash
   python scripts/import_embeddings_to_chroma.py
   ```
   - This will load all embeddings from `data/scad_embeddings_openai.jsonl` into a local Chroma DB at `data/chroma_db/`.
   - The script will also run a sample retrieval for the query `rounded cube module` and print the top results.

3. **Next steps:**
   - You can now build more advanced retrieval or RAG workflows using the Chroma DB. 