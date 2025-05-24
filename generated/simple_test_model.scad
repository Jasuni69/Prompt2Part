// Define the dimensions of the cube
cube_size = 20;

// Define the radius of the sphere
sphere_radius = 10;

// Define the dimensions of the cylinder
cylinder_height = 30;
cylinder_radius = 5;

// Define the position of the cylinder relative to the cube
cylinder_position = [cube_size, cube_size/2, cube_size/2];

// Define the position of the sphere relative to the cube
sphere_position = [cube_size/2, cube_size/2, cube_size + sphere_radius];

// Create a module for the cube
module create_cube() {
    cube(cube_size, center=true);
}

// Create a module for the sphere
module create_sphere() {
    translate(sphere_position)
    sphere(sphere_radius);
}

// Create a module for the cylinder
module create_cylinder() {
    translate(cylinder_position)
    cylinder(h=cylinder_height, r=cylinder_radius, center=true);
}

// Create a main module that calls the other modules
module main() {
    create_cube();
    create_sphere();
    create_cylinder();
}

// Call the main module
main();