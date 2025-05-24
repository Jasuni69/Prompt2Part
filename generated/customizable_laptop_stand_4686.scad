// OpenSCAD Model
// Generated with AI assistance
// Complexity: 11.0 (moderate render)
// Structure: 4 modules, 3 primitives, 1 boolean operations

// Parameters
$fn = 100; // Smoothness for curved surfaces
base_width = 250; // mm, width of the base
base_depth = 200; // mm, depth of the base
base_height = 5; // mm, height of the base
support_height = 50; // mm, height of the support
support_thickness = 5; // mm, thickness of the support
vent_hole_diameter = 15; // mm, diameter of ventilation holes
fillet_radius = 5; // mm, radius for rounded corners
clearance = 0.3; // mm, clearance for moving parts
cable_slot_width = 30; // mm, width of the cable management slot
cable_slot_height = 15; // mm, height of the cable management slot

// Base module
module base() {
    difference() {
        // Base plate with rounded corners
        rounded_rect(base_width, base_depth, base_height, fillet_radius);
        
        // Cutouts for ventilation
        for (x = [-base_width/3 : base_width/6 : base_width/3], 
             y = [-base_depth/3 : base_depth/6 : base_depth/3]) {
            translate([x, y, 0])
                cylinder(h = base_height + 2, d = vent_hole_diameter, center = true);
        }

// Support module
module support() {
    difference() {
        rounded_rect(support_height, base_depth - 20, support_thickness, fillet_radius);
        
        // Optional cable routing hole
        translate([0, 0, 0])
            cylinder(h = support_thickness + 2, d = 20, center = true);
    }

// Rounded rectangle helper module
module rounded_rect(width, depth, height, radius) {
    linear_extrude(height = height, center = true) {
        offset(r = radius) 
            offset(r = -radius)
                square([width, depth], center = true);
    }

// Cable management slot
module cable_management() {
    translate([0, -base_depth/2 + cable_slot_height/2, base_height/2])
        cube([cable_slot_width, cable_slot_height, base_height + 1], center = true);
}

// Assemble the laptop stand
module laptop_stand() {
    // Place the base
    base();
    
    // Place the supports
    translate([base_width/2 - support_thickness/2, 0, base_height/2 + support_height/2])
        rotate([0, 90, 0])
            support();
            
    translate([-base_width/2 + support_thickness/2, 0, base_height/2 + support_height/2])
        rotate([0, 90, 0])
            support();
            
    // Add cable management
    cable_management();
}

// Render the model
laptop_stand();
}}
}}
