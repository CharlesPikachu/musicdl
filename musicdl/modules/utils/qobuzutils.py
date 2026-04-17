'''
Function:
    Implementation of QobuzMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import time
import hashlib
import base64
import binascii
import requests
from urllib.parse import urljoin
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''QobuzMusicClientUtils'''
class QobuzMusicClientUtils():
    APP_ID = None
    MUSIC_QUALITIES = (27, 7, 6, 5)
    RNG_INIT = "abb21364945c0583309667d13ca3d93a"
    BASE_URL = "https://www.qobuz.com/api.json/0.2"
    get_token_func = lambda cookies, *keys: next((cookies.get(k) for k in keys if cookies.get(k)), None)
    '''initappid'''
    @staticmethod
    def initappid(session: requests.Session, headers: dict, cookies: dict, request_overrides: dict = None) -> str:
        if (QobuzMusicClientUtils.APP_ID is not None): return QobuzMusicClientUtils.APP_ID
        (resp := session.get("https://play.qobuz.com/login", headers=headers, cookies=cookies, **(request_overrides := request_overrides or {}))).raise_for_status()
        (resp := session.get(urljoin("https://play.qobuz.com", re.search(r'<script src="(/resources/[^"]+/bundle\.js)"></script>', resp.text).group(1)), headers=headers, cookies=cookies, **request_overrides)).raise_for_status()
        QobuzMusicClientUtils.APP_ID = re.search(r'production:\{api:\{appId:"(\d{9})"', resp.text).group(1)
        return QobuzMusicClientUtils.APP_ID
    '''getrequestsig'''
    @staticmethod
    def getrequestsig(method: str, args: dict, request_ts: str) -> str:
        sorted_args_str = "".join(f"{k}{v}" for k, v in sorted(args.items()))
        req_id = f"{method}{sorted_args_str}{request_ts}{QobuzMusicClientUtils.RNG_INIT}"
        return hashlib.md5(req_id.encode('utf-8')).hexdigest()
    '''startsession'''
    @staticmethod
    def startsession(session: requests.Session, headers: dict, cookies: dict, request_overrides: dict = None) -> dict:
        data = {"profile": "qbz-1", "request_ts": (request_ts := str(int(time.time()))), "request_sig": QobuzMusicClientUtils.getrequestsig("sessionstart", {"profile": "qbz-1"}, request_ts)}
        (resp := session.post(f"{QobuzMusicClientUtils.BASE_URL}/session/start", headers=headers, cookies=cookies, data=data, **(request_overrides := request_overrides or {}))).raise_for_status()
        return resp.json()
    '''gettrackinfo'''
    @staticmethod
    def gettrackinfo(session: requests.Session, headers: dict, cookies: dict, track_id: str, quality: str, request_overrides: dict = None) -> dict:
        params = {"request_ts": (request_ts := str(int(time.time()))), "request_sig": QobuzMusicClientUtils.getrequestsig("fileurl", {"format_id": str(quality), "intent": "stream", "track_id": str(track_id)}, request_ts), "track_id": track_id, "format_id": quality, "intent": "stream"}
        (resp := session.get(f"{QobuzMusicClientUtils.BASE_URL}/file/url", headers=headers, params=params, cookies=cookies, **(request_overrides := request_overrides or {}))).raise_for_status()
        return resp.json()
    '''derivesessionkey'''
    @staticmethod
    def derivesessionkey(infos: str) -> bytes:
        salt = base64.urlsafe_b64decode((parts := infos.split('.'))[0] + "=" * ((4 - len(parts[0]) % 4) % 4))
        info = base64.urlsafe_b64decode(parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4))
        hkdf = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=info, backend=default_backend())
        return hkdf.derive(binascii.unhexlify(QobuzMusicClientUtils.RNG_INIT))
    '''unwrapcontentkey'''
    @staticmethod
    def unwrapcontentkey(session_key: bytes, key_str: str) -> bytes:
        wrapped = base64.urlsafe_b64decode((parts := key_str.split('.'))[1] + "=" * ((4 - len(parts[1]) % 4) % 4))
        iv = base64.urlsafe_b64decode(parts[2] + "=" * ((4 - len(parts[2]) % 4) % 4))
        decryptor = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend()).decryptor()
        decrypted = decryptor.update(wrapped) + decryptor.finalize()
        return decrypted[:-decrypted[-1]]
    '''getqobuzsegmentuuid'''
    @staticmethod
    def getqobuzsegmentuuid(segment_data: bytes):
        return (lambda f: f(f, 0))(lambda self, pos: None if pos + 24 > len(segment_data) else (lambda size: None if size <= 0 or pos + size > len(segment_data) else (bytes(segment_data[pos + 8 : pos + 24]) if bytes(segment_data[pos + 4 : pos + 8]) == b"uuid" else self(self, pos + size)))(int.from_bytes(segment_data[pos : pos + 4], "big")))
    '''decryptqobuzsegment'''
    @staticmethod
    def decryptqobuzsegment(segment_data: bytes, raw_key: bytes, segment_uuid: bytes):
        if segment_uuid is None: return bytes(segment_data)
        buf, pos = bytearray(segment_data), 0
        while pos + 8 <= len(buf):
            if (size := int.from_bytes(buf[pos : pos + 4], "big")) <= 0 or pos + size > len(buf): break
            if not (bytes(buf[pos + 4 : pos + 8]) == b"uuid" and bytes(buf[pos + 8 : pos + 24]) == segment_uuid): pos += size; continue
            pointer = pos + 28; data_end = pos + int.from_bytes(buf[pointer : pointer + 4], "big")
            pointer, counter_len, frame_count = pointer + 8, buf[pointer + 4], int.from_bytes(buf[pointer + 5 : pointer + 8], "big")
            for _ in range(frame_count):
                frame_len = int.from_bytes(buf[pointer : pointer + 4], "big"); flags = int.from_bytes(buf[pointer + 6 : pointer + 8], "big")
                frame_start, frame_end = data_end, data_end + frame_len; data_end = frame_end
                if flags: counter = bytes(buf[pointer + 8 : pointer + 8 + counter_len]) + (b"\x00" * (16 - counter_len)); decryptor = Cipher(algorithms.AES(raw_key), modes.CTR(counter)).decryptor(); buf[frame_start:frame_end] = decryptor.update(bytes(buf[frame_start:frame_end])) + decryptor.finalize()
                pointer += 8 + counter_len
            pos += size
        return bytes(buf)