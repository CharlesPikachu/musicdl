
import json
import subprocess
import sys
import os
from pathlib import Path

def fetch_lyrics_via_lddc(song_info, embed=False):
    """
    Fetch lyrics using LDDC bridge script.
    
    Args:
        song_info (dict or object): MusicDL song info object or dict.
        embed (bool): Whether to embed lyrics into the file (requires song_info['save_path']).
        
    Returns:
        str: Lyrics text, or None if failed.
    """
    try:
        # Convert song_info object to dict if needed
        if hasattr(song_info, 'todict'):
            info_dict = song_info.todict()
        elif isinstance(song_info, dict):
            info_dict = song_info
        else:
            # Try to build dict from attributes
            info_dict = {
                'source': getattr(song_info, 'source', ''),
                'song_name': getattr(song_info, 'song_name', ''),
                'singers': getattr(song_info, 'singers', ''),
                'album': getattr(song_info, 'album', ''),
                'duration': getattr(song_info, 'duration', ''),
                'save_path': getattr(song_info, 'save_path', ''),
            }

        # Prepare arguments
        bridge_script = os.path.join(os.path.dirname(__file__), 'lddc_bridge.py')
        
        # Determine python executable
        # Prefer LDDC's own venv to avoid missing dependencies
        lddc_venv_python = r"z:/code/gitea/LDDC/.venv/Scripts/python.exe"
        if os.path.exists(lddc_venv_python):
            python_exe = lddc_venv_python
        else:
            python_exe = sys.executable

        # Ensure input data is serializable
        # duration might be float or formatted string, json.dumps handles float/str/int
        # singers might be list or string
        input_json = json.dumps(info_dict)
        
        cmd = [python_exe, bridge_script, '--song-info-json', input_json]
        
        if embed and info_dict.get('save_path'):
            cmd.append('--embed')
            # Assuming bridge logic uses input json save_path if not overridden, 
            # or we can pass --save-path from info_dict['save_path']
            cmd.extend(['--save-path', info_dict['save_path']])
            
        # Run subprocess
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            check=False
        )
        
        if result.returncode != 0:
            # print(f"[LDDC Adapter] Error running bridge: {result.stderr}")
            return None
            
        output = result.stdout.strip()
        if not output:
             # print("[LDDC Adapter] No output from bridge")
             return None
             
        # Parse JSON output
        try:
            data = json.loads(output)
            if data.get('success'):
                return data.get('lyrics')
            else:
                # print(f"[LDDC Adapter] LDDC failed: {data.get('error')}")
                return None
        except json.JSONDecodeError:
            # print(f"[LDDC Adapter] Invalid JSON from bridge: {output}")
            return None

    except Exception as e:
        # print(f"[LDDC Adapter] Exception: {e}")
        return None
