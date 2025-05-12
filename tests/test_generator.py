from scad.generator import generate_scad_code

def test_generate_scad_code():
    prompt = "Create a 10x10x10 mm cube."
    code = generate_scad_code(prompt)
    assert isinstance(code, str)
    assert "scad" in code or "//" in code 