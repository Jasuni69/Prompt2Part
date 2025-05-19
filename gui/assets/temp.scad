module gear(number_of_teeth=10) {
    difference() {
        gear_teeth(number_of_teeth);
        gear_hole();
    }
}

gear(10);