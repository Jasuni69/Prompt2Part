import sys
from ui.cli import main_cli
from ui.gui import main_gui

if __name__ == "__main__":
    # Check if user wants GUI mode
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        main_gui()
    else:
        # Default to CLI
        main_cli() 