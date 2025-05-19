// Define parameters
teeth_size = 20;  // mm // Size of the gear teeth
center_hole_diameter = 5;  // mm // Diameter of the center hole
thickness = 10;  // mm // Thickness of the gear

// Module to create a parametric spur gear
module spur_gear(teeth=20, hole_d=5, gear_thickness=10) {
    difference() {
        // Create the main gear cylinder
        cylinder(h=thickness, d=teeth_size*2, $fn=teeth*2);
        
        // Subtract the center hole cylinder
        translate([0, 0, -1]);// Move the hole slightly below the gear surface for better visualization
        cylinder(h=gear_thickness+2, d=center_hole_diameter);
    }
}

// Create the spur gear with defined parameters
spur_gear(teeth_size, center_hole_diameter, thickness);

// Display the gear
translate([0, 0, thickness/2]);// Move the gear up to be visible in the render
cube([teeth_size*2, teeth_size*2, thickness], center=true); // Display a base for better visualization
rotate([90, 0, 0]);// Rotate for better view angle
cylinder(h=thickness, d=teeth_size*2, $fn=teeth_size*2); // Display the gear

// Final render
translate([0, 0, thickness/2]);// Move the gear up to be visible in the render
spur_gear(teeth_size, center_hole_diameter, thickness); // Render the gear with defined parameters