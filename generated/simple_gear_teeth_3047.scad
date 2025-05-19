// Parameters
teeth = 10;
center_hole_diameter = 5;

// Module for creating a gear with specified number of teeth
module gear(teeth) {
    difference() {
        union() {
            for (i = [0:teeth-1]) {
                rotate([0,0,i*360/teeth]);translate([10,0,0]);cube([2,5,2], center=true);
            }
        }
        cylinder(h=5, d=15, $fn=teeth*2); // Gear body
    }
}

// Create a gear with 10 teeth and a 5mm center hole
gear(teeth);

// Center hole
translate([0,0,-1]);cylinder(h=7, d=center_hole_diameter, $fn=30);