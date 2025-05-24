// Stacked Objects Example
// Demonstrates proper 3D object stacking with parameters

// Parameters
$fn = 100; // Smoothness for curved surfaces
base_size = 30; // Size of the base cube
sphere_radius = 15; // Radius of the middle sphere
pyramid_base = 20; // Base size of the top pyramid
pyramid_height = 25; // Height of the top pyramid

// Base cube module
module base_cube(size) {
    cube(size, center=true);
}

// Sphere module
module middle_sphere(radius) {
    sphere(r=radius);
}

// Pyramid module
module top_pyramid(base_size, height) {
    // Calculate pyramid points
    base_half = base_size / 2;
    
    polyhedron(
        points = [
            [-base_half, -base_half, 0],    // 0: bottom left
            [base_half, -base_half, 0],     // 1: bottom right
            [base_half, base_half, 0],      // 2: top right
            [-base_half, base_half, 0],     // 3: top left
            [0, 0, height]                  // 4: apex
        ],
        faces = [
            [0, 1, 2, 3],  // base
            [0, 1, 4],     // front
            [1, 2, 4],     // right
            [2, 3, 4],     // back
            [3, 0, 4]      // left
        ]
    );
}

// Create the stacked objects
module stacked_objects() {
    // Base cube at the origin
    base_cube(base_size);
    
    // Stack sphere on top of cube
    translate([0, 0, base_size/2 + sphere_radius]) 
        middle_sphere(sphere_radius);
    
    // Stack pyramid on top of sphere
    translate([0, 0, base_size/2 + 2*sphere_radius + pyramid_height/2]) 
        top_pyramid(pyramid_base, pyramid_height);
}

// Call the main module
stacked_objects(); 