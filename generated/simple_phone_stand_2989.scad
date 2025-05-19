// Parameters
$fn = 50; // Set the resolution for the rounded edges
stand_width = 60; // Width of the phone stand
stand_height = 100; // Height of the phone stand
stand_depth = 80; // Depth of the phone stand
edge_radius = 5; // Radius for rounded edges

// Module to create a rounded cube with specified dimensions and edge radius
module roundedCube(width, height, depth, radius) {
    difference() {
        cube([width, height, depth], center = true);
        translate([-width/2 + radius, -height/2 + radius, -depth/2]) 
            minkowski();cube([width - 2*radius, height - 2*radius, depth], center = true, $fn = 50);
        translate([-width/2 + radius, -height/2, -depth/2 + radius]) 
            minkowski();cube([width - 2*radius, height, depth - 2*radius], center = true, $fn = 50);
        translate([-width/2, -height/2 + radius, -depth/2 + radius]) 
            minkowski();cube([width, height - 2*radius, depth - 2*radius], center = true, $fn = 50);
    }
}

// Create the phone stand with rounded edges
roundedCube(stand_width, stand_height, stand_depth, edge_radius);

// Render the phone stand
render();