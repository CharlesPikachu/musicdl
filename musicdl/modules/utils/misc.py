'''
Function:
    Implementation of Common Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import re
import os
import html
import emoji
import errno
import shutil
import bleach
import filetype
import requests
import mimetypes
import functools
import puremagic
import subprocess
import json_repair
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
from contextlib import suppress
from pathlib import PurePosixPath
from .importutils import optionalimport
from urllib.parse import urlsplit, unquote
from requests.structures import CaseInsensitiveDict
from pathvalidate import sanitize_filepath, sanitize_filename
from .cmd import FFprobeAudioCodecCommand, ExtractAudioFromVideoFFmpegCommand
from typing import TYPE_CHECKING, Protocol, Callable, Any, Dict, List, Optional, Tuple
curl_cffi = optionalimport('curl_cffi')
if TYPE_CHECKING: import curl_cffi as curl_cffi


'''legalizestring'''
def legalizestring(string: str, fit_gbk: bool = True, max_len: int = 255, fit_utf8: bool = True, replace_null_string: str = 'NULL'):
    # naive process
    if not string: return replace_null_string
    string = re.sub(r"\\/>", "/>", re.sub(r"<\\/", "</", str(string).replace(r'\"', '"')))
    string = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), string)
    # html.unescape
    string = (n1 if (n1 := html.unescape(string)) == string else (n2 if (n2 := html.unescape(n1)) != n1 else n1))
    # bleach.clean
    try: string = BeautifulSoup(string, "lxml").get_text(separator="")
    except: string = bleach.clean(string, tags=[], attributes={}, strip=True)
    # unicodedata.normalize
    string = unicodedata.normalize("NFC", string)
    # emoji.replace_emoji
    string = emoji.replace_emoji(string, replace="")
    # isprintable
    string = "".join([ch for ch in string if ch.isprintable() and not unicodedata.category(ch).startswith("C")])
    # sanitize_filename
    string = sanitize_filename(string, max_len=max_len)
    # fix encoding
    if fit_gbk: string = string.encode("gbk", errors="ignore").decode("gbk", errors="ignore")
    if fit_utf8: string = string.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    # return
    return (replace_null_string if not (string := re.sub(r"\s+", " ", string).strip()) else string)


'''resp2json'''
def resp2json(resp: requests.Response) -> dict:
    if not isinstance(resp, ((requests.Response, curl_cffi.requests.Response) if curl_cffi else requests.Response)): return {}
    try: return (resp.json() or {})
    except Exception: return (json_repair.loads(resp.text) or {})


'''isvalidresp'''
def isvalidresp(resp: requests.Response, valid_status_codes: list | tuple | set = {200, 206}):
    if not isinstance(resp, ((requests.Response, curl_cffi.requests.Response) if curl_cffi else requests.Response)): return False
    if resp.status_code not in valid_status_codes: return False
    return True


'''safeextractfromdict'''
def safeextractfromdict(data, progressive_keys, default_value = None):
    try: result = functools.reduce(lambda x, k: x[k], progressive_keys, data)
    except Exception: result = default_value
    return result


'''usedownloadheaderscookies'''
def usedownloadheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self: ClientProtocolObj, *args, **kwargs):
        self.default_headers = self.default_download_headers
        if hasattr(self, 'default_download_cookies'): self.default_cookies = self.default_download_cookies
        if hasattr(self, 'enable_download_curl_cffi'): self.enable_curl_cffi = self.enable_download_curl_cffi
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''useparseheaderscookies'''
def useparseheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self: ClientProtocolObj, *args, **kwargs):
        self.default_headers = self.default_parse_headers
        if hasattr(self, 'default_parse_cookies'): self.default_cookies = self.default_parse_cookies
        if hasattr(self, 'enable_parse_curl_cffi'): self.enable_curl_cffi = self.enable_parse_curl_cffi
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''usesearchheaderscookies'''
def usesearchheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self: ClientProtocolObj, *args, **kwargs):
        self.default_headers = self.default_search_headers
        if hasattr(self, 'default_search_cookies'): self.default_cookies = self.default_search_cookies
        if hasattr(self, 'enable_search_curl_cffi'): self.enable_curl_cffi = self.enable_search_curl_cffi
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''hashablesth'''
def hashablesth(obj):
    return tuple((k, hashablesth(v)) for k, v in sorted(obj.items())) if isinstance(obj, dict) else tuple(hashablesth(x) for x in obj) if isinstance(obj, list) else tuple(sorted(hashablesth(x) for x in obj)) if isinstance(obj, set) else obj


'''dedupkeeporder'''
def dedupkeeporder(seq):
    seen, out = set(), []
    for item in seq: (seen.add(key), out.append(item)) if (key := hashablesth(item)) not in seen else None
    return out


'''searchdictbykey'''
def searchdictbykey(obj, target_key: str | list | tuple | set) -> list:
    results, target_key = [], [target_key] if isinstance(target_key, str) else target_key
    if isinstance(obj, dict):
        for k, v in obj.items(): results += ([v] if k in target_key else []) + searchdictbykey(v, target_key)
    elif isinstance(obj, list):
        for item in obj: results.extend(searchdictbykey(item, target_key))
    return dedupkeeporder(results)


'''IOUtils'''
class IOUtils():
    '''touchdir'''
    @staticmethod
    def touchdir(directory: str, exist_ok: bool = True, mode: int = 511, auto_sanitize: bool = True):
        if auto_sanitize: directory = sanitize_filepath(directory)
        return os.makedirs(directory, exist_ok=exist_ok, mode=mode)
    '''replacefile'''
    @staticmethod
    def replacefile(src: str, dest: str):
        try: os.replace(src, dest)
        except OSError as exc: (exc.errno == errno.EXDEV or (_ for _ in ()).throw(Exception)); (not os.path.exists(dest) or ((not os.path.isdir(dest) and (os.remove(dest) or True)) or (_ for _ in ()).throw(Exception))); shutil.move(src, dest)


'''ClientProtocolObj'''
class ClientProtocolObj(Protocol):
    default_headers: dict[str, str]
    default_search_headers: dict[str, str]
    default_parse_headers: dict[str, str]
    default_download_headers: dict[str, str]
    default_cookies: dict[str, str]
    default_search_cookies: dict[str, str]
    default_parse_cookies: dict[str, str]
    default_download_cookies: dict[str, str]
    enable_curl_cffi: bool
    enable_search_curl_cffi: bool
    enable_parse_curl_cffi: bool
    enable_download_curl_cffi: bool
    _initsession: Callable[..., Any]


'''AudioLinkTester'''
class AudioLinkTester:
    VALID_AUDIO_EXTS = {
        # common
        "aac", "aax", "aaxc", "ac3", "adts", "aif", "aifc", "aiff", "alac", "amr", "ape", "au", "avr", "awb", "caf", "cda", "dff", "dfsf", "dsf", "dss", "mdl",
        "dts", "dtshd", "ec3", "f32", "f64", "flac", "gsm", "hca", "htk", "iff", "ima", "ircam", "kar", "kss", "l16", "la", "m15", "m3u8", "m4a", "m4b", "hes", 
        "m4p", "m4r", "m4s", "mat4", "mat5", "med", "mid", "midi", "mlp", "mod", "mo3", "mp1", "mp2", "mp3", "mpa", "mpc", "mpc2k", "mp+", "mpp", "ult", "gym", 
        "msv", "mt2", "mtm", "mxmf", "nist", "nsa", "nsf", "oga", "ogg", "okt", "oma", "ofr", "ofs", "opus", "paf", "pcm", "psf", "psf1", "psf2", "ptm", "gsf", 
        "pvf", "qsf", "ra", "ram", "raw", "rf64", "rmi", "rmj", "rmm", "rmx", "roq", "s3m", "sap", "sd2", "sds", "sf", "shn", "sid", "mptm", "ul", "xm", "gbs", 
        "spu", "spx", "ssf", "stm", "snd", "tak", "thd", "tta", "spc", "sd2f", "umx", "usf", "miniusf", "voc", "vgm", "vgz", "wav", "wave", "w64", "it", "far", 
        "wax", "wma", "wve", "wv", "wvx", "xi", "8svx", "16svx", "2sf", "3ga", "669", "aa3", "amf", "at3", "at9", "dmf", "weba",
        # special and encrypted
        "m4s", "mflac", "mgg", "qmcflac", "qmc0", "qmc3", "qmcogg", "bkcmp3", "bkcflac", "tkm", "kgm", "vpr", "kwm", "ncm", "mg3d"
    }
    AUDIO_MIME_PREFIX = "audio/"
    AUDIO_MIME_EXTRA = {"application/octet-stream", "application/flac", "application/ogg", "application/vnd.apple.mpegurl", "application/x-flac", "application/x-mpegurl", "video/mp4"}
    EXT_ALIAS = {"mpeg": "mp3", "mpga": "mp3", "x-mp3": "mp3", "x-mpeg": "mp3", "wave": "wav", "x-wav": "wav", "oga": "ogg", "x-ogg": "ogg", "x-flac": "flac", "x-aac": "aac", "x-m4a": "m4a", "mp4a": "m4a"}
    MIME_TO_PREFERRED_EXT = {
        "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/wave": "wav", "audio/x-wav": "wav", "audio/flac": "flac", "audio/x-flac": "flac", "audio/aac": "aac", "audio/x-aac": "aac", "audio/ogg": "ogg",
        "audio/x-ogg": "ogg", "audio/opus": "opus", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/x-m4p": "m4a", "video/mp4": "m4a", "application/flac": "flac", "application/x-flac": "flac", "application/ogg": "ogg",
        "application/x-mpegurl": "m3u8", "application/vnd.apple.mpegurl": "m3u8",
    }
    def __init__(self, timeout: Tuple[int, int] = (5, 15), headers: Optional[dict] = None, cookies: Optional[dict] = None, verify: bool = True) -> None:
        self.verify = verify
        self.timeout = timeout
        self.cookies = dict(cookies or {})
        self.headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.headers.update(dict(headers or {}))
        self.session = requests.Session()
    '''ffprobeaudiocodec'''
    @staticmethod
    def ffprobeaudiocodec(file_path: str) -> str | None:
        cmd, result = FFprobeAudioCodecCommand().build(file_path), '{}'
        with suppress(Exception): result = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        streams: list[dict] = json_repair.loads(result).get("streams", [])
        if not streams: return None
        return streams[0].get("codec_name")
    '''chooseaudioextfromffprobeoutput'''
    @staticmethod
    def chooseaudioextfromffprobeoutput(codec_name: str | None) -> str:
        if codec_name is None: return ".mka"
        mapping = {"aac": ".m4a", "mp3": ".mp3", "flac": ".flac", "alac": ".m4a", "opus": ".ogg", "vorbis": ".ogg"}
        return mapping[codec_name] if (codec_name := codec_name.lower()) in mapping else ".wav" if codec_name.startswith("pcm_") else ".mka"
    '''extractaudiofromvideolossless'''
    @staticmethod
    def extractaudiofromvideolossless(video_path, audio_path: str | None = None) -> str:
        if not (video_path := Path(video_path)).exists(): raise FileNotFoundError(video_path)
        ext = AudioLinkTester.chooseaudioextfromffprobeoutput(AudioLinkTester.ffprobeaudiocodec(str(video_path)))
        audio_path = str((Path(audio_path) if audio_path is not None else video_path).with_suffix(ext))
        cmd = ExtractAudioFromVideoFFmpegCommand().build(video_path=str(video_path), audio_path=audio_path)
        try: subprocess.run(cmd, capture_output=True, text=True, check=True); return audio_path, ext.removeprefix('.')
        except subprocess.CalledProcessError: subprocess.run(ExtractAudioFromVideoFFmpegCommand().build(str(video_path), (fallback_path := str(video_path.with_suffix(".mka")))), capture_output=True, text=True, check=True); return fallback_path, 'mka'
    '''byte2mb'''
    @staticmethod
    def byte2mb(size: int):
        try: size = 'NULL' if not (mb := round(int(float(size)) / 1024 / 1024, 2)) else f'{mb} MB'
        except Exception: size = 'NULL'
        return size
    '''normalizectype'''
    @staticmethod
    def normalizectype(content_type: Optional[str]) -> Optional[str]:
        if not content_type: return None
        return content_type.split(";", 1)[0].strip().lower() or None
    '''isaudiomime'''
    @classmethod
    def isaudiomime(cls, content_type: Optional[str]) -> bool:
        if not (ctype := cls.normalizectype(content_type)): return False
        return ctype.startswith(cls.AUDIO_MIME_PREFIX) or ctype in cls.AUDIO_MIME_EXTRA
    '''normalizeext'''
    @classmethod
    def normalizeext(cls, ext: Optional[str]) -> Optional[str]:
        if not ext: return None
        if not (ext := ext.strip().lower().lstrip(".")): return None
        return cls.EXT_ALIAS.get(ext, ext)
    '''isvalidaudioext'''
    @classmethod
    def isvalidaudioext(cls, ext: Optional[str]) -> bool:
        ext = cls.normalizeext(ext)
        return bool(ext and ext in cls.VALID_AUDIO_EXTS)
    '''parsesizefromheaders'''
    @staticmethod
    def parsesizefromheaders(headers: CaseInsensitiveDict) -> Optional[int]:
        if (content_length := headers.get("Content-Length")) and str(content_length).isdigit(): return int(content_length)
        if "/" in (content_range := headers.get("Content-Range", "") or ""): return (int(total) if (total := content_range.rsplit("/", 1)[-1].strip()).isdigit() else None)
        return None
    '''extractsuffixfromurl'''
    @staticmethod
    def extractsuffixfromurl(url: Optional[str]) -> Optional[str]:
        if not url: return None
        name = PurePosixPath(unquote(urlsplit(url).path or "")).name
        if not name or "." not in name: return None
        return (PurePosixPath(name).suffix.lower().lstrip(".") or None)
    '''extractfilenamefromcd'''
    @staticmethod
    def extractfilenamefromcd(content_disposition: Optional[str]) -> Optional[str]:
        if not content_disposition: return None
        for part in [p.strip() for p in content_disposition.split(";")]:
            if (key := part.lower()).startswith("filename="): return part.split("=", 1)[1].strip('"')
            if key.startswith("filename*="): return unquote((v.split("''", 1)[1] if "''" in (v := part.split("=", 1)[1]) else v).strip('"'))
        return None
    '''sampleresponsebytes'''
    @staticmethod
    def sampleresponsebytes(resp: requests.Response, max_bytes: int = 8192) -> bytes:
        total = 0; chunks: List[bytes] = []
        for chunk in resp.iter_content(chunk_size=4096):
            if not chunk: continue
            if (remain := max_bytes - total) <= 0: break
            chunks.append((piece := chunk[:remain]))
            if (total := total + len(piece)) >= max_bytes: break
        return b"".join(chunks)
    '''buildrequestkwargs'''
    def buildrequestkwargs(self, request_overrides: Optional[dict] = None) -> dict:
        request_overrides = dict(request_overrides or {})
        request_overrides.setdefault("verify", self.verify)
        request_overrides.setdefault("timeout", self.timeout)
        request_overrides.setdefault("headers", dict(self.headers))
        request_overrides.setdefault("cookies", dict(self.cookies))
        return request_overrides
    '''request'''
    def request(self, method: str, url: str, request_overrides: Optional[dict] = None, range_bytes: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        headers = dict((kwargs := self.buildrequestkwargs(request_overrides)).get("headers") or {})
        if method.upper() == "GET" and range_bytes: headers["Range"] = f"bytes={range_bytes[0]}-{range_bytes[1]}"; kwargs["headers"] = headers
        resp = self.session.request(method=method.upper(), url=url, allow_redirects=True, stream=(method.upper() == "GET"), **kwargs)
        return {"ok": 200 <= resp.status_code < 300, "resp": resp, "status_code": resp.status_code, "download_url": str(resp.url), "ctype": resp.headers.get("Content-Type"), "file_size_bytes": self.parsesizefromheaders(resp.headers)}
    '''inferext'''
    def inferext(self, original_url: str, final_url: Optional[str], content_type: Optional[str], content_disposition: Optional[str], sample_bytes: bytes, reason: List[str]) -> Tuple[Optional[str], str]:
        candidates: List[Tuple[str, Optional[str]]] = []
        # 1) URL suffix first
        candidates.append(("urllib(original_url_suffix)", self.extractsuffixfromurl(original_url)))
        candidates.append(("urllib(final_url_suffix)", self.extractsuffixfromurl(final_url)))
        if (cd_name := self.extractfilenamefromcd(content_disposition)): candidates.append(("urllib(content_disposition_filename)", os.path.splitext(cd_name)[1].lstrip(".")))
        # 2) mimetypes
        candidates.append(("mimetypes.guess_type(original_url)", self.MIME_TO_PREFERRED_EXT.get((mimetypes.guess_type(original_url)[0] or "").lower())))
        candidates.append(("mimetypes.guess_type(final_url)", self.MIME_TO_PREFERRED_EXT.get((mimetypes.guess_type(final_url or "")[0] or "").lower())))
        candidates.append(("mimetypes.from_content_type", self.MIME_TO_PREFERRED_EXT.get((normalized_ctype := self.normalizectype(content_type)))))
        if normalized_ctype: ext = guessed.lstrip(".") if (guessed := mimetypes.guess_extension(normalized_ctype)) else None; candidates.append(("mimetypes.guess_extension(content_type)", ("m4a" if ext == "mp4" and normalized_ctype in {"audio/mp4", "video/mp4"} else ext)))
        for strategy, raw_ext in candidates:
            if self.isvalidaudioext(ext := self.normalizeext(raw_ext)): return ext, strategy
            reason.append(f"{strategy} -> {raw_ext!r} (invalid or non-audio ext)")
        # 3) byte sniff fallback
        if not sample_bytes: reason.append("byte sniff skipped: empty sample bytes"); return None, "NULL"
        try:
            ext = self.normalizeext(getattr(guess, "extension", None) if (guess := filetype.guess(sample_bytes)) else None)
            ext = "m4a" if ext == "mp4" and self.isaudiomime(content_type) else ext
            if self.isvalidaudioext(ext): return ext, "filetype.guess(bytes)"
            reason.append(f"filetype.guess(bytes) -> {ext!r} (invalid or non-audio ext)")
        except Exception as exc:
            reason.append(f"filetype.guess(bytes) error: {exc}")
        try:
            matches, raw_ext = puremagic.from_string(sample_bytes), None
            if matches: raw_ext = getattr(matches[0], "extension", None) or getattr(matches[0], "name", None)
            ext = "m4a" if (ext := self.normalizeext(raw_ext)) == "mp4" and self.isaudiomime(content_type) else ext
            if self.isvalidaudioext(ext): return ext, "puremagic.from_string(bytes)"
            reason.append(f"puremagic.from_string(bytes) -> {ext!r} (invalid or non-audio ext)")
        except Exception as exc:
            reason.append(f"puremagic sniff error: {exc}")
        # return
        return None, "NULL"
    '''test'''
    def test(self, url: str, request_overrides: Optional[dict] = None, renew_session: bool = True) -> Dict[str, Any]:
        # init
        if renew_session: self.session.close(); self.session = requests.Session()
        result, reason = {"ok": False, "ctype": "", "ext": "NULL", "original_download_url": url, "download_url": url, "file_size": "NULL", "file_size_bytes": 0, "method": "", "status_code": 0, "reason": []}, []
        # 1) HEAD
        try:
            head_resp: requests.Response = (head_info := self.request("HEAD", url, request_overrides=request_overrides))["resp"]
            result["status_code"], result["download_url"] = head_info["status_code"], head_info["download_url"] or url
            result["ctype"], result["file_size_bytes"] = head_info["ctype"] or "NULL", head_info["file_size_bytes"] or 0
            result["file_size"] = AudioLinkTester.byte2mb(result["file_size_bytes"])
            if not head_info["ok"]: reason.append(f"HEAD returned non-2xx status: {head_info['status_code']}"); result["method"] = "requests.head"; head_resp.close()
            else:
                reason.append(f"HEAD success: status={head_info['status_code']}, ctype={head_info['ctype']!r}, final_url={head_info['download_url']!r}")
                ext, ext_method = self.inferext(original_url=url, final_url=head_info["download_url"], content_type=head_info["ctype"], content_disposition=head_resp.headers.get("Content-Disposition"), sample_bytes=b"", reason=reason); head_resp.close()
                if ext: result["ext"], result["ok"], result["method"], result["reason"] = ext, True, f"requests.head + {ext_method}", reason; return result
                reason.append("HEAD succeeded but could not infer a valid audio ext; fallback to GET.")
        except Exception as exc:
            reason.append(f"HEAD error: {exc}")
        # 2) GET with Stream
        try:
            get_resp: requests.Response = (get_info := self.request("GET", url, request_overrides=request_overrides))["resp"]
            result["status_code"], result["download_url"] = get_info["status_code"], get_info["download_url"] or url
            result["ctype"], result["file_size_bytes"] = get_info["ctype"] or "NULL", get_info["file_size_bytes"] or 0
            result["file_size"] = AudioLinkTester.byte2mb(result["file_size_bytes"])
            if not get_info["ok"]: reason.append(f"GET returned non-2xx status: {get_info['status_code']}"); result["method"] = "requests.get"; get_resp.close()
            else:
                reason.append(f"GET success: status={get_info['status_code']}, ctype={get_info['ctype']!r}, final_url={get_info['download_url']!r}")
                sample_bytes = self.sampleresponsebytes(get_resp, max_bytes=8192)
                ext, ext_method = self.inferext(original_url=url, final_url=get_info["download_url"], content_type=get_info["ctype"], content_disposition=get_resp.headers.get("Content-Disposition"), sample_bytes=sample_bytes, reason=reason); get_resp.close()
                if ext: result["ext"], result["ok"], result["method"] = ext, True, f"requests.get(stream) + {ext_method}"
                else: reason.append("GET succeeded but still could not infer a valid audio ext."); result["method"] = "requests.get(stream) + ext_inference_failed"
        except Exception as exc:
            reason.append(f"GET error: {exc}")
        # return
        result["reason"] = reason
        if not result["method"]: result["method"] = "HEAD -> GET"
        return result