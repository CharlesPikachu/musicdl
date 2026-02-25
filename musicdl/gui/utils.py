# GUI Utility Functions
"""
Common utilities for the MusicDL GUI.
"""

import sys
import os


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Path relative to the project root
        
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # In dev mode, use the parent of the gui directory (musicdl package)
        # Then go up one more level to reach project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


def parselist(song_infos):
    """
    Expand episodes in song_infos.
    Used by GUI modules to handle albums/books.
    """
    final_song_infos = []
    for song in song_infos:
        episodes = getattr(song, 'episodes', None) or (song.get('episodes') if isinstance(song, dict) else None) or []
        if episodes:
            final_song_infos.extend(episodes)
        else:
            final_song_infos.append(song)
    return final_song_infos
