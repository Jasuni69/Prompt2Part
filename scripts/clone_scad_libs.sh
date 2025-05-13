#!/bin/bash

set -e

mkdir -p scad_library
cd scad_library

git clone https://github.com/revarbat/BOSL BOSL
git clone https://github.com/BelfrySCAD/BOSL2 BOSL2
git clone https://github.com/JustinSDK/dotSCAD dotSCAD
git clone https://github.com/nophead/NopSCADlib NopSCADlib
git clone https://github.com/UBaer21/UB.scad UB.scad
git clone https://github.com/thehans/FunctionalOpenSCAD FunctionalOpenSCAD
git clone https://github.com/solidboredom/constructive constructive
git clone https://github.com/Stone-Age-Sculptor/StoneAgeLib StoneAgeLib
git clone https://github.com/boltsparts/BOLTS_archive BOLTS_archive
git clone https://github.com/AngeloNicoli/OpenSCAD-Snippet OpenSCAD-Snippet
git clone https://github.com/Irev-Dev/Round-Anything Round-Anything
git clone https://github.com/sbambach/MarksEnclosureHelper MarksEnclosureHelper
git clone https://github.com/thehans/funcutils funcutils
git clone https://github.com/rcolyer/threads-scad threads-scad
git clone https://github.com/rcolyer/smooth-prim smooth-prim
git clone https://github.com/rcolyer/plot-function plot-function
git clone https://github.com/rcolyer/closepoints closepoints
git clone https://github.com/sofian/openscad-tray openscad-tray
git clone https://github.com/mrWheel/YAPP_Box YAPP_Box
git clone https://github.com/mmalecki/catchnhole catchnhole
git clone https://github.com/dinther/pathbuilder pathbuilder

echo "All libraries cloned into scad_library/" 