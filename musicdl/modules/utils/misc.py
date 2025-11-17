'''
Function:
    Implementation of common utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import html
import copy
import emoji
import errno
import pickle
import shutil
import bleach
import requests
import functools
import json_repair
import unicodedata
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filepath, sanitize_filename


'''touchdir'''
def touchdir(directory, exist_ok=True, mode=511, auto_sanitize=True):
    if auto_sanitize: directory = sanitize_filepath(directory)
    return os.makedirs(directory, exist_ok=exist_ok, mode=mode)


'''replacefile'''
def replacefile(src: str, dest: str):
    try:
        os.replace(src, dest)
    except OSError as exc:
        if exc.errno != errno.EXDEV: raise
        if os.path.exists(dest):
            if os.path.isdir(dest): raise
            os.remove(dest)
        shutil.move(src, dest)


'''legalizestring'''
def legalizestring(string: str, fit_gbk: bool = True, max_len: int = 255, fit_utf8: bool = True, replace_null_string: str = 'NULL'):
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
    try:
        string = BeautifulSoup(string, "lxml").get_text(separator="")
    except:
        string = bleach.clean(string, tags=[], attributes={}, strip=True)
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
        size = f'{round(size / 1024 / 1024, 2)} MB'
    except:
        size = 'NULL'
    return size


'''resp2json'''
def resp2json(resp: requests.Response):
    if not isinstance(resp, requests.Response): return {}
    try:
        result = resp.json()
    except:
        result = json_repair.loads(resp.text)
    if not result: result = dict()
    return result


'''isvalidresp'''
def isvalidresp(resp: requests.Response, valid_status_codes: list = [200]):
    if not isinstance(resp, requests.Response): return False
    if resp is None or resp.status_code not in valid_status_codes:
        return False
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
def cachecookies(client_name: str = '', cache_cookie_path: str = '', client_cookies: dict = {}):
    if os.path.exists(cache_cookie_path):
        with open(cache_cookie_path, 'rb') as fp:
            cookies = pickle.load(fp)
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
        self.default_cookies = self.default_download_cookies
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''useparseheaderscookies'''
def useparseheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.default_headers = self.default_parse_headers
        self.default_cookies = self.default_parse_cookies
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''usesearchheaderscookies'''
def usesearchheaderscookies(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.default_headers = self.default_search_headers
        self.default_cookies = self.default_search_cookies
        if hasattr(self, '_initsession'): self._initsession()
        return func(self, *args, **kwargs)
    return wrapper


'''AudioLinkTester'''
class AudioLinkTester(object):
    MAGIC = [
        (b"ID3", "mp3"), (b"\xFF\xFB", "mp3"), (b"fLaC", "flac"), (b"RIFF", "wav"), (b"OggS", "ogg"), (b"MThd", "midi"), (b"\x00\x00\x00\x18ftyp", "mp4/m4a"),
    ]
    AUDIO_CT_PREFIX = "audio/"
    AUDIO_CT_EXTRA = {
        "application/octet-stream", "application/x-flac", "application/flac",
    }
    CTYPE_TO_EXT = {
        "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/aac": "aac", "audio/wav": "wav", 
        "audio/x-wav": "wav", "audio/flac": "flac", "audio/x-flac": "flac", "audio/ogg": "ogg", "audio/opus": "opus", "audio/x-aac": "ogg",
    }
    def __init__(self, timeout=(5, 15), headers={}, cookies={}):
        self.session = requests.Session()
        self.timeout = timeout
        self.headers = {
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.headers.update(headers)
        self.cookies = cookies
    '''isaudioct'''
    @staticmethod
    def isaudioct(ct: str):
        if not ct:
            return False
        ct = ct.lower().split(";", 1)[0].strip()
        return ct.startswith(AudioLinkTester.AUDIO_CT_PREFIX) or ct in AudioLinkTester.AUDIO_CT_EXTRA
    '''sniffmagic'''
    @staticmethod
    def sniffmagic(b: str):
        for sig, fmt in AudioLinkTester.MAGIC:
            if b.startswith(sig):
                return fmt
        if len(b) >= 2 and b[0] == 0xFF and (b[1] & 0xF0) == 0xF0:
            return "aac/adts"
        return None
    '''probe'''
    def probe(self, url: str, request_overrides: dict = {}):
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
            if ctype == 'image/jpg; charset=UTF-8' or ctype == 'image/jpg':
                ctype = 'audio/mpeg'
            ext = self.CTYPE_TO_EXT.get(ctype, 'NULL')
            outputs = dict(file_size=file_size, ctype=ctype, ext=ext, download_url=url, final_url=final_url)
        except:
            outputs = dict(file_size='NULL', ctype='NULL', ext='NULL', download_url=url, final_url='NULL')
        if outputs['file_size'] not in ['NULL']: return outputs
        # GETSTREAM probe
        try:
            resp = self.session.get(url, allow_redirects=True, stream=True, **request_overrides)
            resp.raise_for_status()
            resp_headers, final_url = resp.headers, resp.url
            resp.close()
            file_size, ctype = byte2mb(resp_headers.get('content-length')), resp_headers.get('content-type')
            if ctype == 'image/jpg; charset=UTF-8' or ctype == 'image/jpg':
                ctype = 'audio/mpeg'
            ext = self.CTYPE_TO_EXT.get(ctype, 'NULL')
            outputs = dict(file_size=file_size, ctype=ctype, ext=ext, download_url=url, final_url=final_url)
        except:
            outputs = dict(file_size='NULL', ctype='NULL', ext='NULL', download_url=url, final_url='NULL')
        return outputs
    '''test'''
    def test(self, url: str, request_overrides: dict = {}):
        if 'headers' not in request_overrides: request_overrides['headers'] = self.headers
        if 'timeout' not in request_overrides: request_overrides['timeout'] = self.timeout
        if 'cookies' not in request_overrides: request_overrides['cookies'] = self.cookies
        outputs = dict(ok=False, status=0, method="", final_url=None, ctype=None, clen=None, range=None, fmt=None, reason="")
        # HEAD test
        try:
            resp = self.session.head(url, allow_redirects=True, **request_overrides)
            clen = resp.headers.get("Content-Length")
            clen = int(clen) if clen and clen.isdigit() else None
            outputs.update(dict(
                status=resp.status_code, method="HEAD", final_url=str(resp.url), ctype=resp.headers.get("Content-Type"),
                clen=clen, range=(resp.headers.get("Accept-Ranges") or "").lower() == "bytes",
            ))
            if 200 <= resp.status_code < 300 and (self.isaudioct(outputs["ctype"]) and (outputs["clen"] or outputs["range"])):
                outputs.update(dict(
                    ok=True, reason="HEAD success"
                ))
                return outputs
        except Exception as err:
            outputs["reason"] = f"HEAD error: {err}"
        # RANGEGET test
        try:
            headers = copy.deepcopy(self.headers)
            headers["Range"] = "bytes=0-15"
            resp = self.session.get(url, stream=True, allow_redirects=True, **request_overrides)
            outputs.update(dict(
                status=resp.status_code, method="RANGEGET", final_url=str(resp.url),
            ))
            if resp.status_code not in (200, 206):
                outputs["reason"] = f"RANGEGET error: response status {resp.status_code}"
                return outputs
            chunk = b""
            for b in resp.iter_content(chunk_size=16):
                chunk = b
                break
            resp.close()
            outputs["ctype"] = outputs["ctype"] or resp.headers.get("Content-Type")
            outputs["range"] = outputs["range"] or (resp.status_code == 206) or (resp.headers.get("Content-Range") is not None)
            clen = resp.headers.get("Content-Length") or (resp.headers.get("Content-Range") or "").split("/")[-1]
            if clen and clen.isdigit():
                outputs["clen"] = int(clen)
            outputs["fmt"] = self.sniffmagic(chunk)
            if self.isaudioct(outputs["ctype"]) or outputs["fmt"]:
                outputs.update(dict(
                    ok=True, reason="RANGEGET success"
                ))
            else:
                outputs.update(dict(
                    ok=False, reason="RANGEGET error: Not audio-like (CT/magic)"
                ))
        except Exception as err:
            outputs["reason"] = f"RANGEGET error: {err}"
        # return
        return outputs