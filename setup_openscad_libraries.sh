#!/bin/bash
# Setup script to install OpenSCAD libraries for Prompt2Part

echo "🔧 Setting up OpenSCAD libraries for Prompt2Part..."

# Create OpenSCAD libraries directory
OPENSCAD_LIB_DIR="/Users/jasonnicolini/Documents/OpenSCAD/libraries"
mkdir -p "$OPENSCAD_LIB_DIR"

# Get the current project directory
PROJECT_DIR="$(pwd)"
SCAD_LIB_DIR="$PROJECT_DIR/scad_library"

echo "📁 Project directory: $PROJECT_DIR"
echo "📚 OpenSCAD libraries will be installed to: $OPENSCAD_LIB_DIR"

# List of important libraries to symlink
LIBRARIES=(
    "BOSL2"
    "BOSL" 
    "NopSCADlib"
    "dotSCAD"
    "threads-scad"
    "Round-Anything"
    "MCAD"
    "OpenSCAD-Snippet"
    "UB.scad"
    "smooth-prim"
    "YAPP_Box"
    "pathbuilder"
    "catchnhole"
    "closepoints"
    "plot-function"
    "funcutils"
    "MarksEnclosureHelper"
    "BOLTS_archive"
    "StoneAgeLib"
    "constructive"
    "FunctionalOpenSCAD"
    "openscad-tray"
)

echo "🔗 Creating symlinks for libraries..."

for lib in "${LIBRARIES[@]}"; do
    if [ -d "$SCAD_LIB_DIR/$lib" ]; then
        echo "  ✅ Linking $lib"
        ln -sf "$SCAD_LIB_DIR/$lib" "$OPENSCAD_LIB_DIR/$lib"
    else
        echo "  ⚠️  $lib not found, skipping"
    fi
done

echo ""
echo "🎯 Testing OpenSCAD library access..."
echo "Libraries now available in OpenSCAD:"
ls -la "$OPENSCAD_LIB_DIR"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Note: You can now use libraries in OpenSCAD with statements like:"
echo "   use <BOSL2/std.scad>"
echo "   use <NopSCADlib/lib.scad>"
echo "   use <threads-scad/threads.scad>"
echo ""
echo "🚀 Try running the GUI again: python3 gui/main.py" 