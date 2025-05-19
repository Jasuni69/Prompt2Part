// Parameters
height = 10.0; // mm
thickness = 5.0; // mm
letter_size = 20; // mm
spacing = 15; // mm
base_thickness = 3; // mm

$fn = 50;

// Import BOSL2 library
use <BOSL2/std.scad>;

// Module for creating 3D text with a base
module text3d(text_str, letter_height=height, letter_thickness=thickness, font_size=letter_size) {
    linear_extrude(height=letter_height) {
        text(text_str, size=font_size, font="Arial:style=Bold", halign="center");
    }
}

// Module for creating a connected base for all letters
module text_base(text_str, letter_size=letter_size, base_height=base_thickness, total_width=0) {
    // Calculate the base width from the text if not specified
    width = total_width > 0 ? total_width : len(text_str) * letter_size * 0.8;
    
    translate([0, -letter_size/4, 0])
        cube([width, letter_size/2, base_height], center=true);
}

// Create the full name with individual letters on a base
module name_jason() {
    // Create the base
    color("steelblue")
        text_base("JASON", total_width=spacing * 4);
    
    // Create each letter
    for (i = [0:4]) {
        letter = ["J", "A", "S", "O", "N"][i];
        translate([spacing * (i - 2), 0, base_thickness])
            color("lightblue")
                text3d(letter);
    }
}

// Render the name
name_jason();
