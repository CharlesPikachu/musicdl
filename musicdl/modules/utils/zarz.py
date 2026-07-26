'''
Function:
    Implementation of SpotiFLAC-Mobile Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import sys
import hmac
import json
import time
import base64
import shutil
import secrets
import hashlib
import requests
import tempfile
import plistlib
import threading
import webbrowser
import subprocess
import urllib.parse
from typing import Any
from pathlib import Path
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone


'''capturegrantwindows'''
def capturegrantwindows(helper: Path, output: Path):
    import winreg; root = r"Software\Classes\spotiflac"; command_key = root + r"\shell\open\command"
    def read(path, name=""):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key: return winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return None
    previous = (read(root), read(root, "URL Protocol"), read(command_key))
    if (pythonw := (python := Path(sys.executable)).with_name("pythonw.exe")).exists(): python = pythonw
    command = f'"{python}" "{helper}" --receive "%1" --output "{output}"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root) as key: winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:SpotiFLAC Callback"); winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key) as key: winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
    def delete(path):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WRITE,) as key:
                while True:
                    try: child = winreg.EnumKey(key, 0)
                    except OSError: break
                    delete(path + "\\" + child)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            pass
    def restore():
        delete(root)
        root_value, protocol_value, command_value = previous
        if root_value or protocol_value:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root) as key:
                if root_value: winreg.SetValueEx(key, "", 0, root_value[1], root_value[0])
                if protocol_value: winreg.SetValueEx(key, "URL Protocol", 0, protocol_value[1], protocol_value[0])
        if command_value:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key) as key: winreg.SetValueEx(key, "", 0, command_value[1], command_value[0])
    return restore


'''capturegrantlinux'''
def capturegrantlinux(helper: Path, output: Path):
    if not (xdg := shutil.which("xdg-mime")): raise RuntimeError("xdg-mime is required")
    (apps := Path.home() / ".local/share/applications").mkdir(parents=True, exist_ok=True)
    desktop = apps / "spotiflac-python-callback.desktop"
    mime_files = [Path.home() / ".config/mimeapps.list", apps / "mimeapps.list",]
    backup = {p: p.read_bytes() if p.exists() else None for p in mime_files}
    q = lambda s: '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'
    desktop.write_text("\n".join(["[Desktop Entry]", "Type=Application", "Name=SpotiFLAC Callback", "NoDisplay=true", "Terminal=false", f"Exec={q(sys.executable)} {q(str(helper))} --receive %u --output {q(str(output))}", "MimeType=x-scheme-handler/spotiflac;", "",]), encoding="utf-8",)
    subprocess.run([xdg, "default", desktop.name, "x-scheme-handler/spotiflac"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,)
    def restore():
        desktop.unlink(missing_ok=True)
        for path, data in backup.items():
            if data is None: path.unlink(missing_ok=True)
            else: path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    return restore


'''capturegrantmacos'''
def capturegrantmacos(helper: Path, output: Path):
    if not (osacompile := shutil.which("osacompile")): raise RuntimeError("osacompile is required")
    app = (temp := Path(tempfile.mkdtemp(prefix="spotiflac-callback-"))) / "SpotiFLAC Callback.app"
    script = "\n".join(["on open location u", (f'do shell script quoted form of "{Path(sys.executable).resolve()}" & ' f'" " & quoted form of "{helper.resolve()}" & " --receive " & ' f'quoted form of u & " --output " & quoted form of "{output.resolve()}"'), "end open location",])
    subprocess.run([osacompile, "-o", str(app), "-e", script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,)
    with (plist_path := app / "Contents/Info.plist").open("rb") as file: plist = plistlib.load(file)
    plist["CFBundleIdentifier"] = f"local.spotiflac.callback.{os.getpid()}"
    plist["CFBundleURLTypes"] = [{"CFBundleURLName": "SpotiFLAC Callback", "CFBundleURLSchemes": ["spotiflac"],}]
    with plist_path.open("wb") as file: plistlib.dump(plist, file)
    register = Path("/System/Library/Frameworks/CoreServices.framework/" "Frameworks/LaunchServices.framework/Support/lsregister")
    if register.exists(): subprocess.run([str(register), "-f", str(app)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,)
    def restore():
        if register.exists(): subprocess.run([str(register), "-u", str(app)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,)
        shutil.rmtree(temp, ignore_errors=True)
    return restore


'''capturegrant'''
def capturegrant(auth_url: str, state: str, timeout: float = 300) -> str:
    helper = Path(__file__).resolve()
    (output := Path(tempfile.gettempdir()) / (f"spotiflac-{os.getpid()}-{os.urandom(4).hex()}.txt")).unlink(missing_ok=True)
    if sys.platform == "win32": restore = capturegrantwindows(helper, output)
    elif sys.platform == "darwin": restore = capturegrantmacos(helper, output)
    elif sys.platform.startswith("linux"): restore = capturegrantlinux(helper, output)
    else: raise RuntimeError(f"Unsupported platform: {sys.platform}")
    try:
        print("Complete the verification in your browser.")
        print("Approve the SpotiFLAC callback prompt if it appears.")
        if not webbrowser.open(auth_url): print(f"Open this URL manually:\n{auth_url}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if output.exists():
                callback = urllib.parse.unquote(output.read_text(encoding="utf-8").strip())
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(callback).query)
                returned_state, grant = str(query.get("state", [""])[0]), str(query.get("grant", [""])[0])
                if returned_state and returned_state != state: raise RuntimeError("Unexpected callback state")
                if not grant: raise RuntimeError("Callback is missing grant")
                return grant
            time.sleep(0.2)
        raise RuntimeError("Browser verification timed out")
    finally: restore(); output.unlink(missing_ok=True)


'''Session'''
@dataclass
class Session:
    install_id: str = ""
    session_id: str = ""
    session_secret: str = ""
    expires_at: str = ""


'''ZarzQobuzClient'''
class ZarzQobuzClient:
    PLATFORM = "extension"
    EXTENSION_ID = "qobuz-web"
    APP_VERSION = "qobuz-web@1.1.0"
    BASE_URL = "https://api.zarz.moe/v2"
    def __init__(self, session_file: str | Path | None = None, timeout: float = 30, verification_timeout: float = 300,) -> None:
        self.timeout = timeout
        self.lock = threading.RLock()
        self.http = requests.Session()
        self.verification_timeout = verification_timeout
        self.session_file = Path(session_file or Path.home() / ".musicdl/zarz_qobuz_session.json")
    '''close'''
    def close(self) -> None:
        self.http.close()
    '''enter'''
    def __enter__(self):
        return self
    '''exit'''
    def __exit__(self, *_):
        self.close()
    '''clearsession'''
    def clearsession(self) -> None:
        session = self.loadsession()
        session.session_id = session.session_secret = session.expires_at = ""
        self.savesession(session)
    '''getdownloadinfo'''
    def getdownloadinfo(self, track_id, quality="27", request_overrides: dict = None) -> dict[str, Any]:
        track_id, errors = self.formattrackid(track_id), []
        for code in self.constructqualitychain(quality):
            try: return self.parsetrackdetails(track_id, code, request_overrides=request_overrides)
            except Exception as exc: errors.append(f"{code}: {exc}")
        raise RuntimeError("All quality attempts failed: " + "; ".join(errors))
    '''parsetrackdetails'''
    def parsetrackdetails(self, track_id: str, quality: str, request_overrides: dict = None) -> dict[str, Any]:
        track_url, request_overrides = f"https://open.qobuz.com/track/{track_id}", request_overrides or {}
        resource_hash = hashlib.sha256(f"qbz:track:{track_url.lower()}".encode()).hexdigest()
        ticket = self.signedjson("POST", "/tickets", {"capability": "download_ticket", "provider": "qbz", "resource_hash": resource_hash,}, request_overrides=request_overrides)
        if not (ticket_id := str(ticket.get("ticket_id") or ticket.get("ticket") or "")): raise RuntimeError("Missing ticket_id")
        (resp := self.signedrequest("POST", "/dl/qbz", {"quality": self.covertproviderquality(quality), "upload_to_r2": False, "id": track_id, "type": "track", "url": track_url,}, {"X-Zarz-Ticket": ticket_id}, request_overrides=request_overrides)).raise_for_status(); data: dict = resp.json(); resp.close()
        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        url = next((str(value).strip() for value in (data.get("download_url"), data.get("url"), data.get("link"), nested.get("download_url"), nested.get("url"), nested.get("link"),) if value), "")
        if not url: raise RuntimeError("Missing download URL")
        if 0 < (sample_rate := self.tonumber(data.get("sampling_rate") or nested.get("sampling_rate"))) < 1000: sample_rate *= 1000
        return {"url": url, "track_id": track_id, "quality": self.covertproviderquality(quality), "bit_depth": int(self.tonumber(data.get("bit_depth") or nested.get("bit_depth"))), "sample_rate": int(round(sample_rate)), "raw": data,}
    '''signedjson'''
    def signedjson(self, method, path, body, request_overrides: dict = None) -> dict:
        resp = self.signedrequest(method, path, body, request_overrides=request_overrides)
        return resp.json()
    '''signedrequest'''
    def signedrequest(self, method, path, body, extra_headers=None, request_overrides: dict = None):
        with self.lock:
            body_bytes = self.jsonbytes(body); session = self.ensuresession(request_overrides=request_overrides)
            resp = self.sendsigned(session, method, path, body_bytes, extra_headers or {}, request_overrides=request_overrides)
            if resp.status_code in (401, 428): resp.close(); self.clearsession(); session = self.ensuresession(request_overrides=request_overrides); (resp := self.sendsigned(session, method, path, body_bytes, extra_headers or {}, request_overrides=request_overrides)).raise_for_status()
            return resp
    '''sendsigned'''
    def sendsigned(self, session: Session, method: str, path: str, body, extra_headers, request_overrides: dict = None):
        method = method.upper(); url = urllib.parse.urljoin(self.BASE_URL + "/", path.lstrip("/"))
        parsed = urllib.parse.urlsplit(url); now = datetime.now(timezone.utc).replace(microsecond=0)
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z"); nonce = secrets.token_hex(12)
        body_hash = hashlib.sha256(body).hexdigest(); window = int(now.timestamp()) // 300
        rolling_key = self.dob64(hmac.new(session.session_secret.encode(), f"{window}:{session.session_id}".encode(), hashlib.sha256,).digest()).encode()
        signing_input = "\n".join(["ZARZ-HMAC-V1", method, parsed.path or "/", "", body_hash, timestamp, nonce, session.session_id, self.APP_VERSION, self.PLATFORM,]).encode()
        signature = self.dob64(hmac.new(rolling_key, signing_input, hashlib.sha256).digest())
        headers = {
            "Accept": "application/json", "Content-Type": "application/json", "User-Agent": f"SpotiFLAC-Mobile/{self.APP_VERSION}", "X-Zarz-Session": session.session_id, "X-Zarz-Timestamp": timestamp,
            "X-Zarz-Nonce": nonce, "X-Zarz-Body-SHA256": body_hash, "X-Zarz-Signature": signature, "X-Zarz-App-Version": self.APP_VERSION, "X-Zarz-Platform": self.PLATFORM, **extra_headers,
        }
        return self.http.request(method, url, data=body, headers=headers, timeout=self.timeout, **(request_overrides or {}))
    '''ensuresession'''
    def ensuresession(self, request_overrides: dict = None) -> Session:
        if not self.sessionvalid((session := self.loadsession())): session = self.verify(session, request_overrides=request_overrides)
        if (expires := self.parsetime(session.expires_at)) and expires - datetime.now(timezone.utc) <= timedelta(hours=1):
            try: self.refresh(session, request_overrides=request_overrides)
            except Exception: pass
        return session
    '''verify'''
    def verify(self, session: Session, request_overrides: dict = None) -> Session:
        (resp := self.http.get(f"{self.BASE_URL}/bootstrap", params={"app_version": self.APP_VERSION, "install_id": session.install_id,}, headers={"Accept": "application/json", "User-Agent": f"SpotiFLAC-Mobile/{self.APP_VERSION}",}, timeout=self.timeout, **(request_overrides or {}))).raise_for_status(); data: dict = resp.json(); resp.close()
        if all(data.get(k) for k in ("session_id", "session_secret", "expires_at")): self.applysession(session, data); self.savesession(session); return session
        if not (auth_url := str(data.get("auth_url") or data.get("challenge_url") or "")) and data.get("challenge_id"):
            callback = ("spotiflac://session-grant?" + urllib.parse.urlencode({"cb_version": "v2grant", "state": self.EXTENSION_ID,}))
            auth_url = (f"{self.BASE_URL}/challenge?" + urllib.parse.urlencode({"id": str(data["challenge_id"]), "cb": callback,}))
        if not auth_url: raise RuntimeError("Bootstrap returned no verification URL")
        grant = capturegrant(auth_url, self.EXTENSION_ID, self.verification_timeout)
        (resp := self.http.post(f"{self.BASE_URL}/session/exchange", json={"grant": grant, "install_id": session.install_id, "app_version": self.APP_VERSION, "platform": self.PLATFORM,}, headers={"Accept": "application/json", "User-Agent": f"SpotiFLAC-Mobile/{self.APP_VERSION}",}, timeout=self.timeout, **(request_overrides or {}))).raise_for_status(); data: dict = resp.json(); resp.close()
        if not all(data.get(k) for k in ("session_id", "session_secret", "expires_at")): raise RuntimeError("Session exchange response is incomplete")
        self.applysession(session, data); self.savesession(session)
        return session
    '''refresh'''
    def refresh(self, session: Session, request_overrides: dict = None) -> None:
        (resp := self.sendsigned(session, "POST", "/session/refresh", self.jsonbytes({"install_id": session.install_id}), {}, request_overrides=request_overrides)).raise_for_status(); data: dict = resp.json(); resp.close()
        for key in ("session_id", "session_secret", "expires_at"):
            if data.get(key): setattr(session, key, str(data[key]))
        self.savesession(session)
    '''loadsession'''
    def loadsession(self) -> Session:
        session = Session()
        if self.session_file.exists():
            try:
                data: dict = json.loads(self.session_file.read_text(encoding="utf-8"))
                session = Session(str(data.get("install_id", "")), str(data.get("session_id", "")), str(data.get("session_secret", "")), str(data.get("expires_at", "")),)
            except Exception: pass
        if not session.install_id: session.install_id = secrets.token_hex(16); self.savesession(session)
        return session
    '''savesession'''
    def savesession(self, session: Session) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        (temp := self.session_file.with_suffix(".tmp")).write_text(json.dumps(asdict(session), indent=2), encoding="utf-8",)
        try: os.chmod(temp, 0o600)
        except OSError: pass
        os.replace(temp, self.session_file)
    '''sessionvalid'''
    def sessionvalid(self, session: Session) -> bool:
        expires = self.parsetime(session.expires_at)
        return bool(session.session_id and session.session_secret and expires and expires > datetime.now(timezone.utc) + timedelta(minutes=5))
    '''applysession'''
    @staticmethod
    def applysession(session: Session, data: dict):
        session.session_id = str(data["session_id"])
        session.session_secret = str(data["session_secret"])
        session.expires_at = str(data["expires_at"])
    '''jsonbytes'''
    @staticmethod
    def jsonbytes(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,).encode()
    '''dob64'''
    @staticmethod
    def dob64(value):
        return base64.urlsafe_b64encode(value).decode().rstrip("=")
    '''parsetime'''
    @staticmethod
    def parsetime(value):
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if result.tzinfo is None: result = result.replace(tzinfo=timezone.utc)
            return result.astimezone(timezone.utc)
        except (TypeError, ValueError): return None
    '''formattrackid'''
    @staticmethod
    def formattrackid(value):
        if (value := str(value).strip()).startswith(("http://", "https://")):
            parts = [x for x in urllib.parse.urlsplit(value).path.split("/") if x]
            if "track" in parts and parts.index("track") + 1 < len(parts): value = parts[parts.index("track") + 1]
        if not value.isdigit(): raise ValueError(f"Invalid Qobuz track ID: {value!r}")
        return value
    '''constructqualitychain'''
    @staticmethod
    def constructqualitychain(value):
        value = str(value).upper()
        if value in {"HI_RES_LOSSLESS", "27"}: return ["27", "7", "6"]
        if value in {"HI_RES", "7"}: return ["7", "6"]
        if value in {"LOSSLESS", "6"}: return ["6"]
        raise ValueError("Invalid quality")
    '''covertproviderquality'''
    @staticmethod
    def covertproviderquality(value):
        return "hi-res-max" if value == "27" else "hi-res" if value == "7" else "cd"
    '''tonumber'''
    @staticmethod
    def tonumber(value):
        try: return float(value or 0)
        except (TypeError, ValueError): return 0


'''ZarzDeezerClient'''
class ZarzDeezerClient(ZarzQobuzClient):
    EXTENSION_ID = "deezer"
    APP_VERSION = "deezer@1.2.0"
    def __init__(self, session_file: str | Path | None = None, timeout: float = 30, verification_timeout: float = 300,) -> None:
        super().__init__(session_file=(session_file or Path.home() / ".musicdl" / "zarz_deezer_session.json"), timeout=timeout, verification_timeout=verification_timeout,)
    '''getdownloadinfo'''
    def getdownloadinfo(self, track_id: str | int, request_overrides: dict = None) -> dict[str, Any]:
        track_id = self.deezertrackid(track_id); track_url = f"https://www.deezer.com/track/{track_id}"
        resource_hash = hashlib.sha256(f"dzr:track:{track_url.lower()}".encode("utf-8")).hexdigest()
        ticket = self.signedjson("POST", "/tickets", {"capability": "download_ticket", "provider": "dzr", "resource_hash": resource_hash,}, request_overrides=request_overrides)
        ticket_id = str(ticket.get("ticket_id") or ticket.get("ticket") or "").strip()
        if not ticket_id: raise RuntimeError("Ticket response is missing ticket_id")
        (resp := self.signedrequest("POST", "/dl/dzr", {"id": track_id, "type": "track", "platform": "deezer", "url": track_url,}, {"X-Zarz-Ticket": ticket_id,}, request_overrides=request_overrides)).raise_for_status(); descriptor: dict = resp.json(); resp.close()
        if not isinstance(descriptor, dict): raise RuntimeError("Deezer resolver returned invalid JSON")
        if (descriptor.get("success") is False or descriptor.get("error") or descriptor.get("detail")): raise RuntimeError(str(descriptor.get("error") or descriptor.get("detail") or descriptor.get("message") or descriptor))
        if not (download_url := self.descriptorurl(descriptor)): raise RuntimeError("Deezer resolver response does not contain a download URL")
        requires_decryption = self.requiresclientdecryption(descriptor)
        return {
            "url": download_url, "track_id": track_id, "track_url": track_url, "format": str(descriptor.get("deezer_format") or descriptor.get("format") or "flac").lower(), "direct_downloadable": self.parsebool(descriptor.get("direct_downloadable"), None,), "requires_client_decryption": requires_decryption, 
            "encrypted": requires_decryption, "bit_depth": int(self.tonumber(descriptor.get("bit_depth") or 16)), "sample_rate": int(self.tonumber(descriptor.get("sample_rate") or descriptor.get("sampling_rate") or 44100)), "raw": descriptor,
        }
    '''descriptorurl'''
    @classmethod
    def descriptorurl(cls, descriptor: dict[str, Any],) -> str:
        direct_downloadable = cls.parsebool(descriptor.get("direct_downloadable"), None,)
        if (direct_downloadable is True and descriptor.get("direct_download_url")): return str(descriptor["direct_download_url"]).strip()
        if descriptor.get("download_url"): return str(descriptor["download_url"]).strip()
        if descriptor.get("direct_download_url"): return str(descriptor["direct_download_url"]).strip()
        return ""
    '''requiresclientdecryption'''
    @classmethod
    def requiresclientdecryption(cls, descriptor: dict[str, Any],) -> bool:
        explicit = cls.parsebool(descriptor.get("requires_client_decryption"), None,)
        if explicit is not None: return explicit
        direct_downloadable = cls.parsebool(descriptor.get("direct_downloadable"), None,)
        if direct_downloadable is not None: return not direct_downloadable
        return bool(cls.parsebool(descriptor.get("deezer_encrypted"), False,))
    '''parsebool'''
    @staticmethod
    def parsebool(value: Any, default: bool | None,) -> bool | None:
        if isinstance(value, bool): return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "true": return True
            if normalized == "false": return False
        return default
    '''deezertrackid'''
    @staticmethod
    def deezertrackid(track_id: str | int,) -> str:
        if (value := str(track_id).strip()).lower().startswith("deezer:"): value = value.split(":", 1)[1]
        if value.startswith(("http://", "https://")):
            parts = [part for part in urllib.parse.urlsplit(value).path.split("/") if part]
            if "track" in parts and (index := parts.index("track")) + 1 < len(parts): value = parts[index + 1]
        if not value.isdigit(): raise ValueError(f"Invalid Deezer track ID: {track_id!r}")
        return value


'''ZarzTIDALClient'''
class ZarzTIDALClient(ZarzQobuzClient):
    DOWNLOAD_PATH = "/dl/tid"
    EXTENSION_ID = "tidal-web"
    APP_VERSION = "tidal-web@1.1.0"
    def __init__(self, session_file: str | Path | None = None, timeout: float = 30, verification_timeout: float = 300,) -> None:
        super().__init__(session_file=session_file or (Path.home() / ".musicdl" / "zarz_tidal_session.json"), timeout=timeout, verification_timeout=verification_timeout,)
    '''getstreamresponse'''
    def getstreamresponse(self, track_id: str | int, quality: str, request_overrides: dict | None = None,) -> dict[str, Any]:
        quality, track_id, request_overrides = self.normalizequality(quality), self.tidaltrackid(track_id), request_overrides or {}
        resource_hash = hashlib.sha256(f"tid:track:{track_id.lower()}".encode("utf-8")).hexdigest()
        ticket = self.signedjson("/tickets", {"capability": "download_ticket", "provider": "tid", "resource_hash": resource_hash,}, request_overrides=request_overrides,)
        if not (ticket_id := str(ticket.get("ticket_id") or ticket.get("ticket") or "").strip()): raise RuntimeError("Ticket response is missing ticket_id")
        body = ({"id": track_id, "endpoint": "manifests", "formats": ["EAC3_JOC"],} if quality == "DOLBY_ATMOS" else {"id": track_id, "quality": quality})
        payload = self.signedjson(self.DOWNLOAD_PATH, body, extra_headers={"X-Zarz-Ticket": ticket_id,}, request_overrides=request_overrides,)
        if payload.get("success") is False or (error := payload.get("error") or payload.get("detail")): raise RuntimeError(str(error or payload.get("message") or payload))
        if quality == "DOLBY_ATMOS": return self.convertatmos(payload, track_id, self.timeout, headers={}, request_overrides=request_overrides,)
        if not isinstance((data := payload.get("data")), dict): raise RuntimeError("TIDAL resolver returned no data")
        if str(data.get("assetPresentation") or "").upper() == "PREVIEW": raise RuntimeError("TIDAL resolver returned PREVIEW asset")
        if not data.get("manifest"): raise RuntimeError("TIDAL resolver response is missing manifest")
        return data
    '''signedjson'''
    def signedjson(self, path: str, body: dict, extra_headers: dict | None = None, request_overrides: dict | None = None,) -> dict[str, Any]:
        (resp := self.signedrequest("POST", path, body, extra_headers or {}, request_overrides=request_overrides,)).raise_for_status()
        return resp.json()
    '''convertatmos'''
    def convertatmos(self, payload: dict[str, Any], track_id: str, timeout: float, headers: dict[str, str], request_overrides: dict,) -> dict[str, Any]:
        data = data.get("data") if isinstance((data := payload.get("data")), dict) else None
        attributes = (data.get("attributes") if isinstance(data, dict) else None)
        if not isinstance(attributes, dict): raise RuntimeError("Atmos manifest payload is missing attributes")
        if not isinstance((formats := attributes.get("formats")), list) or not any(str(item).upper() == "EAC3_JOC" for item in formats): raise RuntimeError("TIDAL API did not report EAC3_JOC for this track")
        if not (manifest_url := str(attributes.get("uri") or "").strip()): raise RuntimeError("Atmos manifest URI is empty")
        (resp := self.http.get(manifest_url, headers={"Accept": "application/dash+xml,text/xml,application/xml;q=0.9,*/*;q=0.8", "User-Agent": f"SpotiFLAC-Mobile/{self.APP_VERSION}", **headers,}, timeout=timeout, **request_overrides,)).raise_for_status()
        if not (manifest := resp.content): raise RuntimeError("Atmos manifest response is empty")
        return {
            "trackid": track_id, "videoid": None, "streamType": "ON_DEMAND", "assetPresentation": "FULL", "audioMode": "DOLBY_ATMOS", "audioQuality": "DOLBY_ATMOS", 
            "videoQuality": None, "manifestMimeType": "application/dash+xml", "manifest": base64.b64encode(manifest).decode("ascii"),
        }
    '''normalizequality'''
    @staticmethod
    def normalizequality(quality: str) -> str:
        value = {"ATMOS": "DOLBY_ATMOS", "DOLBY": "DOLBY_ATMOS", "EAC3": "DOLBY_ATMOS", "EAC3_JOC": "DOLBY_ATMOS", "HIRES": "HI_RES_LOSSLESS", "HI_RES": "HI_RES_LOSSLESS", "MASTER": "HI_RES_LOSSLESS",}.get((value := str(quality or "").strip().upper()), value)
        if value not in {"DOLBY_ATMOS", "HI_RES_LOSSLESS", "LOSSLESS", "HIGH", "LOW",}: raise ValueError(f"Invalid TIDAL quality: {quality!r}")
        return value
    '''tidaltrackid'''
    @staticmethod
    def tidaltrackid(track_id: str | int) -> str:
        if (value := str(track_id).strip()).lower().startswith("tidal:"): value = value.split(":", 1)[1]
        if value.startswith(("http://", "https://")):
            parts = [part for part in urllib.parse.urlparse(value).path.split("/") if part]
            if "track" in (lowered := [part.lower() for part in parts]):
                if (index := lowered.index("track")) + 1 < len(parts): value = parts[index + 1]
        if not value.isdigit(): raise ValueError(f"Invalid TIDAL track ID: {track_id!r}")
        return value


'''handlecallbackprocess'''
def handlecallbackprocess() -> bool:
    if "--receive" not in sys.argv: return False
    try: callback_url = sys.argv[sys.argv.index("--receive") + 1]; output_file = Path(sys.argv[sys.argv.index("--output") + 1])
    except (ValueError, IndexError) as exc: raise RuntimeError("Invalid callback process arguments") from exc
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_name(output_file.name + ".tmp")
    temporary_file.write_text(callback_url.strip().strip('"'), encoding="utf-8",)
    os.replace(temporary_file, output_file)
    return True


'''debug'''
if __name__ == "__main__":
    if handlecallbackprocess(): raise SystemExit(0)