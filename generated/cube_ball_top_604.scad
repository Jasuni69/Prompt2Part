// OpenSCAD Model
// Generated with AI assistance
// Complexity: 7.5 (quick render)
// Structure: 3 modules, 3 primitives, 0 boolean operations

// Parameters for the entire model
$fn = 100; // Smoothness for curved surfaces

// Auto-defined parameters
pyramid_part = 10; // Auto-defined parameter
vertices = 10; // Auto-defined parameter
base = 10; // Auto-defined parameter
diameter = 20; // Auto-defined parameter
pyramid = 10; // Auto-defined parameter
sphere_part = 10; // Auto-defined parameter
surfaces = 10; // Auto-defined parameter
height = 50; // Auto-defined parameter
cube_base = 10; // Auto-defined parameter


// Dimensions for each part
cube_size = 40; // mm, edge length of the cube
sphere_diameter = 20; // mm, diameter of the sphere
pyramid_base = 30; // mm, base width of the pyramid
pyramid_height = 20; // mm, height of the pyramid

// Module for the cube
module cube_base(size) {
    cube(size, center=true);
}

// Module for the sphere
module sphere_part(diameter) {
    translate([0, 0, cube_size/2 + diameter/2])
        sphere(d=diameter);
}

// Module for the pyramid
module pyramid_part(base, height) {
    translate([0, 0, cube_size/2 + sphere_diameter + height/2])
        polyhedron(
            points=[
                [-base/2, -base/2, -height/2], // Bottom vertices
                [base/2, -base/2, -height/2],
                [base/2, base/2, -height/2],
                [-base/2, base/2, -height/2],
                [0, 0, height/2] // Top vertex
            ],
            faces=[
                [0, 1, 4], // Side faces
                [1, 2, 4],
                [2, 3, 4],
                [3, 0, 4],
                [0, 3, 2, 1] // Bottom face
            ]
        );
}

// Main assembly
module stacked_objects() {
    translate([0, 0, -cube_size/2]) { // Center the cube at the origin along Z
        cube_base(cube_size);
        sphere_part(sphere_diameter);
        pyramid_part(pyramid_base, pyramid_height);
    }

// Render the model
stacked_objects();
}
