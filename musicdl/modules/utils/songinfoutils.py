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
import requests
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
from mutagen.id3 import ID3, APIC, USLT
from .importutils import optionalimportfrom


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
            lyric = lyric_result['lyric']
            song_info.lyric = lyric
            song_info.raw_data['lyric'] = lyric_result
        # write tags to audio file
        if auto_write_tags_to_downloaded_audio:
            try: SongInfoUtils.writetagstoaudio(song_info, overwrite=False)
            except: pass
        # return
        return song_info
    '''writetagstoaudio'''
    @staticmethod
    def writetagstoaudio(song_info: SongInfo, overwrite: bool = False):
        audio_path = Path(song_info.save_path)
        easy = File(audio_path, easy=True)
        if easy is None: raise ValueError(f"Unsupported/unreadable audio file: {audio_path}")
        tags, changed = {"artist": song_info.singers, "album": song_info.album, "title": song_info.song_name}, False
        for k, v in (tags or {}).items(): (not v or v == 'NULL') or ((overwrite or not easy.get(k)) and (easy.__setitem__(k, v if isinstance(v, (list, tuple)) else str(v)) or (changed := True)))
        if changed: 
            try: easy.save(v2_version=3)
            except: easy.save()
        if song_info.cover_url and song_info.cover_url != 'NULL' and (str(song_info.cover_url).startswith('http') or os.path.exists(str(song_info.cover_url))):
            try: changed = SongInfoUtils.writecovertoaudio(audio_path, song_info.cover_url, overwrite=overwrite) or changed
            except: pass
        if song_info.lyric and song_info.lyric != 'NULL':
            try: changed = SongInfoUtils.writelyricstoaudio(audio_path, song_info.lyric, overwrite=overwrite) or changed
            except: pass
        return changed
    '''loadimagebytesandmime'''
    @staticmethod
    def loadimagebytesandmime(cover: str | Path, *, timeout: int = 15) -> tuple[bytes, str]:
        cover_str, headers = str(cover), {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        # local image path
        if not cover_str.startswith('http'):
            path = Path(cover)
            data = path.read_bytes()
            mime = (guess_type(str(path))[0] or "image/jpeg").split(";")[0]
            return data, mime
        # network image url
        resp = requests.get(cover_str, stream=True, timeout=timeout, headers=headers, allow_redirects=True)
        resp.raise_for_status()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        mime, data = (ctype or (guess_type(cover_str)[0] or "image/jpeg")).split(";")[0], resp.content
        if not mime.startswith("image/"):
            sig = data[:12]
            if sig.startswith(b"\xFF\xD8\xFF"): mime = "image/jpeg"
            elif sig.startswith(b"\x89PNG\r\n\x1a\n"): mime = "image/png"
            elif sig[:4] == b"RIFF" and sig[8:12] == b"WEBP": mime = "image/webp"
            elif sig[:6] in (b"GIF87a", b"GIF89a"): mime = "image/gif"
            else: raise ValueError(f"URL did not return an image (Content-Type={ctype!r}).")
        return data, mime
    '''writecovertoaudio'''
    @staticmethod
    def writecovertoaudio(audio_path: Path, cover_path: str | Path, *, overwrite: bool = False):
        # init
        cover_bytes, mime = SongInfoUtils.loadimagebytesandmime(cover_path)
        audio = File(audio_path)
        if audio is None: raise ValueError(f"Unsupported/unreadable audio file: {audio_path}")
        cls, ext = audio.__class__.__name__, audio_path.suffix.lower()
        # mp3
        if ext == ".mp3":
            try: id3 = ID3(audio_path)
            except Exception: id3 = ID3()
            if not overwrite and any(k.startswith("APIC") for k in id3.keys()): return False
            if overwrite: id3.delall("APIC")
            id3.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover_bytes))
            id3.save(audio_path, v2_version=3)
            return True
        # mp4
        if cls == "MP4":
            has_cover = bool(audio.tags) and ("covr" in audio.tags)
            if has_cover and not overwrite: return False
            imgfmt = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
            audio["covr"] = [MP4Cover(cover_bytes, imageformat=imgfmt)]
            audio.save()
            return True
        # flac
        if cls == "FLAC":
            has_cover = bool(getattr(audio, "pictures", []))
            if has_cover and not overwrite: return False
            pic = Picture()
            pic.type, pic.mime, pic.desc, pic.data = 3, mime, "Cover", cover_bytes
            if overwrite: audio.clear_pictures()
            audio.add_picture(pic)
            audio.save()
            return True
        # ogg
        if cls in {"OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            has_cover = bool(audio.tags) and ("METADATA_BLOCK_PICTURE" in audio.tags)
            if has_cover and not overwrite: return False
            pic = Picture()
            pic.type, pic.mime, pic.desc, pic.data = 3, mime, "Cover", cover_bytes
            audio["METADATA_BLOCK_PICTURE"] = [base64.b64encode(pic.write()).decode("ascii")]
            audio.save()
            return True
        # asf
        if cls == "ASF" or ext in {".wma", ".asf"}:
            has_cover = bool(audio.tags) and ("WM/Picture" in audio.tags)
            if has_cover and not overwrite: return False
            ASFPicture, ASFValue = optionalimportfrom('mutagen.asf', 'ASFPicture'), optionalimportfrom('mutagen.asf', 'ASFValue')
            if ASFPicture is not None:
                pic = ASFPicture()
                pic.type, pic.mime_type, pic.description, pic.data = 3, mime, "Cover", cover_bytes
                audio["WM/Picture"] = [pic]
                audio.save()
                return True
            if ASFValue is not None:
                audio["WM/Picture"] = [ASFValue(cover_bytes)]
                audio.save()
                return True
            raise NotImplementedError("ASF(WMA) cover embedding not available in your mutagen build (ASFPicture/ASFValue not exposed). Upgrade mutagen or skip WMA cover.")
        # not supported
        raise NotImplementedError(f"Cover embedding not supported for: {cls} ({ext})")
    '''writelyricstoaudio'''
    def writelyricstoaudio(audio_path: Path, lyrics: str, *, overwrite: bool) -> bool:
        # init
        audio = File(audio_path)
        if audio is None: raise ValueError(f"Unsupported/unreadable audio file: {audio_path}")
        cls, ext = audio.__class__.__name__, audio_path.suffix.lower()
        # mp3
        if ext == ".mp3":
            try: id3 = ID3(audio_path)
            except Exception: id3 = ID3()
            has_lyrics = any(k.startswith("USLT") for k in id3.keys())
            if has_lyrics and not overwrite: return False
            if overwrite: any(id3.__delitem__(k) for k in list(id3.keys()) if k.startswith("USLT"))
            id3.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics))
            id3.save(audio_path)
            return True
        # m4a
        if cls == "MP4":
            has_lyrics = bool(audio.tags) and ("\xa9lyr" in audio.tags)
            if has_lyrics and not overwrite: return False
            audio["\xa9lyr"] = [lyrics]
            audio.save()
            return True
        # flac / ogg
        if cls in {"FLAC", "OggVorbis", "OggOpus", "OggSpeex", "OggTheora"}:
            has_lyrics = bool(audio.tags) and ("LYRICS" in audio.tags)
            if has_lyrics and not overwrite: return False
            audio["LYRICS"] = [lyrics]
            audio.save()
            return True
        # asf
        if cls == "ASF" or ext in {".wma", ".asf"}:
            has_lyrics = bool(audio.tags) and ("WM/Lyrics" in audio.tags)
            if has_lyrics and not overwrite: return False
            audio["WM/Lyrics"] = [lyrics]
            audio.save()
            return True
        # not supported
        raise NotImplementedError(f"Lyrics embedding not supported for: {cls} ({ext})")