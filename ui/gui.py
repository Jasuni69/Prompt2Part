# Placeholder for GUI (Tkinter, Gradio, etc.)
def start_gui():
    print("[MOCK] GUI would start here.") 

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, 
                            QFileDialog, QMessageBox, QProgressBar, QComboBox, QSlider,
                            QGroupBox, QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor
import tempfile
import subprocess
from pathlib import Path

from scad.generator import ScadGenerator
from scad.exporter import ScadExporter
from scad.validator import validate_scad_code, fix_common_issues

class GenerationThread(QThread):
    """Thread for handling OpenSCAD code generation."""
    finished = pyqtSignal(str, bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, prompt, use_rag, model=None, temperature=0.2, selected_libraries=[]):
        super().__init__()
        self.prompt = prompt
        self.use_rag = use_rag
        self.model = model
        self.temperature = temperature
        self.selected_libraries = selected_libraries
        
    def run(self):
        self.progress.emit("Generating code...")
        generator = ScadGenerator(model=self.model, temperature=self.temperature)
        scad_code, is_valid, message = generator.generate_scad_code(
            self.prompt, 
            self.use_rag,
            self.selected_libraries
        )
        self.finished.emit(scad_code, is_valid, message)

class ExportThread(QThread):
    """Thread for handling STL export."""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, scad_code, output_file):
        super().__init__()
        self.scad_code = scad_code
        self.output_file = output_file
        
    def run(self):
        self.progress.emit("Exporting to STL...")
        exporter = ScadExporter()
        success, result = exporter.export_stl(
            scad_code=self.scad_code,
            stl_file=self.output_file
        )
        self.finished.emit(success, result)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_scad_code = ""
        self.output_directory = os.path.join(os.getcwd(), "generated")
        
        # Create output directory if it doesn't exist
        Path(self.output_directory).mkdir(exist_ok=True, parents=True)
        
    def initUI(self):
        self.setWindowTitle("Text-to-CAD Generator (OpenSCAD)")
        self.setGeometry(100, 100, 1000, 800)
        
        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Input
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Prompt section
        prompt_group = QGroupBox("Model Description")
        prompt_layout = QVBoxLayout()
        prompt_group.setLayout(prompt_layout)
        
        prompt_label = QLabel("Describe the 3D model you want to generate:")
        prompt_layout.addWidget(prompt_label)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("E.g., A phone stand with rounded edges that can hold a phone at a 45-degree angle")
        self.prompt_input.setMinimumHeight(80)
        prompt_layout.addWidget(self.prompt_input)
        
        # Options section
        options_layout = QHBoxLayout()
        
        # RAG option
        self.rag_checkbox = QCheckBox("Use RAG (Retrieval Augmented Generation)")
        self.rag_checkbox.setChecked(True)
        self.rag_checkbox.setToolTip("Improves generation by retrieving relevant OpenSCAD code snippets")
        options_layout.addWidget(self.rag_checkbox)
        
        # Model selection
        model_label = QLabel("LLM Model:")
        options_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4", "mistral", "llama3"])
        self.model_combo.setCurrentText("gpt-3.5-turbo")
        options_layout.addWidget(self.model_combo)
        
        # Temperature slider
        temp_label = QLabel("Temperature:")
        options_layout.addWidget(temp_label)
        
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setMinimum(0)
        self.temp_slider.setMaximum(100)
        self.temp_slider.setValue(20)  # Default 0.2
        self.temp_slider.setToolTip("Controls randomness: 0=deterministic, 1=creative")
        options_layout.addWidget(self.temp_slider)
        
        self.temp_value = QLabel("0.2")
        self.temp_slider.valueChanged.connect(self.update_temp_value)
        options_layout.addWidget(self.temp_value)
        
        prompt_layout.addLayout(options_layout)
        
        # Library selection section
        self.lib_group = QGroupBox("Select OpenSCAD Libraries (narrows RAG search scope)")
        self.lib_group.setCheckable(True)
        self.lib_group.setChecked(False)
        lib_layout = QVBoxLayout()
        self.lib_group.setLayout(lib_layout)
        
        # Create scrollable area for libraries
        lib_scroll = QScrollArea()
        lib_scroll.setWidgetResizable(True)
        lib_widget = QWidget()
        lib_scroll_layout = QVBoxLayout(lib_widget)
        
        # Library descriptions
        library_descriptions = {
            "BOSL": "Basic shapes and tools (threads, gears, beziers)",
            "BOSL2": "Enhanced library (text, attachments, 3D shapes, math)",
            "BOLTS_archive": "Standard parts library (screws, nuts, washers)",
            "Round-Anything": "Rounded shapes and fillets",
            "NopSCADlib": "Mechanical and electronic components",
            "threads-scad": "Detailed threading and fasteners",
            "YAPP_Box": "Parametric enclosures and cases",
            "MarksEnclosureHelper": "Box enclosures with various features",
            "constructive": "Functional approach to solid modeling",
            "dotSCAD": "Shapes, patterns and utilities"
        }
        
        # Create checkbox for each library
        self.lib_checkboxes = {}
        for lib_name, description in library_descriptions.items():
            cb = QCheckBox(f"{lib_name}: {description}")
            self.lib_checkboxes[lib_name] = cb
            lib_scroll_layout.addWidget(cb)
        
        lib_scroll.setWidget(lib_widget)
        lib_layout.addWidget(lib_scroll)
        
        # Add to main layout
        prompt_layout.addWidget(self.lib_group)
        
        # Generate button
        generate_button_layout = QHBoxLayout()
        
        self.generate_button = QPushButton("Generate OpenSCAD Code")
        self.generate_button.setMinimumHeight(40)
        font = QFont()
        font.setBold(True)
        self.generate_button.setFont(font)
        self.generate_button.clicked.connect(self.generate_code)
        generate_button_layout.addWidget(self.generate_button)
        
        prompt_layout.addLayout(generate_button_layout)
        
        top_layout.addWidget(prompt_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v%")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        top_layout.addWidget(self.progress_bar)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Output
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Code output section
        code_group = QGroupBox("Generated OpenSCAD Code")
        code_layout = QVBoxLayout()
        code_group.setLayout(code_layout)
        
        self.code_output = QTextEdit()
        self.code_output.setReadOnly(True)
        self.code_output.setFont(QFont("Courier New", 10))
        self.code_output.setLineWrapMode(QTextEdit.NoWrap)
        self.code_output.setMinimumHeight(300)
        code_layout.addWidget(self.code_output)
        
        # Output buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save SCAD File")
        self.save_button.clicked.connect(self.save_scad_file)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        self.export_button = QPushButton("Export to STL")
        self.export_button.clicked.connect(self.export_stl)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        self.preview_button = QPushButton("Open in OpenSCAD")
        self.preview_button.clicked.connect(self.open_in_openscad)
        self.preview_button.setEnabled(False)
        button_layout.addWidget(self.preview_button)
        
        code_layout.addLayout(button_layout)
        
        bottom_layout.addWidget(code_group)
        
        # Status message
        self.status_label = QLabel("")
        bottom_layout.addWidget(self.status_label)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 500])

    def update_temp_value(self):
        """Update the temperature value label when slider changes."""
        value = self.temp_slider.value() / 100
        self.temp_value.setText(f"{value:.2f}")
        
    def generate_code(self):
        """Generate OpenSCAD code from the prompt."""
        prompt = self.prompt_input.toPlainText().strip()
        
        if not prompt:
            QMessageBox.warning(self, "Warning", "Please enter a model description.")
            return
            
        # Disable button and show progress
        self.generate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.status_label.setText("Generating OpenSCAD code...")
        
        # Get parameters
        use_rag = self.rag_checkbox.isChecked()
        model = self.model_combo.currentText()
        temperature = self.temp_slider.value() / 100
        
        # Collect selected libraries
        selected_libraries = []
        if use_rag and self.lib_group.isChecked():
            for lib_name, checkbox in self.lib_checkboxes.items():
                if checkbox.isChecked():
                    selected_libraries.append(lib_name)
        
        # Start generation in a separate thread
        self.gen_thread = GenerationThread(
            prompt, 
            use_rag, 
            model, 
            temperature,
            selected_libraries
        )
        self.gen_thread.progress.connect(self.update_status)
        self.gen_thread.finished.connect(self.handle_generation_complete)
        self.gen_thread.start()
        
    def handle_generation_complete(self, scad_code, is_valid, message):
        """Handle completion of code generation."""
        self.current_scad_code = scad_code
        self.code_output.setText(scad_code)
        
        # Update UI
        self.progress_bar.setValue(100)
        self.generate_button.setEnabled(True)
        
        if is_valid:
            self.status_label.setText("Code generated successfully!")
        else:
            self.status_label.setText(f"Warning: {message}")
            
        # Enable buttons
        self.save_button.setEnabled(True)
        self.export_button.setEnabled(is_valid)
        self.preview_button.setEnabled(True)
        
    def save_scad_file(self):
        """Save the generated SCAD code to a file."""
        if not self.current_scad_code:
            return
            
        # Open save dialog
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save OpenSCAD File",
            self.output_directory,
            "OpenSCAD Files (*.scad)"
        )
        
        if file_name:
            # Ensure .scad extension
            if not file_name.endswith('.scad'):
                file_name += '.scad'
                
            # Save the file
            with open(file_name, 'w') as f:
                f.write(self.current_scad_code)
                
            self.status_label.setText(f"Saved to: {file_name}")
            
    def export_stl(self):
        """Export the generated code to STL."""
        if not self.current_scad_code:
            return
            
        # Open save dialog
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export to STL",
            self.output_directory,
            "STL Files (*.stl)"
        )
        
        if file_name:
            # Ensure .stl extension
            if not file_name.endswith('.stl'):
                file_name += '.stl'
                
            # Disable button and show progress
            self.export_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(30)
            
            # Start export in a separate thread
            self.export_thread = ExportThread(self.current_scad_code, file_name)
            self.export_thread.progress.connect(self.update_status)
            self.export_thread.finished.connect(self.handle_export_complete)
            self.export_thread.start()
            
    def handle_export_complete(self, success, result):
        """Handle completion of STL export."""
        self.export_button.setEnabled(True)
        self.progress_bar.setValue(100)
        
        if success:
            self.status_label.setText(f"STL exported to: {result}")
        else:
            self.status_label.setText(f"Export failed: {result}")
            QMessageBox.warning(self, "Export Error", result)
            
    def open_in_openscad(self):
        """Open the generated code in OpenSCAD."""
        if not self.current_scad_code:
            return
            
        # Create a temporary SCAD file
        with tempfile.NamedTemporaryFile(suffix='.scad', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(self.current_scad_code.encode('utf-8'))
            
        # Try to open the file with OpenSCAD
        try:
            if sys.platform == 'win32':
                os.startfile(tmp_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', tmp_path])
            else:  # Linux
                subprocess.call(['openscad', tmp_path])
                
            self.status_label.setText("Opened in OpenSCAD")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open OpenSCAD: {str(e)}")
            
    def update_status(self, message):
        """Update the status label."""
        self.status_label.setText(message)

def main_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 