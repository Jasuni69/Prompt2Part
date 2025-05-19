// Parameters

$fn = 50;  // Smoothness of curved surfaces
box_dimensions = [100, 60, 40]; // [length, width, height]
corner_radius = 5;  // mm
lid_thickness = 2;  // mm
snap_fit_height = 2;  // mm
snap_fit_tolerance = 0.2;  // mm

// Modules
module roundedBox(length, width, height, radius) {
    difference() {
        hull() {
            translate([radius, radius, 0]);cylinder(d=radius*2, h=height);
            translate([length - radius, radius, 0]);cylinder(d=radius*2, h=height);
            translate([radius, width - radius, 0]);cylinder(d=radius*2, h=height);
            translate([length - radius, width - radius, 0]);cylinder(d=radius*2, h=height);
        }
        cube([length, width, height], center=true);
    }
}

module snapFitLid(length, width, height, thickness, snapHeight, tolerance) {
    difference() {
        cube([length, width, thickness], center=true);
        translate([0, 0, -tolerance]);cube([length - tolerance*2, width - tolerance*2, snapHeight], center=true);
    }
}

// Rendering
roundedBox(box_dimensions[0], box_dimensions[1], box_dimensions[2], corner_radius);

translate([0, 0, box_dimensions[2]]);snapFitLid(box_dimensions[0], box_dimensions[1], lid_thickness, lid_thickness, snap_fit_height, snap_fit_tolerance);