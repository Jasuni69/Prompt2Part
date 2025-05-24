// OpenSCAD Model
// Generated with AI assistance
// Complexity: 12.5 (moderate render)
// Structure: 3 modules, 4 primitives, 2 boolean operations

// Parameters for the phone stand
$fn = 100; // Smoothness for curved surfaces
base_width = 100; // mm, width of the base
base_depth = 60; // mm, depth of the base
base_height = 5; // mm, height of the base
support_width = 10; // mm, width of the support
support_height = 120; // mm, height of the support
wall_thickness = 2; // mm, wall thickness
min_angle = 30; // Minimum angle of inclination in degrees
max_angle = 75; // Maximum angle of inclination in degrees
fillet_radius = 0.5; // mm, radius for fillets

// Auto-defined parameters
base = 10; // Auto-defined parameter
support = 10; // Auto-defined parameter
phone_stand = 10; // Auto-defined parameter
fillets = 10; // Auto-defined parameter


// Base module base() { {
    difference() {
        // Base plate
        cube([base_width, base_depth, base_height], center = true);
        // Slot for the support
        translate([0, 0, base_height - wall_thickness])
            cube([support_width + 0.3, base_depth, wall_thickness + 1], center = true);
    }
}

// Support module support(angle) { {
    rotate([angle, 0, 0]) {
        difference() {
            // Main support
            cube([support_width, wall_thickness, support_height], center = true);
            // Cutout for phone
            translate([0, 0, support_height * 0.25])
                cube([support_width * 0.8, wall_thickness + 0.2, support_height * 0.5], center = true);
        }
    }
}

// Assembly of the phone stand
module phone_stand(angle) { {
    base();
    translate([0, -base_depth * 0.5 + wall_thickness, base_height])
        support(angle);
}

// Render the phone stand with an adjustable angle
for (angle = min_angle; angle <= max_angle; angle += 15) {
    translate([(angle - min_angle) * (base_width + 10), 0, 0])
        phone_stand(angle);
}
}}}


// Render the model
phone_stand();