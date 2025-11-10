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
import emoji
import pickle
import bleach
import filetype
import requests
import unicodedata
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filepath, sanitize_filename


'''touchdir'''
def touchdir(directory, exist_ok=True, mode=511, auto_sanitize=True):
    if auto_sanitize: directory = sanitize_filepath(directory)
    return os.makedirs(directory, exist_ok=exist_ok, mode=mode)


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
def seconds2hms(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return '%02d:%02d:%02d' % (h, m, s)


'''probesongurl'''
def probesongurl(url: str, headers: dict = {}, timeout: int = 30):
    resp = requests.get(url, timeout=timeout, headers=headers)
    resp.raise_for_status()
    headers = resp.headers
    if headers.get('transfer-encoding') != 'chunked':
        file_size = int(resp.headers.get('content-length'))
        file_size = f'{round(int(file_size) / 1024 / 1024, 2)} MB'
    else:
        file_size = '0.00 MB'
    ctype = headers.get('content-type')
    if ctype == 'image/jpg; charset=UTF-8' or ctype == 'image/jpg':
        ctype = 'audio/mpeg'
    ctype_to_ext_mapping = {
        "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/aac": "aac", "audio/wav": "wav", 
        "audio/x-wav": "wav", "audio/flac": "flac", "audio/x-flac": "flac", "audio/ogg": "ogg", "audio/opus": "opus",
    }
    ext = ctype_to_ext_mapping.get(ctype, 'NULL')
    if ext == 'NULL':
        kind = filetype.guess(resp.content)
        ext = kind.extension if kind else 'NULL'
        if ext == "mpga": ext = 'mp3'
    probe_result = {
        "file_size": file_size, "ctype": ctype, "ext": ext, 'download_url': url
    }
    return probe_result


'''cachecookies'''
def cachecookies(client_name: str = '', cache_cookie_path: str = '', client_cookies: dict = {}):
    if os.path.isfile(cache_cookie_path):
        with open(cache_cookie_path, 'rb') as fp:
            cookies = pickle.load(fp)
    else:
        cookies = dict()
    with open(cache_cookie_path, 'wb') as fp:
        cookies[client_name] = client_cookies
        pickle.dump(cookies, fp)