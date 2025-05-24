Sure, here is the OpenSCAD code for a M5 bolt:

// Define bolt parameters
bolt_length = 20; // Length of the bolt
bolt_diameter = 5; // Diameter of the bolt
thread_length = 18; // Length of the thread on the bolt
head_height = 2; // Height of the bolt head
head_diameter = 8; // Diameter of the bolt head

// Define bolt module
module bolt() {
    // Create the bolt head
    cylinder(h=head_height, d=head_diameter, $fn=100);
    
    // Create the bolt shaft
    translate([0, 0, head_height]) {
        cylinder(h=bolt_length, d=bolt_diameter, $fn=100);
    }
    
    // Create the bolt thread
    translate([0, 0, head_height]) {
        for(i = [0:0.5:thread_length]) {
            rotate([0, 0, i*360/thread_length]) {
                translate([0, bolt_diameter/2, i]) {
                    sphere(d=0.5, $fn=100);
                }
            }
        }
    }
}

// Call the main module
bolt();

This code will generate a M5 bolt with a length of 20 units, a diameter of 5 units, a thread length of 18 units, a head height of 2 units, and a head diameter of 8 units. The thread is created by rotating and translating a series of spheres along the length of the bolt shaft. The number of facets used to render the cylinders and spheres is set to 100 for a smooth appearance.