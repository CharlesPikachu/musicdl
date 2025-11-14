'''
Function:
    Implementation of TIDALMusicClient utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import sys
import time
import json
import aigpy
import base64
import shutil
import requests
import webbrowser
import subprocess
from .misc import resp2json
from .logger import colorize
from Crypto.Cipher import AES
from Crypto.Util import Counter
from urllib.parse import urljoin
from typing import List, Optional
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict


'''AV'''
try: import av
except: av = None


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


'''SearchDataBase'''
class SearchDataBase(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.limit = 0
        self.offset = 0
        self.totalNumberOfItems = 0


'''Artist'''
class Artist(aigpy.model.ModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = None
        self.name = None
        self.type = None
        self.picture = None


'''SearchArtists'''
class SearchArtists(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Artist()


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
        self.explicit = False
        self.audioQuality = None
        self.audioModes = None
        self.artist = Artist()
        self.artists = Artist()


'''SearchAlbums'''
class SearchAlbums(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Album()


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
        self.copyRight = None
        self.artist = Artist()
        self.artists = Artist()
        self.album = Album()
        self.allowStreaming = False
        self.playlist = None


'''SearchTracks'''
class SearchTracks(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Track()


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


'''SearchVideos'''
class SearchVideos(SearchDataBase):
    def __init__(self) -> None:
        super().__init__()
        self.items = Video()


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
    '''segments'''
    @property
    def segments(self) -> List[str]:
        if self.segment_list is not None:
            return buildsegmentlist(self.segment_list, self.base_url)
        if self.segment_template is not None:
            return buildsegmenttemplate(self.segment_template, self.base_url, self)
        return []


'''buildsegmentlist'''
def buildsegmentlist(segment_list: SegmentList, base_url: str) -> List[str]:
    segments: List[str] = []
    if segment_list.initialization:
        segments.append(urljoin(base_url, segment_list.initialization))
    for media in segment_list.media_segments:
        segments.append(urljoin(base_url, media))
    return segments


'''completeurl'''
def completeurl(template: str, base_url: str, representation: Representation, *, number: Optional[int] = None, time: Optional[int] = None) -> str:
    mapping = {
        '$RepresentationID$': representation.id, '$Bandwidth$': representation.bandwidth, '$Number$': None if number is None else str(number),
        '$Time$': None if time is None else str(time),
    }
    result = template
    for placeholder, value in mapping.items():
        if value is not None:
            result = result.replace(placeholder, value)
    result = result.replace('$$', '$')
    return urljoin(base_url, result)


'''buildsegmenttemplate'''
def buildsegmenttemplate(template: SegmentTemplate, base_url: str, representation: Representation) -> List[str]:
    segments: List[str] = []
    if template.initialization:
        segments.append(completeurl(template.initialization, base_url, representation))
    number = template.start_number
    current_time: Optional[int] = None
    for entry in template.timeline:
        if entry.start_time is not None:
            current_time = entry.start_time
        elif current_time is None:
            current_time = template.presentation_time_offset
        for _ in range(entry.repeat + 1):
            media = template.media
            if media:
                segments.append(completeurl(media, base_url, representation, number=number, time=current_time))
            number += 1
            if current_time is not None:
                current_time += entry.duration
    return segments


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
    device_code: str = None
    user_code: str = None
    '''tojsonbytes'''
    def tojsonbytes(self):
        data = asdict(self)
        if self.expires is not None:
            data["expires"] = self.expires.isoformat()
        else:
            data["expires"] = None
        return json.dumps(data).encode("utf-8")
    '''fromjsonbytes'''
    @classmethod
    def fromjsonbytes(cls, b: bytes):
        data = json.loads(b.decode("utf-8"))
        if data.get("expires"):
            data["expires"] = datetime.fromisoformat(data["expires"])
        else:
            data["expires"] = None
        return cls(**data)
    '''saveencrypted'''
    def saveencrypted(self, path: str, key: bytes = b'3BxQiWxi32p7SCr9SEjGH2Yzj90lxf0EfQ6bi8Vr0dM='):
        f = Fernet(key)
        encrypted = f.encrypt(self.tojsonbytes())
        with open(path, "wb") as fw:
            fw.write(encrypted)
    '''loadencrypted'''
    @classmethod
    def loadencrypted(cls, path: str, key: bytes = b'3BxQiWxi32p7SCr9SEjGH2Yzj90lxf0EfQ6bi8Vr0dM='):
        f = Fernet(key)
        with open(path, "rb") as fr:
            encrypted = fr.read()
        decrypted = f.decrypt(encrypted)
        return cls.fromjsonbytes(decrypted)


'''TIDALTvSession'''
class TIDALTvSession():
    CANDIDATED_CLIENT_ID_SECRETS = [
        {'client_id': '7m7Ap0JC9j1cOM3n', 'client_secret': 'vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY='},
        {'client_id': '8SEZWa4J1NVC5U5Y', 'client_secret': 'owUYDkxddz+9FpvGX24DlxECNtFEMBxipU0lBfrbq60='},
        {'client_id': 'zU4XHVVkc2tDPo4t', 'client_secret': 'VJKhDFqJPqvsPVNBV6ukXTJmwlvbttP7wlMlrc72se4='},
    ]
    def __init__(self, client_id: str = '7m7Ap0JC9j1cOM3n', client_secret: str = 'vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY=',
                 headers: dict = {}, cookies: dict = {}):
        self.session = requests.Session()
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {'User-Agent': 'TIDAL_ANDROID/1039 okhttp/3.14.9'}
        self.headers.update(headers)
        self.cookies = cookies
        self.storage = SessionStorage()
    '''auth'''
    def auth(self, request_overrides: dict = {}):
        # init
        outputs = dict(
            ok=False, client_id=self.client_id, client_secret=self.client_secret, reason="",
            device_authorization=dict(device_code=None, user_code=None, verification_url=None, auth_check_timeout=None, auth_check_interval=None),
            token=dict(access_token=None, refresh_token=None, expires_in=None), sessions=dict(user_id=None, country_code=None),
        )
        base_url = 'https://auth.tidal.com/v1'
        if 'headers' not in request_overrides: request_overrides['headers'] = self.headers
        if 'cookies' not in request_overrides: request_overrides['cookies'] = self.cookies
        # device authorization
        try:
            resp = self.session.post(f'{base_url}/oauth2/device_authorization', data={'client_id': self.client_id, 'scope': 'r_usr+w_usr+w_sub'}, **request_overrides)
            resp.raise_for_status()
            device_authorization_results = resp2json(resp=resp)
            outputs['device_authorization'] = dict(
                device_code=device_authorization_results['deviceCode'], user_code=device_authorization_results['userCode'], 
                verification_url=device_authorization_results['verificationUri'], auth_check_timeout=device_authorization_results['expiresIn'], 
                auth_check_interval=device_authorization_results['interval']
            )
            self.storage.user_code = device_authorization_results['userCode']
            self.storage.device_code = device_authorization_results['deviceCode']
        except Exception as err:
            outputs['reason'] = f'Device authorization error: {err}'
            return outputs
        # token
        data = {
            'client_id': self.client_id, 'device_code': device_authorization_results['deviceCode'], 'client_secret': self.client_secret,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code', 'scope': 'r_usr+w_usr+w_sub',
        }
        user_login_url = 'https://link.tidal.com/' + device_authorization_results['userCode']
        # --if not ssh to server to use musicdl, auto open user_login_url with webbrowser
        is_remote = bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"))
        if not is_remote:
            try:
                webbrowser.open(user_login_url, new=2)
            except:
                pass
        # --print tips in terminal
        msg = f'Opening {user_login_url} in the browser, log in or sign up to TIDAL manually to continue (in 300 seconds please).'
        print(colorize("TIDAL LOGIN REQUIRED:", 'highlight'))
        print(colorize(msg, 'highlight'))
        # --use tkinter to show tips
        has_display = (
            sys.platform.startswith("win") or sys.platform == "darwin" or bool(os.environ.get("DISPLAY"))
        )
        if has_display:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            messagebox.showinfo("TIDAL Login Required", msg, parent=root)
            root.destroy()
        # --checking user log in or sign up status
        while True:
            resp = self.session.post(f'{base_url}/oauth2/token', data=data, **request_overrides)
            if resp.status_code not in [400]: break
            time.sleep(0.2)
        # --extract required information
        try:
            resp.raise_for_status()
            token_results = resp2json(resp=resp)
            outputs['token'] = dict(
                access_token=token_results['access_token'], refresh_token=token_results['refresh_token'], expires_in=token_results['expires_in']
            )
            self.storage.access_token = token_results['access_token']
            self.storage.refresh_token = token_results['refresh_token']
            self.storage.expires = datetime.now() + timedelta(seconds=token_results['expires_in'])
        except Exception as err:
            outputs['reason'] = f'Token error: {err}'
            return outputs
        # sessions
        request_overrides.pop('headers', {})
        try:
            resp = self.session.get('https://api.tidal.com/v1/sessions', headers=self.auth_headers, **request_overrides)
            resp.raise_for_status()
            sessions_results = resp2json(resp=resp)
            user_id, country_code = sessions_results['userId'], sessions_results['countryCode']
            outputs['sessions'] = dict(user_id=user_id, country_code=country_code)
            self.storage.user_id = user_id
            self.storage.country_code = country_code
        except Exception as err:
            outputs['reason'] = f'Sessions error: {err}'
            return outputs
        # users
        try:
            resp = self.session.get(f'https://api.tidal.com/v1/users/{user_id}?countryCode={country_code}', headers=self.auth_headers, **request_overrides)
            resp.raise_for_status()
        except Exception as err:
            outputs['reason'] = f'Users error: {err}'
            return outputs
        # return
        outputs.update(dict(
            ok=True, reason=f'Successful Routing: {base_url}/oauth2/device_authorization >>> {base_url}/oauth2/token >>> https://api.tidal.com/v1/sessions >>> https://api.tidal.com/v1/users/{user_id}?countryCode={country_code}'
        ))
        return outputs
    '''refresh'''
    def refresh(self, request_overrides: dict = {}):
        # assert
        assert self.storage.access_token is not None
        # refresh
        base_url = 'https://auth.tidal.com/v1'
        resp = self.session.post(
            f'{base_url}/oauth2/token', 
            data={'refresh_token': self.storage.refresh_token, 'client_id': self.client_id, 'client_secret': self.client_secret, 'grant_type': 'refresh_token'},
            **request_overrides
        )
        resp.raise_for_status()
        token_results = resp2json(resp=resp)
        results = dict(
            refresh_token=token_results.get('refresh_token'), expires=datetime.now()+timedelta(seconds=token_results['expires_in']),
            access_token=token_results['access_token']
        )
        self.storage.access_token = results['access_token']
        self.storage.expires = results['expires']
        self.storage.refresh_token = results['refresh_token'] if results['refresh_token'] else self.storage.refresh_token
        # return
        return results
    '''auth_headers'''
    @property
    def auth_headers(self):
        return {
            'X-Tidal-Token': self.client_id, 'Authorization': 'Bearer {}'.format(self.storage.access_token), 'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip', 'User-Agent': 'TIDAL_ANDROID/1039 okhttp/3.14.9'
        }
    '''cache'''
    def cache(self, cache_file_path: str = ''):
        if not cache_file_path:
            cache_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tidal_tv_session.enc')
        self.storage.saveencrypted(path=cache_file_path)
    '''loadfromcache'''
    def loadfromcache(self, cache_file_path: str = ''):
        if not cache_file_path:
            cache_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tidal_tv_session.enc')
        if os.path.exists(cache_file_path):
            self.storage = self.storage.loadencrypted(path=cache_file_path)
            return True
        else:
            return False


'''decryptsecuritytoken'''
def decryptsecuritytoken(security_token):
    master_key = 'UIlTTEMmmLfGowo/UC60x2H45W6MdGgTRfo/umg4754='
    master_key = base64.b64decode(master_key)
    security_token = base64.b64decode(security_token)
    iv = security_token[:16]
    encrypted_st = security_token[16:]
    decryptor = AES.new(master_key, AES.MODE_CBC, iv)
    decrypted_st = decryptor.decrypt(encrypted_st)
    key = decrypted_st[:16]
    nonce = decrypted_st[16:24]
    return key, nonce


'''decryptfile'''
def decryptfile(efile, dfile, key, nonce):
    counter = Counter.new(64, prefix=nonce, initial_value=0)
    decryptor = AES.new(key, AES.MODE_CTR, counter=counter)
    with open(efile, 'rb') as eflac:
        flac = decryptor.decrypt(eflac.read())
        with open(dfile, 'wb') as dflac:
            dflac.write(flac)


'''ffmpegready'''
def ffmpegready():
    ffmpeg_available = shutil.which("ffmpeg") is not None
    return ffmpeg_available


'''pyavready'''
def pyavready():
    av_available = av is not None
    return av_available


'''remuxwithpyav'''
def remuxwithpyav(src_path: str, dest_path: str):
    if not pyavready(): return False, "PyAV backend unavailable"
    assert av is not None
    try:
        with av.open(src_path) as container:
            audio_stream = next((s for s in container.streams if s.type == "audio"), None)
            if audio_stream is None:
                return False, "PyAV could not locate an audio stream"
            with av.open(dest_path, mode="w", format="flac") as output:
                out_stream = output.add_stream(template=audio_stream)
                for packet in container.demux(audio_stream):
                    if packet.dts is None:
                        continue
                    packet.stream = out_stream
                    output.mux(packet)
    except Exception as exc:
        return False, f"PyAV error: {exc}"
    return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0, "PyAV"


'''remuxwithffmpeg'''
def remuxwithffmpeg(src_path: str, dest_path: str):
    if not ffmpegready():
        return False, "ffmpeg backend unavailable"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src_path, "-map", "0:a:0", "-c:a", "copy", dest_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        return False, f"ffmpeg exited with code {exc.returncode}"
    return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0, "ffmpeg"


'''remuxflacstream'''
def remuxflacstream(src_path: str, dest_path: str):
    if os.path.exists(dest_path): os.remove(dest_path)
    last_reason: Optional[str] = None
    for backend in (remuxwithpyav, remuxwithffmpeg):
        ok, reason = backend(src_path, dest_path)
        if ok: return dest_path, reason
        last_reason = reason
        if os.path.exists(dest_path): os.remove(dest_path)
    return src_path, last_reason