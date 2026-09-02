'''
Function:
    Implementation of SpotifyMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import time
import hmac
import json
import struct
import base64
import hashlib
import secrets
import requests
import json_repair
from contextlib import suppress
from dataclasses import dataclass
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse
from .misc import resp2json, safeextractfromdict
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey


'''SpotifyMusicClientUtils'''
class SpotifyMusicClientUtils():
    BROWSER_VERSION = '145'
    COMMON_HEADERS = {'Content-Type': 'application/json', 'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{BROWSER_VERSION}.0.0.0 Safari/537.36', 'Sec-Ch-Ua': f'"Chromium";v="{BROWSER_VERSION}", "Not(A:Brand";v="24", "Google Chrome";v="{BROWSER_VERSION}"'}
    '''getlatesttotpsecret'''
    @staticmethod
    def getlatesttotpsecret(version: int = 61) -> dict:
        VERSION_TO_SECRET = {
            59: [123, 105, 79, 70, 110, 59, 52, 125, 60, 49, 80, 70, 89, 75, 80, 86, 63, 53, 123, 37, 117, 49, 52, 93, 77, 62, 47, 86, 48, 104, 68, 72],
            60: [79, 109, 69, 123, 90, 65, 46, 74, 94, 34, 58, 48, 70, 71, 92, 85, 122, 63, 91, 64, 87, 87],
            61: [44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75, 76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78],
        }
        return {"version": version, "secret": VERSION_TO_SECRET[version]}
    '''generatetotp'''
    @staticmethod
    def generatetotp(secret: List[int]) -> str:
        transformed = [e ^ ((t % 33) + 9) for t, e in enumerate(secret)]
        hex_str = ("".join(str(num) for num in transformed)).encode('ascii').hex()
        base32_secret = base64.b64encode(bytes.fromhex(hex_str)).decode('utf-8').replace('=', '')
        base32_bytes = base64.b64decode(base32_secret + '==')
        time_step = int(time.time() / 30); time_hex = format(time_step, '016x')
        digest = hmac.new(base32_bytes, bytes.fromhex(time_hex), hashlib.sha1).digest()
        offset = digest[19] & 0xf; code = int.from_bytes(digest[offset: offset+4], byteorder='big') & 0x7fffffff
        return str(code % 1000000).zfill(6)
    '''getaccesstoken'''
    @staticmethod
    def getaccesstoken(session: requests.Session, totp: str, totp_ver: int, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        params = {'reason': 'init', 'productType': 'web-player', 'totp': totp, 'totpVer': str(totp_ver), 'totpServer': totp}
        (resp := session.get("https://open.spotify.com/api/token", params=params, headers=SpotifyMusicClientUtils.COMMON_HEADERS, **request_overrides)).raise_for_status()
        return {"accessToken": (data := resp2json(resp=resp)).get('accessToken'), "clientId": data.get('clientId')}
    '''getclienttoken'''
    @staticmethod
    def getclienttoken(session: requests.Session, client_version: str, client_id: str, device_id: str, request_overrides: dict = None) -> str:
        request_overrides = request_overrides or {}
        payload = {"client_data": {"client_version": client_version, "client_id": client_id, "js_sdk_data": {"device_brand": "unknown", "device_model": "unknown", "os": "windows", "os_version": "NT 10.0", "device_id": device_id, "device_type": "computer"}}}
        headers = SpotifyMusicClientUtils.COMMON_HEADERS.copy()
        headers.update({'Authority': 'clienttoken.spotify.com', 'Accept': 'application/json'})
        (resp := session.post('https://clienttoken.spotify.com/v1/clienttoken', headers=headers, json=payload, **request_overrides)).raise_for_status()
        return safeextractfromdict(resp2json(resp=resp), ['granted_token', 'token'], '')
    '''extractjslinks'''
    @staticmethod
    def extractjslinks(html: str) -> List[str]:
        script_tag_regex = re.compile(r'<script[^>]+src="([^"]+\.js)"[^>]*>')
        return script_tag_regex.findall(html)
    '''getsessiondata'''
    @staticmethod
    def getsessiondata(session: requests.Session, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        (resp := session.get('https://open.spotify.com', headers=SpotifyMusicClientUtils.COMMON_HEADERS, **request_overrides)).raise_for_status()
        cookie_match = re.search(r'sp_t=([^;]+)', resp.headers.get('set-cookie', '')); device_id = cookie_match.group(1) if cookie_match else ''
        app_server_config_match, client_version = re.search(r'<script id="appServerConfig" type="text/plain">([^<]+)</script>', resp.text), ''
        try: client_version = json_repair.loads(base64.b64decode(app_server_config_match.group(1)).decode("utf-8")).get("clientVersion", "") if app_server_config_match else (m.group(1) if (m := re.search(r'"clientVersion":"([^"]+)"', resp.text)) else "")
        except Exception: client_version = m.group(1) if (m := re.search(r'"clientVersion":"([^"]+)"', resp.text)) else ""
        all_js_links, js_pack_relative = SpotifyMusicClientUtils.extractjslinks(resp.text), ''
        js_pack_relative = next((link for link in all_js_links if 'web-player/web-player' in link and link.endswith('.js')), js_pack_relative)
        if js_pack_relative.startswith('http'): js_pack = js_pack_relative
        else: js_pack = f'https://open.spotify.com{js_pack_relative}' if js_pack_relative else ''
        return {"deviceId": device_id, "clientVersion": client_version, "jsPack": js_pack}


'''SpotifyMusicClientPlaylistUtils'''
class SpotifyMusicClientPlaylistUtils():
    '''extractmappings'''
    @staticmethod
    def extractmappings(js_code: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        matches = re.compile(r'\{\d+:"[^"]+"(?:,\d+:"[^"]+")*\}').findall(js_code)
        if not matches or len(matches) < 5: return {}, {}
        parse_match_func = lambda match_str: {key.strip(): value.strip().strip('"') for entry in re.split(r',(?=\d+:)', match_str[1:-1]) for key, sep, value in [entry.partition(':')] if sep}
        return parse_match_func(matches[3]), parse_match_func(matches[4])
    '''combinechunks'''
    @staticmethod
    def combinechunks(str_mapping: Dict[str, str], hash_mapping: Dict[str, str]) -> List[str]:
        chunks = []
        for key, string_val in str_mapping.items():
            if (hash_val := hash_mapping.get(key)): chunks.append(f"{string_val}.{hash_val}.js")
        return chunks
    '''getsha256hash'''
    @staticmethod
    def getsha256hash(session: requests.Session, js_pack: str, request_overrides: dict = None) -> str:
        fallback_hash, request_overrides = 'a67612f8c59f4cb4a9723d8e0e0e7b7cb8c5c3d45e3d8c4f5e6f7e8f9a0b1c2d', request_overrides or {}
        if not js_pack: return fallback_hash
        try:
            (resp := session.get(js_pack, headers=SpotifyMusicClientUtils.COMMON_HEADERS, **request_overrides)).raise_for_status()
            raw_hashes = resp.text; str_mapping, hash_mapping = SpotifyMusicClientPlaylistUtils.extractmappings(raw_hashes)
            chunks = SpotifyMusicClientPlaylistUtils.combinechunks(str_mapping, hash_mapping)
            for chunk in chunks:
                with suppress(Exception): raw_hashes += session.get(f"https://open.spotifycdn.com/cdn/build/web-player/{chunk}", headers=SpotifyMusicClientUtils.COMMON_HEADERS, **request_overrides).text
            return (m.group(1) if (m := re.search(r'"fetchPlaylist","(?:query|mutation)","([^"]+)"', raw_hashes)) else fallback_hash)
        except Exception: return fallback_hash
    '''fetchplaylist'''
    @staticmethod
    def fetchplaylist(session: requests.Session, access_token: str, client_token: str, client_version: str, playlist_id: str, js_pack: str, offset: int = 0, limit: int = 25, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        sha256_hash = SpotifyMusicClientPlaylistUtils.getsha256hash(session, js_pack, request_overrides=request_overrides)
        payload = {"operationName": "fetchPlaylist", "variables": {"uri": f"spotify:playlist:{playlist_id}", "offset": offset, "limit": limit, "enableWatchFeedEntrypoint": False}, "extensions": {"persistedQuery": {"version": 1, "sha256Hash": sha256_hash}}}
        headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{SpotifyMusicClientUtils.BROWSER_VERSION}.0.0.0 Safari/537.36', 'Sec-Ch-Ua': f'"Chromium";v="{SpotifyMusicClientUtils.BROWSER_VERSION}", "Not(A:Brand";v="24", "Google Chrome";v="{SpotifyMusicClientUtils.BROWSER_VERSION}"', 'Authorization': f'Bearer {access_token}', 'Client-Token': client_token, 'Spotify-App-Version': client_version, 'Content-Type': 'application/json;charset=UTF-8'}
        (resp := session.post('https://api-partner.spotify.com/pathfinder/v2/query', headers=headers, json=payload, **request_overrides)).raise_for_status()
        return resp2json(resp=resp)
    '''getalltracks'''
    @staticmethod
    def getalltracks(session: requests.Session, access_token: str, client_token: str, client_version: str, playlist_id: str, js_pack: str, request_overrides: dict = None) -> List[dict]:
        tracks, offset, limit, request_overrides, playlist_result_first = [], 0, 343, request_overrides or {}, {}
        while True:
            playlist_result = SpotifyMusicClientPlaylistUtils.fetchplaylist(session, access_token, client_token, client_version, playlist_id, js_pack, offset, limit, request_overrides=request_overrides)
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if not (content := safeextractfromdict(playlist_result, ['data', 'playlistV2', 'content'], {})): break
            tracks.extend(content.get('items', [])); total_count = content.get('totalCount', 0)
            if total_count <= offset + limit: break
            offset += limit
        return tracks, playlist_result_first
    '''parse'''
    @staticmethod
    def parse(session: requests.Session, playlist_id: str, request_overrides: dict = None) -> dict:
        session, request_overrides = session or requests.Session(), request_overrides or {}
        try:
            session_data = SpotifyMusicClientUtils.getsessiondata(session, request_overrides=request_overrides)
            device_id, client_version, js_pack = session_data['deviceId'], session_data['clientVersion'], session_data['jsPack']
            secret_data = SpotifyMusicClientUtils.getlatesttotpsecret(); totp = SpotifyMusicClientUtils.generatetotp(secret_data['secret'])
            token_data = SpotifyMusicClientUtils.getaccesstoken(session, totp, secret_data['version'], request_overrides=request_overrides)
            access_token, client_id = token_data['accessToken'], token_data['clientId']; client_token = SpotifyMusicClientUtils.getclienttoken(session, client_version, client_id, device_id, request_overrides=request_overrides)
            tracks, playlist_result_first = SpotifyMusicClientPlaylistUtils.getalltracks(session, access_token, client_token, client_version, playlist_id, js_pack, request_overrides=request_overrides)
            for item in tracks: uri: str = safeextractfromdict(item, ['itemV2', 'data', 'uri'], None); item['id'], item['song_link'] = uri.split(':')[2], f"https://open.spotify.com/track/{uri.split(':')[2]}"
            return tracks, playlist_result_first
        except Exception: return [], {}


'''SpotifyMusicClientSearchUtils'''
class SpotifyMusicClientSearchUtils():
    '''query'''
    @staticmethod
    def query(session: requests.Session, payload: dict, request_overrides: dict = None) -> dict:
        session, request_overrides = session or requests.Session(), request_overrides or {}
        session_data = SpotifyMusicClientUtils.getsessiondata(session, request_overrides=request_overrides)
        device_id, client_version = session_data['deviceId'], session_data['clientVersion']
        secret_data = SpotifyMusicClientUtils.getlatesttotpsecret(); totp = SpotifyMusicClientUtils.generatetotp(secret_data['secret'])
        token_data = SpotifyMusicClientUtils.getaccesstoken(session, totp, secret_data['version'], request_overrides=request_overrides)
        access_token, client_id = token_data['accessToken'], token_data['clientId']; client_token = SpotifyMusicClientUtils.getclienttoken(session, client_version, client_id, device_id, request_overrides=request_overrides)
        headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{SpotifyMusicClientUtils.BROWSER_VERSION}.0.0.0 Safari/537.36', 'Sec-Ch-Ua': f'"Chromium";v="{SpotifyMusicClientUtils.BROWSER_VERSION}", "Not(A:Brand";v="24", "Google Chrome";v="{SpotifyMusicClientUtils.BROWSER_VERSION}"', 'Authorization': f'Bearer {access_token}', 'Client-Token': client_token, 'Spotify-App-Version': client_version, 'Content-Type': 'application/json;charset=UTF-8'}
        (resp := session.post("https://api-partner.spotify.com/pathfinder/v2/query", json=payload, headers=headers, **request_overrides)).raise_for_status()
        return resp2json(resp=resp)
    '''searchbykeyword'''
    @staticmethod
    def searchbykeyword(session: requests.Session, query: str, limit: int, offset: int, rule: dict = None, request_overrides: dict = None) -> list:
        request_overrides, rule = request_overrides or {}, rule or {}
        (payload := {"variables": {"searchTerm": query, "offset": offset, "limit": limit, "numberOfTopResults": 5, "includeAudiobooks": True, "includeArtistHasConcertsField": False, "includePreReleases": True, "includeAuthors": False}, "operationName": "searchDesktop", "extensions": {"persistedQuery": {"version": 1, "sha256Hash": "fcad5a3e0d5af727fb76966f06971c19cfa2275e6ff7671196753e008611873c"}}}).update(rule)
        return SpotifyMusicClientSearchUtils.query(session, payload, request_overrides=request_overrides)


'''Envelope'''
@dataclass
class Envelope:
    version: int
    flags: int
    expires_at: int
    request_id: bytes
    salt: bytes
    public_key: bytes
    iv: bytes
    ciphertext: bytes
    '''pack'''
    def pack(self) -> bytes:
        if len(self.request_id) != 16: raise ValueError("request_id must be 16 bytes")
        if len(self.salt) != 16: raise ValueError("salt must be 16 bytes")
        if len(self.public_key) != 65: raise ValueError("public_key must be 65 bytes")
        if len(self.iv) != 12: raise ValueError("iv must be 12 bytes")
        return b"".join([bytes([self.version]), bytes([self.flags]), SpotubeSecureClient.u32be(self.expires_at), self.request_id, self.salt, self.public_key, self.iv, SpotubeSecureClient.u32be(len(self.ciphertext)), self.ciphertext])
    '''unpack'''
    @classmethod
    def unpack(cls, data: bytes) -> "Envelope":
        if len(data) < 119: raise ValueError(f"Encrypted envelope is too short: {len(data)}")
        version, flags, expires_at, request_id = data[0], data[1], struct.unpack(">I", data[2:6])[0], data[6:22]
        salt, public_key, iv, cipher_len = data[22:38], data[38:103], data[103:115], struct.unpack(">I", data[115:119])[0]
        if len((ciphertext := data[119:])) != cipher_len: raise ValueError(f"Encrypted envelope length mismatch: expected {cipher_len}, got {len(ciphertext)}")
        return cls(version=version, flags=flags, expires_at=expires_at, request_id=request_id, salt=salt, public_key=public_key, iv=iv, ciphertext=ciphertext)


'''SpotubeSecureClient'''
class SpotubeSecureClient:
    def __init__(self, base_url: str = "https://spotubedl.com"):
        self.server_public_key = None
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.default_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Origin": self.base_url, "Referer": self.base_url + "/", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"}
    '''urljoin'''
    @staticmethod
    def urljoin(base_url: str, path: str) -> str:
        return urljoin(base_url + "/", path.lstrip("/"))
    '''pathfromurl'''
    @staticmethod
    def pathfromurl(url: str) -> str:
        return urlparse(url).path or "/"
    '''pathfromapi'''
    @staticmethod
    def pathfromapi(api_path: str) -> str:
        return urlparse(api_path).path or api_path or "/"
    '''randbytes'''
    @staticmethod
    def randbytes(n: int) -> bytes:
        return secrets.token_bytes(n)
    '''randompath'''
    @staticmethod
    def randompath() -> str:
        return f"/{SpotubeSecureClient.randbytes(6).hex()}/{SpotubeSecureClient.randbytes(8).hex()}/{SpotubeSecureClient.randbytes(6).hex()}"
    '''randomheadername'''
    @staticmethod
    def randomheadername(existing: set = None) -> str:
        existing = existing or set()
        while True:
            if (name := "x-" + SpotubeSecureClient.randbytes(8).hex()).lower() not in existing: return name
    '''b64encode'''
    @staticmethod
    def b64encode(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")
    '''b64decodetext'''
    @staticmethod
    def b64decodetext(text: str) -> bytes:
        return base64.b64decode(text.strip())
    '''u32be'''
    @staticmethod
    def u32be(n: int) -> bytes:
        return struct.pack(">I", n)
    '''jsoncompact'''
    @staticmethod
    def jsoncompact(obj) -> bytes:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    '''spdlenvinfo'''
    @staticmethod
    def spdlenvinfo(path: str, request_id: bytes) -> bytes:
        return b"spdl-env:1:" + path.encode("utf-8") + b"\x00" + request_id
    '''spdlreqinfo'''
    @staticmethod
    def spdlreqinfo(path: str, request_id: bytes) -> bytes:
        return b"spdl-req:1:" + path.encode("utf-8") + b"\x00" + request_id
    '''spdlaad'''
    @staticmethod
    def spdlaad(path: str, request_id: bytes, version: int, expires_at: int) -> bytes:
        return (b"spdl-aad:" + bytes([version]) + b"\x00\x00\x00\x00" + SpotubeSecureClient.u32be(expires_at) + path.encode("utf-8") + b"\x00" + request_id)
    '''spdlreqaad'''
    @staticmethod
    def spdlreqaad(path: str, request_id: bytes, version: int, expires_at: int) -> bytes:
        return (b"spdl-req-aad:" + bytes([version]) + b"\x00\x00\x00\x00" + SpotubeSecureClient.u32be(expires_at) + path.encode("utf-8") + b"\x00" + request_id)
    '''generatep256privatekey'''
    @staticmethod
    def generatep256privatekey():
        return ec.generate_private_key(ec.SECP256R1())
    '''exportrawpublickey'''
    @staticmethod
    def exportrawpublickey(private_key: EllipticCurvePrivateKey) -> bytes:
        return private_key.public_key().public_bytes(encoding=serialization.Encoding.X962, format=serialization.PublicFormat.UncompressedPoint)
    '''loadrawp256publickey'''
    @staticmethod
    def loadrawp256publickey(raw: bytes):
        if len(raw) != 65: raise ValueError(f"P-256 public key length should be 65, got {len(raw)}")
        return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
    '''ecdhsharedsecret'''
    @staticmethod
    def ecdhsharedsecret(private_key: EllipticCurvePrivateKey, peer_public_raw: bytes) -> bytes:
        peer_public_key = SpotubeSecureClient.loadrawp256publickey(peer_public_raw)
        return private_key.exchange(ec.ECDH(), peer_public_key)
    '''hkdfsha256key'''
    @staticmethod
    def hkdfsha256key(shared_secret: bytes, salt: bytes, info: bytes) -> bytes:
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(shared_secret)
    '''fetchserverpublickey'''
    def fetchserverpublickey(self, request_overrides: dict = None) -> bytes:
        if self.server_public_key is not None: return self.server_public_key
        url = SpotubeSecureClient.urljoin(self.base_url, SpotubeSecureClient.randompath())
        resp = self.session.get(url, headers={**self.default_headers, "Accept": "text/plain", "Cache-Control": "no-store", "Pragma": "no-cache"}, timeout=60, **(request_overrides or {}))
        if not resp.ok: raise RuntimeError(f"Secure request key failed: {resp.status_code}\n{resp.text[:500]}")
        if len((key := SpotubeSecureClient.b64decodetext(resp.text))) != 65: raise RuntimeError(f"Invalid secure request key length: {len(key)}")
        self.server_public_key = key
        return key
    '''encryptrequestenvelope'''
    def encryptrequestenvelope(self, post_path: str, plaintext: bytes, request_overrides: dict = None) -> bytes:
        server_public_key, request_private = self.fetchserverpublickey(request_overrides=request_overrides), SpotubeSecureClient.generatep256privatekey()
        request_public_raw = SpotubeSecureClient.exportrawpublickey(request_private)
        shared_secret = SpotubeSecureClient.ecdhsharedsecret(request_private, server_public_key)
        request_id, salt, iv, expires_at = SpotubeSecureClient.randbytes(16), SpotubeSecureClient.randbytes(16), SpotubeSecureClient.randbytes(12), int(time.time()) + 60
        aes_key = SpotubeSecureClient.hkdfsha256key(shared_secret=shared_secret, salt=salt, info=SpotubeSecureClient.spdlreqinfo(post_path, request_id))
        ciphertext = AESGCM(aes_key).encrypt(nonce=iv, data=plaintext, associated_data=SpotubeSecureClient.spdlreqaad(post_path, request_id, 1, expires_at))
        env = Envelope(version=1, flags=2, expires_at=expires_at, request_id=request_id, salt=salt, public_key=request_public_raw, iv=iv, ciphertext=ciphertext)
        return env.pack()
    '''decryptresponseenvelope'''
    def decryptresponseenvelope(self, response_private_key, response_path: str, encrypted_response: bytes) -> bytes:
        if (env := Envelope.unpack(encrypted_response)).version != 1: raise RuntimeError(f"Unsupported envelope version: {env.version}")
        aes_key = SpotubeSecureClient.hkdfsha256key(shared_secret=SpotubeSecureClient.ecdhsharedsecret(response_private_key, env.public_key), salt=env.salt, info=SpotubeSecureClient.spdlenvinfo(response_path, env.request_id))
        plaintext = AESGCM(aes_key).decrypt(nonce=env.iv, data=env.ciphertext, associated_data=SpotubeSecureClient.spdlaad(response_path, env.request_id, env.version, env.expires_at))
        return plaintext
    '''securepost'''
    def securepost(self, api_path: str, body: dict | None = None, request_overrides: dict = None) -> dict:
        api_path = SpotubeSecureClient.pathfromapi(api_path)
        post_url = SpotubeSecureClient.urljoin(self.base_url, (post_path := SpotubeSecureClient.randompath()))
        response_public_raw = SpotubeSecureClient.exportrawpublickey((response_private := SpotubeSecureClient.generatep256privatekey()))
        plaintext = SpotubeSecureClient.jsoncompact({"path": api_path, "method": "GET", "body": body})
        encrypted_body, random_header = self.encryptrequestenvelope(post_path, plaintext, request_overrides), SpotubeSecureClient.randomheadername()
        headers = {**self.default_headers, random_header: SpotubeSecureClient.b64encode(response_public_raw), "Content-Type": "application/octet-stream", "Accept": "application/octet-stream, application/json"}
        resp = self.session.post(post_url, headers=headers, data=encrypted_body, timeout=90, allow_redirects=True, **(request_overrides or {}))
        if "application/octet-stream" not in (resp.headers.get("Content-Type") or "").lower():
            try: parsed = resp.json() if resp.text else None
            except Exception: parsed = resp.text
            return {"ok": resp.ok, "status_code": resp.status_code, "content_type": resp.headers.get("Content-Type"), "data": parsed, "raw_text_preview": resp.text[:500]}
        plaintext_resp = self.decryptresponseenvelope(response_private_key=response_private, response_path=SpotubeSecureClient.pathfromurl(resp.url or post_url), encrypted_response=resp.content)
        return {"ok": resp.ok, "status_code": resp.status_code, "content_type": resp.headers.get("Content-Type"), "data": json.loads(decoded) if (decoded := plaintext_resp.decode("utf-8")) else None}
    '''gettrackmetadata'''
    def gettrackmetadata(self, spotify_track_id: str, request_overrides: dict = None) -> dict:
        return self.securepost("/api/info/track", {"id": spotify_track_id}, request_overrides)
    '''getfullmetadata'''
    def getfullmetadata(self, spotify_track_id: str, request_overrides: dict = None) -> dict:
        return self.securepost("/api/metadata", {"id": spotify_track_id}, request_overrides)
    '''search'''
    def search(self, query: str, request_overrides: dict = None) -> dict:
        return self.securepost("/api/info/search", {"query": query}, request_overrides)
    '''getdownloadinfobyvideoid'''
    def getdownloadinfobyvideoid(self, video_id: str, engine: str = "v1", fmt: str = "mp3", quality: str = "320", request_overrides: dict = None) -> dict:
        return self.securepost("/api/download", {"id": video_id, "engine": engine, "format": fmt, "quality": quality}, request_overrides)
    '''extractspotifytrackid'''
    @staticmethod
    def extractspotifytrackid(text: str) -> str:
        if re.fullmatch(r"[a-zA-Z0-9]{22}", (raw := text.strip())): return raw
        try:
            if "track" in (path_parts := urlparse(raw).path.split("/")) and (idx := path_parts.index("track")) + 1 < len(path_parts) and re.fullmatch(r"[a-zA-Z0-9]{22}", track_id := path_parts[idx + 1]): return track_id
        except Exception: pass
        if (m := re.search(r"[a-zA-Z0-9]{22}", raw)): return m.group(0)
        raise ValueError("Failed to extract a 22-character Spotify track ID from the input")
    '''collectstringvalues'''
    @staticmethod
    def collectstringvalues(obj):
        values = [s for v in obj.values() for s in SpotubeSecureClient.collectstringvalues(v)] if isinstance(obj, dict) else [s for item in obj for s in SpotubeSecureClient.collectstringvalues(item)] if isinstance(obj, list) else [obj] if isinstance(obj, str) else []
        return values
    '''findvaluesbykeys'''
    @staticmethod
    def findvaluesbykeys(obj, key_names):
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items(): (k in key_names and isinstance(v, str) and v.strip() and results.append(v.strip())); results.extend(SpotubeSecureClient.findvaluesbykeys(v, key_names))
        elif isinstance(obj, list):
            for item in obj: results.extend(SpotubeSecureClient.findvaluesbykeys(item, key_names))
        return results
    '''extractyoutubeidfromtext'''
    @staticmethod
    def extractyoutubeidfromtext(text: str):
        if not isinstance(text, str): return None
        if re.fullmatch(r"[a-zA-Z0-9_-]{11}", (text := text.strip())): return text
        patterns = [r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})", r"youtube\.com/embed/([a-zA-Z0-9_-]{11})", r"youtu\.be/([a-zA-Z0-9_-]{11})", r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})", r"[?&]v=([a-zA-Z0-9_-]{11})"]
        matches = (re.search(pattern, text) for pattern in patterns)
        return next((m.group(1) for m in matches if m), None)
    '''extractyoutubevideocandidates'''
    def extractyoutubevideocandidates(self, *responses) -> list[str]:
        likely_keys, candidates, unique = {"videoId", "video_id", "youtubeId", "youtube_id", "ytId", "yt_id", "sourceId", "source_id", "source", "youtube", "youtube_url", "youtubeUrl", "url"}, [], []
        for resp in responses:
            data = resp.get("data") if isinstance(resp, dict) else resp
            for value in SpotubeSecureClient.findvaluesbykeys(data, likely_keys):
                if (yt_id := SpotubeSecureClient.extractyoutubeidfromtext(value)): candidates.append(yt_id)
            for value in self.collectstringvalues(data):
                if (yt_id := SpotubeSecureClient.extractyoutubeidfromtext(value)): candidates.append(yt_id)
        for item in candidates: unique.append(item) if item not in unique else None
        return unique
    '''extractflagurl'''
    @staticmethod
    def extractflagurl(download_info: dict):
        if isinstance((data := download_info.get("data")), dict): return (data.get("url") or data.get("downloadUrl") or data.get("download_url") or data.get("link") or data.get("audioUrl") or data.get("audio_url"))
        if isinstance(data, str) and (data.startswith("http://") or data.startswith("https://")): return data
        return None
    '''getdownloadflagfromspotify'''
    def getdownloadflagfromspotify(self, spotify_input: str, engine: str = "v1", fmt: str = "mp3", quality: str = "320", request_overrides: dict = None) -> dict:
        spotify_id, last_error = self.extractspotifytrackid(spotify_input), None
        track_meta, full_meta = self.gettrackmetadata(spotify_id, request_overrides), self.getfullmetadata(spotify_id, request_overrides)
        for video_id in self.extractyoutubevideocandidates(track_meta, full_meta):
            if (flag_url := SpotubeSecureClient.extractflagurl((download_info := self.getdownloadinfobyvideoid(video_id, engine=engine, fmt=fmt, quality=quality, request_overrides=request_overrides)))):
                return {"spotify_id": spotify_id, "video_id": video_id, "download_info": download_info, "flag": flag_url, "track_meta": track_meta}
            if isinstance((data := download_info.get("data")), dict) and data.get("error"): last_error = data.get("error"); continue
            last_error = download_info
        raise RuntimeError(f"Failed to get a download link for all candidate YouTube IDs. Last error: {last_error}")