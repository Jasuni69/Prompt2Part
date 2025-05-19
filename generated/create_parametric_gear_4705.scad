// OpenSCAD model: Create a parametric gear with 15 teeth and 5mm center hole
Please focus on using modules from these libraries: BOSL2.

The previous code had issues: OpenSCAD render error: ERROR: Parser error: syntax error in file ../../../../../../tmp/tmp604o6qp0.scad, line 2
Please fix and regenerate.

use <BOSL2/std.scad>;

// Parameters
$fn = 100;
teeth = 15;
center_hole_size = 5.0;
gear_thickness = 5.0;

module gear_with_hole(teeth, center_hole_size, thickness) {
    difference() {
        linear_extrude(height = thickness) {
            spur_gear(
                teeth = teeth,
                circular_pitch = 5,
                gear_thickness = thickness,
                rim_thickness = thickness
            );
        }
        translate([0, 0, -1]) {
            cylinder(r = center_hole_size/2, h = thickness + 2, $fn = 30);
        }
    }
}

gear_with_hole(teeth, center_hole_size, gear_thickness);