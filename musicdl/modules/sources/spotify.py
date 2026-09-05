'''
Function:
    Implementation of SpotifyMusicClient: https://open.spotify.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import uuid
import json
import copy
import time
import html
import zlib
import struct
import base64
import locale
import random
import hashlib
import platform
import requests
import requests.compat
from pathlib import Path
from contextlib import suppress
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, urlencode
from ..utils.hosts import SPOTIFY_MUSIC_HOSTS
from .base import BaseMusicClient, BaseMusicClientKwargs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.spotifyutils import SpotifyMusicClientPlaylistUtils, SpotifyMusicClientSearchUtils, SpotubeSecureClient
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, extractdurationsecondsfromlrc, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils, RandomIPGenerator


'''SpotifyMusicClient'''
class SpotifyMusicClient(BaseMusicClient):
    source = 'SpotifyMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(SpotifyMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://open.spotify.com/", "Origin": "https://open.spotify.com/"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://open.spotify.com/", "Origin": "https://open.spotify.com/"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            search_urls.append({'api': SpotifyMusicClientSearchUtils.searchbykeyword, 'inputs': {'session': copy.deepcopy(self.session), 'query': keyword, 'limit': page_size, 'offset': count, 'rule': copy.deepcopy(rule), 'request_overrides': request_overrides}, 'page_no': int(count / page_size) + 1})
            count += page_size
        # return
        return search_urls
    '''_parsewithspotubedlapi'''
    def _parsewithspotubedlapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Origin": "https://spotubedl.com", "Referer": "https://spotubedl.com/", "Accept": "*/*",}
        # parse
        for engine in ('v4', 'v3', 'v2', 'v1'):
            try:
                download_result = SpotubeSecureClient().getdownloadflagfromspotify(f"https://open.spotify.com/track/{song_id}", engine, 'mp3', '320', request_overrides=request_overrides)
                if not (download_url := download_result['flag']) or not str(download_url).startswith('http'): continue
                resp = requests.get(download_url, headers=headers, **request_overrides)
                if not resp.ok:
                    download_url = "https://spotubedl.com/api/download/audiorelay?" + urlencode({"url": download_url})
                    resp = requests.get(download_url, headers=headers, **request_overrides)
                resp.raise_for_status(); download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}; break
            except Exception: continue
        duration_in_secs = float(SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or safeextractfromdict(download_result, ['track_meta', 'data', 'duration'], 0) or 0)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['track_meta', 'data', 'name'], None)), singers=legalizestring(', '.join(safeextractfromdict(download_result, ['track_meta', 'data', 'artists'], []) or [])), album=legalizestring(safeextractfromdict(download_result, ['track_meta', 'data', 'album_name'], None)), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['track_meta', 'data', 'cover_url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=headers,
        )
        # return
        return song_info
    '''_parsewithmusicfabapi'''
    def _parsewithmusicfabapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"origin": "https://musicfab.io", "referer": "https://musicfab.io/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        (resp := requests.post('https://musicfab.io/api/spotify', json={"url": f"https://open.spotify.com/track/{song_id}"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'metadata', 'download'], None)
        (resp := requests.get(download_url, headers=headers, **request_overrides)).raise_for_status()
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or to_seconds_func(safeextractfromdict(download_result, ['data', 'metadata', 'duration'], '') or '0:00')
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'album'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'metadata', 'image'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=headers,
        )
        # return
        return song_info
    '''_parsewithrapidapi'''
    def _parsewithrapidapi(self, search_result: dict, request_overrides: dict = None):
        # init
        shared_keys = [
            "efdc9dead0msh3d6b04344364212p1e7029jsn40fd6cc8da39", "1162fa6edbmsh4e3ada3ee7a56eap10e77ajsn2a5e57cad3bc", "b956d6a526msh7b1a2a3662d09cdp11fa3djsn5b6cad23f10f", "53d36da411mshc55da25ad75d914p19c959jsnec7bf74dad86",
            "d44e6cbbffmsh4904ffce35d0541p157e2bjsn63f9db9e85db", "50b5f3b226msh0966c3a7bd972cap10e911jsn3c815d7d3627", "19712ae800msh39302756eeef1abp1b8019jsnc7967b2210ac", "2f5f8f1ed6msha939c8e6949b10ep16c31bjsnb07bb964bbbb",
            "97f21512b9mshbd44e421ed343a1p1a65b9jsn878d08ec3763", "907f71f2camshab357c69afa7df8p1fd360jsndbc11ed3ad7b", "b5a9edd0b8msh435ffe328e2f725p1bdf97jsn0f7c55a85991", "cff3589cb7msh4356e5ee7bf14cdp1a2aecjsne8f75aee4620",
            "be66b9a47emsh51482eb6cc9732ap18309cjsn51d8aa14fbef", "fc9a982916mshe1f3ad77f3e39ddp1f9b06jsna58c9c5eaba0", "e0f326883amsh94b0942a9513da4p16494ajsn29296f6e19fe", "0647bc5201msh84a9358b48d00eep163485jsne7ecf062e49f",
        ]
        synchsafe2int_func = lambda b: ((b[0] & 0x7f) << 21) | ((b[1] & 0x7f) << 14) | ((b[2] & 0x7f) << 7) | (b[3] & 0x7f)
        isid3_func = lambda b: len(b) >= 10 and b[:3] == b'ID3' and b[3] in (2, 3, 4) and all(x < 0x80 for x in b[6:10])
        id3size_func = lambda b: 10 + synchsafe2int_func(b[6:10]) + (10 if b[3] == 4 and b[5] & 0x10 else 0)
        ismp4_func = lambda b, o=0: len(b) >= o + 12 and b[o + 4:o + 8] == b'ftyp' and 8 <= int.from_bytes(b[o:o + 4], 'big') <= len(b) - o
        fixaudio_func = lambda b: b[id3size_func(b):] if isid3_func(b) and id3size_func(b) < len(b) and ismp4_func(b, id3size_func(b)) else b
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"x-rapidapi-key": random.choice(shared_keys), "x-rapidapi-host": "spotify-downloader9.p.rapidapi.com"}
        # parse
        (resp := requests.get(f"https://spotify-downloader9.p.rapidapi.com/downloadSong?songId={song_id}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'downloadLink'], None)
        (resp := requests.get(download_url, headers=headers, **request_overrides)).raise_for_status(); resp._content = fixaudio_func(resp.content)
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or (float(safeextractfromdict(search_result, ['item', 'data', 'duration', 'totalMilliseconds'], 0) or safeextractfromdict(search_result, ['itemV2', 'data', 'trackDuration', 'totalMilliseconds'], 0) or 0) / 1000)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=headers,
        )
        # return
        return song_info
    '''_parsewithsavemytracksapi'''
    def _parsewithsavemytracksapi(self, search_result: dict, request_overrides: dict = None):
        # init
        system, machine = platform.system(), platform.machine().lower()
        ua_platform = "(Windows NT 10.0; Win64; x64)" if system == "Windows" else "(Macintosh; Intel Mac OS X 10_15_7)" if system == "Darwin" else f"(X11; Linux {'x86_64' if machine in {'x86_64', 'amd64'} else machine or 'unknown'})" if system == "Linux" else f"({system or 'Unknown'}; {machine or 'unknown'})"
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": f"Mozilla/5.0 {ua_platform} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36", "Referer": "https://savemytracks.com/", "Origin": "https://savemytracks.com"}
        session = requests.Session(); session.headers.update((headers := RandomIPGenerator().addrandomipv4toheaders(headers=headers)))
        # parse
        (resp := session.get("https://savemytracks.com/", timeout=20, **request_overrides)).raise_for_status()
        ajax_url, usage_url = requests.compat.urljoin(resp.url, "/wp-admin/admin-ajax.php"), requests.compat.urljoin(resp.url, "/usage/api/api.php"); page_source = html.unescape(resp.text).replace("\\/", "/").replace('\\"', '"').replace("\\'", "'")
        nonce_candidates = list(dict.fromkeys(re.findall(r'''(?:["']?(?:nonce|smd_nonce|smdNonce|ajax_nonce|ajaxNonce)["']?)\s*[:=]\s*["']([A-Za-z0-9_-]{6,64})["']''', page_source, re.I) + re.findall(r'''name=["'](?:nonce|smd_nonce|smdNonce|ajax_nonce|ajaxNonce)["'][^>]*value=["']([A-Za-z0-9_-]{6,64})["']''', page_source, re.I)))
        for nonce in nonce_candidates:
            with suppress(Exception):
                (resp := session.post(ajax_url, data={"action": "smd_spotify_info", "nonce": nonce, "url": f"https://open.spotify.com/track/{song_id}"}, timeout=30, **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
                if isinstance(download_result, dict) and download_result.get("success") and download_result.get("youtubeUrl"): break
        else:
            raise RuntimeError("unable to obtain Spotify info with SaveMyTracks nonce")
        cache_root = Path(os.getenv("LOCALAPPDATA") or os.getenv("XDG_CACHE_HOME") or (Path.home() / "Library" / "Caches" if system == "Darwin" else Path.home() / ".cache")); device_seed_path = cache_root / "musicdl" / "savemytracks_device"; device_seed = ""
        with suppress(Exception): device_seed = device_seed_path.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[0-9a-f]{64}", device_seed or ""):
            device_seed = hashlib.sha256(f"{platform.node()}|{system}|{platform.release()}|{platform.machine()}|{uuid.getnode()}".encode()).hexdigest()
            with suppress(Exception): device_seed_path.parent.mkdir(parents=True, exist_ok=True); device_seed_path.write_text(device_seed, encoding="utf-8")
        screen = ""; browser_platform = "Win32" if system == "Windows" else "MacIntel" if system == "Darwin" else f"Linux {'x86_64' if machine in {'x86_64', 'amd64'} else machine or 'unknown'}" if system == "Linux" else system or "Unknown"; device_id = f"smtw_{hashlib.sha1(device_seed.encode()).hexdigest()}"; device_fp = f"fp_{hashlib.sha256((device_seed + '|fp').encode()).hexdigest()[:8]}"
        with suppress(Exception):
            import tkinter
            root = tkinter.Tk(); root.withdraw(); screen = f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}x{root.winfo_screendepth()}"; root.destroy()
        if not screen: screen = "0x0x0"
        if not (timezone := os.getenv("TZ") or "") and os.path.islink("/etc/localtime"):
            with suppress(Exception): timezone = os.path.realpath("/etc/localtime").split("/zoneinfo/", 1)[1]
        timezone = timezone or (time.tzname[0] if time.tzname else "") or "UTC"; language = (locale.getlocale()[0] or os.getenv("LANG", "en_US").split(".")[0] or "en_US").replace("_", "-")
        pixel = hashlib.sha256(f"{device_seed}|{screen}|{timezone}|{language}|{browser_platform}".encode()).digest()[:3] + b"\xff"; png_chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        canvas_png = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 300, 150, 8, 6, 0, 0, 0)) + png_chunk(b"IDAT", zlib.compress((b"\x00" + pixel * 300) * 150)) + png_chunk(b"IEND", b""); canvas = f"data:image/png;base64,{base64.b64encode(canvas_png).decode()}"
        fingerprint = base64.b64encode(json.dumps({"screen": screen, "timezone": timezone, "language": language, "platform": browser_platform, "canvas": canvas}, ensure_ascii=False, separators=(",", ":")).encode()).decode()[:255]
        with suppress(Exception): (resp := session.post("https://spdlicense.vidaraa.com/api/activate/status", json={"deviceId": device_id, "fingerprint": device_fp, "deviceInfo": system or "Unknown", "version": "1.0.0"}, timeout=20, **request_overrides)).raise_for_status(); device_id = resp2json(resp=resp).get("canonicalDeviceId") or device_id
        (resp := session.post(usage_url, data={"action": "check_limit", "fingerprint": fingerprint}, timeout=20, **request_overrides)).raise_for_status(); limit_result = resp2json(resp=resp); dl_token = limit_result["dl_token"]
        (resp := session.post(ajax_url, data={"action": "smd_download", "nonce": nonce, "url": download_result["youtubeUrl"], "format": "mp3", "dl_token": dl_token, "device_id": device_id, "device_fp": device_fp}, timeout=30, **request_overrides)).raise_for_status()
        download_result['job'] = resp2json(resp=resp); job_id = download_result['job'].get("job_id"); max_retry_times = 120
        for _ in range(max_retry_times):
            (resp := session.get(ajax_url, params={"action": "smd_job_status", "job_id": job_id}, timeout=30, **request_overrides)).raise_for_status()
            if (job := resp2json(resp=resp)).get("status") == "completed" and job.get("download_url"): download_url = job["download_url"]; break
            if job.get("status") in {"failed", "error", "cancelled"}: raise RuntimeError(job.get("error") or "job failed")
            time.sleep(2)
        else:
            raise TimeoutError("download job timed out")
        (resp := session.post(usage_url, data={"action": "record_download", "fingerprint": fingerprint, "download_url": download_url}, timeout=20, **request_overrides)).raise_for_status()
        (resp := session.get(download_url, **request_overrides)).raise_for_status()
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or (download_result.get('durationMs') / 1000)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('title')), singers=legalizestring(download_result.get('artist')), album=legalizestring(download_result.get('album') or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=download_result.get('thumbnailUrl'), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=session.headers
        )
        # return
        return song_info
    '''_parsewithspotidownmeapi'''
    def _parsewithspotidownmeapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), requests.Session()
        session.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'}
        # parse
        (resp := session.get('https://spotidown.me/en1', **request_overrides)).raise_for_status()
        csrf = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)', resp.text).group(1)
        (resp_track := session.post('https://spotidown.me/getTrackData', json={'spotify_url': f'https://open.spotify.com/track/{song_id}'}, headers={'X-CSRF-TOKEN': csrf, 'Referer': 'https://spotidown.me/en1', 'Origin': 'https://spotidown.me',}, **request_overrides)).raise_for_status()
        (resp := session.post('https://spotidown.me/convert', json={'urls': f'https://open.spotify.com/track/{song_id}'}, headers={'X-CSRF-TOKEN': csrf, 'Referer': 'https://spotidown.me/en1', 'Origin': 'https://spotidown.me',}, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)
        download_result.update(resp2json(resp=resp_track)); (resp := session.get(download_url, **request_overrides)).raise_for_status()
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or (float(safeextractfromdict(download_result, ['data', 'duration_ms'], 0) or 0) / 1000)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)),  singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(download_result, ['data', 'artists'], None) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'album', 'images', 0, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=session.headers, 
        )
        # return
        return song_info
    '''_parsewithspotisaverapi'''
    def _parsewithspotisaverapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36', 'Referer': 'https://spotisaver.net/en1', 'Accept': 'application/json', 'Cache-Control': 'no-cache'})
        b64_func = lambda data: base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode()).decode().rstrip('=')
        # parse
        (resp := session.get('https://spotisaver.net/en1', **request_overrides)).raise_for_status()
        user_ip, request_token, wire = re.search(r'const user_ip = "([^"]+)"', resp.text).group(1), re.search(r'requestToken:\s*"([^"]+)"', resp.text).group(1), json.loads(re.search(r'wire:\s*(\{[^\r\n]+\})\s*\};', resp.text).group(1))
        get_sign_function = lambda action, ctx: session.get('https://spotisaver.net/api/get_signature.php', params={wire['token_param']: request_token, wire['action_param']: wire['actions'][action], wire['ctx_param']: b64_func(ctx)}, **request_overrides).json()
        sign = get_sign_function('get_playlist', {'id': song_id, 'type': 'track', 'lang': 'en'})
        data = session.get('https://spotisaver.net/api/get_playlist.php', params={'id': song_id, 'type': 'track', 'lang': 'en'}, headers={wire['sig_header']: sign['token'], wire['exp_header']: str(sign['exp'])}, **request_overrides).json(); track = data['tracks'][0]
        sign = get_sign_function('download_track', {'lang': 'en', 'id': str(track['id']), 'name': track['name'], 'duration_ms': str(int(float(track['duration_ms'])))})
        download_headers = {wire['sig_header']: sign['token'], wire['exp_header']: str(sign['exp'])}
        download_data = {'track': track, 'download_dir': 'downloads', 'filename_tag': 'SPOTISAVER', 'user_ip': user_ip, 'is_premium': False, 'lang': 'en'}
        (resp := session.post('https://spotisaver.net/api/download_track.php', headers=download_headers, json=download_data, **request_overrides)).raise_for_status()
        download_url = {'url': 'https://spotisaver.net/api/download_track.php', 'headers': download_headers, 'json': download_data, 'method': 'post'}
        download_result = {'track': track, 'download_url': download_url}
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or (float(safeextractfromdict(download_result, ['track', 'duration_ms'], 0) or 0) / 1000)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['track', 'name'], None)), singers=legalizestring(', '.join(safeextractfromdict(download_result, ['track', 'artists'], None) or [])), album=legalizestring(safeextractfromdict(download_result, ['track', 'album'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)),
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['track', 'image', 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=download_headers, 
        )
        # return
        return song_info
    '''_parsewithspotsaverapi'''
    def _parsewithspotsaverapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36', 'Referer': 'https://spotsaver.net/results/', 'Accept': '*/*', 'Cache-Control': 'no-cache'})
        # parse
        (resp := session.get('https://spotsaver.net/api/spotify/', params={'url': f'https://open.spotify.com/track/{song_id}'}, **request_overrides)).raise_for_status()
        spotify_result: dict = resp2json(resp=resp); track: dict = (spotify_result.get('items') or [])[0]
        song_name, singer = str(track.get('title') or ''), str(track.get('artist') or '')
        (resp := session.post('https://spotsaver.net/api/get-id/', json={'title': song_name, 'artist': singer}, **request_overrides)).raise_for_status()
        id_result: dict = resp2json(resp=resp); video_id, candidate_ids = id_result.get('videoId'), id_result.get('candidateIds') or []
        download_data = {'videoId': video_id, 'candidateIds': candidate_ids, 'format': 'mp3', 'title': ' - '.join(filter(None, [song_name, singer])) or 'track'}
        (resp := session.post('https://spotsaver.net/api/download/', json=download_data, **request_overrides)).raise_for_status()
        download_result = resp2json(resp=resp); download_url = download_result.get('downloadUrl') or download_result.get('url') or download_result.get('fileUrl') or download_result.get('mediaUrl')
        (resp := session.get(download_url, **request_overrides)).raise_for_status()
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or float(download_result.get('duration') or track.get('duration') or 0)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {'spotify': spotify_result, 'get_id': id_result, 'download': download_result}, 'lyric': {}}, source=self.source, song_name=legalizestring(song_name), singers=legalizestring(singer), album=legalizestring(track.get('album') or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)),
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=track.get('thumbnail'), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=session.headers,
        )
        # return
        return song_info
    '''_parsewithspotifydownloadsapi'''
    def _parsewithspotifydownloadsapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36', 'Referer': 'https://www.spotify-downloads.com/', 'Accept': '*/*', 'Cache-Control': 'no-cache'}
        session.headers.update((headers := RandomIPGenerator().addrandomipv4toheaders(headers=headers)))
        # parse
        download_data = {'url': f'https://open.spotify.com/track/{song_id}', 'quality': '320k'}
        (resp := session.post('https://www.spotify-downloads.com/api/download', json=download_data, **request_overrides)).raise_for_status()
        download_result = resp2json(resp=resp); job_id = download_result['job_id']; status_result = {}
        for _ in range(120):
            (resp := session.get(f'https://www.spotify-downloads.com/api/status/{job_id}', **request_overrides)).raise_for_status()
            if (status_result := resp2json(resp=resp)).get('status') == 'ready': break
            assert status_result.get('status') != 'error', status_result.get('error')
            time.sleep(2)
        (resp := session.get((download_url := f'https://www.spotify-downloads.com/api/file/{job_id}'), **request_overrides)).raise_for_status()
        if resp.content.startswith(b'ID3') and resp.content[(id3_size := 10 + sum((resp.content[6 + i] & 0x7f) << (21 - i * 7) for i in range(4))) + 4:id3_size + 8] == b'ftyp': resp._content = resp.content[id3_size:]
        download_url_status = {'download_url': download_url, 'ok': True, 'file_size_bytes': len(resp.content), 'file_size': SongInfoUtils.byte2mb(len(resp.content)), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        duration_in_secs = SongInfoUtils.naiveguessdurationfromaudiobytes(resp.content) or (float(safeextractfromdict(search_result, ['item', 'data', 'duration', 'totalMilliseconds'], 0) or safeextractfromdict(search_result, ['itemV2', 'data', 'duration', 'totalMilliseconds'], 0) or 0) / 1000)
        assert download_url_status['file_size_bytes'] > duration_in_secs * 8 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {'create': download_result, 'status': status_result}, 'lyric': {}}, source=self.source, song_name=legalizestring(status_result.get('name')), singers=legalizestring(status_result.get('artist')), album=legalizestring(status_result.get('album') or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'coverArt', 'sources', 0, 'url'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'coverArt', 'sources', 0, 'url'], None), download_url=download_url, download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=session.headers,
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithspotidownmeapi, self._parsewithrapidapi, self._parsewithspotsaverapi, self._parsewithspotifydownloadsapi, self._parsewithspotubedlapi, self._parsewithspotisaverapi, self._parsewithsavemytracksapi, self._parsewithmusicfabapi, ]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            pass  # TODO: Solve DRM Issues in Spotify
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_api, search_api_inputs, page_no, search_result_idx = request_overrides or {}, search_url['api'], search_url['inputs'], search_url['page_no'], -1
        lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            for search_result_idx, search_result in enumerate(safeextractfromdict((search_resp := search_api(**search_api_inputs)), ['data', 'searchV2', 'tracksV2', 'items'], []) or safeextractfromdict(search_resp, ['data', 'searchV2', 'tracks', 'items'], [])):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                search_result['id'] = safeextractfromdict(search_result, ['item', 'data', 'id'], None) or str(safeextractfromdict(search_result, ['item', 'data', 'uri'], '')).removeprefix('spotify:track:')
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                # --append to song_infos
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(task_id, description=f'{self.source}._search >>> {search_result_idx+1} search results processed on page {page_no}')
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **dict(request_overrides := request_overrides or {})).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SPOTIFY_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, playlist_result_first = SpotifyMusicClientPlaylistUtils.parse(copy.deepcopy(self.session), playlist_id=playlist_id, request_overrides=request_overrides)
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['data', 'playlistV2', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos