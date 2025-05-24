module bolt(length=30, diameter=10, head_diameter=15, head_height=5) {
    // Create the bolt shaft
    cylinder(h=length, r=diameter/2, $fn=100);
    
    // Create the hex head
    translate([0, 0, length]) {
        cylinder(h=head_height, r1=head_diameter/2, r2=head_diameter/2, $fn=6);
    }
}

bolt();