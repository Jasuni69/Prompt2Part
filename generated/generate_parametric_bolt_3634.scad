// OpenSCAD Model
// Generated with AI assistance
// Complexity: 5.5 (quick render)
// Structure: 3 modules, 1 primitives, 0 boolean operations


// Auto-defined parameters
threaded_shaft = 10; // Auto-defined parameter
bolt_head = 10; // Auto-defined parameter
thread = 10; // Auto-defined parameter
bolt_length = 10; // Auto-defined parameter
bolt = 10; // Auto-defined parameter

module bolt_head(diameter, height) { {
    cylinder(h = height, d = diameter, $fn = $fn);
}

// Module to create the threaded shaft
module threaded_shaft(diameter, length, pitch) { {
    thread(
        diameter = diameter,
        length = length,
        pitch = pitch,
        internal = false,
        taper = 0,
        lead_in = 0,;
        lead_out = 0,;
        $fn = $fn;
    );
}

// Main module to assemble the bolt
module bolt() { {
    // Create the bolt head
    translate([0, 0, bolt_length - head_height])
        bolt_head(head_diameter, head_height);
    
    // Create the threaded shaft
    threaded_shaft(bolt_diameter, bolt_length - head_height, thread_pitch);
}

// Render the bolt
bolt();
}}}


// Render the model
bolt();