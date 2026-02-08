import sys
import json
import os
import argparse
import traceback
from pathlib import Path

# Add project root to path to allow importing LDDC
LDDC_PATH = r"z:\code\gitea\LDDC"
if LDDC_PATH not in sys.path:
    sys.path.insert(0, LDDC_PATH)

# Redirect stderr to file
sys.stderr = open('bridge_stderr.log', 'w', encoding='utf-8')

try:
    from PySide6.QtCore import QCoreApplication, QTimer
    from LDDC.common.models import SongInfo, Artist, Source, Lyrics, LyricsFormat
    from LDDC.core.auto_fetch import auto_fetch
    from LDDC.core.song_info import write_lyrics
    import logging
    # Configure logging to stderr to avoid polluting stdout (which we use for JSON result)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
except ImportError as e:
    print(json.dumps({"error": f"ImportError: {e}", "sys_path": sys.path}), file=sys.stdout)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="LDDC Bridge for MusicDL")
    parser.add_argument("--song-info-json", type=str, required=True, help="JSON string of song info")
    parser.add_argument("--save-path", type=str, help="Path to save music file to embed lyrics")
    parser.add_argument("--embed", action="store_true", help="Embed lyrics into file")
    
    args = parser.parse_args()

    app = None
    if not QCoreApplication.instance():
        app = QCoreApplication(sys.argv)
    
    try:
        # Load Song Info from JSON
        song_data = json.loads(args.song_info_json)
        
        # Map MusicDL source to LDDC Source
        # MusicDL sources: 'MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', etc.
        # LDDC sources: Source.QM, Source.KG, Source.NE, Source.LRCLIB
        source_map = {
            'NeteaseMusicClient': Source.NE,
            'QQMusicClient': Source.QM,
            'KugouMusicClient': Source.KG,
        }
        
        musicdl_source_str = song_data.get('source', '')
        # Remove 'MusicClient' suffix if present to match keys better, though exact match is safer
        # Let's map directly based on knowledge
        # If source is not supported (not in map), use Source.MULTI to let LDDC find best match from any source
        lddc_source = source_map.get(musicdl_source_str, Source.MULTI) 
        
        # Parse artist
        artist_raw = song_data.get('singers', '')
        if isinstance(artist_raw, list):
            artists = artist_raw
        elif isinstance(artist_raw, str):
            # Split by common separators
            # Replace various separators with a single comma then split
            normalized_artists = artist_raw.replace('、', ',').replace('/', ',').replace('&', ',').replace(';', ',')
            artists = [a.strip() for a in normalized_artists.split(',') if a.strip()]
        else:
            artists = []
            
        # Parse duration (ms)
        duration_ms = 0
        duration_raw = song_data.get('duration', '')
        if isinstance(duration_raw, str) and ':' in duration_raw:
             parts = duration_raw.split(':')
             if len(parts) == 2:
                 duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
             elif len(parts) == 3:
                 duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
        elif isinstance(duration_raw, (int, float)):
             duration_ms = int(duration_raw * 1000) # Assuming seconds if int/float and small
        
        # Construct LDDC SongInfo
        info = SongInfo(
            source=lddc_source,
            title=song_data.get('song_name', ''),
            artist=Artist(artists),
            album=song_data.get('album', ''),
            duration=duration_ms if duration_ms > 0 else None,
            path=Path(args.save_path) if args.save_path else None
        )
        
        # Fetch Lyrics
        # auto_fetch(info, min_score=60, sources=(Source.QM, Source.KG, Source.NE), return_search_results=False)
        # We can broaden sources if needed. Let's use default or multiple.
        # LDDC uses QEventLoop internally.
        
        # Note: auto_fetch runs a local QEventLoop.
        # Explicitly search all sources to find best match
        # Retry mechanism for duration mismatch
        try:
            lyrics = auto_fetch(
                info, 
                min_score=40, 
                sources=(Source.QM, Source.KG, Source.NE, Source.LRCLIB)
            )
        except Exception:
            # If failed, try again without duration check (if duration was set)
            if info.duration is not None:
                print("DEBUG: Retrying without duration check", file=sys.stderr)
                # SongInfo might be immutable, so create a new one
                new_info = SongInfo(
                    source=info.source,
                    title=info.title,
                    artist=info.artist,
                    album=info.album,
                    duration=None,
                    path=info.path
                )
                lyrics = auto_fetch(
                    new_info, 
                    min_score=40, 
                    sources=(Source.QM, Source.KG, Source.NE, Source.LRCLIB)
                )
            else:
                raise
        
        # Convert to LRC string (standard format)
        # LDDC's Lyrics.to() method:
        # def to(self, lyrics_format: LyricsFormat, langs: list[str] | None, offset: int = 0) -> str:
        # Try different formats and languages
        lyric_text = ""
        formats_to_try = [LyricsFormat.VERBATIMLRC, LyricsFormat.ENHANCEDLRC, LyricsFormat.LINEBYLINELRC]
        
        for fmt in formats_to_try:
            try:
                # Try with explicit langs to ensure we get 'orig' or 'trans' or 'ts'
                # keys might differ based on source. 'orig' is standard.
                text = lyrics.to(fmt, langs=['orig', 'ts', 'trans'])
                if text and text.strip():
                    lyric_text = text
                    break
            except Exception as e:
                pass
        
        if not lyric_text:
             # Fallback: just try without langs
             lyric_text = lyrics.to(LyricsFormat.LINEBYLINELRC, langs=None)
        
        result_data = {
            "lyrics": lyric_text,
            "success": True,
            "source": str(lyrics.source),
            "debug_info": {
                "types": {k: str(v) for k, v in lyrics.types.items()},
                "keys": list(lyrics.keys())
            }
        }
        
        if args.embed and args.save_path:
             path_obj = Path(args.save_path)
             if path_obj.exists():
                 try:
                     # LDDC write_lyrics(file_path, lyrics_text, lyrics=None)
                     # passing lyrics object allows it to write SYLT (synchronized lyrics) if supported (e.g. ID3v2)
                     write_lyrics(path_obj, lyric_text, lyrics=lyrics)
                     result_data["embedded"] = True
                 except Exception as e:
                     result_data["embedded"] = False
                     result_data["embed_error"] = str(e)
        
        # Ensure we write valid JSON to stdout
        print(json.dumps(result_data))

    except Exception as e:
        # Print error details to stderr (which is redirected to log file)
        traceback.print_exc()
        # Return error JSON to stdout
        # Note: formatting traceback might be useful for user if client reads it
        print(json.dumps({"error": str(e), "success": False, "traceback": traceback.format_exc()}))
        
    if app:
        app.quit()

if __name__ == "__main__":
    main()
