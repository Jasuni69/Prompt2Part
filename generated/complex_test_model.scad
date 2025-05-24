// Importing the required libraries
use <BOSL2/std.scad>;
use <Round-Anything/Round-Anything.scad>;

// Defining the dimensions
base_width = 100; // Base width
base_depth = 80; // Base depth
holder_min_width = 60; // Minimum width of the phone holder
holder_max_width = 90; // Maximum width of the phone holder
round_radius = 5; // Radius for the rounded corners

// Module for the base of the phone stand
module base() {
    roundedBox(base_width, base_depth, 5, round_radius, center=true);
}

// Module for the phone holder with adjustable width
module holder(width) {
    rotate([0, 0, 0]) 
    translate([0, 0, 5]) 
    roundedBox(width, 10, 5, round_radius, center=true);
}

// Module for the adjustable angle
module adjustable_angle(min_angle, max_angle) {
    angle = min_angle;
    while (angle <= max_angle) {
        rotate([0, angle, 0])
        holder(holder_min_width);
        angle = angle + 1;
    }
}

// Module for the cable management
module cable_management() {
    translate([0, -base_depth/2, 2.5])
    cylinder(h=5, r=5, center=true);
}

// Main module
module main() {
    base();
    adjustable_angle(45, 75);
    cable_management();
}

// Calling the main module
main();