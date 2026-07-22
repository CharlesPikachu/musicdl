'''
Function:
    Implementation of QobuzMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import json
import hmac
import time
import queue
import base64
import hashlib
import secrets
import binascii
import requests
import threading
import webbrowser
from pathlib import Path
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple
from cryptography.hazmat.primitives import hashes
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from urllib.parse import urljoin, urlsplit, parse_qs, parse_qsl, urlencode, urlunsplit


'''CommunitySessionRecord'''
@dataclass
class CommunitySessionRecord:
    install_id: str = ""
    session_id: str = ""
    session_secret: str = ""
    expires_at: str = ""


'''QobuzCommunityClient'''
class QobuzCommunityClient:
    API_URL = "https://qbz-oss.spotbye.qzz.io/api/dl"
    VERIFY_BASE_URL = "https://verify.spotbye.qzz.io"
    def __init__(self, app_version: str = "7.2.0", platform: str = "desktop", session_file: Optional[str | Path] = None, request_timeout: float = 30, verification_timeout: float = 300, session_skew_seconds: int = 300,) -> None:
        self.platform = str(platform).strip()
        self.request_timeout = request_timeout
        self.app_version = str(app_version).strip()
        self.verification_timeout = verification_timeout
        self.session_skew = timedelta(seconds=session_skew_seconds)
        self.session_file = Path(session_file or (Path.home() / ".musicdl" / "qobuz_community_client_session.json"))
        self.http = requests.Session()
    '''requesttrack'''
    def requesttrack(self, track_id: str | int, quality: str | int = "24", request_overrides: dict = None) -> dict[str, Any]:
        normalized_track_id, community_quality, request_overrides = self.normalizetrackid(track_id), quality, request_overrides or {}
        resp = self.senddownloadrequest(track_id=normalized_track_id, community_quality=community_quality, request_overrides=request_overrides)
        if resp.status_code in (401, 428): resp.close(); self.clearsessioncredentials(); resp = self.senddownloadrequest(track_id=normalized_track_id, community_quality=community_quality, request_overrides=request_overrides)
        resp.raise_for_status()
        return resp.json()
    '''clearsessioncredentials'''
    def clearsessioncredentials(self) -> None:
        record = self.loadsession()
        record.session_id = ""
        record.session_secret = ""
        record.expires_at = ""
        self.savesession(record)
    '''close'''
    def close(self) -> None:
        self.http.close()
    '''enter'''
    def __enter__(self) -> "QobuzCommunityClient":
        return self
    '''exit'''
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any,) -> None:
        self.close()
    '''senddownloadrequest'''
    def senddownloadrequest(self, track_id: str, community_quality: str, request_overrides: dict = None) -> requests.Response:
        record = self.ensuresession(); body = self.makerequestbody(track_id=track_id, community_quality=community_quality,)
        headers = self.makesignedheaders(method="POST", url=self.API_URL, body=body, record=record,)
        return self.http.post(self.API_URL, data=body, headers=headers, timeout=self.request_timeout, **(request_overrides or {}))
    '''makerequestbody'''
    @staticmethod
    def makerequestbody(track_id: str, community_quality: str,) -> bytes:
        payload = {"id": track_id, "quality": community_quality,}
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False,).encode("utf-8")
    '''makesignedheaders'''
    def makesignedheaders(self, method: str, url: str, body: bytes, record: CommunitySessionRecord,) -> dict[str, str]:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        timestamp, nonce, body_hash, rolling_window = now.strftime("%Y-%m-%dT%H:%M:%S.000Z"), secrets.token_hex(12), hashlib.sha256(body).hexdigest(), int(now.timestamp()) // 300
        rolling_input = (f"{rolling_window}:" f"{record.session_id}").encode("utf-8")
        rolling_key = hmac.new(record.session_secret.encode("utf-8"), rolling_input, hashlib.sha256,).digest()
        request_path = (parsed_url := urlsplit(url)).path or "/"; request_query = parsed_url.query
        signing_input = "\n".join(["SPOTIFLAC-HMAC-V1", method.upper(), request_path, request_query, body_hash, timestamp, nonce, record.session_id, self.app_version, self.platform,]).encode("utf-8")
        signature_bytes = hmac.new(rolling_key, signing_input, hashlib.sha256,).digest()
        signature = (base64.urlsafe_b64encode(signature_bytes).decode("ascii").rstrip("="))
        return {
            "User-Agent": f"SpotiFLAC/{self.app_version}", "Accept": "application/json", "Content-Type": "application/json", "X-Sig-Session": record.session_id, "X-Sig-Timestamp": timestamp,
            "X-Sig-Nonce": nonce, "X-Sig-Body-SHA256": body_hash, "X-Sig-Signature": signature, "X-Sig-App-Version": self.app_version, "X-Sig-Platform": self.platform,
        }
    '''ensuresession'''
    def ensuresession(self, request_overrides: dict = None) -> CommunitySessionRecord:
        if self.sessionvalid((record := self.loadsession())): return record
        grant = self.runbrowserverification(record, request_overrides=request_overrides)
        return self.exchangegrant(record=record, grant=grant, request_overrides=request_overrides)
    '''loadsession'''
    def loadsession(self,) -> CommunitySessionRecord:
        record = CommunitySessionRecord()
        if self.session_file.exists():
            try:
                data: dict = json.loads(self.session_file.read_text(encoding="utf-8"))
                record = CommunitySessionRecord(install_id=str(data.get("install_id", "")), session_id=str(data.get("session_id", "")), session_secret=str(data.get("session_secret", "")), expires_at=str(data.get("expires_at", "")),)
            except Exception: record = CommunitySessionRecord()
        if not record.install_id: record.install_id = secrets.token_hex(16); self.savesession(record)
        return record
    '''savesession'''
    def savesession(self, record: CommunitySessionRecord,) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True,)
        temporary_file = self.session_file.with_suffix(self.session_file.suffix + ".tmp")
        temporary_file.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2,), encoding="utf-8",)
        try: os.chmod(self.session_file.parent, 0o700,); os.chmod(temporary_file, 0o600,)
        except OSError: pass
        os.replace(temporary_file, self.session_file,)
        try: os.chmod(self.session_file, 0o600,)
        except OSError: pass
    '''sessionvalid'''
    def sessionvalid(self, record: CommunitySessionRecord,) -> bool:
        if not all([record.session_id, record.session_secret, record.expires_at,]): return False
        try:
            expires_at = datetime.fromisoformat(record.expires_at.replace("Z", "+00:00",))
            if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
            remaining = (expires_at.astimezone(timezone.utc) - datetime.now(timezone.utc))
            return remaining > self.session_skew
        except (TypeError, ValueError): return False
    '''runbrowserverification'''
    def runbrowserverification(self, record: CommunitySessionRecord, request_overrides: dict = None) -> str:
        grant_queue: queue.Queue[str] = queue.Queue(maxsize=1); callback_state = secrets.token_hex(16)
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self) -> None:
                if (parsed := urlsplit(handler_self.path)).path != "/session-grant": handler_self.send_error(404); return
                returned_state = (params := parse_qs(parsed.query)).get("state", [""],)[0]
                if not hmac.compare_digest(returned_state, callback_state,): handler_self.send_error(400, "Invalid callback state",); return
                if not (grant := params.get("grant", [""],)[0].strip()): handler_self.send_error(400, "Missing grant",); return
                html = ("<!doctype html>" "<meta charset='utf-8'>" "<h2>Verification successful</h2>" "<p>You may close this page.</p>" "<script>" "setTimeout(() => window.close(), 700);" "</script>").encode("utf-8")
                handler_self.send_response(200); handler_self.send_header("Content-Type", "text/html; charset=utf-8",); handler_self.send_header("Cache-Control", "no-store",)
                handler_self.send_header("Content-Length", str(len(html)),); handler_self.end_headers(); handler_self.wfile.write(html)
                try: grant_queue.put_nowait(grant)
                except queue.Full: pass
            def log_message(handler_self, fmt: str, *args: Any,) -> None: pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), CallbackHandler,)
        (server_thread := threading.Thread(target=server.serve_forever, daemon=True,)).start()
        callback_url = (f"http://127.0.0.1:" f"{server.server_address[1]}" f"/session-grant" f"?state={callback_state}")
        try:
            (bootstrap_resp := self.http.get(f"{self.VERIFY_BASE_URL}/bootstrap", params={"install_id": record.install_id, "app_version": self.app_version, "platform": self.platform,}, headers={"User-Agent": "Go-http-client/1.1",}, timeout=15, **(request_overrides or {}))).raise_for_status()
            bootstrap_data: dict = bootstrap_resp.json(); challenge_url = str(bootstrap_data.get("challenge_url", "",)).strip()
            if (parsed_challenge := urlsplit(challenge_url)).scheme != "https": raise RuntimeError("bootstrap returns invalid challenge_url")
            query_pairs = [(key, value) for key, value in parse_qsl(parsed_challenge.query, keep_blank_values=True,) if key != "cb"]; query_pairs.append(("cb", callback_url))
            opened = webbrowser.open((final_challenge_url := (urlunsplit(parsed_challenge._replace(query=urlencode(query_pairs))))))
            if not opened: print(f'Your browser did not open automatically. Please copy the URL "{final_challenge_url}" and open it manually.')
            try: grant = grant_queue.get(timeout=self.verification_timeout)
            except queue.Empty as exc: raise RuntimeError("timeout for browser verification") from exc
            return grant
        finally: server.shutdown(); server.server_close(); server_thread.join(timeout=1)
    '''exchangegrant'''
    def exchangegrant(self, record: CommunitySessionRecord, grant: str, request_overrides: dict = None) -> CommunitySessionRecord:
        (resp := self.http.post(f"{self.VERIFY_BASE_URL}/session/exchange", json={"grant": grant, "install_id": record.install_id, "app_version": self.app_version, "platform": self.platform,}, headers={"User-Agent": "Go-http-client/1.1",}, timeout=15, **(request_overrides or {}))).raise_for_status()
        data: dict = resp.json(); record.session_id = str(data.get("session_id", "")).strip()
        record.session_secret = str(data.get("session_secret", "")).strip(); record.expires_at = str(data.get("expires_at", "")).strip()
        if not all([record.session_id, record.session_secret, record.expires_at,]): raise RuntimeError("session exchange errors")
        self.savesession(record)
        return record
    '''normalizetrackid'''
    @staticmethod
    def normalizetrackid(track_id: str | int,) -> str:
        if (value := str(track_id).strip()).startswith(("http://", "https://",)):
            parts = [item for item in urlsplit(value).path.split("/") if item]
            if "track" in parts and (index := parts.index("track")) + 1 < len(parts): value = parts[index + 1]
        if not value.isdigit(): raise ValueError(f"Invalid Qobuz track ID: {track_id!r}")
        return value


'''ArcodClient'''
class ArcodClient:
    def __init__(self, base_url: str = "https://arcod.xyz", timeout: int = 30) -> None:
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.supabase_url: Optional[str] = None
        self.access_token: Optional[str] = None
        self.supabase_anon_key: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "Referer": self.base_url + "/"})
    '''joinpathtourl'''
    def joinpathtourl(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))
    '''extractscripturls'''
    def extractscripturls(self, html_text: str) -> list[str]:
        urls: list[str] = []
        for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html_text):
            if ".js" not in src: continue
            urls.append(urljoin(self.base_url + "/", src))
        return list(dict.fromkeys(urls))
    '''discoversupabaseconfig'''
    def discoversupabaseconfig(self, request_overrides: dict = None) -> Tuple[str, str]:
        html_text = self.session.get(self.base_url + "/", timeout=self.timeout, **(request_overrides := request_overrides or {})).text
        script_urls, supabase_url_re, anon_key_re = self.extractscripturls(html_text), re.compile(r"https://[a-z0-9]+\.supabase\.co"), re.compile(r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
        found_url: Optional[str] = None; found_key: Optional[str] = None
        for script_url in script_urls:
            with suppress(Exception): text = ''; text = self.session.get(script_url, timeout=self.timeout, **request_overrides).text
            found_url = m_url.group(0) if found_url is None and (m_url := supabase_url_re.search(text)) else found_url
            found_key = m_key.group(0) if found_key is None and (m_key := anon_key_re.search(text)) else found_key
            if found_url and found_key: break
        self.supabase_url, self.supabase_anon_key = found_url, found_key
        return found_url, found_key
    '''checkmigrated'''
    def checkmigrated(self, email: str, request_overrides: dict = None) -> Dict[str, Any]:
        (resp := self.session.post(self.joinpathtourl("/api/auth/check-migrated"), json={"email": email}, headers={"Content-Type": "application/json", "Origin": self.base_url}, timeout=self.timeout, **(request_overrides or {}))).raise_for_status()
        return resp.json()
    '''login'''
    def login(self, email: str, password: str, request_overrides: dict = None) -> str:
        if self.access_token: return self.access_token
        if not self.supabase_url or not self.supabase_anon_key: self.discoversupabaseconfig(request_overrides=request_overrides)
        assert self.supabase_url is not None and self.supabase_anon_key is not None
        self.checkmigrated(email, request_overrides=request_overrides); url = self.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password"
        headers = {"apikey": self.supabase_anon_key, "Content-Type": "application/json;charset=UTF-8", "Origin": self.base_url, "Referer": self.base_url + "/", "x-client-info": "supabase-js-web/2.99.3", "x-supabase-api-version": "2024-01-01"}
        (resp := self.session.post(url, headers=headers, json={"email": email, "password": password, "gotrue_meta_security": {}}, timeout=self.timeout, **(request_overrides or {}))).raise_for_status()
        self.access_token = (resp.json() or {}).get("access_token")
        return self.access_token
    '''constructapiheaders'''
    def constructapiheaders(self, *, country: Optional[str] = None, download_token: Optional[str] = None, access_token: Optional[str] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}; token = access_token or self.access_token
        if country: headers["Token-Country"] = country
        if token: headers["Authorization"] = token
        if download_token: headers["X-Download-Token"] = download_token
        return headers
    '''gettrack'''
    def gettrack(self, track_id: str, *, country: Optional[str] = None, request_overrides: dict = None) -> Dict[str, Any]:
        (resp := self.session.get(self.joinpathtourl("/api/get-track"), params={"track_id": track_id}, headers=self.constructapiheaders(country=country), timeout=self.timeout, **(request_overrides or {}))).raise_for_status()
        return resp.json()["data"]
    '''buildtrackdownloadpayload'''
    def buildtrackdownloadpayload(self, track: Dict[str, Any], *, quality: int = 27, output_format: str = "FLAC", bitrate: int = 320, embed_lyrics: bool = True, lyrics_mode: str = "embed", download_booklet: bool = False, attach_cover: bool = False, country: Optional[str] = None) -> Dict[str, Any]:
        album_image = (album := track.get("album") or {}).get("image") or {}
        album_artist, performer = album.get("artist") or {}, track.get("performer") or {}
        album_id, track_id = str(album.get("id") or album.get("upc") or ""), str(track.get("id") or track.get("qobuz_id") or "")
        artist_name, artist_id = album_artist.get("name") or performer.get("name") or "Unknown Artist", str(album_artist.get("id") or performer.get("id") or "")
        album_title, cover_url = album.get("title") or "Unknown Album", album_image.get("large") or album_image.get("small") or ""
        release_date = album.get("release_date_original") or track.get("release_date_original")
        payload: Dict[str, Any] = {"albumId": album_id, "trackId": track_id, "albumTitle": album_title, "artistName": artist_name, "artistId": artist_id, "coverUrl": cover_url, "releaseDate": release_date, "tracksCount": 1, "quality": quality, "format": output_format, "bitrate": bitrate, "embedLyrics": embed_lyrics, "lyricsMode": lyrics_mode, "downloadBooklet": download_booklet, "attachCover": attach_cover, "zipName": "{artists} - {name}", "trackName": "{track} - {name}"}
        if country: payload["country"] = country
        return payload
    '''createdownload'''
    def createdownload(self, payload: Dict[str, Any], *, country: Optional[str] = None, request_overrides: dict = None) -> Tuple[str, Optional[str]]:
        (resp := self.session.post(self.joinpathtourl("/api/v2/downloads"), json=payload, headers={"Content-Type": "application/json", "Origin": self.base_url, **self.constructapiheaders(country=country)}, timeout=self.timeout, **(request_overrides or {}))).raise_for_status()
        return resp.json()['id'], resp.json()['accessToken']
    '''getdownloadstatus'''
    def getdownloadstatus(self, download_id: str, *, download_token: Optional[str] = None, request_overrides: dict = None) -> Dict[str, Any]:
        (resp := self.session.get(self.joinpathtourl(f"/api/v2/downloads/{download_id}"), headers=self.constructapiheaders(download_token=download_token), timeout=self.timeout, **(request_overrides or {}))).raise_for_status()
        return resp.json()
    '''polluntilcompleted'''
    def polluntilcompleted(self, download_id: str, *, download_token: Optional[str] = None, interval: float = 2.0, max_polls: int = 300, request_overrides: dict = None) -> Dict[str, Any]:
        last: Dict[str, Any] = {}
        for _ in range(max_polls):
            last = self.getdownloadstatus(download_id, download_token=download_token, request_overrides=request_overrides)
            if (status := last.get("status")) == "completed": return last
            if status in {"failed", "cancelled"}: raise RuntimeError(f"Download job ended with {status}: {last.get('error')}")
            time.sleep(interval)
        raise RuntimeError(f"Timed out waiting for completion; last status: {last}")
    '''getfreshdownloadurl'''
    def getfreshdownloadurl(self, download_id: str, *, download_token: Optional[str] = None, request_overrides: dict = None) -> Dict[str, Any]:
        (resp := self.session.post(self.joinpathtourl(f"/api/v2/downloads/{download_id}/url"), json={}, headers={"Content-Type": "application/json", "Origin": self.base_url, **self.constructapiheaders(download_token=download_token)}, timeout=self.timeout, **(request_overrides or {}))).raise_for_status()
        return resp.json()


'''QobuzMusicClientUtils'''
class QobuzMusicClientUtils():
    SEARCH_APP_ID = "712109809"
    SEARCH_APP_SECRET = "589be88e4538daea11f509d29e4a23b1"
    PARSE_APP_ID = "798273057"
    PARSE_APP_SECRET = "abb21364945c0583309667d13ca3d93a"
    MUSIC_QUALITIES = (27, 7, 6, 5)
    BASE_URL = "https://www.qobuz.com/api.json/0.2"
    get_token_func = lambda cookies, *keys: next((cookies.get(k) for k in keys if cookies.get(k)), None)
    '''initsearchappid'''
    @staticmethod
    def initsearchappid(session: requests.Session, headers: dict, cookies: dict, request_overrides: dict = None) -> str:
        if (QobuzMusicClientUtils.SEARCH_APP_ID not in {"712109809"} and QobuzMusicClientUtils.SEARCH_APP_SECRET not in {"589be88e4538daea11f509d29e4a23b1"}): return QobuzMusicClientUtils.SEARCH_APP_ID, QobuzMusicClientUtils.SEARCH_APP_SECRET
        (resp := session.get("https://open.qobuz.com/track/1", headers=headers, cookies=cookies, **(request_overrides := request_overrides or {}))).raise_for_status()
        (resp := session.get(urljoin("https://open.qobuz.com", re.search(r'<script[^>]+src="([^"]+/js/main\.js|/resources/[^"]+/js/main\.js)"', resp.text).group(1)), headers=headers, cookies=cookies, **request_overrides)).raise_for_status()
        QobuzMusicClientUtils.SEARCH_APP_ID = re.search(r'app_id:"(?P<app_id>\d{9})",app_secret:"(?P<app_secret>[a-f0-9]{32})"', resp.text).group(1)
        QobuzMusicClientUtils.SEARCH_APP_SECRET = re.search(r'app_id:"(?P<app_id>\d{9})",app_secret:"(?P<app_secret>[a-f0-9]{32})"', resp.text).group(2)
        return QobuzMusicClientUtils.SEARCH_APP_ID, QobuzMusicClientUtils.SEARCH_APP_SECRET
    '''initparseappid'''
    @staticmethod
    def initparseappid(session: requests.Session, headers: dict, cookies: dict, request_overrides: dict = None) -> str:
        if (QobuzMusicClientUtils.PARSE_APP_ID not in {"798273057"}): return QobuzMusicClientUtils.PARSE_APP_ID
        (resp := session.get("https://play.qobuz.com/login", headers=headers, cookies=cookies, **(request_overrides := request_overrides or {}))).raise_for_status()
        (resp := session.get(urljoin("https://play.qobuz.com", re.search(r'<script src="(/resources/[^"]+/bundle\.js)"></script>', resp.text).group(1)), headers=headers, cookies=cookies, **request_overrides)).raise_for_status()
        QobuzMusicClientUtils.PARSE_APP_ID = re.search(r'production:\{api:\{appId:"(\d{9})"', resp.text).group(1)
        return QobuzMusicClientUtils.PARSE_APP_ID
    '''getrequestsig'''
    @staticmethod
    def getrequestsig(method: str, args: dict, request_ts: str, secret: str, ignore_keys: dict = None) -> str:
        normalized_method, ignore_keys = method.strip("/").replace("/", ""), ignore_keys or {"app_id", "request_ts", "request_sig"}
        sorted_args_str = "".join(f"{k}{v}" for k, v in sorted(args.items()) if k not in ignore_keys)
        req_id = f"{normalized_method}{sorted_args_str}{request_ts}{secret}"
        return hashlib.md5(req_id.encode('utf-8')).hexdigest()
    '''startsession'''
    @staticmethod
    def startsession(session: requests.Session, headers: dict, cookies: dict, request_overrides: dict = None) -> dict:
        data = {"profile": "qbz-1", "request_ts": (request_ts := str(int(time.time()))), "request_sig": QobuzMusicClientUtils.getrequestsig("sessionstart", {"profile": "qbz-1"}, request_ts, QobuzMusicClientUtils.PARSE_APP_SECRET)}
        (resp := session.post(f"{QobuzMusicClientUtils.BASE_URL}/session/start", headers=headers, cookies=cookies, data=data, **(request_overrides := request_overrides or {}))).raise_for_status()
        return resp.json()
    '''gettrackinfo'''
    @staticmethod
    def gettrackinfo(session: requests.Session, headers: dict, cookies: dict, track_id: str, quality: str, request_overrides: dict = None) -> dict:
        params = {"request_ts": (request_ts := str(int(time.time()))), "request_sig": QobuzMusicClientUtils.getrequestsig("fileurl", {"format_id": str(quality), "intent": "stream", "track_id": str(track_id)}, request_ts, QobuzMusicClientUtils.PARSE_APP_SECRET), "track_id": track_id, "format_id": quality, "intent": "stream"}
        (resp := session.get(f"{QobuzMusicClientUtils.BASE_URL}/file/url", headers=headers, params=params, cookies=cookies, **(request_overrides := request_overrides or {}))).raise_for_status()
        return resp.json()
    '''derivesessionkey'''
    @staticmethod
    def derivesessionkey(infos: str) -> bytes:
        salt = base64.urlsafe_b64decode((parts := infos.split('.'))[0] + "=" * ((4 - len(parts[0]) % 4) % 4))
        info = base64.urlsafe_b64decode(parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4))
        hkdf = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=info, backend=default_backend())
        return hkdf.derive(binascii.unhexlify(QobuzMusicClientUtils.PARSE_APP_SECRET))
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