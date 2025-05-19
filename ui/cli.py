import os
import click
import json
from scad.generator import ScadGenerator
from scad.exporter import ScadExporter
from scad.validator import analyze_model_complexity
import random
import time
from pathlib import Path
import subprocess

def generate_filename(prompt, prefix="model"):
    """Generate a filename based on the prompt."""
    # Extract a few words from the prompt for the filename
    words = prompt.lower().split()
    words = [w for w in words if len(w) > 2 and w not in ('the', 'and', 'with', 'for', 'that', 'this')]
    
    if words:
        # Use up to 3 words from the prompt
        name_words = words[:min(3, len(words))]
        name = '_'.join(name_words)
    else:
        # Fallback if we couldn't extract good words
        name = f"{prefix}_{random.randint(1000, 9999)}"
    
    # Add timestamp to ensure uniqueness
    timestamp = int(time.time()) % 10000
    return f"{name}_{timestamp}"

@click.group()
def cli():
    """Text-to-CAD Generator using OpenSCAD and AI."""
    pass

@cli.command()
@click.option('--prompt', prompt='Describe your 3D model', help='Text description of the model to generate.')
@click.option('--use-rag/--no-rag', default=True, help='Whether to use RAG for improved generation.')
@click.option('--save/--no-save', default=True, help='Save the generated SCAD code to a file.')
@click.option('--model', help='Specify the LLM model to use (if supported).')
@click.option('--export-stl/--no-export', default=False, help='Export to STL file after generation.')
@click.option('--output-dir', default='generated', help='Directory for output files.')
@click.option('--filename', help='Base filename for output (default: auto-generated from prompt).')
@click.option('--temperature', default=0.2, type=float, help='Temperature for LLM generation (0.0-1.0).')
@click.option('--libraries', '-l', multiple=True, help='Specific libraries to use (can specify multiple, e.g. -l BOSL -l BOSL2).')
@click.option('--manufacturing', '-m', type=click.Choice(['3dprint', 'cnc', 'injection']), 
              help='Specify manufacturing method for design optimization.')
@click.option('--open/--no-open', default=False, help='Open the generated file in OpenSCAD after creation.')
@click.option('--attempts', default=3, type=int, help='Maximum number of generation attempts for valid code.')
@click.option('--analyze/--no-analyze', default=True, help='Show complexity analysis of the generated model.')
def generate(prompt, use_rag, save, model, export_stl, output_dir, filename, temperature, libraries, 
             manufacturing, open, attempts, analyze):
    """Generate an OpenSCAD model from a text description."""
    click.secho(f"🔄 Generating OpenSCAD code for: ", fg='blue', nl=False)
    click.secho(prompt, fg='white', bold=True)
    
    # Modify prompt based on manufacturing method
    if manufacturing:
        manufacturing_methods = {
            '3dprint': 'designed for 3D printing',
            'cnc': 'designed for CNC machining',
            'injection': 'designed for injection molding'
        }
        if manufacturing in manufacturing_methods and manufacturing_methods[manufacturing] not in prompt.lower():
            prompt = f"{prompt} ({manufacturing_methods[manufacturing]})"
            click.secho(f"💡 Added manufacturing context: ", fg='yellow', nl=False)
            click.secho(manufacturing_methods[manufacturing], fg='yellow', bold=True)
    
    if use_rag:
        click.secho("🔍 Using RAG to improve generation with code examples...", fg='cyan')
        
    if libraries and use_rag:
        lib_names = ', '.join(libraries)
        click.secho(f"📚 Focusing on libraries: {lib_names}", fg='cyan')
    
    # Initialize generator and exporter
    generator = ScadGenerator(output_dir=output_dir, model=model, temperature=temperature)
    exporter = ScadExporter(output_dir=output_dir)
    
    # Generate code
    start_time = time.time()
    with click.progressbar(length=100, label='Generating model') as bar:
        # Update progress while waiting for generation
        update_interval = 0.2
        max_updates = 100
        
        # Start generation in separate thread
        import threading
        result = [None, None, None]  # scad_code, is_valid, message
        
        def generate_code():
            result[0], result[1], result[2] = generator.generate_scad_code(
                prompt, use_rag, selected_libraries=libraries, max_attempts=attempts
            )
        
        thread = threading.Thread(target=generate_code)
        thread.start()
        
        # Show progress while generation is happening
        updates = 0
        while thread.is_alive() and updates < max_updates:
            time.sleep(update_interval)
            bar.update(1)
            updates += 1
        
        thread.join()
        # Fill the remainder of the progress bar
        bar.update(max(0, 100 - updates))
        
    scad_code, is_valid, message = result
    generation_time = time.time() - start_time
    
    # Auto-generate filename if not provided
    if not filename:
        filename = generate_filename(prompt)
    
    # Ensure .scad extension
    if not filename.endswith('.scad'):
        filename += '.scad'
    
    # Print code summary
    click.echo()
    click.secho(f"✅ Generation completed in {generation_time:.2f} seconds.", fg='green')
    
    if not is_valid:
        click.secho(f"⚠️  Warning: Generated code may have issues: {message}", fg='yellow')
    
    code_lines = scad_code.count('\n') + 1
    click.secho(f"📊 Generated {code_lines} lines of OpenSCAD code.", fg='white')
    
    # Show complexity analysis
    if analyze:
        complexity_data = analyze_model_complexity(scad_code)
        click.echo()
        click.secho("📊 Model Complexity Analysis:", fg='blue', bold=True)
        click.secho(f"  • Complexity score: {complexity_data['complexity_score']:.1f}", fg='white')
        click.secho(f"  • Render time: {complexity_data['render_time_estimate']}", fg='white')
        click.secho(f"  • Structure: {complexity_data['modules_count']} modules, "
                   f"{complexity_data['primitives_count']} primitives, "
                   f"{complexity_data['operations_count']} operations", fg='white')
        
        if complexity_data['recommendations']:
            click.echo()
            click.secho("💡 Recommendations:", fg='yellow', bold=True)
            for rec in complexity_data['recommendations']:
                click.secho(f"  • {rec}", fg='yellow')
    
    # Save file
    if save:
        saved_path = exporter.save_scad_file(scad_code, filename)
        click.echo()
        click.secho(f"💾 Saved to: ", fg='green', nl=False)
        click.secho(saved_path, fg='green', bold=True)
        
        # Save metadata
        try:
            # Create a clean version of the complexity data that's JSON serializable
            complexity_data_cleaned = None
            if analyze and complexity_data:
                complexity_data_cleaned = {
                    "complexity_score": float(complexity_data["complexity_score"]),
                    "render_time_estimate": complexity_data["render_time_estimate"],
                    "modules_count": complexity_data["modules_count"],
                    "primitives_count": complexity_data["primitives_count"],
                    "operations_count": complexity_data["operations_count"],
                    "variables_count": complexity_data["variables_count"],
                    "recommendations": list(complexity_data["recommendations"]) if "recommendations" in complexity_data else []
                }
            
            metadata = {
                "prompt": prompt,
                "generation_time": generation_time,
                "is_valid": is_valid,
                "validation_message": message,
                "complexity": complexity_data_cleaned,
                "libraries": list(libraries) if libraries else None,
                "temperature": temperature,
                "timestamp": time.time()
            }
            
            meta_path = str(Path(saved_path).with_suffix('.json'))
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            click.secho(f"⚠️  Warning: Could not save metadata: {e}", fg='yellow')
    
    # Export to STL if requested
    if export_stl:
        click.echo()
        click.secho("🔄 Exporting to STL...", fg='blue')
        success, result = exporter.export_stl(scad_code=scad_code, stl_file=filename.replace('.scad', '.stl'))
        
        if success:
            click.secho(f"✅ STL exported to: ", fg='green', nl=False)
            click.secho(result, fg='green', bold=True)
        else:
            click.secho(f"❌ STL export failed: {result}", fg='red')
    
    # Open in OpenSCAD if requested
    if open and save:
        try:
            click.echo()
            click.secho("🚀 Opening in OpenSCAD...", fg='blue')
            subprocess.Popen(['openscad', saved_path], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        except Exception as e:
            click.secho(f"❌ Failed to open OpenSCAD: {e}", fg='red')
    
    return scad_code

@cli.command()
@click.argument('scad_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output STL file path.')
def export(scad_file, output):
    """Export an existing SCAD file to STL."""
    click.secho(f"🔄 Exporting {scad_file} to STL...", fg='blue')
    
    # Default output filename if not specified
    if not output:
        output = os.path.splitext(scad_file)[0] + '.stl'
    
    exporter = ScadExporter()
    success, result = exporter.export_stl(scad_file=scad_file, stl_file=output)
    
    if success:
        click.secho(f"✅ STL exported to: ", fg='green', nl=False)
        click.secho(result, fg='green', bold=True)
    else:
        click.secho(f"❌ Export failed: {result}", fg='red')

@cli.command()
@click.argument('scad_file', type=click.Path(exists=True))
def analyze(scad_file):
    """Analyze the complexity of an existing OpenSCAD file."""
    click.secho(f"🔍 Analyzing {scad_file}...", fg='blue')
    
    # Read the file
    with open(scad_file, 'r') as f:
        scad_code = f.read()
    
    # Analyze complexity
    complexity = analyze_model_complexity(scad_code)
    
    click.echo()
    click.secho("📊 Model Complexity Analysis:", fg='blue', bold=True)
    click.secho(f"  • File: {scad_file}", fg='white')
    click.secho(f"  • Complexity score: {complexity['complexity_score']:.1f}", fg='white')
    click.secho(f"  • Render time: {complexity['render_time_estimate']}", fg='white')
    click.secho(f"  • Structure: {complexity['modules_count']} modules, "
               f"{complexity['primitives_count']} primitives, "
               f"{complexity['operations_count']} operations", fg='white')
    click.secho(f"  • Variables: {complexity['variables_count']}", fg='white')
    
    if complexity['recommendations']:
        click.echo()
        click.secho("💡 Recommendations:", fg='yellow', bold=True)
        for rec in complexity['recommendations']:
            click.secho(f"  • {rec}", fg='yellow')

def main_cli():
    """Main entry point for CLI."""
    cli() 