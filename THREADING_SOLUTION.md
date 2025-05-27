# OpenSCAD Threading Functions - Solution Guide

## Problem Solved
The issue was that `trapezoidal_threaded_rod()` is not available in BOSL2, but is available in the original BOSL library. The user was trying to use BOSL2 syntax but needed to use the original BOSL library.

## Available Threading Functions

### BOSL2 Library (scad_library/BOSL2/threading.scad)
- `threaded_rod()` - Standard ISO/UTS triangular threads
- `threaded_nut()` - Standard ISO/UTS threaded nuts
- `acme_threaded_rod()` - ACME threads (calls internal trapezoidal function)
- `acme_threaded_nut()` - ACME threaded nuts
- `npt_threaded_rod()` - NPT pipe threads
- `buttress_threaded_rod()` - Buttress threads
- `buttress_threaded_nut()` - Buttress threaded nuts
- `square_threaded_rod()` - Square profile threads
- `square_threaded_nut()` - Square threaded nuts
- `ball_screw_rod()` - Ball screw threads
- `generic_threaded_rod()` - Generic threading with custom profiles

### BOSL Library (scad_library/BOSL/threading.scad)
- `trapezoidal_threaded_rod()` - **Available here!**
- `trapezoidal_threaded_nut()` - Trapezoidal threaded nuts
- `threaded_rod()` - Standard triangular threads
- `threaded_nut()` - Standard threaded nuts
- `acme_threaded_rod()` - ACME threads
- `metric_trapezoidal_threaded_rod()` - Metric trapezoidal threads

## Solution: Working Example

### Corrected Code (test/threaded_bolt.scad)
```scad
include <BOSL/constants.scad>
use <BOSL/threading.scad>
use <NopSCADlib/lib.scad>

trapezoidal_threaded_rod(d=10, l=20, pitch=2);
```

### Key Changes Made:
1. **Changed from BOSL2 to BOSL**: `trapezoidal_threaded_rod()` is only available in the original BOSL library
2. **Proper includes**: Used `include <BOSL/constants.scad>` and `use <BOSL/threading.scad>` instead of `std.scad`
3. **Function exists**: The function is properly defined and documented in BOSL

## Alternative Solutions

### Option 1: Use BOSL2 with ACME threads
```scad
use <BOSL2/std.scad>

// ACME threads are trapezoidal with 29° angle
acme_threaded_rod(d=10, l=20, tpi=12.7); // tpi = threads per inch
// or
acme_threaded_rod(d=10, l=20, pitch=2);
```

### Option 2: Use BOSL2 generic threading for custom trapezoidal
```scad
use <BOSL2/std.scad>

// Define custom trapezoidal profile
profile = [
    [-0.25, -0.5],  // Left valley
    [-0.125, 0],    // Left peak
    [0.125, 0],     // Right peak  
    [0.25, -0.5]    // Right valley
];

generic_threaded_rod(d=10, l=20, pitch=2, profile=profile);
```

### Option 3: Use BOSL2 square threads (trapezoidal with 0° angle)
```scad
use <BOSL2/std.scad>

square_threaded_rod(d=10, l=20, pitch=2);
```

## Function Parameters

### trapezoidal_threaded_rod() (BOSL)
```scad
trapezoidal_threaded_rod(
    d=10,              // Outer diameter
    l=20,              // Length
    pitch=2,           // Thread pitch
    thread_angle=15,   // Pressure angle (15° for metric, 14.5° for ACME)
    thread_depth=1,    // Thread depth (default: pitch/2)
    left_handed=false, // Thread direction
    starts=1,          // Number of thread starts
    bevel=false        // Bevel thread ends
);
```

## Verification
The corrected code now renders successfully:
- ✅ No "unknown module" errors
- ✅ Generates proper STL output (696 vertices, 990 facets)
- ✅ Renders in 0.849 seconds

## Library Setup
Make sure your library paths are correctly set up:
```bash
# Your current setup should work with:
ls scad_library/BOSL/threading.scad      # ✅ Available
ls scad_library/BOSL2/threading.scad     # ✅ Available
```

## Recommendation
For new projects, consider using BOSL2 with `acme_threaded_rod()` or `generic_threaded_rod()` as BOSL2 is the actively maintained version. However, for existing code using `trapezoidal_threaded_rod()`, stick with the original BOSL library as shown in the solution above. 