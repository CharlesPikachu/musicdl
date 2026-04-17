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
import struct
import base64
import shutil
import requests
import tempfile
from io import BytesIO
from pathlib import Path
from .data import SongInfo
from mutagen.mp3 import MP3
from tinytag import TinyTag
from mutagen.asf import ASF
from .lyric import WhisperLRC
from mutagen.aiff import AIFF
from mutagen.wave import WAVE
from mimetypes import guess_type
from .logger import LoggerHandle
from mutagen.mp4 import MP4Cover, MP4
from mutagen.flac import Picture, FLAC
from mutagen import File as MutagenFile
from mutagen.oggvorbis import OggVorbis
from mutagen.asf import ASFByteArrayAttribute
from mutagen.id3 import ID3, USLT, APIC, TIT2, TALB, TPE1, PictureType


'''SongInfoUtils'''
class SongInfoUtils:
    '''supplsonginfothensavelyricsthenwritetags'''
    @staticmethod
    def supplsonginfothensavelyricsthenwritetags(song_info: SongInfo, logger_handle: LoggerHandle, disable_print: bool, auto_save_lyrics_then_write_tags: bool = True, enable_whisperlrc: bool = False) -> SongInfo:
        # correct file size
        song_info.file_size_bytes = (path := Path(song_info.save_path)).stat().st_size
        song_info.file_size = SongInfoUtils.byte2mb(size=song_info.file_size_bytes)
        # tinytag parse
        try: tag = TinyTag.get(str(path))
        except Exception as err: logger_handle.warning(f'SongInfoUtils.supplsonginfothensavelyricsthenwritetags >>> {str(path)} (Err: {err})', disable_print=disable_print); tag = None
        song_info.bitrate = int(round(tag.bitrate)) if tag and tag.bitrate else song_info.bitrate
        song_info.samplerate = int(tag.samplerate) if tag and tag.samplerate else song_info.samplerate
        song_info.channels = int(tag.channels) if tag and tag.channels else song_info.channels
        tag and tag.duration and setattr(song_info, "duration_s", int(round(tag.duration))) is None and setattr(song_info, "duration", SongInfoUtils.seconds2hms(tag.duration))
        song_info.codec = (tag.codec if tag and getattr(tag, "codec", None) else (tag.extra.get("codec") or tag.extra.get("mime-type")) if tag and getattr(tag, "extra", None) else song_info.codec)
        # supplement lyric if set
        if ((os.environ.get('ENABLE_WHISPERLRC', 'False').lower() == 'true') or enable_whisperlrc) and ((not song_info.lyric) or (song_info.lyric in {'NULL', 'null', 'None', 'none'})):
            song_info.raw_data['lyric'] = WhisperLRC(model_size_or_path='small').fromfilepath(str(path)); song_info.lyric = song_info.raw_data['lyric']['lyric']
        # write tags to audio file
        if auto_save_lyrics_then_write_tags:
            try: SongInfoUtils.savelyricsthenwritetagstoaudio(song_info, overwrite=False)
            except Exception as err: logger_handle.warning(f'SongInfoUtils.supplsonginfothensavelyricsthenwritetags >>> {str(path)} (Err: {err})', disable_print=disable_print)
        # return
        return song_info
    '''savelyricsthenwritetagstoaudio'''
    @staticmethod
    def savelyricsthenwritetagstoaudio(song_info: SongInfo, overwrite: bool = False, *, timeout: int = 15) -> dict:
        lyrics_text = SongInfoUtils.normalizetext(getattr(song_info, "lyric", None)); title = SongInfoUtils.normalizetext(getattr(song_info, "song_name", None))
        album = SongInfoUtils.normalizetext(getattr(song_info, "album", None)); artists = SongInfoUtils.normalizetext(getattr(song_info, "singers", None))
        cover_source = SongInfoUtils.normalizetext(getattr(song_info, "cover_url", None)); audio_path = Path(song_info.save_path)
        results = {"lyrics_embedded": False, "basic_tags_embedded": False, "cover_embedded": False, "lrc_saved": False}
        if lyrics_text: results["lrc_saved"] = SongInfoUtils.savelrctofile(audio_path, lyrics_text, overwrite=overwrite)
        if lyrics_text: results["lyrics_embedded"] = SongInfoUtils.safeeditaudio(audio_path=audio_path, editor=SongInfoUtils.embedlyrics, overwrite=overwrite, lyrics_text=lyrics_text)
        if title or album or artists: results["basic_tags_embedded"] = SongInfoUtils.safeeditaudio(audio_path=audio_path, editor=SongInfoUtils.embedbasictags, overwrite=overwrite, title=title, album=album, artists=artists)
        if cover_source and SongInfoUtils.lookslikecoversource(cover_source): results["cover_embedded"] = SongInfoUtils.safeeditaudio(audio_path=audio_path, editor=SongInfoUtils.embedcover, overwrite=overwrite, cover_source=cover_source, timeout=timeout)
        return results
    '''savelrctofile'''
    @staticmethod
    def savelrctofile(audio_path: Path, lyrics_text: str, *, overwrite: bool = False) -> bool:
        if (lrc_path := audio_path.with_suffix(".lrc")).exists() and (not overwrite): return False
        if (not (content := (lyrics_text or "").replace("\r\n", "\n").strip())) or (content in {'None', 'none', 'NULL', 'null'}): return False
        return SongInfoUtils.atomicwritetext(lrc_path, content + "\n" if (not content.endswith("\n")) else content)
    '''safeeditaudio'''
    @staticmethod
    def safeeditaudio(audio_path: Path, editor, **editor_kwargs) -> bool:
        if (not audio_path.exists()) or (not SongInfoUtils.audioreadable(audio_path)): return False
        temp_path, backup_path = SongInfoUtils.maketemppath(audio_path), audio_path.with_suffix(audio_path.suffix + ".bak")
        try:
            shutil.copy2(audio_path, temp_path)
            if not bool(editor(temp_path, **editor_kwargs)): return False
            if not SongInfoUtils.audioreadable(temp_path): return False
            backup_path.unlink(missing_ok=True); os.replace(audio_path, backup_path); os.replace(temp_path, audio_path)
            if not SongInfoUtils.audioreadable(audio_path): os.replace(backup_path, audio_path); return False
            backup_path.unlink(missing_ok=True); return True
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
        if ((audio := MutagenFile(audio_path)) is None) or (not (text := (lyrics_text or "").replace("\r\n", "\n").strip())): return False
        cls = audio.__class__.__name__; audio: FLAC | MP3 = audio
        # MP3
        if cls == "MP3":
            id3 = SongInfoUtils.loadorcreateid3(audio_path)
            if any(str(k).startswith("USLT") for k in id3.keys()) and (not overwrite): return False
            overwrite and id3.delall("USLT"); id3.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=text)); id3.save(audio_path, v2_version=3)
            return True
        # MP4/M4A
        if cls == "MP4":
            tags = SongInfoUtils.safegeteditabletags(audio=audio)
            if tags.get((key := "\xa9lyr")) and (not overwrite): return False
            tags[key] = [text]; audio.tags = tags; audio.save()
            return True
        # FLAC/OGG/OPUS
        if cls in {"FLAC", "OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            tags = SongInfoUtils.safegeteditabletags(audio=audio)
            if bool(tags.get("LYRICS")) and (not overwrite): return False
            tags["LYRICS"] = [text]; audio.tags = tags; audio.save()
            return True
        # ASF/WMA
        if cls == "ASF":
            tags = SongInfoUtils.safegeteditabletags(audio=audio)
            if tags.get((key := "WM/Lyrics")) and (not overwrite): return False
            tags[key] = [text]; audio.tags = tags; audio.save()
            return True
        return False
    '''embedbasictags'''
    @staticmethod
    def embedbasictags(audio_path: Path, *, overwrite: bool, title: str | None, album: str | None, artists: list[str] | None) -> bool:
        # init
        if (audio := MutagenFile(audio_path)) is None: return False
        cls = audio.__class__.__name__; changed = False; audio: FLAC | MP3 = audio
        # MP3
        if cls == "MP3":
            id3 = SongInfoUtils.loadorcreateid3(audio_path)
            title and (overwrite or not id3.getall("TIT2")) and (id3.setall("TIT2", [TIT2(encoding=3, text=title)]), changed := True)
            album and (overwrite or not id3.getall("TALB")) and (id3.setall("TALB", [TALB(encoding=3, text=album)]), changed := True)
            artists and (overwrite or not id3.getall("TPE1")) and (id3.setall("TPE1", [TPE1(encoding=3, text=artists)]), changed := True)
            changed and id3.save(audio_path, v2_version=3); return changed
        # MP4 / M4A
        if cls == "MP4":
            tags = SongInfoUtils.safegeteditabletags(audio=audio)
            title and (overwrite or not tags.get("\xa9nam")) and (tags.__setitem__("\xa9nam", [title]), changed := True)
            album and (overwrite or not tags.get("\xa9alb")) and (tags.__setitem__("\xa9alb", [album]), changed := True)
            artists and (overwrite or not tags.get("\xa9ART")) and (tags.__setitem__("\xa9ART", artists), changed := True)
            changed and (setattr(audio, "tags", tags), audio.save()); return changed
        # FLAC / OGG / OPUS
        if cls in {"FLAC", "OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            tags = SongInfoUtils.safegeteditabletags(audio=audio)
            title and (overwrite or not tags.get("TITLE")) and (tags.__setitem__("TITLE", [title]), changed := True)
            album and (overwrite or not tags.get("ALBUM")) and (tags.__setitem__("ALBUM", [album]), changed := True)
            artists and (overwrite or not tags.get("ARTIST")) and (tags.__setitem__("ARTIST", artists), changed := True)
            changed and (setattr(audio, "tags", tags), audio.save()); return changed
        # ASF / WMA
        if cls == "ASF":
            tags = SongInfoUtils.safegeteditabletags(audio=audio)
            title and (overwrite or not tags.get("Title")) and (tags.__setitem__("Title", [title]), changed := True)
            album and (overwrite or not tags.get("WM/AlbumTitle")) and (tags.__setitem__("WM/AlbumTitle", [album]), changed := True)
            artists and (overwrite or not tags.get("Author")) and (tags.__setitem__("Author", artists), changed := True)
            changed and (setattr(audio, "tags", tags), audio.save()); return changed
        # Not Match
        return False
    '''embedcover'''
    @staticmethod
    def embedcover(audio_path: Path, *, overwrite: bool, cover_source: str, timeout: int = 15) -> bool:
        # init
        if (audio := MutagenFile(audio_path)) is None: return False
        cls = audio.__class__.__name__; audio: FLAC | MP3 = audio
        cover_bytes, mime = SongInfoUtils.loadimagebytesandmime(cover_source, timeout=timeout)
        # MP3
        if cls == "MP3":
            id3 = SongInfoUtils.loadorcreateid3(audio_path)
            if any(str(k).startswith("APIC") for k in id3.keys()) and (not overwrite): return False
            overwrite and id3.delall("APIC"); id3.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover_bytes)); id3.save(audio_path, v2_version=3)
            return True
        # MP4
        if cls == "MP4":
            if mime not in {"image/jpeg", "image/png"}: return False
            if (tags := SongInfoUtils.safegeteditabletags(audio=audio)).get("covr") and (not overwrite): return False
            image_format = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
            tags["covr"] = [MP4Cover(cover_bytes, imageformat=image_format)]; audio.tags = tags; audio.save()
            return True
        # FLAC
        if cls == "FLAC":
            if bool(getattr(audio, "pictures", [])) and (not overwrite): return False
            picture = Picture(); picture.type = 3; picture.mime = mime; picture.desc = "Cover"; picture.data = cover_bytes
            overwrite and audio.clear_pictures(); audio.add_picture(picture); audio.save()
            return True
        # OGG/OPUS
        if cls in {"OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            if (tags := SongInfoUtils.safegeteditabletags(audio=audio)).get("METADATA_BLOCK_PICTURE") and (not overwrite): return False
            picture = Picture(); picture.type = 3; picture.mime = mime; picture.desc = "Cover"; picture.data = cover_bytes
            tags["METADATA_BLOCK_PICTURE"] = [base64.b64encode(picture.write()).decode("ascii")]; audio.tags = tags; audio.save()
            return True
        # ASF/WMA
        if cls == "ASF":
            if (tags := SongInfoUtils.safegeteditabletags(audio=audio)).get("WM/Picture") and (not overwrite): return False
            pic_bytes = struct.pack("<BI", int(PictureType.COVER_FRONT), len(cover_bytes)) + mime.encode("utf-16le") + b"\x00\x00" + "Cover".encode("utf-16le") + b"\x00\x00" + cover_bytes
            tags["WM/Picture"] = [ASFByteArrayAttribute(pic_bytes)]; audio.tags = tags; audio.save()
            return True
        # Not Match
        return False
    '''loadimagebytesandmime'''
    @staticmethod
    def loadimagebytesandmime(cover: str | Path, *, timeout: int = 15) -> tuple[bytes, str]:
        # naive judgement
        if not (cover_str := str(cover).strip()): raise ValueError("Empty cover")
        # local path judgement
        if not cover_str.startswith("http"): cover_path = Path(cover_str); data = cover_path.read_bytes(); mime = (guess_type(str(cover_path))[0] or "image/jpeg").split(";", 1)[0].lower(); return data, mime
        # url judgement
        (resp := requests.get(cover_str, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)).raise_for_status()
        content_type = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        mime = (content_type or (guess_type(cover_str)[0] or "image/jpeg")).split(";", 1)[0].lower()
        # minimal signature fallback
        signature = (data := (resp.content or b""))[:8]
        if signature.startswith(b"\xFF\xD8\xFF"): mime = "image/jpeg"
        elif signature.startswith(b"\x89PNG\r\n\x1a\n"): mime = "image/png"
        if not mime.startswith("image/"): raise ValueError(f"Not an image (Content-Type={content_type!r})")
        # return
        return data, mime
    '''normalizetext'''
    @staticmethod
    def normalizetext(value) -> str | None:
        if not value or value in {'NULL', 'null', 'None', 'none'}: return None
        return (str(value).strip() or None)
    '''lookslikecoversource'''
    @staticmethod
    def lookslikecoversource(cover_source: str) -> bool:
        return cover_source.startswith("http") or Path(cover_source).exists()
    '''audioreadable'''
    @staticmethod
    def audioreadable(audio_path: Path) -> bool:
        try:
            if not audio_path.exists() or audio_path.stat().st_size <= 0: return False
            if (audio := MutagenFile(audio_path)) is None or getattr(audio, "info", None) is None: return False
            TinyTag.get(str(audio_path)); return True
        except Exception:
            return False
    '''maketemppath'''
    @staticmethod
    def maketemppath(audio_path: Path) -> Path:
        fd, temp_name = tempfile.mkstemp(prefix=audio_path.stem + ".", suffix=audio_path.suffix, dir=str(audio_path.parent)); os.close(fd)
        return Path(temp_name)
    '''atomicwritetext'''
    @staticmethod
    def atomicwritetext(path: Path, text: str) -> bool:
        fd, temp_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=path.suffix, dir=str(path.parent)); os.close(fd); temp_path = Path(temp_name)
        try: temp_path.write_text(text, encoding="utf-8"); os.replace(temp_path, path); return True
        except Exception: return False
        finally: temp_path.unlink(missing_ok=True)
    '''loadorcreateid3'''
    @staticmethod
    def loadorcreateid3(audio_path: Path) -> ID3:
        try: return ID3(audio_path)
        except Exception: return ID3()
    '''safegeteditabletags'''
    @staticmethod
    def safegeteditabletags(audio: FLAC | MP3):
        if (tags := getattr(audio, "tags", None)) is not None: return tags
        try: audio.add_tags()
        except Exception: pass
        return getattr(audio, "tags", None) or {}
    '''estimatedurationwithfilesizebr'''
    @staticmethod
    def estimatedurationwithfilesizebr(file_size_bytes: int, br_kbps: float, return_seconds: bool = False) -> str:
        if (not file_size_bytes) or (not br_kbps) or (br_kbps <= 0): return (0 if return_seconds else "-:-:-")
        duration_seconds = int(file_size_bytes * 8 / (br_kbps * 1000))
        hours, minutes, seconds = duration_seconds // 3600, (duration_seconds % 3600) // 60, duration_seconds % 60
        return (duration_seconds if return_seconds else f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    '''estimatedurationwithfilelink'''
    @staticmethod
    def estimatedurationwithfilelink(filelink: str = '', headers: dict = None, request_overrides: dict = None):
        headers, request_overrides = dict(headers or {}), dict(request_overrides or {})
        try: (resp := requests.get(filelink, headers=headers, timeout=10, **request_overrides)).raise_for_status(); audio: FLAC = MutagenFile(BytesIO(resp.content)); return int(getattr(audio.info, "length", 0))
        except Exception: return 0
    '''seconds2hms'''
    @staticmethod
    def seconds2hms(seconds: int):
        try: hms = '-:-:-' if not (t := int(float(seconds))) else f'{t//3600:02d}:{t//60%60:02d}:{t%60:02d}'
        except Exception: hms = '-:-:-'
        return hms
    '''byte2mb'''
    @staticmethod
    def byte2mb(size: int):
        try: size = 'NULL' if not (mb := round(int(float(size)) / 1024 / 1024, 2)) else f'{mb} MB'
        except Exception: size = 'NULL'
        return size
    '''mb2byte'''
    def mb2byte(size: str | float):
        try: nbytes = 0 if size == 'NULL' else int(float(size.removesuffix('MB').strip()) * 1024 * 1024)
        except Exception: nbytes = 0
        return nbytes
    '''naiveguessextfromaudiobytes'''
    @staticmethod
    def naiveguessextfromaudiobytes(content: bytes):
        if (audio := MutagenFile(BytesIO(content))) is None: return None
        AUDIO_EXTENSIONS = {MP3: "mp3", FLAC: "flac", MP4: "m4a", OggVorbis: "ogg", WAVE: "wav", AIFF: "aiff", ASF: "wma"}
        for cls, ext in AUDIO_EXTENSIONS.items():
            if isinstance(audio, cls): return ext
        return None