#!/usr/bin/env python3
# MusicDL GUI Entry Point
"""
MusicDL - Music Download Tool with PyQt6 GUI
Modern, modular GUI with theme presets and Windows dark mode detection.
"""

import sys
import os

# --- Patch rich.progress BEFORE importing musicdl ---
# This prevents console output in GUI mode
import rich.progress
from gui.workers import GUIProgress
rich.progress.Progress = GUIProgress
# ----------------------------------------------------

from PyQt6.QtWidgets import QApplication

# Handle imports for both development and PyInstaller
try:
    from gui import MainWindow
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from gui import MainWindow


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("MusicDL")
    app.setOrganizationName("MusicDL")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
