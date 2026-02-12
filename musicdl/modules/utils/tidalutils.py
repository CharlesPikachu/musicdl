'''
Function:
    Implementation of TIDALMusicClient Utils (Refer To https://github.com/yaronzz/Tidal-Media-Downloader)
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import sys
import time
import json
import aigpy
import base64
import shutil
import hashlib
import secrets
import requests
import tempfile
import webbrowser
import subprocess
from enum import Enum
from pathlib import Path
from .logger import colorize
from functools import reduce
from Crypto.Cipher import AES
from mutagen.flac import FLAC
from Crypto.Util import Counter
from xml.etree import ElementTree
from abc import ABC, abstractmethod
from collections import defaultdict
from platformdirs import user_log_dir
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from .misc import safeextractfromdict, replacefile
from urllib.parse import urljoin, urlparse, parse_qs
from .importutils import optionalimport, optionalimportfrom
from typing import List, Optional, Any, Union, Tuple, Callable, Dict


'''MediaMetadata'''
class MediaMetadata(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.tags = []


'''StreamUrl'''
class StreamUrl(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.trackid = None
        self.url = None
        self.urls = None
        self.codec = None
        self.encryptionKey = None
        self.soundQuality = None
        self.sampleRate = None
        self.bitDepth = None


'''VideoStreamUrl'''
class VideoStreamUrl(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.codec = None
        self.resolution = None
        self.resolutions = None
        self.m3u8Url = None


'''Artist'''
class Artist(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = None
        self.name = None
        self.type = None
        self.picture = None


'''Album'''
class Album(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = None
        self.title = None
        self.duration = 0
        self.numberOfTracks = 0
        self.numberOfVideos = 0
        self.numberOfVolumes = 0
        self.releaseDate = None
        self.type = None
        self.version = None
        self.cover = None
        self.videoCover = None
        self.explicit = False
        self.audioQuality = None
        self.audioModes = None
        self.upc = None
        self.popularity = None
        self.copyright = None
        self.streamStartDate = None
        self.mediaMetadata = MediaMetadata()
        self.artist = Artist()
        self.artists = Artist()


'''Playlist'''
class Playlist(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.uuid = None
        self.title = None
        self.numberOfTracks = 0
        self.numberOfVideos = 0
        self.description = None
        self.duration = 0
        self.image = None
        self.squareImage = None


'''Track'''
class Track(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = None
        self.title = None
        self.duration = 0
        self.trackNumber = 0
        self.volumeNumber = 0
        self.trackNumberOnPlaylist = 0
        self.version = None
        self.isrc = None
        self.explicit = False
        self.audioQuality = None
        self.audioModes = None
        self.copyRight = None
        self.replayGain = None
        self.peak = None
        self.popularity = None
        self.streamStartDate = None
        self.mediaMetadata = MediaMetadata()
        self.artist = Artist()
        self.artists = Artist()
        self.album = Album()
        self.allowStreaming = False
        self.playlist = None


'''Video'''
class Video(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = None
        self.title = None
        self.duration = 0
        self.imageID = None
        self.trackNumber = 0
        self.releaseDate = None
        self.version = None
        self.quality = None
        self.explicit = False
        self.artist = Artist()
        self.artists = Artist()
        self.album = Album()
        self.allowStreaming = False
        self.playlist = None


'''Mix'''
class Mix(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = None
        self.tracks = Track()
        self.videos = Video()


'''Lyrics'''
class Lyrics(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.trackId = None
        self.lyricsProvider = None
        self.providerCommontrackId = None
        self.providerLyricsId = None
        self.lyrics = None
        self.subtitles = None


'''SearchDataBase'''
class SearchDataBase(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.limit = 0
        self.offset = 0
        self.totalNumberOfItems = 0


'''SearchAlbums'''
class SearchAlbums(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Album()


'''SearchArtists'''
class SearchArtists(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Artist()


'''SearchTracks'''
class SearchTracks(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Track()


'''SearchVideos'''
class SearchVideos(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Video()


'''SearchPlaylists'''
class SearchPlaylists(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Playlist()


'''SearchResult'''
class SearchResult(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.artists = SearchArtists()
        self.albums = SearchAlbums()
        self.tracks = SearchTracks()
        self.videos = SearchVideos()
        self.playlists = SearchPlaylists()


'''LoginKey'''
class LoginKey(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.deviceCode = None
        self.userCode = None
        self.verificationUrl = None
        self.authCheckTimeout = None
        self.authCheckInterval = None
        self.userId = None
        self.countryCode = None
        self.accessToken = None
        self.refreshToken = None
        self.expiresIn = None
        self.pkceState = None
        self.pkceCodeVerifier = None
        self.pkceRedirectUri = None
        self.pkceClientUniqueKey = None
        self.pkceTokenUrl = None


'''StreamRespond'''
class StreamRespond(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.trackid = None
        self.videoid = None
        self.streamType = None
        self.assetPresentation = None
        self.audioMode = None
        self.audioQuality = None
        self.videoQuality = None
        self.manifestMimeType = None
        self.manifest = None


'''AudioQuality'''
class AudioQuality(Enum):
    Normal = 0
    High = 1
    HiFi = 2
    Master = 3
    Max = 4


'''VideoQuality'''
class VideoQuality(Enum):
    P240 = 240
    P360 = 360
    P480 = 480
    P720 = 720
    P1080 = 1080


'''Type'''
class Type(Enum):
    Album = 0
    Track = 1
    Video = 2
    Playlist = 3
    Artist = 4
    Mix = 5
    Null = 6


'''SegmentTimelineEntry'''
@dataclass
class SegmentTimelineEntry:
    start_time: Optional[int]
    duration: int
    repeat: int = 0


'''SegmentTemplate'''
@dataclass
class SegmentTemplate:
    media: Optional[str]
    initialization: Optional[str]
    start_number: int = 1
    timescale: int = 1
    presentation_time_offset: int = 0
    timeline: List[SegmentTimelineEntry] = field(default_factory=list)


'''SegmentList'''
@dataclass
class SegmentList:
    initialization: Optional[str]
    media_segments: List[str] = field(default_factory=list)


'''Representation'''
@dataclass
class Representation:
    id: Optional[str]
    bandwidth: Optional[str]
    codec: Optional[str]
    base_url: str
    segment_template: Optional[SegmentTemplate]
    segment_list: Optional[SegmentList]
    @property
    def segments(self) -> List[str]:
        if self.segment_list is not None: return TIDALMusicClientDashUtils.buildsegmentlist(self.segment_list, self.base_url)
        if self.segment_template is not None: return TIDALMusicClientDashUtils.buildsegmenttemplate(self.segment_template, self.base_url, self)
        return []


'''AdaptationSet'''
@dataclass
class AdaptationSet:
    content_type: Optional[str]
    base_url: str
    representations: List[Representation] = field(default_factory=list)


'''Period'''
@dataclass
class Period:
    base_url: str
    adaptation_sets: List[AdaptationSet] = field(default_factory=list)


'''Manifest'''
@dataclass
class Manifest:
    base_url: str
    periods: List[Period] = field(default_factory=list)


'''SessionStorage'''
@dataclass
class SessionStorage:
    access_token: str = None
    refresh_token: str = None
    expires: datetime = None
    user_id: str = None
    country_code: str = None
    client_id: str = None
    client_secret: str = None
    def tojson(self): return {**asdict(self), "expires": (lambda x: x if isinstance(x, str) else None)(self.expires.isoformat()) if (self.expires is not None and callable(getattr(self.expires, "isoformat", None))) else None}
    def tojsonbytes(self): return json.dumps(self.tojson()).encode("utf-8")
    @classmethod
    def fromjsonbytes(cls, b: bytes): return cls(**(lambda d: ({**d, "expires": datetime.fromisoformat(d["expires"])} if d.get("expires") else {**d, "expires": None}))(json.loads(b.decode("utf-8"))))
    def saveencrypted(self, path: str, key: bytes = b'3BxQiWxi32p7SCr9SEjGH2Yzj90lxf0EfQ6bi8Vr0dM='): open(path, "wb").write(Fernet(key).encrypt(self.tojsonbytes()))
    @classmethod
    def loadencrypted(cls, path: str, key: bytes = b'3BxQiWxi32p7SCr9SEjGH2Yzj90lxf0EfQ6bi8Vr0dM='): return cls.fromjsonbytes(Fernet(key).decrypt(open(path, "rb").read()))


'''TidalSession'''
class TidalSession(ABC):
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires = None
        self.user_id = None
        self.country_code = None
    @property
    def auth_headers(self) -> dict: pass
    @abstractmethod
    def refresh(self): pass
    @staticmethod
    def session_type() -> str: pass
    '''setstorage'''
    def setstorage(self, storage: dict | SessionStorage):
        if isinstance(storage, SessionStorage): storage = storage.tojson()
        self.access_token = storage.get("access_token")
        self.refresh_token = storage.get("refresh_token")
        self.expires = storage.get("expires")
        self.user_id = storage.get("user_id")
        self.country_code = storage.get("country_code")
    '''getstorage'''
    def getstorage(self) -> "SessionStorage":
        return SessionStorage(**{"access_token": self.access_token, "refresh_token": self.refresh_token, "expires": self.expires, "user_id": self.user_id, "country_code": self.country_code, 'client_id': getattr(self, 'client_id'), 'client_secret': getattr(self, 'client_secret')})
    '''getsubscription'''
    def getsubscription(self, request_overrides: dict = None) -> str:
        if not self.access_token: return
        request_overrides = request_overrides or {}
        resp = requests.get(f"https://api.tidal.com/v1/users/{self.user_id}/subscription", params={"countryCode": self.country_code}, headers=self.auth_headers, **request_overrides)
        resp.raise_for_status()
        return resp.json()["subscription"]["type"]
    '''valid'''
    def valid(self, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        if not isinstance(self, TidalSession) and (self.access_token is None or datetime.now() > self.expires): return False
        resp = requests.get("https://api.tidal.com/v1/sessions", headers=self.auth_headers, **request_overrides)
        return resp.status_code == 200


'''TidalMobileSession'''
class TidalMobileSession(TidalSession):
    TIDAL_AUTH_BASE = "https://auth.tidal.com/v1/"
    TIDAL_LOGIN_BASE = "https://login.tidal.com/api/"
    CANDIDATED_CLIENT_ID_SECRETS = [
        {'client_id': '7m7Ap0JC9j1cOM3n', 'client_secret': 'vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY='}, {'client_id': '8SEZWa4J1NVC5U5Y', 'client_secret': 'owUYDkxddz+9FpvGX24DlxECNtFEMBxipU0lBfrbq60='},
        {'client_id': 'zU4XHVVkc2tDPo4t', 'client_secret': 'VJKhDFqJPqvsPVNBV6ukXTJmwlvbttP7wlMlrc72se4='}, {'client_id': 'fX2JxdmntZWK0ixT', 'client_secret': '1Nm5AfDAjxrgJFJbKNWLeAyKGVGmINuXPPLHVXAvxAg='},
        {'client_id': 'Dt4NnnGCAeHlCFnZ', 'client_secret': 'fmEBbWpJYd6eR6THNksXWEZSTNPWmIejTMNxncSGHmU='},
    ]
    def __init__(self, client_id: str = '7m7Ap0JC9j1cOM3n'):
        super(TidalMobileSession, self).__init__()
        self.client_id = client_id
        self.redirect_uri = "https://tidal.com/android/login/auth"
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=")
        self.code_challenge = base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier).digest()).rstrip(b"=")
        self.client_unique_key = secrets.token_hex(8)
    @property
    def auth_headers(self): return {"Host": "api.tidal.com", "X-Tidal-Token": self.client_id, "Authorization": "Bearer {}".format(self.access_token), "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
    @staticmethod
    def session_type(): return "Mobile"
    '''auth'''
    def auth(self, username: str, password: str, request_overrides: dict = None):
        session, request_overrides = requests.Session(), request_overrides or {}
        resp = session.post("https://dd.tidal.com/js/", data={"jsData": f'{{"opts":"endpoint,ajaxListenerPath","ua":"Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36"}}', "ddk": "1F633CDD8EF22541BD6D9B1B8EF13A", "Referer": "https%3A%2F%2Ftidal.com%2F", "responsePage": "origin", "ddv": "4.17.0"}, headers={"user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36", "content-type": "application/x-www-form-urlencoded"}, **request_overrides)
        resp.raise_for_status()
        assert safeextractfromdict(resp.json(), ['cookie'], "")
        dd_cookie = safeextractfromdict(resp.json(), ['cookie'], "").split(";")[0]
        session.cookies[dd_cookie.split("=")[0]] = dd_cookie.split("=")[1]
        params = {"response_type": "code", "redirect_uri": self.redirect_uri, "lang": "en_US", "appMode": "android", "client_id": self.client_id, "client_unique_key": self.client_unique_key, "code_challenge": self.code_challenge, "code_challenge_method": "S256", "restrict_signup": "true"}
        resp = session.get("https://login.tidal.com/authorize", params=params, headers={"user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36", "accept-language": "en-US", "x-requested-with": "com.aspiro.tidal"}, **request_overrides)
        resp.raise_for_status()
        resp = session.post(self.TIDAL_LOGIN_BASE + "email", params=params, json={"email": username}, headers={"user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36", "x-csrf-token": session.cookies["_csrf-token"], "accept": "application/json, text/plain, */*", "content-type": "application/json", "accept-language": "en-US", "x-requested-with": "com.aspiro.tidal"}, **request_overrides)
        resp.raise_for_status()
        assert resp.json()['isValidEmail'] and not resp.json()['newUser']
        resp = session.post(self.TIDAL_LOGIN_BASE + "email/user/existing", params=params, json={"email": username, "password": password}, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36", "x-csrf-token": session.cookies["_csrf-token"], "accept": "application/json, text/plain, */*", "content-type": "application/json", "accept-language": "en-US", "x-requested-with": "com.aspiro.tidal"}, **request_overrides)
        resp.raise_for_status()
        resp = session.get("https://login.tidal.com/success", allow_redirects=False, headers={"user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36", "accept-language": "en-US", "x-requested-with": "com.aspiro.tidal"}, **request_overrides)
        assert resp.status_code == 302
        oauth_code = parse_qs(urlparse(resp.headers["location"]).query)["code"][0]
        resp = requests.post(self.TIDAL_AUTH_BASE + "oauth2/token", data={"code": oauth_code, "client_id": self.client_id, "grant_type": "authorization_code", "redirect_uri": self.redirect_uri, "scope": "r_usr w_usr w_sub", "code_verifier": self.code_verifier, "client_unique_key": self.client_unique_key}, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 8 Build/TQ2A.230505.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.163 Mobile Safari/537.36"}, **request_overrides)
        resp.raise_for_status()
        self.access_token, self.refresh_token = resp.json()["access_token"], resp.json()["refresh_token"]
        self.expires = datetime.now() + timedelta(seconds=resp.json()["expires_in"])
        resp = requests.get("https://api.tidal.com/v1/sessions", headers=self.auth_headers, **request_overrides)
        resp.raise_for_status()
        self.user_id, self.country_code = resp.json()["userId"], resp.json()["countryCode"]
    '''refresh'''
    def refresh(self, request_overrides: dict = None):
        assert self.refresh_token is not None
        request_overrides = request_overrides or {}
        resp = requests.post(self.TIDAL_AUTH_BASE + "oauth2/token", data={"refresh_token": self.refresh_token, "client_id": self.client_id, "grant_type": "refresh_token"}, **request_overrides)
        resp.raise_for_status()
        self.access_token = resp.json()["access_token"]
        self.expires = datetime.now() + timedelta(seconds=resp.json()["expires_in"])
        if "refresh_token" in resp.json(): self.refresh_token = resp.json()["refresh_token"]
        

'''TidalTvSession'''
class TidalTvSession(TidalSession):
    TIDAL_AUTH_BASE = "https://auth.tidal.com/v1/"
    CANDIDATED_CLIENT_ID_SECRETS = [
        {'client_id': '7m7Ap0JC9j1cOM3n', 'client_secret': 'vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY='}, {'client_id': '8SEZWa4J1NVC5U5Y', 'client_secret': 'owUYDkxddz+9FpvGX24DlxECNtFEMBxipU0lBfrbq60='},
        {'client_id': 'zU4XHVVkc2tDPo4t', 'client_secret': 'VJKhDFqJPqvsPVNBV6ukXTJmwlvbttP7wlMlrc72se4='}, {'client_id': 'fX2JxdmntZWK0ixT', 'client_secret': '1Nm5AfDAjxrgJFJbKNWLeAyKGVGmINuXPPLHVXAvxAg='},
        {'client_id': 'Dt4NnnGCAeHlCFnZ', 'client_secret': 'fmEBbWpJYd6eR6THNksXWEZSTNPWmIejTMNxncSGHmU='},
    ]
    def __init__(self, client_id: str = '7m7Ap0JC9j1cOM3n', client_secret: str = 'vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY='):
        super(TidalTvSession, self).__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.expires = None
        self.user_id = None
        self.country_code = None
    @property
    def auth_headers(self): return {"X-Tidal-Token": self.client_id, "Authorization": "Bearer {}".format(self.access_token), "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
    @staticmethod
    def session_type(): return "Tv"
    '''auth'''
    def auth(self, request_overrides: dict = None):
        session, request_overrides = requests.Session(), request_overrides or {}
        resp = session.post(self.TIDAL_AUTH_BASE + "oauth2/device_authorization", data={"client_id": self.client_id, "scope": "r_usr+w_usr+w_sub"}, **request_overrides)
        resp.raise_for_status()
        device_code, user_code = resp.json()["deviceCode"], resp.json()["userCode"]
        user_login_url = f'https://link.tidal.com/{user_code}'
        msg = f'Opening {user_login_url} in the browser, log in or sign up to TIDAL manually to continue (in 300 seconds please).'
        print(colorize("TIDAL LOGIN REQUIRED:", 'highlight'))
        print(colorize(msg, 'highlight'))
        is_remote = bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"))
        if not is_remote:
            try: webbrowser.open(user_login_url, new=2)
            except Exception: pass
        if sys.platform.startswith("win") or sys.platform == "darwin" or bool(os.environ.get("DISPLAY")):
            import tkinter as tk; from tkinter import messagebox
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); messagebox.showinfo("TIDAL Login Required", msg, parent=root); root.destroy()
        data = {"client_id": self.client_id, "device_code": device_code, "client_secret": self.client_secret, "grant_type": "urn:ietf:params:oauth:grant-type:device_code", "scope": "r_usr+w_usr+w_sub"}
        while True:
            resp = session.post(self.TIDAL_AUTH_BASE + "oauth2/token", data=data, **request_overrides)
            if resp.status_code not in {400}: break
            time.sleep(0.2)
        resp.raise_for_status()
        self.access_token, self.refresh_token = resp.json()["access_token"], resp.json()["refresh_token"]
        self.expires = datetime.now() + timedelta(seconds=resp.json()["expires_in"])
        resp = session.get("https://api.tidal.com/v1/sessions", headers=self.auth_headers, **request_overrides)
        resp.raise_for_status()
        self.user_id, self.country_code = resp.json()["userId"], resp.json()["countryCode"]
        resp = session.get("https://api.tidal.com/v1/users/{}?countryCode={}".format(self.user_id, self.country_code), headers=self.auth_headers, **request_overrides)
        resp.raise_for_status()
    '''refresh'''
    def refresh(self, request_overrides: dict = None):
        assert self.refresh_token is not None
        request_overrides = request_overrides or {}
        resp = requests.post(self.TIDAL_AUTH_BASE + "oauth2/token", data={"refresh_token": self.refresh_token, "client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "refresh_token"}, **request_overrides)
        resp.raise_for_status()
        self.access_token = resp.json()["access_token"]
        self.expires = datetime.now() + timedelta(seconds=resp.json()["expires_in"])
        if "refresh_token" in resp.json(): self.refresh_token = resp.json()["refresh_token"]


'''TIDALMusicClientDashUtils'''
class TIDALMusicClientDashUtils:
    '''parsemanifest'''
    @staticmethod
    def parsemanifest(xml: Union[str, bytes]) -> Manifest:
        xml_text = xml.decode("utf-8") if isinstance(xml, bytes) else str(xml)
        xml_text = re.sub(r'xmlns="[^"]+"', '', xml_text, count=1)
        root = ElementTree.fromstring(xml_text)
        manifest_base = TIDALMusicClientDashUtils.getbaseurl(root, '')
        manifest = Manifest(base_url=manifest_base)
        for period_el in root.findall('Period'): manifest.periods.append(TIDALMusicClientDashUtils.parseperiod(period_el, manifest_base))
        return manifest
    '''getbaseurl'''
    @staticmethod
    def getbaseurl(element: ElementTree.Element, inherited: str) -> str:
        base_el = element.find('BaseURL')
        return urljoin(inherited, (base_el.text or '').strip()) if base_el is not None and (base_el.text or '').strip() else inherited
    '''parseperiod'''
    @staticmethod
    def parseperiod(element: ElementTree.Element, parent_base: str) -> Period:
        base_url = TIDALMusicClientDashUtils.getbaseurl(element, parent_base)
        period = Period(base_url=base_url)
        for adaptation_el in element.findall('AdaptationSet'): period.adaptation_sets.append(TIDALMusicClientDashUtils.parseadaptation(adaptation_el, base_url))
        return period
    '''parseadaptation'''
    @staticmethod
    def parseadaptation(element: ElementTree.Element, parent_base: str) -> AdaptationSet:
        base_url = TIDALMusicClientDashUtils.getbaseurl(element, parent_base)
        adaptation = AdaptationSet(content_type=element.get('contentType'), base_url=base_url)
        for rep_el in element.findall('Representation'): adaptation.representations.append(TIDALMusicClientDashUtils.parserepresentation(rep_el, base_url))
        return adaptation
    '''parserepresentation'''
    @staticmethod
    def parserepresentation(element: ElementTree.Element, parent_base: str) -> Representation:
        base_url = TIDALMusicClientDashUtils.getbaseurl(element, parent_base)
        template = element.find('SegmentTemplate')
        seg_template = TIDALMusicClientDashUtils.parsesegmenttemplate(template) if template is not None else None
        seg_list_el = element.find('SegmentList')
        seg_list = TIDALMusicClientDashUtils.parsesegmentlist(seg_list_el) if seg_list_el is not None else None
        return Representation(id=element.get('id'), bandwidth=element.get('bandwidth'), codec=element.get('codecs'), base_url=base_url, segment_template=seg_template, segment_list=seg_list)
    '''parsesegmenttemplate'''
    @staticmethod
    def parsesegmenttemplate(element: ElementTree.Element) -> SegmentTemplate:
        timeline_el = element.find('SegmentTimeline')
        template = SegmentTemplate(media=element.get('media'), initialization=element.get('initialization'), start_number=int(element.get('startNumber') or 1), timescale=int(element.get('timescale') or 1), presentation_time_offset=int(element.get('presentationTimeOffset') or 0))
        if timeline_el is not None: template.timeline.extend(SegmentTimelineEntry(start_time=(int(t) if (t := s.get('t')) else None), duration=int(s.get('d')), repeat=int(s.get('r') or 0)) for s in timeline_el.findall('S'))
        return template
    '''parsesegmentlist'''
    @staticmethod
    def parsesegmentlist(element: ElementTree.Element) -> SegmentList:
        init_el = element.find('Initialization')
        initialization = init_el.get('sourceURL') if init_el is not None else None
        media_segments = [seg.get('media') for seg in element.findall('SegmentURL') if seg.get('media')]
        return SegmentList(initialization=initialization, media_segments=media_segments)
    '''completeurl'''
    @staticmethod
    def completeurl(template: str, base_url: str, representation: Representation, *, number: Optional[int] = None, time: Optional[int] = None) -> str:
        mapping = {'$RepresentationID$': representation.id, '$Bandwidth$': representation.bandwidth, '$Number$': None if number is None else str(number), '$Time$': None if time is None else str(time)}
        result = reduce(lambda s, kv: s.replace(kv[0], kv[1]), ((k, v) for k, v in mapping.items() if v is not None), template)
        result = result.replace('$$', '$')
        return urljoin(base_url, result)
    '''buildsegmentlist'''
    @staticmethod
    def buildsegmentlist(segment_list: SegmentList, base_url: str) -> List[str]:
        segments: List[str] = []
        if segment_list.initialization: segments.append(urljoin(base_url, segment_list.initialization))
        for media in segment_list.media_segments: segments.append(urljoin(base_url, media))
        return segments
    '''buildsegmenttemplate'''
    @staticmethod
    def buildsegmenttemplate(template: SegmentTemplate, base_url: str, representation: Representation) -> List[str]:
        segments: List[str] = []
        number = template.start_number
        current_time: Optional[int] = None
        if template.initialization: segments.append(TIDALMusicClientDashUtils.completeurl(template.initialization, base_url, representation))
        for entry in template.timeline:
            current_time = entry.start_time if entry.start_time is not None else (template.presentation_time_offset if current_time is None else current_time)
            for _ in range(entry.repeat + 1): media = template.media; media and segments.append(TIDALMusicClientDashUtils.completeurl(media, base_url, representation, number=number, time=current_time)); number += 1; current_time = (current_time + entry.duration) if current_time is not None else None
        return segments


'''TIDALMusicClientUtils'''
class TIDALMusicClientUtils:
    SESSION_STORAGE = SessionStorage()
    ALBUM_COVER_CACHE: Dict[str, bytes] = {}
    MUSIC_QUALITIES = [('hi_res_lossless', 'HI_RES_LOSSLESS'), ('high_lossless', 'LOSSLESS'), ('low_320k', 'HIGH'), ('low_96k', 'LOW')]
    COVER_CANDIDATES = ["cover.jpg", "folder.jpg", "front.jpg", "Cover.jpg", "Folder.jpg", "Front.jpg", "cover.jpeg", "folder.jpeg", "front.jpeg", "cover.png", "folder.png", "front.png"]
    '''ffmpegready'''
    @staticmethod
    def ffmpegready() -> bool: return bool(shutil.which("ffmpeg") is not None)
    '''pyavready'''
    @staticmethod
    def pyavready() -> bool: return bool(optionalimport('av') is not None)
    '''flacremuxavailable'''
    @staticmethod
    def flacremuxavailable() -> bool: return TIDALMusicClientUtils.ffmpegready() or TIDALMusicClientUtils.pyavready()
    '''decryptsecuritytoken'''
    @staticmethod
    def decryptsecuritytoken(security_token):
        master_key = 'UIlTTEMmmLfGowo/UC60x2H45W6MdGgTRfo/umg4754='
        master_key = base64.b64decode(master_key)
        security_token = base64.b64decode(security_token)
        iv, encrypted_st = security_token[:16], security_token[16:]
        decryptor = AES.new(master_key, AES.MODE_CBC, iv)
        decrypted_st = decryptor.decrypt(encrypted_st)
        key, nonce = decrypted_st[:16], decrypted_st[16:24]
        return key, nonce
    '''decryptfile'''
    @staticmethod
    def decryptfile(efile, dfile, key, nonce):
        counter = Counter.new(64, prefix=nonce, initial_value=0)
        decryptor = AES.new(key, AES.MODE_CTR, counter=counter)
        with open(efile, 'rb') as eflac:
            flac = decryptor.decrypt(eflac.read())
            with open(dfile, 'wb') as dflac: dflac.write(flac)
    '''decryptdownloadedaudio'''
    @staticmethod
    def decryptdownloadedaudio(stream: StreamUrl, src_path: str, desc_path: str) -> str:
        if aigpy.string.isNull(stream.encryptionKey): replacefile(src_path, desc_path); return desc_path
        key, nonce = TIDALMusicClientUtils.decryptsecuritytoken(stream.encryptionKey)
        TIDALMusicClientUtils.decryptfile(src_path, desc_path, key, nonce)
        try: os.remove(src_path)
        except Exception: pass
        return desc_path
    '''guessstreamextension'''
    @staticmethod
    def guessstreamextension(stream: StreamUrl) -> str:
        candidates = []
        if stream.url: candidates.append(stream.url)
        if stream.urls: candidates.extend(stream.urls)
        if (ext := next((e for c in candidates if c for s in (c.split("?")[0].lower(),) for e in (".flac", ".mp4", ".m4a", ".m4b", ".mp3", ".ogg", ".aac") if s.endswith(e)), None)) is not None: return ext
        codec = (stream.codec or "").lower()
        if "flac" in codec: return ".flac"
        if "mp4" in codec or "m4a" in codec or "aac" in codec: return ".m4a"
        return ".m4a"
    '''getexpectedextension'''
    @staticmethod
    def getexpectedextension(stream: StreamUrl):
        url, codec = (stream.url or '').lower(), (stream.codec or '').lower()
        if '.flac' in url: return '.flac'
        if ".mp4" in url: return ".mp4" if ("ac4" in codec or "mha1" in codec) else (".flac" if "flac" in codec else ".m4a")
        return '.m4a'
    '''shouldremuxflac'''
    @staticmethod
    def shouldremuxflac(download_ext: str, final_ext: str, stream: StreamUrl) -> bool:
        if final_ext != ".flac" or download_ext == ".flac": return False
        return "flac" in (stream.codec or "").lower()
    '''remuxwithpyav'''
    @staticmethod
    def remuxwithpyav(src_path: str, dest_path: str) -> Tuple[bool, str]:
        if not TIDALMusicClientUtils.pyavready(): return False, "PyAV backend unavailable"
        av = optionalimport('av'); assert av is not None
        try:
            with av.open(src_path) as container:
                audio_stream = next((s for s in container.streams if s.type == "audio"), None)
                if audio_stream is None: return False, "PyAV could not locate an audio stream"
                with av.open(dest_path, mode="w", format="flac") as output:
                    out_stream = output.add_stream(template=audio_stream)
                    for pkt in container.demux(audio_stream):
                        if pkt.dts is None: continue
                        pkt.stream = out_stream; output.mux(pkt)
        except Exception as exc:
            return False, f"PyAV error: {exc}"
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0, "PyAV"
    '''remuxwithffmpeg'''
    @staticmethod
    def remuxwithffmpeg(src_path: str, dest_path: str) -> Tuple[bool, str]:
        if not TIDALMusicClientUtils.ffmpegready(): return False, "ffmpeg backend unavailable"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src_path, "-map", "0:a:0", "-c:a", "copy", dest_path]
        try: subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as exc: return False, f"ffmpeg exited with code {exc.returncode}"
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0, "ffmpeg"
    '''remuxflacstream'''
    @staticmethod
    def remuxflacstream(src_path: str, dest_path: str) -> Tuple[str, Optional[str]]:
        if os.path.exists(dest_path): os.remove(dest_path)
        last_reason: Optional[str] = None
        for backend in (TIDALMusicClientUtils.remuxwithpyav, TIDALMusicClientUtils.remuxwithffmpeg):
            ok, reason = backend(src_path, dest_path)
            if ok: return dest_path, reason
            last_reason = reason
            if os.path.exists(dest_path): os.remove(dest_path)
        if last_reason: raise RuntimeError(last_reason)
        return src_path, last_reason
    '''extractmediatags'''
    @staticmethod
    def extractmediatags(track: Track, album: Optional[Album]) -> list[str]:
        tags: list[str] = []
        for source in (getattr(track, "mediaMetadata", None), getattr(album, "mediaMetadata", None) if album else None):
            if source and getattr(source, "tags", None):
                tags = [tag for tag in source.tags if tag]
                if tags: break
        return tags
    '''collectcontributorroles'''
    @staticmethod
    def collectcontributorroles(contributors: Optional[dict]) -> dict[str, list[str]]:
        role_map: dict[str, list[str]] = defaultdict(list)
        items = contributors.get("items") if contributors else None
        if not isinstance(items, list): return role_map
        for e in items:
            if isinstance(e, dict) and (role := e.get("role")) and (name := e.get("name")):
                key = f"CREDITS_{str(role).upper().replace(' ', '_')}"
                role_map[key].append(str(name)) if name not in role_map[key] else None
        return role_map
    '''formatgain'''
    @staticmethod
    def formatgain(value: Optional[Any]) -> Optional[str]:
        if value is None: return None
        try: return f"{float(value):.2f} dB"
        except (TypeError, ValueError): return str(value)
    '''formatpeak'''
    @staticmethod
    def formatpeak(value: Optional[Any]) -> Optional[str]:
        if value is None: return None
        try: return f"{float(value):.6f}"
        except (TypeError, ValueError): return str(value)
    '''setflacaudiotag'''
    @staticmethod
    def setflacaudiotag(audio: FLAC, key: str, value: Any) -> None:
        if value is None: return
        xs = value if isinstance(value, (list, tuple, set)) else [value]
        xs = [("1" if x else "0") if isinstance(x, bool) else str(x).strip() for x in xs if x is not None]
        if (xs := [x for x in xs if x]): audio[key] = xs
    '''updateflacmetadata'''
    @staticmethod
    def updateflacmetadata(filepath: str, track: Track, album: Optional[Album], contributors: Optional[dict], stream: Optional[StreamUrl]) -> None:
        audio = FLAC(filepath)
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_TRACK_ID", track.id)
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_TRACK_VERSION", track.version)
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_TRACK_POPULARITY", track.popularity)
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_STREAM_START_DATE", track.streamStartDate)
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_EXPLICIT", track.explicit)
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_AUDIO_QUALITY", getattr(track, "audioQuality", None))
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_AUDIO_MODES", getattr(track, "audioModes", None) or [])
        TIDALMusicClientUtils.setflacaudiotag("TIDAL_MEDIA_METADATA_TAGS", TIDALMusicClientUtils.extractmediatags(track, album))
        TIDALMusicClientUtils.setflacaudiotag("REPLAYGAIN_TRACK_GAIN", TIDALMusicClientUtils.formatgain(getattr(track, "replayGain", None)))
        TIDALMusicClientUtils.setflacaudiotag("REPLAYGAIN_TRACK_PEAK", TIDALMusicClientUtils.formatpeak(getattr(track, "peak", None)))
        if album is not None: TIDALMusicClientUtils.setflacaudiotag("TIDAL_ALBUM_ID", album.id); TIDALMusicClientUtils.setflacaudiotag("TIDAL_ALBUM_VERSION", album.version); TIDALMusicClientUtils.setflacaudiotag("BARCODE", getattr(album, "upc", None)); TIDALMusicClientUtils.setflacaudiotag("TIDAL_ALBUM_POPULARITY", getattr(album, "popularity", None)); TIDALMusicClientUtils.setflacaudiotag("DATE", album.releaseDate); TIDALMusicClientUtils.setflacaudiotag("TIDAL_ALBUM_STREAM_START_DATE", getattr(album, "streamStartDate", None)); TIDALMusicClientUtils.setflacaudiotag("TIDAL_ALBUM_AUDIO_QUALITY", getattr(album, "audioQuality", None)); TIDALMusicClientUtils.setflacaudiotag("TIDAL_ALBUM_AUDIO_MODES", getattr(album, "audioModes", None) or [])
        if stream is not None: TIDALMusicClientUtils.setflacaudiotag("CODEC", stream.codec); TIDALMusicClientUtils.setflacaudiotag("TIDAL_STREAM_SOUND_QUALITY", stream.soundQuality); TIDALMusicClientUtils.setflacaudiotag("BITS_PER_SAMPLE", stream.bitDepth); TIDALMusicClientUtils.setflacaudiotag("SAMPLERATE", stream.sampleRate)
        if track.trackNumberOnPlaylist: TIDALMusicClientUtils.setflacaudiotag("TIDAL_PLAYLIST_TRACK_NUMBER", track.trackNumberOnPlaylist)
        copyright_text = track.copyRight or (getattr(album, "copyright", None) if album else None)
        TIDALMusicClientUtils.setflacaudiotag("COPYRIGHT", copyright_text)
        contributor_roles = TIDALMusicClientUtils.collectcontributorroles(contributors)
        for role_key, names in contributor_roles.items(): TIDALMusicClientUtils.setflacaudiotag(role_key, names)
        if contributor_roles: TIDALMusicClientUtils.setflacaudiotag("TIDAL_CREDITS", [name for names in contributor_roles.values() for name in names])
        TIDALMusicClientUtils.setflacaudiotag("URL", f"https://listen.tidal.com/track/{track.id}")
        if album is not None and album.id is not None: TIDALMusicClientUtils.setflacaudiotag("URL_OFFICIAL_RELEASE_SITE", f"https://listen.tidal.com/album/{album.id}")
        audio.save()
    '''getcoverurl'''
    @staticmethod
    def getcoverurl(sid: str, width="320", height="320"):
        if sid is None: return ""
        return f"https://resources.tidal.com/images/{sid.replace('-', '/')}/{width}x{height}.jpg"
    '''parsecontributors'''
    @staticmethod
    def parsecontributors(role_type: str, contributors: Optional[dict]) -> Optional[list[str]]:
        if contributors is None: return None
        try: return [it["name"] for it in contributors["items"] if it["role"] == role_type]
        except (KeyError, TypeError): return None
    '''ensureflaccoverartdependenciesready'''
    @staticmethod
    def ensureflaccoverartdependenciesready() -> bool:
        av = optionalimport('av'); Image = optionalimportfrom('PIL', 'Image')
        metaflac_available = shutil.which("metaflac") is not None
        backend_available = bool(av is not None and Image is not None) or bool(shutil.which("ffmpeg") is not None)
        return bool(metaflac_available and backend_available)
    '''ensureflaccoverartisalreadygood'''
    @staticmethod
    def ensureflaccoverartisalreadygood(flac_path: Path, max_px: int) -> bool:
        run_cmd_func = lambda cmd, *, check=True, capture=True: subprocess.run(list(cmd), check=check, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, text=True)
        try: out = run_cmd_func(["metaflac", "--list", "--block-type=PICTURE", str(flac_path)]).stdout
        except subprocess.CalledProcessError: return False
        blocks = out.split("METADATA_BLOCK_PICTURE")
        if len(blocks) != 2: return False
        block = blocks[1].splitlines()
        if not any("type:" in line and " 3 " in line for line in block): return False
        mime = next((line.split(":", 1)[1].strip().lower() for line in block if line.strip().startswith("mime type:")), "")
        if mime != "image/jpeg": return False
        try: width_line = next(line for line in block if line.strip().startswith("width:")).split(); width, height = int(width_line[1][:-2]), int(width_line[3][:-2])
        except (StopIteration, ValueError, IndexError): return False
        return max(width, height) <= max_px
    '''hasmetaflacfrontcover'''
    @staticmethod
    def hasmetaflacfrontcover(flac_path: Path) -> bool:
        run_cmd_func = lambda cmd, *, check=True, capture=True: subprocess.run(list(cmd), check=check, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, text=True)
        try: out = run_cmd_func(["metaflac", "--list", "--block-type=PICTURE", str(flac_path)]).stdout
        except subprocess.CalledProcessError: return False
        return bool(re.compile(r"^\s*type:\s+3\b", re.M).search(out))
    '''exportexistingpicture'''
    @staticmethod
    def exportexistingpicture(flac_path: Path, dest_file: Path) -> bool:
        run_cmd_func = lambda cmd, *, check=True, capture=True: subprocess.run(list(cmd), check=check, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, text=True)
        try: run_cmd_func(["metaflac", f"--export-picture-to={dest_file}", str(flac_path)])
        except subprocess.CalledProcessError: return False
        return dest_file.exists() and dest_file.stat().st_size > 0
    '''findfoldercover'''
    @staticmethod
    def findfoldercover(start_dir: Path) -> Path | None:
        for name in TIDALMusicClientUtils.COVER_CANDIDATES:
            candidate = start_dir / name
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0: return candidate
        return None
    '''importfrontcover'''
    @staticmethod
    def importfrontcover(flac_path: Path, jpg_file: Path) -> None:
        run_cmd_func = lambda cmd, *, check=True, capture=True: subprocess.run(list(cmd), check=check, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, text=True)
        run_cmd_func(["metaflac", "--remove", "--block-type=PICTURE", str(flac_path)], capture=False)
        run_cmd_func(["metaflac", f"--import-picture-from=3|image/jpeg|||{jpg_file}", str(flac_path)], capture=False)
    '''reencodewithffmpeg'''
    @staticmethod
    def reencodewithffmpeg(src_img: Path, out_jpg: Path, max_px: int) -> Tuple[bool, str]:
        if not bool(shutil.which("ffmpeg") is not None): return False, "ffmpeg backend unavailable"
        run_cmd_func = lambda cmd, *, check=True, capture=True: subprocess.run(list(cmd), check=check, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, text=True)
        scale = "scale='min({0},iw)':'min({0},ih)':force_original_aspect_ratio=decrease".format(max_px)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src_img), "-vf", scale, "-q:v", "3", "-pix_fmt", "yuvj420p", str(out_jpg)]
        try: run_cmd_func(cmd)
        except subprocess.CalledProcessError as exc: return False, f"ffmpeg exited with code {exc.returncode}"
        return out_jpg.exists() and out_jpg.stat().st_size > 0, "ffmpeg"
    '''reencodewithpyav'''
    @staticmethod
    def reencodewithpyav(src_img: Path, out_jpg: Path, max_px: int) -> Tuple[bool, str]:
        av = optionalimport('av'); Image = optionalimportfrom('PIL', 'Image')
        if not bool(av is not None and Image is not None): return False, "PyAV backend unavailable"
        try:
            with av.open(str(src_img)) as container:
                stream = next((s for s in container.streams if s.type == "video"), None)
                if stream is None: return False, "PyAV could not locate a video stream"
                frame = next(container.decode(stream), None)
                if frame is None: return False, "PyAV failed to decode the image frame"
                image = frame.to_image()
        except Exception as exc:
            return False, f"PyAV error: {exc}"
        try:
            width, height = image.size; scale = min(1.0, max_px / max(width, height))
            if scale < 1.0: new_size = (max(1, int(width * scale)), max(1, int(height * scale))); image = image.resize(new_size, Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
            image = image.convert("RGB")
            image.save(out_jpg, format="JPEG", quality=85, optimize=True, progressive=False)
        except Exception as exc:
            return False, f"PyAV/Pillow error: {exc}"
        return out_jpg.exists() and out_jpg.stat().st_size > 0, "PyAV"
    '''reencodetobaselinejpeg'''
    @staticmethod
    def reencodetobaselinejpeg(src_img: Path, out_jpg: Path, max_px: int) -> Tuple[bool, str]:
        backends, last_reason = (TIDALMusicClientUtils.reencodewithpyav, TIDALMusicClientUtils.reencodewithffmpeg), ""
        for backend in backends:
            success, detail = backend(src_img, out_jpg, max_px)
            if success: return True, detail
            last_reason = detail
        return False, last_reason or "No available backend"
    '''ensureflaccoverart'''
    @staticmethod
    def ensureflaccoverart(flac_path: str | Path, *, max_px: int = 1400, report: bool = False, fetch_cover: Optional[Callable[[Path], Optional[Path]]] = None) -> bool | Tuple[bool, str]:
        path, status_message = Path(flac_path), ""
        if path.suffix.lower() != ".flac" or not path.exists(): return (False, "Target is not a FLAC file") if report else False
        if not TIDALMusicClientUtils.ensureflaccoverartdependenciesready(): return (False, "Required cover art tools are unavailable") if report else False
        try:
            if TIDALMusicClientUtils.ensureflaccoverartisalreadygood(path, max_px): return (True, "Cover art already meets baseline JPEG requirements") if report else True
            if TIDALMusicClientUtils.hasmetaflacfrontcover(path): return (True, "Cover art already present in FLAC metadata") if report else True
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir); extracted = tmp_path / "extracted_art"; baseline = tmp_path / "cover.jpg"
                have_art = TIDALMusicClientUtils.exportexistingpicture(path, extracted)
                if not have_art:
                    folder_cover = TIDALMusicClientUtils.findfoldercover(path.parent)
                    if folder_cover: extracted, have_art = folder_cover, True
                if not have_art and fetch_cover is not None:
                    try: fetched = fetch_cover(tmp_path)
                    except Exception: fetched = None
                    if fetched is not None and fetched.exists() and fetched.stat().st_size > 0: extracted, have_art = fetched, True
                if not have_art: return (False, "No cover art was found to embed") if report else False
                success, backend = TIDALMusicClientUtils.reencodetobaselinejpeg(extracted, baseline, max_px)
                if not success: return (False, f"Failed to re-encode cover art ({backend})") if report else False
                TIDALMusicClientUtils.importfrontcover(path, baseline)
                return (True, f"Embedded baseline JPEG cover using {backend}") if report else True
        except FileNotFoundError:
            status_message = "metaflac executable was not found"
        except Exception:
            status_message = "Unexpected error while normalising cover art"
        return (False, status_message) if report else False
    '''setmetadata'''
    @staticmethod
    def setmetadata(track: Track, album: Album, filepath: str, contributors: Optional[dict], lyrics: str, stream: Optional[StreamUrl]) -> None:
        is_flac_file = filepath.lower().endswith(".flac")
        obj = aigpy.tag.TagTool(filepath)
        obj.album, obj.title = track.album.title, track.title
        if not aigpy.string.isNull(track.version): obj.title += ' (' + track.version + ')'
        obj.artist = list(map(lambda artist: artist.name, track.artists))
        obj.copyright, obj.tracknumber, obj.discnumber = track.copyRight, track.trackNumber, track.volumeNumber
        obj.composer = TIDALMusicClientUtils.parsecontributors('Composer', contributors)
        obj.isrc, obj.date, obj.totaldisc, obj.lyrics = track.isrc, album.releaseDate, album.numberOfVolumes, lyrics
        obj.albumartist = list(map(lambda artist: artist.name, album.artists))
        if obj.totaldisc <= 1: obj.totaltrack = album.numberOfTracks
        coverpath = TIDALMusicClientUtils.getcoverurl(album.cover, "1280", "1280")
        obj.save(coverpath)
        if is_flac_file: TIDALMusicClientUtils.ensureflaccoverart(filepath, report=True, fetch_cover=TIDALMusicClientUtils.makecoverfetcher(album)); TIDALMusicClientUtils.updateflacmetadata(filepath, track, album, contributors, stream)
    '''downloadcoverbytes'''
    @staticmethod
    def downloadcoverbytes(url: str, album: Optional[Album]) -> Optional[bytes]:
        try: resp = requests.get(url, timeout=30); resp.raise_for_status()
        except Exception: return None
        if not resp.content: return None
        return resp.content
    '''makecoverfetcher'''
    @staticmethod
    def makecoverfetcher(album: Optional["Album"]) -> Optional[Callable[[Path], Optional[Path]]]:
        cover_id = getattr(album, "cover", None) if album else None
        if aigpy.string.isNull(cover_id): return None
        url, cache_key = TIDALMusicClientUtils.getcoverurl(cover_id, "1280", "1280"), str(cover_id)
        def _fetch(tmp_path: Path) -> Optional[Path]:
            destination, cover_bytes = tmp_path / "fallback_cover.jpg", TIDALMusicClientUtils.ALBUM_COVER_CACHE.get(cache_key)
            if cover_bytes is None:
                cover_bytes = TIDALMusicClientUtils.downloadcoverbytes(url, album)
                if cover_bytes is None: return None
                TIDALMusicClientUtils.ALBUM_COVER_CACHE[cache_key] = cover_bytes
            try: destination.write_bytes(cover_bytes)
            except OSError: return None
            return destination
        return _fetch
    '''parsempd'''
    @staticmethod
    def parsempd(xml: bytes) -> Manifest:
        manifest = TIDALMusicClientDashUtils.parsemanifest(xml)
        if any(a.content_type == "audio" and any(r.segments for r in a.representations) for p in manifest.periods for a in p.adaptation_sets): return manifest
        raise ValueError('No playable audio representations were found in MPD manifest.')
    '''tidalhifiapiget'''
    @staticmethod
    def tidalhifiapiget(path, params: Optional[dict] = None, urlpre: str = 'https://api.tidalhifi.com/v1/', request_overrides: dict = None):
        request_overrides, headers, params = request_overrides or {}, {'authorization': f'Bearer {TIDALMusicClientUtils.SESSION_STORAGE.access_token}'}, dict(params or {})
        params['countryCode'] = TIDALMusicClientUtils.SESSION_STORAGE.country_code
        resp = requests.get(urlpre + path, headers=headers, params=params, **request_overrides)
        resp.raise_for_status()
        return resp.json()
    '''getstreamurlofficialapi'''
    @staticmethod
    def getstreamurlofficialapi(song_id, quality: str, request_overrides: dict = None):
        params, request_overrides = {"audioquality": quality, "playbackmode": "STREAM", "assetpresentation": "FULL"}, request_overrides or {}
        data = TIDALMusicClientUtils.tidalhifiapiget(f'tracks/{str(song_id)}/playbackinfopostpaywall', params, request_overrides=request_overrides)
        resp = aigpy.model.dictToModel(data, StreamRespond())
        if "vnd.tidal.bt" in resp.manifestMimeType:
            manifest = json.loads(base64.b64decode(resp.manifest).decode('utf-8'))
            ret = StreamUrl()
            ret.trackid, ret.soundQuality, ret.codec, ret.encryptionKey, ret.url, ret.urls = resp.trackid, resp.audioQuality, manifest['codecs'], manifest['keyId'] if 'keyId' in manifest else "", manifest['urls'][0], [manifest['urls'][0]]
            return ret, data
        elif "dash+xml" in resp.manifestMimeType:
            manifest = TIDALMusicClientUtils.parsempd(base64.b64decode(resp.manifest))
            ret = StreamUrl()
            ret.trackid, ret.soundQuality, audio_reps = resp.trackid, resp.audioQuality, []
            audio_reps.extend(r for p in manifest.periods for a in p.adaptation_sets if a.content_type == "audio" for r in a.representations)
            if not audio_reps: raise ValueError('MPD manifest did not contain any audio representations.')
            representation: Representation = next((rep for rep in audio_reps if rep.segments), audio_reps[0])
            codec = (representation.codec or '').upper()
            if codec.startswith('MP4A'): codec = 'AAC'
            ret.codec, ret.encryptionKey, ret.urls = codec, "", representation.segments
            if len(ret.urls) > 0: ret.url = ret.urls[0]
            return ret, data
        raise Exception("Can't get the streamUrl, type is " + resp.manifestMimeType)
    '''getstreamurlsquidapi'''
    @staticmethod
    def getstreamurlsquidapi(song_id, quality: str, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"}
        data = requests.get(f'https://triton.squid.wtf/track/?id={song_id}&quality={quality}', headers=headers, **request_overrides).json()['data']
        resp = aigpy.model.dictToModel(data, StreamRespond())
        if "vnd.tidal.bt" in resp.manifestMimeType:
            manifest = json.loads(base64.b64decode(resp.manifest).decode('utf-8'))
            ret = StreamUrl()
            ret.trackid, ret.soundQuality, ret.codec, ret.encryptionKey, ret.url, ret.urls = resp.trackid, resp.audioQuality, manifest['codecs'], manifest['keyId'] if 'keyId' in manifest else "", manifest['urls'][0], [manifest['urls'][0]]
            return ret, data
        elif "dash+xml" in resp.manifestMimeType:
            manifest = TIDALMusicClientUtils.parsempd(base64.b64decode(resp.manifest))
            ret = StreamUrl()
            ret.trackid, ret.soundQuality, audio_reps = resp.trackid, resp.audioQuality, []
            audio_reps.extend(r for p in manifest.periods for a in p.adaptation_sets if a.content_type == "audio" for r in a.representations)
            if not audio_reps: raise ValueError('MPD manifest did not contain any audio representations.')
            representation: Representation = next((rep for rep in audio_reps if rep.segments), audio_reps[0])
            codec = (representation.codec or '').upper()
            if codec.startswith('MP4A'): codec = 'AAC'
            ret.codec, ret.encryptionKey, ret.urls = codec, "", representation.segments
            if len(ret.urls) > 0: ret.url = ret.urls[0]
            return ret, data
        raise Exception("Can't get the streamUrl, type is " + resp.manifestMimeType)
    '''getstreamurl'''
    @staticmethod
    def getstreamurl(song_id, quality: str, request_overrides: dict = None):
        for parser in [TIDALMusicClientUtils.getstreamurlsquidapi, TIDALMusicClientUtils.getstreamurlofficialapi]:
            try: stream_url, stream_resp = parser(song_id=song_id, quality=quality, request_overrides=request_overrides); assert stream_url.urls; break
            except Exception: continue
        return stream_url, stream_resp
    '''downloadstreamwithnm3u8dlre'''
    @staticmethod
    def downloadstreamwithnm3u8dlre(stream_url: str, download_path: str, silent: bool = False, random_uuid: str = ''):
        download_path_obj = Path(download_path)
        download_path_obj.parent.mkdir(parents=True, exist_ok=True)
        log_file_path = os.path.join(user_log_dir(appname='musicdl', appauthor='zcjin'), f"musicdl_{random_uuid}.log")
        cmd = [
            "N_m3u8DL-RE", stream_url, "--binary-merge", "--ffmpeg-binary-path", shutil.which('ffmpeg'), "--save-name", download_path_obj.stem, "--save-dir", download_path_obj.parent, 
            "--tmp-dir", download_path_obj.parent, "--log-file-path", log_file_path, "--auto-select", "--save-pattern", download_path_obj.name
        ]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)