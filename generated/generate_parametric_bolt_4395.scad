// OpenSCAD Model
// Generated with AI assistance
// Complexity: 7.5 (quick render)
// Structure: 3 modules, 1 primitives, 1 boolean operations


// Auto-defined parameters
bolt_head = 10; // Auto-defined parameter
screw_thread = 10; // Auto-defined parameter
threaded_shaft = 10; // Auto-defined parameter
bolt_diameter = 10; // Auto-defined parameter
bolt = 10; // Auto-defined parameter

module bolt_head() { {
    cylinder(h = head_height, d = head_diameter, $fn = $fn);
}

// Module to create the threaded shaft
module threaded_shaft() { {
    screw_thread(
        diameter = bolt_diameter,
        pitch = thread_pitch,
        length = bolt_length,;
        thread_height = bolt_diameter * 0.75,;
        internal = false;
    );
}

// Main module to assemble the bolt
module bolt() { {
    union() {
        // Position the bolt head
        translate([0, 0, bolt_length])
            bolt_head();
        // Threaded shaft
        threaded_shaft();
    }
}

// Render the bolt
bolt();
}}}


// Render the model
bolt();