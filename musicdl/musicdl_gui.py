#!/usr/bin/env python3
# MusicDL GUI Entry Point
"""
MusicDL - Music Download Tool with PyQt6 GUI
Modern, modular GUI with theme presets and Windows dark mode detection.
"""

import sys
import os

# Add project root to path to allow running script directly
# This handles both development (running from source) and frozen (PyInstaller) modes
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    _script_dir = os.path.dirname(sys.executable)
else:
    # Running as script - add parent of musicdl package to path
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_script_dir)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

# --- Patch rich.progress BEFORE importing musicdl ---
# This prevents console output in GUI mode
import rich.progress
from musicdl.gui.workers import GUIProgress
rich.progress.Progress = GUIProgress

# ALSO patch the already-imported Progress in base module
# This is critical because base.py imports Progress at module load time
# before the above patch takes effect
from musicdl.modules.sources import base as base_module
from musicdl.modules.sources import qq as qq_module
from musicdl.modules.sources import netease as netease_module
base_module.Progress = GUIProgress
qq_module.Progress = GUIProgress
netease_module.Progress = GUIProgress
# ----------------------------------------------------

from PyQt6.QtWidgets import QApplication
from musicdl.gui import MainWindow


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("MusicDL")
    app.setOrganizationName("MusicDL")
    app.setApplicationVersion("2.9.10")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
