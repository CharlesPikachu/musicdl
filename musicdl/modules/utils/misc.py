'''
Function:
    Implementation of Common Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import html
import emoji
import errno
import pickle
import shutil
import bleach
import hashlib
import requests
import functools
import json_repair
import unicodedata
from io import BytesIO
from pathlib import Path
from bs4 import BeautifulSoup
from .importutils import optionalimport
from mutagen import File as MutagenFile
from pathvalidate import sanitize_filepath, sanitize_filename


'''estimatedurationwithfilesizebr'''
def estimatedurationwithfilesizebr(file_size_bytes: int, br_kbps: float, return_seconds: bool = False) -> str:
    if not file_size_bytes or not br_kbps or br_kbps <= 0: return "-:-:-"
    total_bits = file_size_bytes * 8
    duration_seconds = int(total_bits / (br_kbps * 1000))
    if return_seconds: return duration_seconds
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


'''estimatedurationwithfilelink'''
def estimatedurationwithfilelink(filelink: str = '', headers: dict = None, request_overrides: dict = None):
    headers, request_overrides = headers or {}, request_overrides or {}
    try:
        resp = requests.get(filelink, headers=headers, timeout=10, **request_overrides)
        resp.raise_for_status()
        f = BytesIO(resp.content)
        audio = MutagenFile(f)
        length = getattr(audio.info, "length", 0)
        return int(length)
    except:
        return 0


'''cookies2dict'''
def cookies2dict(cookies: str | dict = None):
    if not cookies: cookies = {}
    if isinstance(cookies, dict): return cookies
    if isinstance(cookies, str): return dict(item.split("=", 1) for item in cookies.split("; "))
    raise TypeError(f'cookies type is "{type(cookies)}", expect cookies to "str" or "dict" or "None".')


'''cookies2string'''
def cookies2string(cookies: str | dict = None):
    if not cookies: cookies = ""
    if isinstance(cookies, str): return cookies
    if isinstance(cookies, dict): return "; ".join(f"{k}={v}" for k, v in cookies.items())
    raise TypeError(f'cookies type is "{type(cookies)}", expect cookies to "str" or "dict" or "None".')


'''touchdir'''
def touchdir(directory, exist_ok=True, mode=511, auto_sanitize=True):
    if auto_sanitize: directory = sanitize_filepath(directory)
    return os.makedirs(directory, exist_ok=exist_ok, mode=mode)


'''replacefile'''
def replacefile(src: str, dest: str):
    try:
        os.replace(src, dest)
    except OSError as exc:
        if exc.errno != errno.EXDEV: raise Exception
        if os.path.exists(dest):
            if os.path.isdir(dest): raise Exception
            os.remove(dest)
        shutil.move(src, dest)


'''legalizestring'''
def legalizestring(string: str, fit_gbk: bool = True, max_len: int = 255, fit_utf8: bool = True, replace_null_string: str = 'NULL'):
    if not string: return replace_null_string
    string = str(string)
    string = string.replace(r'\"', '"')
    string = re.sub(r"<\\/", "</", string)
    string = re.sub(r"\\/>", "/>", string)
    string = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), string)
    # html.unescape
    for _ in range(2):
        new_string = html.unescape(string)
        if new_string == string: break
        string = new_string
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
    string = re.sub(r"\s+", " ", string).strip()
    if not string: string = replace_null_string
    return string


'''shortenpathsinsonginfos'''
def shortenpathsinsonginfos(song_infos: list, max_path: int = 240, keep_ext: bool = True, with_hash_suffix: bool = False):
    used_paths = set()
    for info in song_infos:
        raw_path = (info.save_path or "").strip()
        if not raw_path or raw_path.upper() == "NULL": continue
        src_path = Path(raw_path)
        output_dir = src_path.parent.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
        ext = src_path.suffix if keep_ext else ""
        stem = src_path.stem
        digest = hashlib.md5(str(src_path).encode("utf-8")).hexdigest()
        for hash_len in (8, 10):
            hash_suffix = f"-{digest[:hash_len]}" if with_hash_suffix else ""
            max_stem_len = max(1, max_path - (len(str(output_dir)) + 1 + len(hash_suffix) + len(ext)))
            safe_stem = (stem[:max_stem_len].rstrip(" .") or "NULL")
            out_path = str(output_dir / f"{safe_stem}{hash_suffix}{ext}")
            if out_path.lower() not in used_paths: break
        used_paths.add(out_path.lower()); info._save_path = out_path
    return song_infos


'''seconds2hms'''
def seconds2hms(seconds: int):
    try:
        seconds = int(float(seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        hms = '%02d:%02d:%02d' % (h, m, s)
        if hms == '00:00:00': hms = '-:-:-'
    except:
        hms = '-:-:-'
    return hms


'''byte2mb'''
def byte2mb(size: int):
    try:
        size = int(float(size))
        if size == 0: return 'NULL'
        size = round(size / 1024 / 1024, 2)
        if size == 0.0: return 'NULL'
        size = f'{size} MB'
    except:
        size = 'NULL'
    return size


'''resp2json'''
def resp2json(resp: requests.Response):
    curl_cffi = optionalimport('curl_cffi')
    valid_resp_object = (requests.Response, curl_cffi.requests.Response) if curl_cffi else requests.Response
    if not isinstance(resp, valid_resp_object): return {}
    try: result = resp.json()
    except: result = json_repair.loads(resp.text)
    if not result: result = dict()
    return result


'''isvalidresp'''
def isvalidresp(resp: requests.Response, valid_status_codes: list | tuple | set = {200, 206}):
    curl_cffi = optionalimport('curl_cffi')
    valid_resp_object = (requests.Response, curl_cffi.requests.Response) if curl_cffi else requests.Response
    if not isinstance(resp, valid_resp_object): return False
    if resp is None or resp.status_code not in valid_status_codes: return False
    return True


'''safeextractfromdict'''
def safeextractfromdict(data, progressive_keys, default_value):
    try:
        result = data
        for key in progressive_keys: result = result[key]
    except:
        result = default_value
    return result


'''cachecookies'''
def cachecookies(client_name: str = '', cache_cookie_path: str = '', client_cookies: dict = None):
    if os.path.exists(cache_cookie_path):
        with open(cache_cookie_path, 'rb') as fp: cookies = pickle.load(fp)
    else:
        cookies = dict()
    with open(cache_cookie_path, 'wb') as fp:
        cookies[client_name] = client_cookies
        pickle.dump(cookies, fp)


'''usedownloadheaderscookies'''
def usedownloadheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.default_headers = self.default_download_headers
        if hasattr(self, 'default_download_cookies'): self.default_cookies = self.default_download_cookies
        if hasattr(self, 'enable_download_curl_cffi'): self.enable_curl_cffi = self.enable_download_curl_cffi
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''useparseheaderscookies'''
def useparseheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.default_headers = self.default_parse_headers
        if hasattr(self, 'default_parse_cookies'): self.default_cookies = self.default_parse_cookies
        if hasattr(self, 'enable_parse_curl_cffi'): self.enable_curl_cffi = self.enable_parse_curl_cffi
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''usesearchheaderscookies'''
def usesearchheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.default_headers = self.default_search_headers
        if hasattr(self, 'default_search_cookies'): self.default_cookies = self.default_search_cookies
        if hasattr(self, 'enable_search_curl_cffi'): self.enable_curl_cffi = self.enable_search_curl_cffi
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''searchdictbykey'''
def searchdictbykey(obj, target_key: str):
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target_key: results.append(v)
            results.extend(searchdictbykey(v, target_key))
    elif isinstance(obj, list):
        for item in obj: results.extend(searchdictbykey(item, target_key))
    return results


'''AudioLinkTester'''
class AudioLinkTester(object):
    MAGIC = [
        (b"ID3", "mp3"), (b"\xFF\xFB", "mp3"), (b"fLaC", "flac"), (b"RIFF", "wav"), (b"OggS", "ogg"), (b"MThd", "midi"), (b"\x00\x00\x00\x18ftyp", "mp4/m4a"),
    ]
    AUDIO_CT_PREFIX = "audio/"
    AUDIO_CT_EXTRA = {
        "application/octet-stream", "application/x-flac", "application/flac", "application/x-mpegurl", "video/mp4"
    }
    CTYPE_TO_EXT = {
        "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/aac": "aac", "audio/wav": "wav", "video/mp4": "mp4",
        "audio/x-wav": "wav", "audio/flac": "flac", "audio/x-flac": "flac", "audio/ogg": "ogg", "audio/opus": "opus", "audio/x-aac": "ogg",
    }
    def __init__(self, timeout=(5, 15), headers: dict = None, cookies: dict = None):
        self.session = requests.Session()
        self.timeout = timeout
        self.headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.headers.update(headers or {})
        self.cookies = cookies or {}
    '''isaudioct'''
    @staticmethod
    def isaudioct(ct: str):
        if not ct: return False
        ct = ct.lower().split(";", 1)[0].strip()
        return ct.startswith(AudioLinkTester.AUDIO_CT_PREFIX) or ct in AudioLinkTester.AUDIO_CT_EXTRA
    '''sniffmagic'''
    @staticmethod
    def sniffmagic(b: str):
        for sig, fmt in AudioLinkTester.MAGIC:
            if b.startswith(sig): return fmt
        if len(b) >= 2 and b[0] == 0xFF and (b[1] & 0xF0) == 0xF0: return "aac/adts"
        return None
    '''probe'''
    def probe(self, url: str, request_overrides: dict = None):
        request_overrides, naive_guess_ext = request_overrides or {}, url.split('?')[0].split('.')[-1]
        if 'headers' not in request_overrides: request_overrides['headers'] = self.headers
        if 'timeout' not in request_overrides: request_overrides['timeout'] = self.timeout
        if 'cookies' not in request_overrides: request_overrides['cookies'] = self.cookies
        outputs = dict(file_size='NULL', ctype='NULL', ext='NULL', download_url=url, final_url='NULL')
        # HEAD probe
        try:
            resp = self.session.head(url, allow_redirects=True, **request_overrides)
            resp.raise_for_status()
            resp_headers, final_url = resp.headers, resp.url
            resp.close()
            file_size, ctype = byte2mb(resp_headers.get('content-length')), resp_headers.get('content-type')
            if ctype == 'image/jpg; charset=UTF-8' or ctype == 'image/jpg': ctype = 'audio/mpeg'
            if ctype == 'text/plain' and naive_guess_ext == 'm4s': ctype = 'audio/mp4'
            ext = self.CTYPE_TO_EXT.get(ctype, 'NULL')
            outputs = dict(file_size=file_size, ctype=ctype, ext=ext, download_url=url, final_url=final_url)
        except:
            outputs = dict(file_size='NULL', ctype='NULL', ext='NULL', download_url=url, final_url='NULL')
        if outputs['file_size'] and outputs['file_size'] not in ('NULL',): return outputs
        # GETSTREAM probe
        try:
            resp = self.session.get(url, allow_redirects=True, stream=True, **request_overrides)
            resp.raise_for_status()
            resp_headers, final_url = resp.headers, resp.url
            resp.close()
            file_size, ctype = byte2mb(resp_headers.get('content-length')), resp_headers.get('content-type')
            if ctype == 'image/jpg; charset=UTF-8' or ctype == 'image/jpg': ctype = 'audio/mpeg'
            if ctype == 'text/plain' and naive_guess_ext == 'm4s': ctype = 'audio/mp4'
            ext = self.CTYPE_TO_EXT.get(ctype, 'NULL')
            outputs = dict(file_size=file_size, ctype=ctype, ext=ext, download_url=url, final_url=final_url)
        except:
            outputs = dict(file_size='NULL', ctype='NULL', ext='NULL', download_url=url, final_url='NULL')
        return outputs
    '''test'''
    def test(self, url: str, request_overrides: dict = None):
        request_overrides, naive_guess_ext = request_overrides or {}, url.split('?')[0].split('.')[-1]
        if 'headers' not in request_overrides: request_overrides['headers'] = self.headers
        if 'timeout' not in request_overrides: request_overrides['timeout'] = self.timeout
        if 'cookies' not in request_overrides: request_overrides['cookies'] = self.cookies
        outputs = dict(ok=False, status=0, method="", final_url=None, ctype=None, clen=None, range=None, fmt=None, reason="")
        # HEAD test
        try:
            resp = self.session.head(url, allow_redirects=True, **request_overrides)
            clen = resp.headers.get("Content-Length")
            clen = int(clen) if clen and clen.isdigit() else None
            outputs.update(dict(status=resp.status_code, method="HEAD", final_url=str(resp.url), ctype=resp.headers.get("Content-Type"), clen=clen, range=(resp.headers.get("Accept-Ranges") or "").lower() == "bytes"))
            if outputs["ctype"] == 'text/plain' and naive_guess_ext == 'm4s': outputs["ctype"] = 'audio/mp4'
            if 200 <= resp.status_code < 300 and ((self.isaudioct(outputs["ctype"]) or (naive_guess_ext in ('m4s',))) and (outputs["clen"] or outputs["range"])):
                outputs.update(dict(ok=True, reason="HEAD success"))
                return outputs
        except Exception as err:
            outputs["reason"] = f"HEAD error: {err}"
        # RANGEGET test
        try:
            resp = self.session.get(url, stream=True, allow_redirects=True, **request_overrides)
            outputs.update(dict(status=resp.status_code, method="RANGEGET", final_url=str(resp.url)))
            if resp.status_code not in (200, 206): outputs["reason"] = f"RANGEGET error: response status {resp.status_code}"; return outputs
            chunk = b""
            for b in resp.iter_content(chunk_size=16): chunk = b; break
            resp.close()
            outputs["ctype"] = outputs["ctype"] or resp.headers.get("Content-Type")
            if outputs["ctype"] == 'text/plain' and naive_guess_ext == 'm4s': outputs["ctype"] = 'audio/mp4'
            outputs["range"] = outputs["range"] or (resp.status_code == 206) or (resp.headers.get("Content-Range") is not None)
            clen = resp.headers.get("Content-Length") or (resp.headers.get("Content-Range") or "").split("/")[-1]
            if clen and clen.isdigit(): outputs["clen"] = int(clen)
            outputs["fmt"] = self.sniffmagic(chunk)
            if self.isaudioct(outputs["ctype"]) or outputs["fmt"] or (naive_guess_ext in ('m4s',)): outputs.update(dict(ok=True, reason="RANGEGET success"))
            else: outputs.update(dict(ok=False, reason="RANGEGET error: Not audio-like (CT/magic)"))
        except Exception as err:
            outputs["reason"] = f"RANGEGET error: {err}"
        # return
        return outputs