import subprocess

def export_stl(scad_file, stl_file):
    """
    Export a .scad file to .stl using the OpenSCAD CLI.
    """
    # TODO: Check if openscad is installed, handle errors
    cmd = ["openscad", "-o", stl_file, scad_file]
    print(f"[MOCK] Would run: {' '.join(cmd)}")
    # subprocess.run(cmd, check=True) 