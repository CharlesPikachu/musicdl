'''
Function:
    Implementation of QobuzCommunityClient and TidalCommunityClient: https://spotbye.qzz.io/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import os
import re
import time
import json
import hmac
import queue
import base64
import secrets
import hashlib
import requests
import threading
import webbrowser
from pathlib import Path
from itertools import chain
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Any, Callable, Optional
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit


'''CommunitySessionRecord'''
@dataclass
class CommunitySessionRecord:
    install_id: str = ""
    session_id: str = ""
    session_secret: str = ""
    expires_at: str = ""


'''CommunityCooldownError'''
class CommunityCooldownError(RuntimeError):
    def __init__(self, service: str, message: str, retry_after: Optional[float] = None,) -> None:
        super().__init__(message)
        self.service = service
        self.retry_after = retry_after


'''CommunityClientBase'''
class CommunityClientBase:
    API_URL = ""
    SERVICE_NAME = "Community"
    SESSION_LOCK = threading.RLock()
    SESSION_RETRY_STATUS_CODES = {401, 428}
    TRANSIENT_STATUS_CODES = {429, 502, 504}
    VERIFY_BASE_URL = "https://verify.spotbye.qzz.io"
    def __init__(self, app_version: str = "7.2.0", platform: str = "desktop", session_file: Optional[str | Path] = None, request_timeout: float = 60, verification_timeout: float = 300, session_skew_seconds: int = 300, max_retries: int = 6, browser_opener: Optional[Callable[[str], Any]] = None,) -> None:
        self.platform = str(platform).strip() or "desktop"
        self.app_version = str(app_version).strip() or "unknown"
        self.max_retries = max(0, int(max_retries))
        self.request_timeout = float(request_timeout)
        self.verification_timeout = float(verification_timeout)
        self.session_skew = timedelta(seconds=int(session_skew_seconds))
        self.session_file = Path(session_file or Path.home() / ".musicdl" / "community_session.json")
        self.http = requests.Session()
        self.browser_opener = browser_opener or webbrowser.open
    '''requesttrack'''
    def requesttrack(self, track_id: str | int, quality: str | int, request_overrides: Optional[dict[str, Any]] = None,) -> dict[str, Any]:
        (resp := self.requestwithretry(track_id=self.normalizetrackid(track_id), quality=self.normalizequality(quality), request_overrides=request_overrides,)).raise_for_status()
        return self.parseresponse(resp.content)
    '''requesturl'''
    def requesturl(self, track_id: str | int, quality: str | int, request_overrides: Optional[dict[str, Any]] = None,) -> str:
        result = self.requesttrack(track_id, quality, request_overrides=request_overrides,)
        if not (url := str(result.get("url", "")).strip()): raise RuntimeError(f"No download URL in {self.SERVICE_NAME} response: {result!r}")
        return url
    '''requestwithretry'''
    def requestwithretry(self, track_id: str, quality: str, request_overrides: Optional[dict[str, Any]],) -> requests.Response:
        verification_retried, transient_attempt = False, 0
        while True:
            resp = self.senddownloadrequest(track_id, quality, request_overrides=request_overrides,)
            if resp.status_code == 503: message, retry_after = self.cooldowndetails(resp); resp.close(); raise CommunityCooldownError(self.SERVICE_NAME, message, retry_after,)
            if (resp.status_code in self.SESSION_RETRY_STATUS_CODES and not verification_retried): resp.close(); self.clearsessioncredentials(); verification_retried = True; continue
            if resp.status_code not in self.TRANSIENT_STATUS_CODES: return resp
            if transient_attempt >= self.max_retries: return resp
            wait = self.retrywaitseconds(resp, transient_attempt); resp.close(); transient_attempt += 1; time.sleep(wait)
    '''senddownloadrequest'''
    def senddownloadrequest(self, track_id: str, quality: str, request_overrides: Optional[dict[str, Any]] = None,) -> requests.Response:
        record, body = self.ensuresession(request_overrides=request_overrides), self.makerequestbody(track_id, quality)
        headers = self.makesignedheaders("POST", self.API_URL, body, record,)
        return self.http.post(self.API_URL, data=body, headers=headers, timeout=self.request_timeout, **(request_overrides or {}),)
    '''makerequestbody'''
    @staticmethod
    def makerequestbody(track_id: str, quality: str) -> bytes:
        return json.dumps({"id": str(track_id), "quality": str(quality)}, separators=(",", ":"), ensure_ascii=False,).encode("utf-8")
    '''makesignedheaders'''
    def makesignedheaders(self, method: str, url: str, body: bytes, record: CommunitySessionRecord,) -> dict[str, str]:
        timestamp = (now := datetime.now(timezone.utc).replace(microsecond=0)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        nonce, body_hash, window = secrets.token_hex(12), hashlib.sha256(body).hexdigest(), int(now.timestamp()) // 300
        rolling_key = hmac.new(record.session_secret.encode(), f"{window}:{record.session_id}".encode(), hashlib.sha256,).digest()
        signing_input = "\n".join(["SPOTIFLAC-HMAC-V1", method.upper(), urlsplit(url).path or "/", "", body_hash, timestamp, nonce, record.session_id, self.app_version, self.platform,]).encode()
        signature = (base64.urlsafe_b64encode(hmac.new(rolling_key, signing_input, hashlib.sha256,).digest()).decode("ascii").rstrip("="))
        return {
            "User-Agent": f"SpotiFLAC/{self.app_version}", "Accept": "application/json", "Content-Type": "application/json", "X-Sig-Session": record.session_id, "X-Sig-Timestamp": timestamp,
            "X-Sig-Nonce": nonce, "X-Sig-Body-SHA256": body_hash, "X-Sig-Signature": signature, "X-Sig-App-Version": self.app_version, "X-Sig-Platform": self.platform,
        }
    '''ensuresession'''
    def ensuresession(self, request_overrides: Optional[dict[str, Any]] = None,) -> CommunitySessionRecord:
        with self.SESSION_LOCK:
            if self.sessionvalid((record := self.loadsession())): return record
            grant = self.runbrowserverification(record, request_overrides=request_overrides,)
            return self.exchangegrant(record, grant, request_overrides=request_overrides,)
    '''clearsessioncredentials'''
    def clearsessioncredentials(self) -> None:
        with self.SESSION_LOCK: record = self.loadsession(); record.session_id = ""; record.session_secret = ""; record.expires_at = ""; self.savesession(record)
    '''loadsession'''
    def loadsession(self) -> CommunitySessionRecord:
        record = CommunitySessionRecord()
        if self.session_file.exists():
            try:
                data: dict = json.loads(self.session_file.read_text(encoding="utf-8"))
                record = CommunitySessionRecord(install_id=str(data.get("install_id", "")), session_id=str(data.get("session_id", "")), session_secret=str(data.get("session_secret", "")), expires_at=str(data.get("expires_at", "")),)
            except (OSError, ValueError, TypeError): record = CommunitySessionRecord()
        if not record.install_id: record.install_id = secrets.token_hex(16); self.savesession(record)
        return record
    '''savesession'''
    def savesession(self, record: CommunitySessionRecord) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.session_file.with_suffix(self.session_file.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8",)
        with suppress(Exception): os.chmod(self.session_file.parent, 0o700); os.chmod(temporary, 0o600)
        os.replace(temporary, self.session_file)
        with suppress(Exception): os.chmod(self.session_file, 0o600)
    '''sessionvalid'''
    def sessionvalid(self, record: CommunitySessionRecord) -> bool:
        if not all([record.session_id, record.session_secret, record.expires_at,]): return False
        try:
            expires_at = datetime.fromisoformat(record.expires_at.replace("Z", "+00:00"))
            if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
            return (expires_at.astimezone(timezone.utc) - datetime.now(timezone.utc)) > self.session_skew
        except (TypeError, ValueError): return False
    '''runbrowserverification'''
    def runbrowserverification(self, record: CommunitySessionRecord, request_overrides: Optional[dict[str, Any]] = None,) -> str:
        grant_queue: queue.Queue[str] = queue.Queue(maxsize=1); callback_state = secrets.token_hex(16)
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self) -> None:
                if (parsed := urlsplit(handler_self.path)).path != "/session-grant": handler_self.send_error(404); return
                state = (params := parse_qs(parsed.query)).get("state", [""])[0]
                if not hmac.compare_digest(state, callback_state): handler_self.send_error(400, "Invalid callback state"); return
                if not (grant := params.get("grant", [""])[0].strip()): handler_self.send_error(400, "Missing grant"); return
                html = ("<!doctype html><meta charset='utf-8'>" "<h2>Verification successful</h2>" "<p>You may close this page.</p>" "<script>setTimeout(()=>window.close(),700)</script>").encode()
                handler_self.send_response(200); handler_self.send_header("Content-Type", "text/html; charset=utf-8",)
                handler_self.send_header("Cache-Control", "no-store"); handler_self.send_header("Content-Length", str(len(html)),)
                handler_self.end_headers(); handler_self.wfile.write(html)
                with suppress(Exception): grant_queue.put_nowait(grant)
            def log_message(handler_self, fmt: str, *args: Any,) -> None: pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), CallbackHandler,)
        (thread := threading.Thread(target=server.serve_forever, daemon=True,)).start()
        callback_url = (f"http://127.0.0.1:{server.server_address[1]}" f"/session-grant?state={callback_state}")
        try:
            (resp := self.http.get(f"{self.VERIFY_BASE_URL}/bootstrap", params={"install_id": record.install_id, "app_version": self.app_version, "platform": self.platform,}, timeout=15, **dict(request_overrides or {}),)).raise_for_status(); data: dict = resp.json(); resp.close()
            if (parsed_challenge := urlsplit(str(data.get("challenge_url", "")).strip())).scheme != "https": raise RuntimeError("Invalid verification challenge URL")
            pairs = [(k, v) for k, v in parse_qsl(parsed_challenge.query, keep_blank_values=True,) if k != "cb"]
            pairs.append(("cb", callback_url)); final_url = urlunsplit(parsed_challenge._replace(query=urlencode(pairs)))
            if not self.browser_opener(final_url): print("Open this URL manually:\n" + final_url)
            try: return grant_queue.get(timeout=self.verification_timeout)
            except queue.Empty as exc: raise RuntimeError("Timed out waiting for browser verification") from exc
        finally: server.shutdown(); server.server_close(); thread.join(timeout=1)
    '''exchangegrant'''
    def exchangegrant(self, record: CommunitySessionRecord, grant: str, request_overrides: Optional[dict[str, Any]] = None,) -> CommunitySessionRecord:
        (resp := self.http.post(f"{self.VERIFY_BASE_URL}/session/exchange", json={"grant": grant, "install_id": record.install_id, "app_version": self.app_version, "platform": self.platform,}, timeout=15, **dict(request_overrides or {}),)).raise_for_status(); data: dict = resp.json(); resp.close()
        record.session_id = str(data.get("session_id", "")).strip()
        record.session_secret = str(data.get("session_secret", "")).strip()
        record.expires_at = str(data.get("expires_at", "")).strip()
        if not all([record.session_id, record.session_secret, record.expires_at,]): raise RuntimeError("Session exchange response is incomplete")
        self.savesession(record)
        return record
    '''normalizetrackid'''
    @classmethod
    def normalizetrackid(cls, track_id: str | int) -> str:
        if (value := str(track_id).strip()).startswith(("http://", "https://")):
            parts = [item for item in urlsplit(value).path.split("/") if item]
            if "track" in (lower := [item.lower() for item in parts]):
                if (index := lower.index("track")) + 1 < len(parts): value = parts[index + 1]
        if not value.isdigit(): raise ValueError(f"Invalid {cls.SERVICE_NAME} track ID: {track_id!r}")
        return value
    '''retrywaitseconds'''
    @staticmethod
    def retrywaitseconds(resp: requests.Response, attempt: int,) -> float:
        if resp.status_code != 429: return float((attempt + 1) * 5)
        if (retry_after := resp.headers.get("Retry-After", "").strip()):
            try: return max(0.0, float(retry_after)) + 0.25
            except ValueError: pass
        if (reset := resp.headers.get("X-RateLimit-Reset", "").strip()):
            try:
                if (wait := int(reset) - int(time.time())) > 0: return float(wait) + 0.25
            except ValueError: pass
        return 30.0
    '''cooldowndetails'''
    def cooldowndetails(self, resp: requests.Response,) -> tuple[str, Optional[float]]:
        retry_after, raw, message = None, resp.headers.get("Retry-After", "").strip(), ""
        with suppress(Exception): raw and (retry_after := max(0.0, float(raw)))
        with suppress(Exception): message = str(getattr((data := resp.json()), "get", lambda *_: "")("error", "")).strip()
        if not message: minutes = max(1, int(((retry_after or 30) + 59) // 60),); message = ("The server is taking a scheduled short break. " f"Please try again in about {minutes} minute(s).")
        return message, retry_after
    '''normalizequality'''
    @staticmethod
    def normalizequality(quality: str | int) -> str:
        raise NotImplementedError
    '''parseresponse'''
    def parseresponse(self, body: bytes) -> dict[str, Any]:
        raise NotImplementedError
    '''close'''
    def close(self) -> None:
        self.http.close()
    '''enter'''
    def __enter__(self) -> "CommunityClientBase":
        return self
    '''exit'''
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any,) -> None:
        self.close()


'''QobuzCommunityClient'''
class QobuzCommunityClient(CommunityClientBase):
    SERVICE_NAME = "Qobuz"
    API_URL = "https://qbz-oss.spotbye.qzz.io/api/dl"
    URL_PATTERN = re.compile(r"https?://[^\s\"'<>\\)]+")
    URL_KEYS = ("download_url", "url", "play_url", "stream_url", "link", "file",)
    '''requesttrack'''
    def requesttrack(self, track_id: str | int, quality: str | int = "27", request_overrides: Optional[dict[str, Any]] = None,) -> dict[str, Any]:
        return super().requesttrack(track_id, quality, request_overrides=request_overrides,)
    '''requesturl'''
    def requesturl(self, track_id: str | int, quality: str | int = "27", request_overrides: Optional[dict[str, Any]] = None,) -> str:
        return super().requesturl(track_id, quality, request_overrides=request_overrides,)
    '''normalizequality'''
    @staticmethod
    def normalizequality(quality: str | int) -> str:
        if str(quality).strip().upper() in {"27", "7", "24", "HI_RES", "HI_RES_LOSSLESS",}: return "24"
        return "16"
    '''parseresponse'''
    def parseresponse(self, body: bytes) -> dict[str, Any]:
        if not (url := self.extractstreamingurl(body)): preview = body.decode("utf-8", errors="replace")[:500]; raise RuntimeError(f"No streamable URL in Qobuz response: {preview!r}")
        with suppress(Exception): data = {}; data = json.loads(body)
        result = dict(data) if isinstance(data, dict) else {"response": data}
        result["url"] = url
        return result
    '''extractstreamingurl'''
    @classmethod
    def extractstreamingurl(cls, body: bytes | str) -> str:
        if not (text := (body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)).strip()): return ""
        with suppress(Exception): payload = None; payload = json.loads(text)
        if payload is not None and (found := cls.findurl(payload)): return found
        open_index, close_index = text.find("("), text.rfind(")")
        if open_index >= 0 and close_index > open_index + 1:
            if (found := cls.extractstreamingurl(text[open_index + 1 : close_index])): return found
        for match in cls.URL_PATTERN.findall(text):
            if cls.validurl((candidate := str(match).replace(r"\/", "/"))): return candidate
        return ""
    '''findurl'''
    @classmethod
    def findurl(cls, value: Any | dict) -> str:
        if isinstance(value, str): candidate = value.strip().replace(r"\/", "/"); return candidate if cls.validurl(candidate) else ""
        if isinstance(value, list): return next((found for item in value if (found := cls.findurl(item))), "")
        return next((found for item in chain((value[key] for key in cls.URL_KEYS if key in value), value.values()) if (found := cls.findurl(item))), "")
    '''validurl'''
    @staticmethod
    def validurl(value: str) -> bool:
        return (parsed := urlsplit(value)).scheme in {"http", "https"} and bool(parsed.netloc)


'''TidalCommunityClient'''
class TidalCommunityClient(CommunityClientBase):
    SERVICE_NAME = "Tidal"
    API_URL = "https://tdl-oss.spotbye.qzz.io/api/dl"
    '''requesttrack'''
    def requesttrack(self, track_id: str | int, quality: str | int = "24", request_overrides: Optional[dict[str, Any]] = None,) -> dict[str, Any]:
        return super().requesttrack(track_id, quality, request_overrides=request_overrides,)
    '''requesturl'''
    def requesturl(self, track_id: str | int, quality: str | int = "24", request_overrides: Optional[dict[str, Any]] = None,) -> str:
        return super().requesturl(track_id, quality, request_overrides=request_overrides,)
    '''normalizequality'''
    @staticmethod
    def normalizequality(quality: str | int) -> str:
        if (value := str(quality).strip().upper()) in {"ATMOS", "DOLBY", "EAC3", "EAC3_JOC", "DOLBY_ATMOS"}: return "atmos"
        if value in {"HI_RES_LOSSLESS", "HI_RES", "24"}: return "24"
        return "16"
    '''parseresponse'''
    def parseresponse(self, body: bytes) -> dict[str, Any]:
        try: data = json.loads(body)
        except ValueError as exc: preview = body.decode("utf-8", errors="replace")[:500]; raise RuntimeError(f"Tidal returned invalid JSON: {preview!r}") from exc
        if not isinstance(data, dict): raise RuntimeError(f"Unexpected Tidal response: {data!r}")
        result = dict(data); result["quality"] = str(result.get("quality", "")).strip()
        result["url"] = str(result.get("url", "")).strip(); result["lyric"] = str(result.get("lyric", "") or "")
        if not result["url"]:
            if (error := str(result.get("error", "")).strip()): raise RuntimeError(f"Tidal API error: {error}")
            raise RuntimeError(f"No download URL in Tidal response: {result!r}")
        return result