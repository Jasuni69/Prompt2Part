# Text-to-CAD Generator (AI + OpenSCAD)

## Overview
This project enables users to generate 3D models from natural language prompts using a local LLM and OpenSCAD. It optionally uses Retrieval-Augmented Generation (RAG) to improve code quality by referencing OpenSCAD documentation and code snippets.

## Features
- Natural language to OpenSCAD code generation
- Local LLM integration (no external API required)
- Optional RAG for enhanced code generation
- Export to .scad and .stl
- CLI and (optional) GUI

## Project Structure
- `data/` - OpenSCAD docs and code snippets for RAG
- `models/` - Local LLM interface
- `rag/` - Retrieval logic
- `scad/` - OpenSCAD code generation and export
- `ui/` - User interfaces
- `tests/` - Unit and integration tests

## Setup
1. Install Python 3.10+
2. Install dependencies: `pip install -r requirements.txt`
3. Set up your local LLM (see `models/local_llm.py`)

## Usage
Run the main entry point:
```bash
python main.py
```

## Goals
- Streamline early-stage CAD prototyping
- Demonstrate advanced AI integration (local LLM + RAG)
- Achieve VG-level project depth 