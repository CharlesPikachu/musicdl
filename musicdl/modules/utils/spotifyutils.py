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
import base64
import hashlib
import requests
import json_repair
from typing import Dict, List, Tuple
from .misc import resp2json, safeextractfromdict


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
                chunk_url = f"https://open.spotifycdn.com/cdn/build/web-player/{chunk}"
                try: raw_hashes += session.get(chunk_url, headers=SpotifyMusicClientUtils.COMMON_HEADERS, **request_overrides).text
                except Exception: pass
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