import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from gui.rag_backend import generate_openscad_code

class Prompt2PartGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Prompt2Part - RAG OpenSCAD Generator')
        self.resize(900, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Prompt input
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText('Enter your prompt (e.g., "Generate a parametric L-bracket with mounting holes")')
        layout.addWidget(QLabel('Prompt:'))
        layout.addWidget(self.prompt_edit)

        # Generate button
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton('Generate')
        self.generate_btn.clicked.connect(self.on_generate)
        btn_layout.addWidget(self.generate_btn)
        layout.addLayout(btn_layout)

        # Code display
        layout.addWidget(QLabel('Generated OpenSCAD Code:'))
        self.code_edit = QTextEdit()
        self.code_edit.setReadOnly(False)
        layout.addWidget(self.code_edit)

        # Render preview
        layout.addWidget(QLabel('Rendered Preview:'))
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        self.setLayout(layout)

    def on_generate(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, 'No Prompt', 'Please enter a prompt.')
            return
        # --- Backend stub: Replace with real RAG/LLM call ---
        code = self.generate_code(prompt)
        self.code_edit.setPlainText(code)
        # --- Render with OpenSCAD CLI ---
        img_path = self.render_scad(code)
        if img_path:
            self.image_label.setPixmap(QPixmap(img_path).scaled(400, 400, Qt.KeepAspectRatio))
        else:
            self.image_label.setText('Render failed.')

    def clean_code(self, code):
        # Remove triple backticks and any language tag
        code = re.sub(r'```[a-zA-Z]*\n?', '', code)
        code = code.replace('```', '')
        return code.strip()

    def generate_code(self, prompt):
        # Use the real RAG/LLM backend
        code = generate_openscad_code(prompt)
        return self.clean_code(code)

    def render_scad(self, code):
        # Save code to temp file
        os.makedirs('gui/assets', exist_ok=True)
        scad_path = 'gui/assets/temp.scad'
        png_path = 'gui/assets/temp.png'
        with open(scad_path, 'w') as f:
            f.write(code)
        # Call OpenSCAD CLI to render PNG
        cmd = f"openscad -o {png_path} {scad_path}"
        result = os.system(cmd)
        if result == 0 and os.path.exists(png_path):
            return png_path
        return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = Prompt2PartGUI()
    gui.show()
    sys.exit(app.exec_()) 