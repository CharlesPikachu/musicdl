'''
Function:
    Implementation of Lyric Related Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import random
import tempfile
import requests
from .misc import resp2json
from urllib.parse import quote
from typing import Optional, TYPE_CHECKING
from .importutils import optionalimportfrom


'''cleanlrc'''
cleanlrc = lambda text: "\n".join(line for raw in re.sub(r"\r\n?", "\n", str(text)).split("\n") if (line := raw.strip("\ufeff\u200b\u200c\u200d\u2060\u00a0 \t").strip()) and not re.fullmatch(r"\[(\d{2}:)?\d{2}:\d{2}(?:\.\d{1,3})?\]", line))


'''fractoseconds'''
def fractoseconds(frac: str | None) -> float:
    if not frac: return 0.0
    scale = 10 ** len(frac)
    return int(frac) / scale


'''extractdurationsecondsfromlrc'''
def extractdurationsecondsfromlrc(lrc: str) -> Optional[float]:
    if not lrc or (lrc in {'NULL', 'None', 'none'}): return None
    max_t, time_pattern_re = None, re.compile(r"\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")
    for h, m, s, frac in time_pattern_re.findall(lrc):
        hh = int(h) if h else 0; mm = int(m); ss = int(s)
        t = hh * 3600 + mm * 60 + ss + fractoseconds(frac)
        max_t = t if (max_t is None or t > max_t) else max_t
    return max_t


'''WhisperLRC'''
class WhisperLRC:
    def __init__(self, model_size_or_path: str = "small", device: str = "auto", compute_type: str = "int8", cpu_threads: int = 4, num_workers: int = 1, **kwargs):
        WhisperModel = optionalimportfrom('faster_whisper', 'WhisperModel')
        if TYPE_CHECKING: from faster_whisper import WhisperModel as WhisperModel
        self.whisper_model = WhisperModel(model_size_or_path, device=device, compute_type=compute_type, cpu_threads=cpu_threads, num_workers=num_workers, **kwargs) if WhisperModel else None
    '''downloadtotmpdir'''
    @staticmethod
    def downloadtotmpdir(url: str, headers: dict = None, timeout: int = 300, cookies: dict = None, request_overrides: dict = None):
        headers, cookies, request_overrides = dict(headers or {}), dict(cookies or {}), dict(request_overrides or {})
        if 'headers' not in request_overrides: request_overrides['headers'] = headers
        if 'timeout' not in request_overrides: request_overrides['timeout'] = timeout
        if 'cookies' not in request_overrides: request_overrides['cookies'] = cookies
        (resp := requests.get(url, stream=True, **request_overrides)).raise_for_status()
        m = re.search(r"\.([a-z0-9]{2,5})(?:\?|$)", url, re.I)
        fd, path = tempfile.mkstemp(suffix="."+(m.group(1).lower() if m else "bin"))
        with os.fdopen(fd, "wb") as fp:
            for ch in resp.iter_content(32768):
                if ch: fp.write(ch)
        return path
    '''timestamp'''
    @staticmethod
    def timestamp(t):
        t = max(0.0, float(t)); mm = int(t//60); ss = t - mm*60
        return f"[{mm:02d}:{ss:05.2f}]"
    '''fromurl'''
    def fromurl(self, url: str, transcribe_overrides: dict = None, headers: dict = None, timeout: int = 300, cookies: dict = None, request_overrides: dict = None):
        assert self.whisper_model is not None, 'faster_whisper should be installed via "pip install "faster_whisper"'
        transcribe_overrides, headers, cookies, request_overrides, tmp_file_path = transcribe_overrides or {}, headers or {}, cookies or {}, request_overrides or {}, ''
        try:
            tmp_file_path = self.downloadtotmpdir(url, headers=headers, timeout=timeout, cookies=cookies, request_overrides=request_overrides)
            (default_transcribe_settings := {'language': None, 'vad_filter': True, 'vad_parameters': dict(min_silence_duration_ms=300), 'chunk_length': 30, 'beam_size': 5}).update(transcribe_overrides)
            segs, info = self.whisper_model.transcribe(tmp_file_path, **default_transcribe_settings)
            lrc = "\n".join(f"{self.timestamp(s.start)}{s.text.strip()}" for s in segs)
            result = {"language": info.language, "prob": info.language_probability, "duration": getattr(info, "duration", None), 'lyric': lrc}
            return result
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path): os.remove(tmp_file_path)
    '''fromfilepath'''
    def fromfilepath(self, file_path: str, transcribe_overrides: dict = None):
        assert self.whisper_model is not None, 'faster_whisper should be installed via "pip install "faster_whisper"'
        (default_transcribe_settings := {'language': None, 'vad_filter': True, 'vad_parameters': dict(min_silence_duration_ms=300), 'chunk_length': 30, 'beam_size': 5}).update(dict(transcribe_overrides or {}))
        segs, info = self.whisper_model.transcribe(file_path, **default_transcribe_settings)
        lrc = "\n".join(f"{self.timestamp(s.start)}{s.text.strip()}" for s in segs)
        result = {"language": info.language, "prob": info.language_probability, "duration": getattr(info, "duration", None), 'lyric': lrc}
        return result


'''LyricSearchClient'''
class LyricSearchClient():
    '''search'''
    @staticmethod
    def search(track_name: str, artist_name: str, allowed_lyric_apis: tuple = ('searchbylrclibapig', 'searchbylrclibapis'), request_overrides: dict = None):
        lyric_result, lyric = {}, 'NULL'
        for lyric_api in allowed_lyric_apis:
            if not callable(lyric_api): lyric_api = getattr(LyricSearchClient, lyric_api, None)
            try: lyric_result, lyric = lyric_api(track_name=track_name, artist_name=artist_name, request_overrides=request_overrides)
            except Exception: lyric_result, lyric = {}, 'NULL'
            if lyric and (lyric not in {'NULL', 'None'}): return lyric_result, lyric
        return lyric_result, lyric
    '''searchbylrclibapig'''
    @staticmethod
    def searchbylrclibapig(track_name: str, artist_name: str, request_overrides: dict = None):
        request_overrides = request_overrides or {}; headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        (resp := requests.get("https://lrclib.net/api/get", params={"artist_name": artist_name, "track_name": track_name}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        lyric = cleanlrc((lyric_result := resp2json(resp=resp)).get('syncedLyrics') or lyric_result.get('plainLyrics') or 'NULL')
        return lyric_result, lyric
    '''searchbylrclibapis'''
    @staticmethod
    def searchbylrclibapis(track_name: str, artist_name: str, request_overrides: dict = None):
        request_overrides = request_overrides or {}; headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        (resp := requests.get("https://lrclib.net/api/search", params={"q": f"{artist_name} {track_name}"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        lyric = cleanlrc((lyric_result := resp2json(resp=resp))[0].get('syncedLyrics') or lyric_result[0].get('plainLyrics') or 'NULL')
        return lyric_result, lyric
    '''searchbylyricsovhapiv1'''
    @staticmethod
    def searchbylyricsovhapiv1(track_name: str, artist_name: str, request_overrides: dict = None):
        request_overrides = request_overrides or {}; headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        (resp := requests.get(f"https://api.lyrics.ovh/v1/{quote(artist_name, safe='')}/{quote(track_name, safe='')}", headers=headers, timeout=10, **request_overrides))
        lyric = cleanlrc((lyric_result := resp2json(resp=resp)).get('lyrics') or 'NULL')
        return lyric_result, lyric
    '''searchbyhappiapiv1'''
    @staticmethod
    def searchbyhappiapiv1(track_name: str, artist_name: str, request_overrides: dict = None):
        request_overrides = request_overrides or {}; headers = {'accept': 'application/json', 'x-happi-token': 'hk254-C1VegxwlJjYdYFPtdUDpg8qiVpmAXVl0aA'}
        (resp := requests.get('https://api.happi.dev/v1/lyrics', params={'artist': artist_name, 'track': track_name}, headers=headers, timeout=10, **request_overrides))
        lyric = cleanlrc((lyric_result := resp2json(resp=resp))['result'][0]['lyrics'] or 'NULL')
        return lyric_result, lyric
    '''searchbymusixmatchapi'''
    @staticmethod
    def searchbymusixmatchapi(track_name: str, artist_name: str, request_overrides: dict = None):
        candidate_req_keys = ['3bc1042fde1ac8c1979c400d6f921320']
        request_overrides = request_overrides or {}; headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        (resp := requests.get(f"https://api.musixmatch.com/ws/1.1/matcher.lyrics.get?apikey={random.choice(candidate_req_keys)}&q_track={track_name}&q_artist={artist_name}", headers=headers, timeout=10, **request_overrides))
        lyric = cleanlrc((lyric_result := resp2json(resp=resp))['message']['body']['lyrics']['lyrics_body'] or 'NULL')
        return lyric_result, lyric