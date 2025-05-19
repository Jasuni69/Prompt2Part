// Parameters
$fn = 100;  // mm  // Set the number of fragments to approximate a circle
thread_diameter = 5.0;  // mm // mm
length = 50.0;  // mm // mm

// Module for creating a bolt with ISO metric threads
module bolt(thread_diameter, length) {
    difference() {
        union() {
            // Bolt body
            cylinder(thread_diameter, length);
            
            // Threaded part
            translate([0, 0, -length]) {
                threads_ext(ISO_metric_thread_pitch(thread_diameter);, thread_diameter, length*2);
            }
        }
        
        // Hexagonal head
        translate([0, 0, length]);{
            cylinder(thread_diameter*1.5, thread_diameter*1.5);
        }
    }
}

// ISO metric thread pitch calculation function
function ISO_metric_thread_pitch(diameter) = 0.6134 * diameter;

// Importing threads library for creating ISO metric threads
use <threads.scad>;

// Create the M5mm bolt with 50mm length
bolt(thread_diameter, length);

// Render the bolt
translate([0, 0, -5]);cube([10, 10, 60]); // Display cube for better visualization