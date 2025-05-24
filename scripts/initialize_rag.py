#!/usr/bin/env python3
"""
Initialize the RAG system with example OpenSCAD code.
This script populates the vector database with common OpenSCAD patterns and examples.
"""

import os
import chromadb
from chromadb.config import Settings

# Example OpenSCAD code snippets
EXAMPLE_CODE = [
    {
        "id": "phone_stand",
        "text": """// EXAMPLE: Phone Stand with Adjustable Angle
module phone_stand(width=80, height=120, angle=45) {
    thickness = 5;
    base_width = width + 20;
    
    difference() {
        // Main body
        union() {
            // Base
            cube([base_width, base_width, thickness]);
            // Stand
            translate([base_width/2, base_width/2, thickness])
            rotate([angle, 0, 0])
            cube([width, height, thickness], center=true);
        }
        // Cable management hole
        translate([base_width/2, base_width/2, -1])
        cylinder(d=10, h=thickness+2);
    }
}""",
        "metadata": {"type": "stand", "features": ["adjustable", "cable_management"]}
    },
    {
        "id": "parametric_gear",
        "text": """// EXAMPLE: Parametric Gear
module gear(teeth=20, module=2, thickness=5) {
    // Calculate gear parameters
    pitch_radius = (teeth * module) / 2;
    outer_radius = pitch_radius + module;
    inner_radius = pitch_radius - module;
    
    // Generate gear profile
    points = [
        for (i = [0:teeth-1])
        let (angle = i * 360 / teeth)
        [
            outer_radius * cos(angle),
            outer_radius * sin(angle)
        ]
    ];
    
    // Create gear
    linear_extrude(height=thickness)
    polygon(points);
}""",
        "metadata": {"type": "gear", "features": ["parametric", "mechanical"]}
    },
    {
        "id": "honeycomb_pattern",
        "text": """// EXAMPLE: Honeycomb Pattern
module honeycomb_cell(size=10, height=5) {
    // Create hexagonal cell
    linear_extrude(height=height)
    polygon([
        [size, 0],
        [size/2, size * 0.866],
        [-size/2, size * 0.866],
        [-size, 0],
        [-size/2, -size * 0.866],
        [size/2, -size * 0.866]
    ]);
}

module honeycomb_pattern(width=100, height=100, cell_size=10) {
    // Calculate grid
    rows = ceil(height / (cell_size * 1.732));
    cols = ceil(width / (cell_size * 1.5));
    
    // Generate pattern
    for (row = [0:rows-1]) {
        for (col = [0:cols-1]) {
            translate([
                col * cell_size * 1.5,
                row * cell_size * 1.732 + (col % 2) * cell_size * 0.866,
                0
            ])
            honeycomb_cell(cell_size);
        }
    }
}""",
        "metadata": {"type": "pattern", "features": ["structural", "repeating"]}
    }
]

def initialize_rag():
    """Initialize the RAG system with example code"""
    print("Initializing RAG system...")
    
    # Create or get the ChromaDB client
    client = chromadb.Client(Settings(
        persist_directory="data/chroma",
        anonymized_telemetry=False
    ))
    
    # Create or get the collection
    collection = client.get_or_create_collection(
        name="openscad_examples",
        metadata={"description": "OpenSCAD code examples for RAG"}
    )
    
    # Add example code to the collection
    collection.add(
        documents=[example["text"] for example in EXAMPLE_CODE],
        ids=[example["id"] for example in EXAMPLE_CODE],
        metadatas=[example["metadata"] for example in EXAMPLE_CODE]
    )
    
    print("RAG system initialized with example code!")
    print(f"Added {len(EXAMPLE_CODE)} examples to the database.")

if __name__ == "__main__":
    initialize_rag() 