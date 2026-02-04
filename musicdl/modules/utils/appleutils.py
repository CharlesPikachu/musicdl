'''
Function:
    Implementation of AppleMusicClient Utils, refer to https://github.com/glomatico/gamdl
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import io
import m3u8
import uuid
import json
import base64
import shutil
import datetime
import requests
import subprocess
from enum import Enum
from typing import Any
from pathlib import Path
from xml.dom import minidom
from mutagen.mp4 import MP4
from xml.etree import ElementTree
from dataclasses import dataclass
from platformdirs import user_log_dir
from pywidevine import PSSH, Cdm, Device
from urllib.parse import parse_qs, urlparse
from .misc import safeextractfromdict, resp2json
from pywidevine.license_protocol_pb2 import WidevinePsshData


'''settings'''
FOURCC_MAP = {"h264": "avc1", "h265": "hvc1"}
MEDIA_TYPE_STR_MAP = {1: "Song", 6: "Music Video"}
LEGACY_SONG_CODECS = {"aac-legacy", "aac-he-legacy"}
IMAGE_FILE_EXTENSION_MAP = {"jpeg": ".jpg", "tiff": ".tif"}
MEDIA_RATING_STR_MAP = {0: "None", 1: "Explicit", 2: "Clean"}
MP4_FORMAT_CODECS = ["ec-3", "hvc1", "audio-atmos", "audio-ec3"]
SONG_MEDIA_TYPE = {"song", "songs", "library-songs"}
ALBUM_MEDIA_TYPE = {"album", "albums", "library-albums"}
MUSIC_VIDEO_MEDIA_TYPE = {"music-video", "music-videos", "library-music-videos"}
ARTIST_MEDIA_TYPE = {"artist", "artists", "library-artists"}
UPLOADED_VIDEO_MEDIA_TYPE = {"post", "uploaded-videos"}
PLAYLIST_MEDIA_TYPE = {"playlist", "playlists", "library-playlists"}
UPLOADED_VIDEO_QUALITY_RANK = ["1080pHdVideo", "720pHdVideo", "sdVideoWithPlusAudio", "sdVideo", "sd480pVideo", "provisionalUploadVideo"]
SONG_CODEC_REGEX_MAP = {
    "aac": r"audio-stereo-\d+", "aac-he": r"audio-HE-stereo-\d+", "aac-binaural": r"audio-stereo-\d+-binaural", "aac-downmix": r"audio-stereo-\d+-downmix", "aac-he-binaural": r"audio-HE-stereo-\d+-binaural", 
    "aac-he-downmix": r"audio-HE-stereo-\d+-downmix", "atmos": r"audio-atmos-.*", "ac3": r"audio-ac3-.*", "alac": r"audio-alac-.*",
}
DRM_DEFAULT_KEY_MAPPING = {
    "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed": ("data:text/plain;base64,AAAAOHBzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAABgSEAAAAAAAAAAAczEvZTEgICBI88aJmwY="),
    "com.microsoft.playready": ("data:text/plain;charset=UTF-16;base64,vgEAAAEAAQC0ATwAVwBSAE0ASABFAEEARABFAFIAIAB4AG0AbABuAHMAPQAiAGgAdAB0AHAAOgAvAC8AcwBjAGgAZQBtAGEAcwAuAG0AaQBjAHIAbwBzAG8AZgB0AC4AYwBvAG0ALwBEAFIATQAvADIAMAAwADcALwAwADMALwBQAGwAYQB5AFIAZQBhAGQAeQBIAGUAYQBkAGUAcgAiACAAdgBlAHIAcwBpAG8AbgA9ACIANAAuADMALgAwAC4AMAAiAD4APABEAEEAVABBAD4APABQAFIATwBUAEUAQwBUAEkATgBGAE8APgA8AEsASQBEAFMAPgA8AEsASQBEACAAQQBMAEcASQBEAD0AIgBBAEUAUwBDAEIAQwAiACAAVgBBAEwAVQBFAD0AIgBBAEEAQQBBAEEAQQBBAEEAQQBBAEIAegBNAFMAOQBsAE0AUwBBAGcASQBBAD0APQAiAD4APAAvAEsASQBEAD4APAAvAEsASQBEAFMAPgA8AC8AUABSAE8AVABFAEMAVABJAE4ARgBPAD4APAAvAEQAQQBUAEEAPgA8AC8AVwBSAE0ASABFAEEARABFAFIAPgA="),
    "com.apple.streamingkeydelivery": "skd://itunes.apple.com/P000000000/s1/e1",
}
DEFAULT_SONG_DECRYPTION_KEY = "32b8ade1769e26b1ffb8986352793fc6"
HARDCODED_WVD = """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QrSyZcBqHO0QrdPcU35GBT7S7+IJr2AAXvnjqnb8yrtpPWN2ZW/IWUJN2z4vZ7/HV4aj3OZhkxC1DIMNyvsusUKoQQuf8gwKiEe8cFwbwFSicywlFk9la2IPe8oFShcxAzHLCCn/TIYUAvEL3/4LgaZvqWm80qCPYbgIP5HT8hPYkKWJ4WYknEWK+3InbnkzteFfGrQFCq4CCAESEGnj6Ji7LD+4o7MoHYT4jBQYjtW+kQUijgIwggEKAoIBAQDY9um1ifBRIOmkPtDZTqH+CZUBbb0eK0Cn3NHFf8MFUDzPEz+emK/OTub/hNxCJCao//pP5L8tRNUPFDrrvCBMo7Rn+iUb+mA/2yXiJ6ivqcN9Cu9i5qOU1ygon9SWZRsujFFB8nxVreY5Lzeq0283zn1Cg1stcX4tOHT7utPzFG/ReDFQt0O/GLlzVwB0d1sn3SKMO4XLjhZdncrtF9jljpg7xjMIlnWJUqxDo7TQkTytJmUl0kcM7bndBLerAdJFGaXc6oSY4eNy/IGDluLCQR3KZEQsy/mLeV1ggQ44MFr7XOM+rd+4/314q/deQbjHqjWFuVr8iIaKbq+R63ShAgMBAAEo8CISgAMii2Mw6z+Qs1bvvxGStie9tpcgoO2uAt5Zvv0CDXvrFlwnSbo+qR71Ru2IlZWVSbN5XYSIDwcwBzHjY8rNr3fgsXtSJty425djNQtF5+J2jrAhf3Q2m7EI5aohZGpD2E0cr+dVj9o8x0uJR2NWR8FVoVQSXZpad3M/4QzBLNto/tz+UKyZwa7Sc/eTQc2+ZcDS3ZEO3lGRsH864Kf/cEGvJRBBqcpJXKfG+ItqEW1AAPptjuggzmZEzRq5xTGf6or+bXrKjCpBS9G1SOyvCNF1k5z6lG8KsXhgQxL6ADHMoulxvUIihyPY5MpimdXfUdEQ5HA2EqNiNVNIO4qP007jW51yAeThOry4J22xs8RdkIClOGAauLIl0lLA4flMzW+VfQl5xYxP0E5tuhn0h+844DslU8ZF7U1dU2QprIApffXD9wgAACk26Rggy8e96z8i86/+YYyZQkc9hIdCAERrgEYCEbByzONrdRDs1MrS/ch1moV5pJv63BIKvQHGvLkaFwoMY29tcGFueV9uYW1lEgd1bmtub3duGioKCm1vZGVsX25hbWUSHEFuZHJvaWQgU0RLIGJ1aWx0IGZvciB4ODZfNjQaGwoRYXJjaGl0ZWN0dXJlX25hbWUSBng4Nl82NBodCgtkZXZpY2VfbmFtZRIOZ2VuZXJpY194ODZfNjQaIAoMcHJvZHVjdF9uYW1lEhBzZGtfcGhvbmVfeDg2XzY0GmMKCmJ1aWxkX2luZm8SVUFuZHJvaWQvc2RrX3Bob25lX3g4Nl82NC9nZW5lcmljX3g4Nl82NDo5L1BTUjEuMTgwNzIwLjAxMi80OTIzMjE0OnVzZXJkZWJ1Zy90ZXN0LWtleXMaHgoUd2lkZXZpbmVfY2RtX3ZlcnNpb24SBjE0LjAuMBokCh9vZW1fY3J5cHRvX3NlY3VyaXR5X3BhdGNoX2xldmVsEgEwMg4QASAAKA0wAEAASABQAA=="""
APPLE_MUSIC_COOKIE_DOMAIN = ".music.apple.com"
AMP_API_URL = "https://amp-api.music.apple.com"
ITUNES_PAGE_API_URL = "https://music.apple.com"
APPLE_MUSIC_HOMEPAGE_URL = "https://music.apple.com"
ITUNES_LOOKUP_API_URL = "https://itunes.apple.com/lookup"
WEBPLAYBACK_API_URL = "https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/webPlayback"
LICENSE_API_URL = "https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/acquireWebPlaybackLicense"
STOREFRONT_IDS = {
    "AE": "143481-2,32", "AG": "143540-2,32", "AI": "143538-2,32", "AL": "143575-2,32", "AM": "143524-2,32", "AO": "143564-2,32", "AR": "143505-28,32", "AT": "143445-4,32",
    "AU": "143460-27,32", "AZ": "143568-2,32", "BB": "143541-2,32", "BE": "143446-2,32", "BF": "143578-2,32", "BG": "143526-2,32", "BH": "143559-2,32", "BJ": "143576-2,32",
    "BM": "143542-2,32", "BN": "143560-2,32", "BO": "143556-28,32", "BR": "143503-15,32", "BS": "143539-2,32", "BT": "143577-2,32", "BW": "143525-2,32", "BY": "143565-2,32",
    "BZ": "143555-2,32", "CA": "143455-6,32", "CG": "143582-2,32", "CH": "143459-57,32", "CM": "143574-2,32", "CL": "143483-28,32", "CN": "143465-19,32", "CO": "143501-28,32",
    "CR": "143495-28,32", "CV": "143580-2,32", "CY": "143557-2,32", "CZ": "143489-2,32", "DE": "143443-4,32", "DK": "143458-2,32", "DM": "143545-2,32", "DO": "143508-28,32",
    "DZ": "143563-2,32", "EC": "143509-28,32", "EE": "143518-2,32", "EG": "143516-2,32", "ES": "143454-8,32", "FI": "143447-2,32", "FJ": "143583-2,32", "FM": "143591-2,32",
    "FR": "143442-3,32", "GB": "143444-2,32", "GD": "143546-2,32", "GH": "143573-2,32", "GM": "143584-2,32", "GR": "143448-2,32", "GT": "143504-28,32", "GW": "143585-2,32",
    "GY": "143553-2,32", "HK": "143463-45,32", "HN": "143510-28,32", "HR": "143494-2,32", "HU": "143482-2,32", "ID": "143476-2,32", "IE": "143449-2,32", "IL": "143491-2,32",
    "IN": "143467-2,32", "IS": "143558-2,32", "IT": "143450-7,32", "JM": "143511-2,32", "JO": "143528-2,32", "JP": "143462-9,32", "KE": "143529-2,32", "KG": "143586-2,32",
    "KH": "143579-2,32", "KN": "143548-2,32", "KR": "143466-13,32", "KW": "143493-2,32", "KY": "143544-2,32", "KZ": "143517-2,32", "LA": "143587-2,32", "LB": "143497-2,32",
    "LC": "143549-2,32", "LK": "143486-2,32", "LR": "143588-2,32", "LT": "143520-2,32", "LU": "143451-2,32", "LV": "143519-2,32", "MD": "143523-2,32", "MG": "143531-2,32",
    "MK": "143530-2,32", "ML": "143532-2,32", "MN": "143592-2,32", "MO": "143515-45,32", "MR": "143590-2,32", "MS": "143547-2,32", "MT": "143521-2,32", "MU": "143533-2,32",
    "MW": "143589-2,32", "MX": "143468-28,32", "MY": "143473-2,32", "MZ": "143593-2,32", "NA": "143594-2,32", "NE": "143534-2,32", "NG": "143561-2,32", "NI": "143512-28,32",
    "NL": "143452-10,32", "NO": "143457-2,32", "NP": "143484-2,32", "NZ": "143461-27,32", "OM": "143562-2,32", "PA": "143485-28,32", "PE": "143507-28,32", "PG": "143597-2,32",
    "PH": "143474-2,32", "PK": "143477-2,32", "PL": "143478-2,32", "PT": "143453-24,32", "PW": "143595-2,32", "PY": "143513-28,32", "QA": "143498-2,32", "RO": "143487-2,32",
    "RU": "143469-16,32", "SA": "143479-2,32", "SB": "143601-2,32", "SC": "143599-2,32", "SE": "143456-17,32", "SG": "143464-19,32", "SI": "143499-2,32", "SK": "143496-2,32",
    "SL": "143600-2,32", "SN": "143535-2,32", "SR": "143554-2,32", "ST": "143598-2,32", "SV": "143506-28,32", "SZ": "143602-2,32", "TC": "143552-2,32", "TD": "143581-2,32",
    "TH": "143475-2,32", "TJ": "143603-2,32", "TM": "143604-2,32", "TN": "143536-2,32", "TR": "143480-2,32", "TT": "143551-2,32", "TW": "143470-18,32", "TZ": "143572-2,32",
    "UA": "143492-2,32", "UG": "143537-2,32", "US": "143441-1,32", "UY": "143514-2,32", "UZ": "143566-2,32", "VC": "143550-2,32", "VE": "143502-28,32", "VG": "143543-2,32", 
    "VN": "143471-2,32", "YE": "143571-2,32", "ZA": "143472-2,32", "ZW": "143605-2,32",
}


'''CoverFormat'''
class CoverFormat(Enum):
    JPG = "jpg"
    PNG = "png"
    RAW = "raw"


'''RemuxFormatMusicVideo'''
class RemuxFormatMusicVideo(Enum):
    M4V = "m4v"
    MP4 = "mp4"


'''SyncedLyricsFormat'''
class SyncedLyricsFormat(Enum):
    LRC = "lrc"
    SRT = "srt"
    TTML = "ttml"


'''MediaType'''
class MediaType(Enum):
    SONG = 1
    MUSIC_VIDEO = 6
    def __str__(self): return MEDIA_TYPE_STR_MAP[self.value]
    def __int__(self): return self.value


'''MediaRating'''
class MediaRating(Enum):
    NONE = 0
    EXPLICIT = 1
    CLEAN = 2
    def __str__(self): return MEDIA_RATING_STR_MAP[self.value]
    def __int__(self): return self.value


'''MediaFileFormat'''
class MediaFileFormat(Enum):
    MP4 = "mp4"
    M4V = "m4v"
    M4A = "m4a"


'''DownloadMode'''
class DownloadMode(Enum):
    NM3U8DLRE = "nm3u8dlre"


'''RemuxMode'''
class RemuxMode(Enum):
    FFMPEG = "ffmpeg"
    MP4BOX = "mp4box"


'''SongCodec'''
class SongCodec(Enum):
    AAC_LEGACY = "aac-legacy"
    AAC_HE_LEGACY = "aac-he-legacy"
    AAC = "aac"
    AAC_HE = "aac-he"
    AAC_BINAURAL = "aac-binaural"
    AAC_DOWNMIX = "aac-downmix"
    AAC_HE_BINAURAL = "aac-he-binaural"
    AAC_HE_DOWNMIX = "aac-he-downmix"
    ATMOS = "atmos"
    AC3 = "ac3"
    ALAC = "alac"
    ASK = "ask"
    def islegacy(self): return self.value in LEGACY_SONG_CODECS


'''MusicVideoCodec'''
class MusicVideoCodec(Enum):
    H264 = "h264"
    H265 = "h265"
    ASK = "ask"
    def fourcc(self): return FOURCC_MAP[self.value]


'''MusicVideoResolution'''
class MusicVideoResolution(Enum):
    R240P = "240p"
    R360P = "360p"
    R480P = "480p"
    R540P = "540p"
    R720P = "720p"
    R1080P = "1080p"
    R1440P = "1440p"
    R2160P = "2160p"
    def __int__(self): return int(self.value[:-1])


'''Lyrics'''
@dataclass
class Lyrics:
    synced: str = None
    unsynced: str = None


'''MediaTags'''
@dataclass
class MediaTags:
    album: str = None
    album_artist: str = None
    album_id: int = None
    album_sort: str = None
    artist: str = None
    artist_id: int = None
    artist_sort: str = None
    comment: str = None
    compilation: bool = None
    composer: str = None
    composer_id: int = None
    composer_sort: str = None
    copyright: str = None
    date: datetime.date | str = None
    disc: int = None
    disc_total: int = None
    gapless: bool = None
    genre: str = None
    genre_id: int = None
    lyrics: str = None
    media_type: MediaType = None
    rating: MediaRating = None
    storefront: str = None
    title: str = None
    title_id: int = None
    title_sort: str = None
    track: int = None
    track_total: int = None
    xid: str = None
    '''asmp4tags'''
    def asmp4tags(self, date_format: str = None):
        disc_mp4 = [self.disc if self.disc is not None else 0, self.disc_total if self.disc_total is not None else 0]
        if disc_mp4[0] == 0 and disc_mp4[1] == 0: disc_mp4 = None
        track_mp4 = [self.track if self.track is not None else 0, self.track_total if self.track_total is not None else 0]
        if track_mp4[0] == 0 and track_mp4[1] == 0: track_mp4 = None
        if isinstance(self.date, datetime.date):
            if date_format is None: date_mp4 = self.date.isoformat()
            else: date_mp4 = self.date.strftime(date_format)
        elif isinstance(self.date, str):
            date_mp4 = self.date
        else:
            date_mp4 = None
        mp4_tags = {
            "\xa9alb": self.album, "aART": self.album_artist, "plID": self.album_id, "soal": self.album_sort, "\xa9ART": self.artist, "atID": self.artist_id, "soar": self.artist_sort, "\xa9cmt": self.comment, "xid": self.xid,
            "cpil": bool(self.compilation) if self.compilation is not None else None, "\xa9wrt": self.composer, "cmID": self.composer_id, "soco": self.composer_sort, "cprt": self.copyright, "\xa9day": date_mp4, "trkn": track_mp4, 
            "disk": disc_mp4, "pgap": bool(self.gapless) if self.gapless is not None else None, "\xa9lyr": self.lyrics, "geID": self.genre_id, "stik": int(self.media_type) if self.media_type is not None else None, "\xa9nam": self.title,
            "\xa9gen": self.genre, "rtng": int(self.rating) if self.rating is not None else None, "sfID": self.storefront, "cnID": self.title_id, "sonm": self.title_sort, 
        }
        return {k: ([v] if not isinstance(v, bool) else v) for k, v in mp4_tags.items() if v is not None}


'''PlaylistTags'''
@dataclass
class PlaylistTags:
    playlist_artist: str = None
    playlist_id: int = None
    playlist_title: str = None
    playlist_track: int = None


'''StreamInfo'''
@dataclass
class StreamInfo:
    stream_url: str = None
    widevine_pssh: str = None
    playready_pssh: str = None
    fairplay_key: str = None
    codec: str = None
    width: int = None
    height: int = None


'''StreamInfoAv'''
@dataclass
class StreamInfoAv:
    media_id: str = None
    video_track: StreamInfo = None
    audio_track: StreamInfo = None
    file_format: MediaFileFormat = None


'''DecryptionKey'''
@dataclass
class DecryptionKey:
    kid: str = None
    key: str = None


'''DecryptionKeyAv'''
@dataclass
class DecryptionKeyAv:
    video_track: DecryptionKey = None
    audio_track: DecryptionKey = None


'''DownloadItem'''
@dataclass
class DownloadItem:
    media_metadata: dict = None
    playlist_metadata: dict = None
    random_uuid: str = None
    lyrics: Lyrics = None
    media_tags: MediaTags = None
    extra_tags: dict = None
    playlist_tags: PlaylistTags = None
    stream_info: StreamInfoAv = None
    decryption_key: DecryptionKeyAv = None
    cover_url_template: str = None
    cover_url: str = None
    staged_path: str = None
    final_path: str = None
    playlist_file_path: str = None
    synced_lyrics_path: str = None
    cover_path: str = None
    flat_filter_result: Any = None
    error: Exception = None


'''UrlInfo'''
@dataclass
class UrlInfo:
    storefront: str = None
    type: str = None
    slug: str = None
    id: str = None
    sub_id: str = None
    library_storefront: str = None
    library_type: str = None
    library_id: str = None


'''AppleMusicClientAPIUtils'''
class AppleMusicClientAPIUtils:
    def __init__(self, storefront: str = "us", language: str = "en-US", media_user_token: str | None = None, developer_token: str | None = None) -> None:
        self.storefront = storefront
        self.language = language
        self.media_user_token = media_user_token
        self.token = developer_token
    @property
    def active_subscription(self) -> bool: return safeextractfromdict(getattr(self, "account_info", {}), ['meta', 'subscription', 'active'], False)
    @property
    def account_restrictions(self) -> dict | None: return safeextractfromdict(getattr(self, "account_info", {}), ['data', 0, 'attributes', 'restrictions'], None)
    '''createfromnetscapecookies'''
    @classmethod
    def createfromnetscapecookies(cls, cookies: dict, request_overrides: dict = None, *args, **kwargs) -> "AppleMusicClientAPIUtils":
        request_overrides = request_overrides or {}
        media_user_token = cookies.get('media-user-token')
        if not media_user_token: raise ValueError('"media-user-token" is not configured in cookies.')
        return cls.create(storefront=None, media_user_token=media_user_token, developer_token=None, request_overrides=request_overrides, *args, **kwargs)
    '''createfromwrapper'''
    @classmethod
    def createfromwrapper(cls, wrapper_account_url: str = "http://127.0.0.1:30020/", request_overrides: dict = None, *args, **kwargs) -> "AppleMusicClientAPIUtils":
        request_overrides = request_overrides or {}
        wrapper_account_response = requests.get(wrapper_account_url)
        wrapper_account_response.raise_for_status()
        wrapper_account_info = wrapper_account_response.json()
        return cls.create(storefront=None, media_user_token=wrapper_account_info["music_token"], developer_token=wrapper_account_info["dev_token"], request_overrides=request_overrides, *args, **kwargs)
    '''create'''
    @classmethod
    def create(cls, storefront: str | None = "us", language: str = "en-US", media_user_token: str | None = None, developer_token: str | None = None, request_overrides: dict = None) -> "AppleMusicClientAPIUtils":
        request_overrides = request_overrides or {}
        api = cls(storefront=storefront, language=language, media_user_token=media_user_token, developer_token=developer_token)
        api.initialize(request_overrides=request_overrides)
        return api
    '''initialize'''
    def initialize(self, request_overrides: dict = None) -> None:
        request_overrides = request_overrides or {}
        self.initializeclient(); self.initializetoken(request_overrides=request_overrides); self.initializeaccountinfo(request_overrides=request_overrides)
    '''initializeclient'''
    def initializeclient(self) -> None:
        self.client = requests.Session()
        self.client.headers.update({
            "accept": "*/*", "accept-language": "en-US", "origin": APPLE_MUSIC_HOMEPAGE_URL, "priority": "u=1, i", "referer": APPLE_MUSIC_HOMEPAGE_URL, "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"', "sec-ch-ua-mobile": "?0", 
            "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        })
    '''gettoken'''
    def gettoken(self, request_overrides: dict = None) -> str:
        request_overrides = request_overrides or {}
        resp = self.client.get(APPLE_MUSIC_HOMEPAGE_URL, params={"l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        index_js_uri_match = re.search(r"/(assets/index-legacy[~-][^/\"]+\.js)", resp.text)
        if not index_js_uri_match: raise Exception("index.js URI not found in Apple Music homepage")
        index_js_uri = index_js_uri_match.group(1)
        resp = self.client.get(f"{APPLE_MUSIC_HOMEPAGE_URL}/{index_js_uri}", params={"l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        token_match = re.search('(?=eyJh)(.*?)(?=")', resp.text)
        if not token_match: raise Exception("Token not found in index.js page")
        token = token_match.group(1)
        return token
    '''initializetoken'''
    def initializetoken(self, request_overrides: dict = None) -> None:
        request_overrides = request_overrides or {}
        self.token = self.token or self.gettoken(request_overrides=request_overrides)
        self.client.headers.update({"authorization": f"Bearer {self.token}"})
    '''initializeaccountinfo'''
    def initializeaccountinfo(self, request_overrides: dict = None) -> None:
        request_overrides = request_overrides or {}
        if not self.media_user_token: return
        self.client.cookies.update({"media-user-token": self.media_user_token})
        self.account_info = self.getaccountinfo(request_overrides=request_overrides)
        self.storefront = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
    '''getaccountinfo'''
    def getaccountinfo(self, meta: str | None = "subscription", request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/me/account", params={**({"meta": meta} if meta else {}), **{"l": self.language}}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        account_info = resp2json(resp=resp)
        if not "data" in account_info or (meta and "meta" not in account_info): raise Exception("Error getting account info: ", resp.text)
        return account_info
    '''getsong'''
    def getsong(self, song_id: str, extend: str = "extendedAssetUrls", include: str = "lyrics,albums", request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/songs/{song_id}", params={"extend": extend, "include": include, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        song = resp2json(resp=resp)
        if not ("data" in song): raise Exception("Error getting song: ", resp.text)
        return song
    '''getmusicvideo'''
    def getmusicvideo(self, music_video_id: str, include: str = "albums", request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/music-videos/{music_video_id}", params={"include": include, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        music_video = resp2json(resp=resp)
        if not ("data" in music_video): raise Exception("Error getting music video: ", resp.text)
        return music_video
    '''getuploadedvideo'''
    def getuploadedvideo(self, post_id: str, request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/uploaded-videos/{post_id}", params={"l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        uploaded_video = resp2json(resp=resp)
        if not ("data" in uploaded_video): raise Exception("Error getting uploaded video: ", resp.text)
        return uploaded_video
    '''getalbum'''
    def getalbum(self, album_id: str, extend: str = "extendedAssetUrls", request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/albums/{album_id}", params={"extend": extend, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        album = resp2json(resp=resp)
        if not ("data" in album): raise Exception("Error getting album: ", resp.text)
        return album
    '''getplaylist'''
    def getplaylist(self, playlist_id: str, limit_tracks: int = 300, extend: str = "extendedAssetUrls", request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/playlists/{playlist_id}", params={"limit[tracks]": limit_tracks, "extend": extend, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        playlist = resp2json(resp=resp)
        if not ("data" in playlist): raise Exception("Error getting playlist: ", resp.text)
        return playlist
    '''getartist'''
    def getartist(self, artist_id: str, include: str = "albums,music-videos", limit: int = 100, request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/artists/{artist_id}", params={"include": include, "l": self.language, **{f"limit[{_include}]": limit for _include in include.split(",")}}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        artist = resp2json(resp=resp)
        if not ("data" in artist): raise Exception("Error getting artist:", resp.text)
        return artist
    '''getlibraryalbum'''
    def getlibraryalbum(self, album_id: str, extend: str = "extendedAssetUrls", request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/me/library/albums/{album_id}", params={"extend": extend, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        album = resp2json(resp=resp)
        if not ("data" in album): raise Exception("Error getting library album: ", resp.text)
        return album
    '''getlibraryplaylist'''
    def getlibraryplaylist(self, playlist_id: str, include: str = "tracks", limit: int = 100, extend: str = "extendedAssetUrls", request_overrides: dict = None) -> dict | None:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/me/library/playlists/{playlist_id}", params={"include": include, **{f"limit[{_include}]": limit for _include in include.split(",")}, "extend": extend, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        playlist = resp2json(resp=resp)
        if not ("data" in playlist): raise Exception("Error getting library playlist: ", resp.text)
        return playlist
    '''getsearchresults'''
    def getsearchresults(self, term: str, types: str = "songs,music-videos,albums,playlists,artists", limit: int = 50, offset: int = 0, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{AMP_API_URL}/v1/catalog/{self.storefront}/search", params={"term": term, "types": types, "limit": limit, "offset": offset, "l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        search_results = resp2json(resp=resp)
        if not ("results" in search_results): raise Exception("Error searching: ", resp.text)
        return search_results
    '''extendapidata'''
    def extendapidata(self, api_response: dict, extend: str = "extendedAssetUrls", request_overrides: dict = None):
        request_overrides = request_overrides or {}
        next_uri: str = api_response.get("next")
        if not next_uri: return
        next_uri_params = parse_qs(urlparse(next_uri).query)
        limit = int(next_uri_params["offset"][0])
        while next_uri:
            extended_api_data = self.getextendedapidata(next_uri, limit, extend, request_overrides)
            yield extended_api_data
            next_uri = extended_api_data.get("next")
    '''getextendedapidata'''
    def getextendedapidata(self, next_uri: str, limit: int, extend: str, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.get(AMP_API_URL + next_uri, params={"limit": limit, "extend": extend, "l": self.language, **parse_qs(urlparse(next_uri).query)}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        extended_api_data = resp2json(resp=resp)
        if not ("data" in extended_api_data): raise Exception("Error getting extended API data: ", resp.text)
        return extended_api_data
    '''getwebplayback'''
    def getwebplayback(self, track_id: str, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.post(WEBPLAYBACK_API_URL, json={"salableAdamId": track_id, "language": self.language}, params={"l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        webplayback = resp2json(resp=resp)
        if not ("songList" in webplayback): raise Exception("Error getting webplayback: ", resp.text)
        return webplayback
    '''getlicenseexchange'''
    def getlicenseexchange(self, track_id: str, track_uri: str, challenge: str, key_system: str = "com.widevine.alpha", request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.post(LICENSE_API_URL, json={"challenge": challenge, "key-system": key_system, "uri": track_uri, "adamId": track_id, "isLibrary": False, "user-initiated": True}, params={"l": self.language}, allow_redirects=True, **request_overrides)
        resp.raise_for_status()
        license_exchange = resp2json(resp=resp)
        if not ("license" in license_exchange): raise Exception("Error getting license exchange: ", resp.text)
        return license_exchange


'''AppleMusicClientItunesApiUtils'''
class AppleMusicClientItunesApiUtils:
    def __init__(self, storefront: str = "us", language: str = "en-US") -> None:
        self.storefront = storefront
        self.language = language
        self.initialize()
    '''initialize'''
    def initialize(self) -> None:
        self.initializestorefrontid()
        self.initializeclient()
    '''initializestorefrontid'''
    def initializestorefrontid(self) -> None:
        try: self.storefront_id = STOREFRONT_IDS[self.storefront.upper()]
        except KeyError: raise Exception(f"No storefront id for {self.storefront}")
    '''initializeclient'''
    def initializeclient(self) -> None:
        self.client = requests.Session()
        self.client.headers.update({"X-Apple-Store-Front": f"{self.storefront_id} t:music31"})
    '''getlookupresult'''
    def getlookupresult(self, media_id: str, entity: str = "album", request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.get(ITUNES_LOOKUP_API_URL, params={"id": media_id, "entity": entity, "country": self.storefront, "lang": self.language}, **request_overrides)
        resp.raise_for_status()
        lookup_result = resp2json(resp)
        if ("results" not in lookup_result): raise Exception("Error getting lookup result: ", resp.text)
        return lookup_result
    '''getitunespage'''
    def getitunespage(self, media_type: str, media_id: str, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        resp = self.client.get(f"{ITUNES_PAGE_API_URL}/{media_type}/{media_id}", params={"country": self.storefront, "lang": self.language}, **request_overrides)
        resp.raise_for_status()
        itunes_page = resp2json(resp)
        if ("storePlatformData" not in itunes_page): raise Exception("Error getting iTunes page: ", resp.text)
        return itunes_page


'''AppleMusicClientDownloadSongUtils'''
class AppleMusicClientDownloadSongUtils:
    cdm = Cdm.from_device(Device.loads(HARDCODED_WVD))
    cdm.MAX_NUM_OF_SESSIONS = float("inf")
    '''getrandomuuid4'''
    @staticmethod
    def getrandomuuid4() -> str: return uuid.uuid4().hex
    '''parsedate'''
    @staticmethod
    def parsedate(date: str) -> datetime.datetime: return datetime.datetime.fromisoformat(date.split("Z")[0])
    '''fixkeyid'''
    @staticmethod
    def fixkeyid(input_path: str):
        count = 0
        with open(input_path, "rb+") as f:
            while (data := f.read(4096)):
                pos, i = f.tell(), 0
                while (tenc := max(0, data.find(b"tenc", i))):
                    kid = tenc + 12; f.seek(max(0, pos - 4096) + kid, 0); f.write(bytes.fromhex(f"{count:032}")); count += 1; i = kid + 1
                f.seek(pos, 0)
    '''getmediaidoflibrarymedia'''
    @staticmethod
    def getmediaidoflibrarymedia(library_media_metadata: dict) -> str:
        play_params = safeextractfromdict(library_media_metadata, ['attributes', 'playParams'], {})
        return play_params.get("catalogId", library_media_metadata["id"])
    '''getlyrics'''
    @staticmethod
    def getlyrics(song_metadata: dict, synced_lyrics_format: SyncedLyricsFormat = SyncedLyricsFormat.LRC, apple_music_api: AppleMusicClientAPIUtils = None, request_overrides: dict = None) -> Lyrics | None:
        # no lyrics
        if not safeextractfromdict(song_metadata, ['attributes', 'hasLyrics'], None): return None
        # init
        parse_ttml_timestamp_func = lambda ts: datetime.datetime.fromtimestamp((lambda parts: (int(parts[-2]) * 60 + int(parts[-1])) if (len(parts) == 2 and ":" in ts) else (int(parts[-1]) / 1000) if (len(parts) == 1) else ((int(parts[-3]) * 60) if (len(parts) > 2) else 0) + float(f"{parts[-2]}.{parts[-1]}"))(re.findall(r"\d+", ts)), tz=datetime.timezone.utc)
        get_lyrics_line_srt_func = lambda index, element: (f"{index}\n" f"{parse_ttml_timestamp_func(element.attrib.get('begin')).strftime('%H:%M:%S,%f')[:-3]} --> " f"{parse_ttml_timestamp_func(element.attrib.get('end')).strftime('%H:%M:%S,%f')[:-3]}\n" f"{element.text}\n")
        get_lyrics_line_lrc_func = lambda element: ((lambda ts, text: (lambda ms_new: f"[{((ts + (datetime.timedelta(milliseconds=((int(ms_new[:2]) + 1) * 10))) - datetime.timedelta(microseconds=ts.microsecond)) if int(ms_new[-1]) >= 5 else ts).strftime('%M:%S.%f')[:-4]}]{text}")(ts.strftime("%f")[:-3]))(parse_ttml_timestamp_func(element.attrib.get("begin")), element.text))
        # re-fetch lyrics if need
        if ("relationships" not in song_metadata or "lyrics" not in song_metadata["relationships"]): song_metadata = (apple_music_api.getsong(AppleMusicClientDownloadSongUtils.getmediaidoflibrarymedia(song_metadata), request_overrides=request_overrides))["data"][0]
        lyrics_ttml = safeextractfromdict(song_metadata, ['relationships', 'lyrics', 'data', 0, 'attributes', 'ttml'], None)
        if not lyrics_ttml: return None
        # refactor lyrics
        lyrics_ttml_et, unsynced_lyrics, synced_lyrics, index = ElementTree.fromstring(lyrics_ttml), [], [], 1
        for div in lyrics_ttml_et.iter("{http://www.w3.org/ns/ttml}div"):
            stanza = []; unsynced_lyrics.append(stanza)
            for p in div.iter("{http://www.w3.org/ns/ttml}p"):
                if p.text is not None: stanza.append(p.text)
                if p.attrib.get("begin"):
                    if synced_lyrics_format == SyncedLyricsFormat.LRC: synced_lyrics.append(get_lyrics_line_lrc_func(p))
                    if synced_lyrics_format == SyncedLyricsFormat.SRT: synced_lyrics.append(get_lyrics_line_srt_func(index, p))
                    if synced_lyrics_format == SyncedLyricsFormat.TTML:
                        if not synced_lyrics: synced_lyrics.append(minidom.parseString(lyrics_ttml).toprettyxml())
                        continue
                    index += 1
        # return
        return Lyrics(synced="\n".join(synced_lyrics + ["\n"]) if synced_lyrics else None, unsynced=("\n\n".join(["\n".join(lyric_group) for lyric_group in unsynced_lyrics]) if unsynced_lyrics else None))
    '''getmediadate'''
    @staticmethod
    def getmediadate(media_id: str, itunes_api: AppleMusicClientItunesApiUtils, request_overrides: dict = None) -> datetime.datetime | None:
        lookup_result = itunes_api.getlookupresult(media_id, request_overrides=request_overrides)
        if not lookup_result["results"]: return None
        release_date = safeextractfromdict(lookup_result, ['results', 0, 'releaseDate'], None)
        if not release_date: return None
        parsed_date = AppleMusicClientDownloadSongUtils.parsedate(release_date)
        return parsed_date
    '''gettags'''
    @staticmethod
    def gettags(webplayback: dict, lyrics: str | None = None, use_album_date: bool = False, itunes_api: AppleMusicClientItunesApiUtils = None, request_overrides: dict = None) -> MediaTags:
        webplayback_metadata = safeextractfromdict(webplayback, ['songList', 0, 'assets', 0, 'metadata'], {})
        tags = MediaTags(
            album=webplayback_metadata["playlistName"], album_artist=webplayback_metadata["playlistArtistName"], album_id=int(webplayback_metadata["playlistId"]), album_sort=webplayback_metadata["sort-album"], disc=webplayback_metadata["discNumber"], track_total=webplayback_metadata["trackCount"], 
            artist=webplayback_metadata["artistName"], artist_id=int(webplayback_metadata["artistId"]), artist_sort=webplayback_metadata["sort-artist"], comment=webplayback_metadata.get("comments"), rating=MediaRating(webplayback_metadata["explicit"]), lyrics=lyrics if lyrics else None,
            compilation=webplayback_metadata["compilation"], composer=webplayback_metadata.get("composerName"), composer_id=(int(webplayback_metadata.get("composerId")) if webplayback_metadata.get("composerId") else None), genre=webplayback_metadata.get("genre"), media_type=MediaType.SONG,
            composer_sort=webplayback_metadata.get("sort-composer"), copyright=webplayback_metadata.get("copyright"), disc_total=webplayback_metadata["discCount"], gapless=webplayback_metadata["gapless"], genre_id=int(webplayback_metadata["genreId"]), xid=webplayback_metadata.get("xid"), 
            date=(AppleMusicClientDownloadSongUtils.getmediadate(webplayback_metadata["playlistId"], itunes_api, request_overrides) if use_album_date else (AppleMusicClientDownloadSongUtils.parsedate(webplayback_metadata["releaseDate"]) if webplayback_metadata.get("releaseDate") else None)),
            track=webplayback_metadata["trackNumber"], storefront=webplayback_metadata["s"], title=webplayback_metadata["itemName"], title_id=int(webplayback_metadata["itemId"]), title_sort=webplayback_metadata["sort-name"],
        )
        return tags
    '''getextratags'''
    @staticmethod
    def getextratags(song_metadata: dict, request_overrides: dict = None) -> dict:
        request_overrides = request_overrides or {}
        previews = safeextractfromdict(song_metadata, ['attributes', 'previews'], []) or []
        if not previews: return {}
        preview_url = previews[0]["url"]
        preview_response = requests.get(preview_url, **request_overrides)
        preview_bytes = preview_response.content
        preview_tags = dict(MP4(io.BytesIO(preview_bytes)).tags)
        return preview_tags
    '''getplaylisttags'''
    @staticmethod
    def getplaylisttags(playlist_metadata: dict, media_metadata: dict) -> PlaylistTags:
        playlist_track = (safeextractfromdict(playlist_metadata, ['relationships', 'tracks', 'data'], '').index(media_metadata) + 1)
        return PlaylistTags(
            playlist_artist=safeextractfromdict(playlist_metadata, ['attributes', 'curatorName'], 'Unknown'), playlist_id=playlist_metadata["attributes"]["playParams"]["id"],
            playlist_title=playlist_metadata["attributes"]["name"], playlist_track=playlist_track,
        )
    '''getstreaminfolegacy'''
    @staticmethod
    def getstreaminfolegacy(webplayback: dict, codec: SongCodec, request_overrides: dict = None) -> StreamInfoAv:
        request_overrides = request_overrides or {}
        flavor = "32:ctrp64" if codec == SongCodec.AAC_HE_LEGACY else "28:ctrp256"
        stream_info = StreamInfo()
        stream_info.stream_url = next(i for i in webplayback["songList"][0]["assets"] if i["flavor"] == flavor)["URL"]
        m3u8_obj = m3u8.loads(requests.get(stream_info.stream_url, **request_overrides).text)
        stream_info.widevine_pssh = m3u8_obj.keys[0].uri
        stream_info_av = StreamInfoAv(media_id=webplayback["songList"][0]["songId"], audio_track=stream_info, file_format=MediaFileFormat.M4A)
        return stream_info_av
    '''getdecryptionkeylegacy'''
    @staticmethod
    def getdecryptionkeylegacy(stream_info: StreamInfoAv, cdm: Cdm, apple_music_api: AppleMusicClientAPIUtils = None, request_overrides: dict = None) -> DecryptionKeyAv:
        stream_info_audio, request_overrides = stream_info.audio_track, request_overrides or {}
        try:
            cdm_session = cdm.open(); widevine_pssh_data = WidevinePsshData()
            widevine_pssh_data.algorithm = 1
            widevine_pssh_data.key_ids.append(base64.b64decode(stream_info_audio.widevine_pssh.split(",")[1]))
            pssh_obj = PSSH(widevine_pssh_data.SerializeToString())
            challenge = base64.b64encode(cdm.get_license_challenge(cdm_session, pssh_obj)).decode()
            license_resp = apple_music_api.getlicenseexchange(stream_info.media_id, stream_info.audio_track.widevine_pssh, challenge, request_overrides=request_overrides)
            cdm.parse_license(cdm_session, license_resp["license"])
            decryption_key = next(i for i in cdm.get_keys(cdm_session) if i.type == "CONTENT")
        finally:
            cdm.close(cdm_session)
        decryption_key = DecryptionKeyAv(audio_track=DecryptionKey(kid=decryption_key.kid.hex, key=decryption_key.key.hex()))
        return decryption_key
    '''getdecryptionkey'''
    @staticmethod
    def getdecryptionkey(stream_info: StreamInfoAv, cdm: Cdm, apple_music_api: AppleMusicClientAPIUtils, request_overrides: dict = None) -> DecryptionKeyAv:
        track_uri, track_id = stream_info.audio_track.widevine_pssh, stream_info.media_id
        try:
            cdm_session = cdm.open(); pssh_obj = PSSH(track_uri.split(",")[-1])
            challenge = base64.b64encode(cdm.get_license_challenge(cdm_session, pssh_obj)).decode()
            license = apple_music_api.getlicenseexchange(track_id, track_uri, challenge, request_overrides=request_overrides)
            cdm.parse_license(cdm_session, license["license"])
            decryption_key_info = next(i for i in cdm.get_keys(cdm_session) if i.type == "CONTENT")
        finally:
            cdm.close(cdm_session)
        decryption_key = DecryptionKey(key=decryption_key_info.key.hex(), kid=decryption_key_info.kid.hex)
        return DecryptionKeyAv(audio_track=decryption_key)
    '''getplaylistfromcodec'''
    @staticmethod
    def getplaylistfromcodec(m3u8_data: dict, codec: SongCodec) -> dict | None:
        matching_playlists = [playlist for playlist in m3u8_data["playlists"] if re.fullmatch(SONG_CODEC_REGEX_MAP[codec.value], playlist["stream_info"]["audio"])]
        if not matching_playlists: return None
        return max(matching_playlists, key=lambda x: x["stream_info"]["average_bandwidth"])
    '''getm3u8metadata'''
    @staticmethod
    def getm3u8metadata(m3u8_data: dict, data_id: str):
        for session_data in m3u8_data.get("session_data", []):
            if session_data["data_id"] == data_id:
                return json.loads(base64.b64decode(session_data["value"]).decode("utf-8"))
        return None
    '''getaudiosessionkeymetadata'''
    @staticmethod
    def getaudiosessionkeymetadata(m3u8_data: dict):
        return AppleMusicClientDownloadSongUtils.getm3u8metadata(m3u8_data, "com.apple.hls.AudioSessionKeyInfo")
    '''getassetmetadata'''
    @staticmethod
    def getassetmetadata(m3u8_data: dict):
        return AppleMusicClientDownloadSongUtils.getm3u8metadata(m3u8_data, "com.apple.hls.audioAssetMetadata")
    '''getdrmurifromsessionkey'''
    @staticmethod
    def getdrmurifromsessionkey(drm_infos: dict, drm_ids: list, drm_key: str) -> str | None:
        for drm_id in drm_ids:
            if drm_id != "1" and drm_key in drm_infos.get(drm_id, {}):
                return drm_infos[drm_id][drm_key]["URI"]
        return None
    '''getdrmurifromm3u8keys'''
    @staticmethod
    def getdrmurifromm3u8keys(m3u8_obj: m3u8.M3U8, drm_key: str) -> str | None:
        default_uri = DRM_DEFAULT_KEY_MAPPING[drm_key]
        for key in m3u8_obj.keys:
            if key.keyformat == drm_key and key.uri != default_uri: return key.uri
        return None
    '''getstreaminfo'''
    @staticmethod
    def getstreaminfo(song_metadata: dict, codec: SongCodec, request_overrides: dict = None) -> StreamInfoAv | None:
        request_overrides = request_overrides or {}
        m3u8_master_url: str = safeextractfromdict(song_metadata, ['attributes', 'extendedAssetUrls', 'enhancedHls'], None)
        if not m3u8_master_url: return None
        m3u8_master_obj = m3u8.loads(requests.get(m3u8_master_url, **request_overrides).text)
        m3u8_master_data = m3u8_master_obj.data
        playlist = AppleMusicClientDownloadSongUtils.getplaylistfromcodec(m3u8_master_data, codec)
        if playlist is None: return None
        stream_info = StreamInfo()
        stream_info.stream_url = (f"{m3u8_master_url.rpartition('/')[0]}/{playlist['uri']}")
        stream_info.codec = playlist["stream_info"]["codecs"]
        is_mp4 = any(stream_info.codec.startswith(codec) for codec in MP4_FORMAT_CODECS)
        session_key_metadata = AppleMusicClientDownloadSongUtils.getaudiosessionkeymetadata(m3u8_master_data)
        if session_key_metadata:
            asset_metadata = AppleMusicClientDownloadSongUtils.getassetmetadata(m3u8_master_data)
            drm_ids = asset_metadata[playlist["stream_info"]["stable_variant_id"]]["AUDIO-SESSION-KEY-IDS"]
            stream_info.widevine_pssh = AppleMusicClientDownloadSongUtils.getdrmurifromsessionkey(session_key_metadata, drm_ids, "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed")
            stream_info.playready_pssh = AppleMusicClientDownloadSongUtils.getdrmurifromsessionkey(session_key_metadata, drm_ids, "com.microsoft.playready")
            stream_info.fairplay_key = AppleMusicClientDownloadSongUtils.getdrmurifromsessionkey(session_key_metadata, drm_ids, "com.apple.streamingkeydelivery")
        else:
            m3u8_obj = m3u8.loads(requests.get(stream_info.stream_url, **request_overrides).text)
            stream_info.widevine_pssh = AppleMusicClientDownloadSongUtils.getdrmurifromm3u8keys(m3u8_obj, "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed")
            stream_info.playready_pssh = AppleMusicClientDownloadSongUtils.getdrmurifromm3u8keys(m3u8_obj, "com.microsoft.playready")
            stream_info.fairplay_key = AppleMusicClientDownloadSongUtils.getdrmurifromm3u8keys(m3u8_obj, "com.apple.streamingkeydelivery")
        stream_info_av = StreamInfoAv(audio_track=stream_info, file_format=MediaFileFormat.MP4 if is_mp4 else MediaFileFormat.M4A)
        return stream_info_av
    '''getrawcoverurl'''
    @staticmethod
    def getrawcoverurl(cover_url_template: str) -> str:
        return re.sub(r"image/thumb/", "", re.sub(r"is1-ssl", "a1", cover_url_template))
    '''getcoverurltemplate'''
    @staticmethod
    def getcoverurltemplate(metadata: dict, cover_format: CoverFormat) -> str:
        if cover_format == CoverFormat.RAW:
            cover_url_template = AppleMusicClientDownloadSongUtils.getrawcoverurl(metadata["attributes"]["artwork"]["url"])
        cover_url_template = metadata["attributes"]["artwork"]["url"]
        return cover_url_template
    '''getcoverurl'''
    @staticmethod
    def getcoverurl(cover_url_template: str, cover_size: int, cover_format: CoverFormat) -> str:
        cover_url = re.sub(r"\{w\}x\{h\}([a-z]{2})\.jpg", (f"{cover_size}x{cover_size}bb.{cover_format.value}" if cover_format != CoverFormat.RAW else ""), cover_url_template)
        return cover_url
    '''getdownloaditem'''
    @staticmethod
    def getdownloaditem(song_metadata: dict, playlist_metadata: dict, synced_lyrics_format: SyncedLyricsFormat = SyncedLyricsFormat.LRC, codec: SongCodec = SongCodec.AAC_LEGACY, apple_music_api: AppleMusicClientAPIUtils = None, itunes_api: AppleMusicClientItunesApiUtils = None, use_album_date: bool = False, fetch_extra_tags: bool = False, use_wrapper: bool = False, cover_format: CoverFormat = CoverFormat.JPG, cover_size: int = 1200, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        download_item = DownloadItem()
        download_item.media_metadata, download_item.playlist_metadata = song_metadata, playlist_metadata
        # lyrics
        song_id = AppleMusicClientDownloadSongUtils.getmediaidoflibrarymedia(song_metadata)
        download_item.lyrics = AppleMusicClientDownloadSongUtils.getlyrics(song_metadata, synced_lyrics_format=synced_lyrics_format, apple_music_api=apple_music_api, request_overrides=request_overrides)
        # get media tags
        webplayback = apple_music_api.getwebplayback(song_id, request_overrides=request_overrides)
        download_item.media_tags = AppleMusicClientDownloadSongUtils.gettags(webplayback, download_item.lyrics.unsynced if download_item.lyrics else None, use_album_date, itunes_api, request_overrides)
        if fetch_extra_tags: download_item.extra_tags = AppleMusicClientDownloadSongUtils.getextratags(song_metadata, request_overrides)
        if playlist_metadata: download_item.playlist_tags = AppleMusicClientDownloadSongUtils.getplaylisttags(playlist_metadata, song_metadata)
        # None for all paths as default value, auto set after searching
        download_item.final_path = None; download_item.synced_lyrics_path = None; download_item.staged_path = None; download_item.playlist_file_path = None
        # stream info and decryption key
        if codec.islegacy():
            download_item.stream_info = AppleMusicClientDownloadSongUtils.getstreaminfolegacy(webplayback, codec, request_overrides)
            download_item.decryption_key = AppleMusicClientDownloadSongUtils.getdecryptionkeylegacy(download_item.stream_info, AppleMusicClientDownloadSongUtils.cdm, apple_music_api=apple_music_api, request_overrides=request_overrides)
        else:
            download_item.stream_info = AppleMusicClientDownloadSongUtils.getstreaminfo(song_metadata, codec, request_overrides=request_overrides)
            if (not use_wrapper and download_item.stream_info and download_item.stream_info.audio_track.widevine_pssh):
                download_item.decryption_key = AppleMusicClientDownloadSongUtils.getdecryptionkey(download_item.stream_info, AppleMusicClientDownloadSongUtils.cdm, apple_music_api=apple_music_api, request_overrides=request_overrides)
            else:
                download_item.decryption_key = None
        # cover url
        download_item.cover_url_template = AppleMusicClientDownloadSongUtils.getcoverurltemplate(song_metadata, cover_format)
        download_item.cover_url = AppleMusicClientDownloadSongUtils.getcoverurl(download_item.cover_url_template, cover_size, cover_format)
        # uuid for tmp results saving
        download_item.random_uuid = AppleMusicClientDownloadSongUtils.getrandomuuid4()
        # return
        return download_item
    '''remuxmp4box'''
    @staticmethod
    def remuxmp4box(input_path: str, output_path: str, silent: bool = False, artist: str = ''):
        cmd = ["MP4Box", "-quiet", "-add", input_path, "-itags", f"artist={artist}", "-keep-utc", "-new", output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''remuxffmpeg'''
    @staticmethod
    def remuxffmpeg(input_path: str, output_path: str, decryption_key: str = None, silent: bool = False):
        key = ["-decryption_key", decryption_key] if decryption_key else []
        cmd = ['ffmpeg', "-loglevel", "error", "-y", *key, "-i", input_path, "-c", "copy", "-movflags", "+faststart", output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''decryptmp4decrypt'''
    @staticmethod
    def decryptmp4decrypt(input_path: str, output_path: str, decryption_key: str, legacy: bool, silent: bool = False):
        if legacy: keys = ["--key", f"1:{decryption_key}"]
        else: AppleMusicClientDownloadSongUtils.fixkeyid(input_path); keys = ["--key", "0" * 31 + "1" + f":{decryption_key}", "--key", "0" * 32 + f":{DEFAULT_SONG_DECRYPTION_KEY}"]
        cmd = ["mp4decrypt", *keys, input_path, output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''decryptamdecrypt'''
    @staticmethod
    def decryptamdecrypt(input_path: str, output_path: str, media_id: str, fairplay_key: str, wrapper_decrypt_ip: str = "127.0.0.1:10020", silent: bool = False):
        cmd = ['amdecrypt', wrapper_decrypt_ip, shutil.which('mp4decrypt'), media_id, fairplay_key, input_path, output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''stage'''
    @staticmethod
    def stage(encrypted_path: str, decrypted_path: str, staged_path: str, decryption_key: DecryptionKeyAv, codec: SongCodec, media_id: str, fairplay_key: str, remux_mode: RemuxMode = RemuxMode.MP4BOX, silent: bool = False, wrapper_decrypt_ip: str = "127.0.0.1:10020", artist: str = "", use_wrapper: bool = False):
        if codec.islegacy() and remux_mode == RemuxMode.FFMPEG:
            AppleMusicClientDownloadSongUtils.remuxffmpeg(encrypted_path, staged_path, decryption_key.audio_track.key, silent=silent)
        elif codec.islegacy() or not use_wrapper:
            AppleMusicClientDownloadSongUtils.decryptmp4decrypt(encrypted_path, decrypted_path, decryption_key.audio_track.key, codec.islegacy(), silent)
            if remux_mode == RemuxMode.FFMPEG: AppleMusicClientDownloadSongUtils.remuxffmpeg(decrypted_path, staged_path, silent=silent)
            else: AppleMusicClientDownloadSongUtils.remuxmp4box(decrypted_path, staged_path, silent=silent, artist=artist)
        else:
            AppleMusicClientDownloadSongUtils.decryptamdecrypt(encrypted_path, staged_path, media_id, fairplay_key, wrapper_decrypt_ip=wrapper_decrypt_ip, silent=silent)
    '''downloadstreamwithnm3u8dlre'''
    @staticmethod
    def downloadstreamwithnm3u8dlre(stream_url: str, download_path: str, silent: bool = False, random_uuid: str = ''):
        download_path_obj = Path(download_path)
        download_path_obj.parent.mkdir(parents=True, exist_ok=True)
        log_file_path = os.path.join(user_log_dir(appname='musicdl', appauthor='zcjin'), f"musicdl_{random_uuid}.log")
        cmd = [
            "N_m3u8DL-RE", stream_url, "--binary-merge", "--ffmpeg-binary-path", shutil.which('ffmpeg'), "--save-name", download_path_obj.stem, 
            "--save-dir", download_path_obj.parent, "--tmp-dir", download_path_obj.parent, "--log-file-path", log_file_path,
        ]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''download'''
    @staticmethod
    def download(download_item: DownloadItem, work_dir: str = './', silent: bool = False, codec: SongCodec = SongCodec.AAC_LEGACY, wrapper_decrypt_ip: str = "127.0.0.1:10020", remux_mode: RemuxMode = RemuxMode.MP4BOX, artist: str = "", use_wrapper: bool = False):
        ext = download_item.stream_info.file_format.value
        encrypted_path = os.path.join(work_dir, f"{download_item.random_uuid}_encrypted.m4a")
        is_success = AppleMusicClientDownloadSongUtils.downloadstreamwithnm3u8dlre(download_item.stream_info.audio_track.stream_url, encrypted_path, silent=silent, random_uuid=download_item.random_uuid)
        decrypted_path = os.path.join(work_dir, f"{download_item.random_uuid}_decrypted.m4a")
        download_item.staged_path = os.path.join(work_dir, f"{download_item.random_uuid}_staged.{ext}")
        is_success = AppleMusicClientDownloadSongUtils.stage(
            encrypted_path=encrypted_path, decrypted_path=decrypted_path, staged_path=download_item.staged_path, decryption_key=download_item.decryption_key,
            codec=codec, media_id=download_item.media_metadata["id"], fairplay_key=download_item.stream_info.audio_track.fairplay_key, remux_mode=remux_mode,
            silent=silent, wrapper_decrypt_ip=wrapper_decrypt_ip, artist=artist, use_wrapper=use_wrapper,
        )
        return is_success