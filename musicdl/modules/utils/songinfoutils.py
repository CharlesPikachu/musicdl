'''
Function:
    Implementation of SongInfoUtils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import os
import base64
import shutil
import requests
import tempfile
from pathlib import Path
from mutagen import File
from .data import SongInfo
from tinytag import TinyTag
from .lyric import WhisperLRC
from mimetypes import guess_type
from .logger import LoggerHandle
from mutagen.flac import Picture
from mutagen.mp4 import MP4Cover
from .misc import seconds2hms, byte2mb
from mutagen.id3 import ID3, USLT, APIC, TIT2, TALB, TPE1


'''SongInfoUtils'''
class SongInfoUtils:
    '''fillsongtechinfo'''
    @staticmethod
    def fillsongtechinfo(song_info: SongInfo, logger_handle: LoggerHandle, disable_print: bool, auto_write_tags_to_downloaded_audio: bool = True) -> SongInfo:
        path = Path(song_info.save_path)
        # correct file size
        size = path.stat().st_size
        song_info.file_size_bytes = size
        song_info.file_size = byte2mb(size=size)
        # tinytag parse
        try: tag = TinyTag.get(str(path))
        except Exception as err: logger_handle.warning(f'SongInfoUtils.fillsongtechinfo >>> {str(path)} (Err: {err})', disable_print=disable_print); return song_info
        if tag.duration: song_info.duration_s = int(round(tag.duration)); song_info.duration = seconds2hms(tag.duration)
        if tag.bitrate: song_info.bitrate = int(round(tag.bitrate))
        if tag.samplerate: song_info.samplerate = int(tag.samplerate)
        if tag.channels: song_info.channels = int(tag.channels)
        if getattr(tag, "codec", None): song_info.codec = tag.codec
        elif getattr(tag, "extra", None) and isinstance(tag.extra, dict): song_info.codec = tag.extra.get("codec") or tag.extra.get("mime-type")
        # lyric
        if os.environ.get('ENABLE_WHISPERLRC', 'False').lower() == 'true' and ((not song_info.lyric) or (song_info.lyric == 'NULL')):
            lyric_result = WhisperLRC(model_size_or_path='small').fromfilepath(str(path))
            lyric = lyric_result['lyric']; song_info.lyric = lyric; song_info.raw_data['lyric'] = lyric_result
        # write tags to audio file
        if auto_write_tags_to_downloaded_audio:
            try: SongInfoUtils.writetagstoaudio(song_info, overwrite=False)
            except: pass
        # return
        return song_info
    '''writetagstoaudio'''
    @staticmethod
    def writetagstoaudio(song_info: SongInfo, overwrite: bool = False, *, timeout: int = 15) -> dict:
        audio_path = Path(song_info.save_path)
        lyrics_text = SongInfoUtils.normalizetext(getattr(song_info, "lyric", None))
        title = SongInfoUtils.normalizetext(getattr(song_info, "song_name", None))
        album = SongInfoUtils.normalizetext(getattr(song_info, "album", None))
        artists = SongInfoUtils.normalizetext(getattr(song_info, "singers", None))
        cover_source = SongInfoUtils.normalizetext(getattr(song_info, "cover_url", None))
        results = {"lyrics_embedded": False, "basic_tags_embedded": False, "cover_embedded": False, "lrc_saved": False}
        if lyrics_text: results["lrc_saved"] = SongInfoUtils.savelrctofile(audio_path, lyrics_text, overwrite=overwrite)
        if lyrics_text: results["lyrics_embedded"] = SongInfoUtils.safeeditaudio(audio_path=audio_path, editor=SongInfoUtils.embedlyrics, overwrite=overwrite, lyrics_text=lyrics_text)
        if title or album or artists: results["basic_tags_embedded"] = SongInfoUtils.safeeditaudio(audio_path=audio_path, editor=SongInfoUtils.embedbasictags, overwrite=overwrite, title=title, album=album, artists=artists)
        if cover_source and SongInfoUtils.lookslikecoversource(cover_source): results["cover_embedded"] = SongInfoUtils.safeeditaudio(audio_path=audio_path, editor=SongInfoUtils.embedcover, overwrite=overwrite, cover_source=cover_source, timeout=timeout)
        return results
    '''savelrctofile'''
    @staticmethod
    def savelrctofile(audio_path: Path, lyrics_text: str, *, overwrite: bool = False) -> bool:
        lrc_path = audio_path.with_suffix(".lrc")
        if lrc_path.exists() and not overwrite: return False
        content = (lyrics_text or "").replace("\r\n", "\n").strip()
        if not content: return False
        if not content.endswith("\n"): content += "\n"
        return SongInfoUtils.atomicwritetext(lrc_path, content)
    '''safeeditaudio'''
    @staticmethod
    def safeeditaudio(audio_path: Path, editor, **editor_kwargs) -> bool:
        if not audio_path.exists(): return False
        if not SongInfoUtils.audioreadable(audio_path): return False
        temp_path = SongInfoUtils.maketemppath(audio_path)
        backup_path = audio_path.with_suffix(audio_path.suffix + ".bak")
        try:
            shutil.copy2(audio_path, temp_path)
            changed = bool(editor(temp_path, **editor_kwargs))
            if not changed: return False
            if not SongInfoUtils.audioreadable(temp_path): return False
            backup_path.unlink(missing_ok=True)
            os.replace(audio_path, backup_path)
            os.replace(temp_path, audio_path)
            if not SongInfoUtils.audioreadable(audio_path): os.replace(backup_path, audio_path); return False
            backup_path.unlink(missing_ok=True)
            return True
        except Exception:
            if (not audio_path.exists()) and backup_path.exists():
                try: os.replace(backup_path, audio_path)
                except Exception: pass
            return False
        finally:
            temp_path.unlink(missing_ok=True)
    '''embedlyrics'''
    @staticmethod
    def embedlyrics(audio_path: Path, *, overwrite: bool, lyrics_text: str) -> bool:
        # init
        audio = File(audio_path)
        if audio is None: return False
        cls = audio.__class__.__name__; text = (lyrics_text or "").replace("\r\n", "\n").strip()
        if not text: return False
        # MP3
        if cls == "MP3":
            id3 = SongInfoUtils.loadorcreateid3(audio_path)
            has = any(k.startswith("USLT") for k in id3.keys())
            if has and not overwrite: return False
            if overwrite: id3.delall("USLT")
            id3.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=text))
            id3.save(audio_path, v2_version=3)
            return True
        # MP4/M4A
        if cls == "MP4":
            tags = audio.tags or {}; key = "\xa9lyr"
            if tags.get(key) and not overwrite: return False
            tags[key] = [text]; audio.tags = tags; audio.save()
            return True
        # FLAC/OGG/OPUS
        if cls in {"FLAC", "OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            tags = audio.tags or {}; has = bool(tags.get("LYRICS"))
            if has and not overwrite: return False
            tags["LYRICS"] = [text]; audio.tags = tags; audio.save()
            return True
        # ASF/WMA
        if cls == "ASF":
            tags = audio.tags or {}; key = "WM/Lyrics"
            if tags.get(key) and not overwrite: return False
            tags[key] = [text]; audio.tags = tags; audio.save()
            return True
        return False
    '''embedbasictags'''
    @staticmethod
    def embedbasictags(audio_path: Path, *, overwrite: bool, title: str | None, album: str | None, artists: list[str] | None) -> bool:
        # init
        audio = File(audio_path)
        if audio is None: return False
        cls = audio.__class__.__name__; changed = False
        # MP3
        if cls == "MP3":
            id3 = SongInfoUtils._load_or_create_id3(audio_path)
            if title and (overwrite or not id3.getall("TIT2")): id3.setall("TIT2", [TIT2(encoding=3, text=title)]); changed = True
            if album and (overwrite or not id3.getall("TALB")): id3.setall("TALB", [TALB(encoding=3, text=album)]); changed = True
            if artists and (overwrite or not id3.getall("TPE1")): id3.setall("TPE1", [TPE1(encoding=3, text=artists)]); changed = True
            if changed: id3.save(audio_path, v2_version=3)
            return changed
        # MP4/M4A
        if cls == "MP4":
            tags = audio.tags or {}
            if title and (overwrite or not tags.get("\xa9nam")): tags["\xa9nam"] = [title]; changed = True
            if album and (overwrite or not tags.get("\xa9alb")): tags["\xa9alb"] = [album]; changed = True
            if artists and (overwrite or not tags.get("\xa9ART")): tags["\xa9ART"] = artists; changed = True
            if changed: audio.tags = tags; audio.save()
            return changed
        # FLAC / OGG / OPUS
        if cls in {"FLAC", "OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            tags = audio.tags or {}
            if title and (overwrite or not tags.get("TITLE")): tags["TITLE"] = [title]; changed = True
            if album and (overwrite or not tags.get("ALBUM")): tags["ALBUM"] = [album]; changed = True
            if artists and (overwrite or not tags.get("ARTIST")): tags["ARTIST"] = artists; changed = True
            if changed: audio.tags = tags; audio.save()
            return changed
        # ASF/WMA
        if cls == "ASF":
            tags = audio.tags or {}
            if title and (overwrite or not tags.get("Title")): tags["Title"] = [title]; changed = True
            if album and (overwrite or not tags.get("WM/AlbumTitle")): tags["WM/AlbumTitle"] = [album]; changed = True
            if artists and (overwrite or not tags.get("Author")): tags["Author"] = artists; changed = True
            if changed: audio.tags = tags; audio.save()
            return changed
        return False
    '''embedcover'''
    @staticmethod
    def embedcover(audio_path: Path, *, overwrite: bool, cover_source: str, timeout: int = 15) -> bool:
        audio = File(audio_path)
        if audio is None: return False
        cls = audio.__class__.__name__
        cover_bytes, mime = SongInfoUtils.loadimagebytesandmime(cover_source, timeout=timeout)
        # MP3
        if cls == "MP3":
            id3 = SongInfoUtils._load_or_create_id3(audio_path)
            has = any(k.startswith("APIC") for k in id3.keys())
            if has and not overwrite: return False
            if overwrite: id3.delall("APIC")
            id3.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover_bytes))
            id3.save(audio_path, v2_version=3)
            return True
        # MP4
        if cls == "MP4":
            if mime not in {"image/jpeg", "image/png"}: return False
            tags = audio.tags or {}
            if tags.get("covr") and not overwrite: return False
            image_format = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
            tags["covr"] = [MP4Cover(cover_bytes, imageformat=image_format)]
            audio.tags = tags; audio.save()
            return True
        # FLAC
        if cls == "FLAC":
            has = bool(getattr(audio, "pictures", []))
            if has and not overwrite: return False
            picture = Picture()
            picture.type = 3; picture.mime = mime; picture.desc = "Cover"; picture.data = cover_bytes
            if overwrite: audio.clear_pictures()
            audio.add_picture(picture); audio.save()
            return True
        # OGG/OPUS
        if cls in {"OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            tags = audio.tags or {}
            if tags.get("METADATA_BLOCK_PICTURE") and not overwrite: return False
            picture = Picture()
            picture.type = 3; picture.mime = mime; picture.desc = "Cover"; picture.data = cover_bytes
            tags["METADATA_BLOCK_PICTURE"] = [base64.b64encode(picture.write()).decode("ascii")]
            audio.tags = tags; audio.save()
            return True
        # ASF/WMA
        if cls == "ASF":
            try: from mutagen.asf import ASFPicture
            except Exception: return False
            tags = audio.tags or {}
            if tags.get("WM/Picture") and not overwrite: return False
            picture = ASFPicture()
            picture.type = 3; picture.mime_type = mime; picture.description = "Cover"; picture.data = cover_bytes
            tags["WM/Picture"] = [picture]
            audio.tags = tags; audio.save()
            return True
        return False
    '''loadimagebytesandmime'''
    @staticmethod
    def loadimagebytesandmime(cover: str | Path, *, timeout: int = 15) -> tuple[bytes, str]:
        cover_str = str(cover).strip()
        if not cover_str: raise ValueError("Empty cover")
        # local path
        if not cover_str.startswith("http"): cover_path = Path(cover_str); data = cover_path.read_bytes(); mime = (guess_type(str(cover_path))[0] or "image/jpeg").split(";", 1)[0].lower(); return data, mime
        # url
        (resp := requests.get(cover_str, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)).raise_for_status()
        data = resp.content or b""
        content_type = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        mime = (content_type or (guess_type(cover_str)[0] or "image/jpeg")).split(";", 1)[0].lower()
        # minimal signature fallback
        signature = data[:8]
        if signature.startswith(b"\xFF\xD8\xFF"): mime = "image/jpeg"
        elif signature.startswith(b"\x89PNG\r\n\x1a\n"): mime = "image/png"
        if not mime.startswith("image/"): raise ValueError(f"Not an image (Content-Type={content_type!r})")
        return data, mime
    '''normalizetext'''
    @staticmethod
    def normalizetext(value) -> str | None:
        if not value or value in {'NULL', 'null', 'None', 'none'}: return None
        text = str(value).strip()
        return text or None
    '''lookslikecoversource'''
    @staticmethod
    def lookslikecoversource(cover_source: str) -> bool:
        return cover_source.startswith("http") or Path(cover_source).exists()
    '''audioreadable'''
    @staticmethod
    def audioreadable(audio_path: Path) -> bool:
        try:
            if not audio_path.exists() or audio_path.stat().st_size <= 0: return False
            audio = File(audio_path)
            if audio is None or getattr(audio, "info", None) is None: return False
            TinyTag.get(str(audio_path))
            return True
        except Exception:
            return False
    '''maketemppath'''
    @staticmethod
    def maketemppath(audio_path: Path) -> Path:
        fd, temp_name = tempfile.mkstemp(prefix=audio_path.stem + ".", suffix=audio_path.suffix, dir=str(audio_path.parent))
        os.close(fd)
        return Path(temp_name)
    '''atomicwritetext'''
    @staticmethod
    def atomicwritetext(path: Path, text: str) -> bool:
        fd, temp_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=path.suffix, dir=str(path.parent))
        os.close(fd); temp_path = Path(temp_name)
        try: temp_path.write_text(text, encoding="utf-8"); os.replace(temp_path, path); return True
        except Exception: return False
        finally: temp_path.unlink(missing_ok=True)
    '''loadorcreateid3'''
    @staticmethod
    def loadorcreateid3(audio_path: Path) -> ID3:
        try: return ID3(audio_path)
        except Exception: return ID3()