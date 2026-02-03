#!/usr/bin/env python3
"""Extract version from musicdl_gui.py for build script."""
import re
import sys
from pathlib import Path

def get_version():
    gui_path = Path(__file__).parent.parent / 'musicdl' / 'musicdl_gui.py'
    try:
        content = gui_path.read_text(encoding='utf-8')
        match = re.search(r'ApplicationVersion\(["\']([^"\']+)["\']\)', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return '1.0.0'

if __name__ == '__main__':
    print(get_version())
