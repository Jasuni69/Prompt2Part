// Variables for dimensions
base_width = 80;
base_depth = 60;
base_height = 10;
holder_height = 15;
holder_angle_min = 45;
holder_angle_max = 75;
cable_slot_width = 10;
cable_slot_height = 5;
rounding_radius = 5;

// Main module
module phone_stand() {
    // Base with rounded corners
    difference() {
        cube([base_width, base_depth, base_height], center = true);
        translate([-base_width/2, -base_depth/2, -base_height/2]) cylinder(r=rounding_radius, h=base_height+1);
        translate([-base_width/2, base_depth/2, -base_height/2]) cylinder(r=rounding_radius, h=base_height+1);
        translate([base_width/2, -base_depth/2, -base_height/2]) cylinder(r=rounding_radius, h=base_height+1);
        translate([base_width/2, base_depth/2, -base_height/2]) cylinder(r=rounding_radius, h=base_height+1);
    }
    
    // Phone holder with adjustable angle
    for (angle = [holder_angle_min:10:holder_angle_max]) {
        rotate([angle, 0, 0]) 
        translate([0, base_depth/2, holder_height]) 
        cube([base_width, 2, holder_height], center = true);
    }
    
    // Slot for cable management
    translate([0, -base_depth/2, -base_height/2]) 
    cube([cable_slot_width, 2, cable_slot_height]);
}

// Call the main module
phone_stand();