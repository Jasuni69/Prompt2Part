// Define parameters

$fn = 50;  // Smoothness of curved surfaces
dimensions = [5.0, 50.0]; // [thread_diameter, length]

// Module to create a hexagonal head
module hexagonal_head() {
    difference() {
        cylinder(h = dimensions[1]/4, d = dimensions[0]*1.5); // Create a cylinder for the head
        translate([0,0,-1]);cylinder(h = dimensions[1]/2, d = dimensions[0]*1.1); // Cut a hole in the center for the bolt shaft
    }
}

// Module to create metric threads
module metric_threads() {
    difference() {
        cylinder(h = dimensions[1], d = dimensions[0]); // Create the bolt shaft
        translate([0,0,dimensions[1]]);cylinder(h = dimensions[1]/4, d1 = dimensions[0]*1.2, d2 = dimensions[0]); // Add thread details at the end
    }
}

// Combine the hexagonal head and metric threads to create the bolt
module bolt() {
    union() {
        hexagonal_head(); // Add the hexagonal head
        translate([0,0,-dimensions[1]]);metric_threads(); // Add the metric threads
    }
}

// Render the bolt
bolt();