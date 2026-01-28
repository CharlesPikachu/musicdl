'''
Function:
    Implementation of AppleMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
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
from xml.etree import ElementTree
from dataclasses import dataclass
from platformdirs import user_log_dir
from pywidevine import PSSH, Cdm, Device
from pywidevine.license_protocol_pb2 import WidevinePsshData


'''settings'''
MEDIA_TYPE_STR_MAP = {1: "Song", 6: "Music Video"}
MEDIA_RATING_STR_MAP = {0: "None", 1: "Explicit", 2: "Clean"}
LEGACY_SONG_CODECS = {"aac-legacy", "aac-he-legacy"}
DRM_DEFAULT_KEY_MAPPING = {
    "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed": ("data:text/plain;base64,AAAAOHBzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAABgSEAAAAAAAAAAAczEvZTEgICBI88aJmwY="),
    "com.microsoft.playready": ("data:text/plain;charset=UTF-16;base64,vgEAAAEAAQC0ATwAVwBSAE0ASABFAEEARABFAFIAIAB4AG0AbABuAHMAPQAiAGgAdAB0AHAAOgAvAC8AcwBjAGgAZQBtAGEAcwAuAG0AaQBjAHIAbwBzAG8AZgB0AC4AYwBvAG0ALwBEAFIATQAvADIAMAAwADcALwAwADMALwBQAGwAYQB5AFIAZQBhAGQAeQBIAGUAYQBkAGUAcgAiACAAdgBlAHIAcwBpAG8AbgA9ACIANAAuADMALgAwAC4AMAAiAD4APABEAEEAVABBAD4APABQAFIATwBUAEUAQwBUAEkATgBGAE8APgA8AEsASQBEAFMAPgA8AEsASQBEACAAQQBMAEcASQBEAD0AIgBBAEUAUwBDAEIAQwAiACAAVgBBAEwAVQBFAD0AIgBBAEEAQQBBAEEAQQBBAEEAQQBBAEIAegBNAFMAOQBsAE0AUwBBAGcASQBBAD0APQAiAD4APAAvAEsASQBEAD4APAAvAEsASQBEAFMAPgA8AC8AUABSAE8AVABFAEMAVABJAE4ARgBPAD4APAAvAEQAQQBUAEEAPgA8AC8AVwBSAE0ASABFAEEARABFAFIAPgA="),
    "com.apple.streamingkeydelivery": "skd://itunes.apple.com/P000000000/s1/e1",
}
MP4_FORMAT_CODECS = ["ec-3", "hvc1", "audio-atmos", "audio-ec3"]
SONG_CODEC_REGEX_MAP = {
    "aac": r"audio-stereo-\d+", "aac-he": r"audio-HE-stereo-\d+", "aac-binaural": r"audio-stereo-\d+-binaural", "aac-downmix": r"audio-stereo-\d+-downmix", "aac-he-binaural": r"audio-HE-stereo-\d+-binaural", 
    "aac-he-downmix": r"audio-HE-stereo-\d+-downmix", "atmos": r"audio-atmos-.*", "ac3": r"audio-ac3-.*", "alac": r"audio-alac-.*",
}
FOURCC_MAP = {"h264": "avc1", "h265": "hvc1"}
UPLOADED_VIDEO_QUALITY_RANK = ["1080pHdVideo", "720pHdVideo", "sdVideoWithPlusAudio", "sdVideo", "sd480pVideo", "provisionalUploadVideo"]
HARDCODED_WVD = """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QrSyZcBqHO0QrdPcU35GBT7S7+IJr2AAXvnjqnb8yrtpPWN2ZW/IWUJN2z4vZ7/HV4aj3OZhkxC1DIMNyvsusUKoQQuf8gwKiEe8cFwbwFSicywlFk9la2IPe8oFShcxAzHLCCn/TIYUAvEL3/4LgaZvqWm80qCPYbgIP5HT8hPYkKWJ4WYknEWK+3InbnkzteFfGrQFCq4CCAESEGnj6Ji7LD+4o7MoHYT4jBQYjtW+kQUijgIwggEKAoIBAQDY9um1ifBRIOmkPtDZTqH+CZUBbb0eK0Cn3NHFf8MFUDzPEz+emK/OTub/hNxCJCao//pP5L8tRNUPFDrrvCBMo7Rn+iUb+mA/2yXiJ6ivqcN9Cu9i5qOU1ygon9SWZRsujFFB8nxVreY5Lzeq0283zn1Cg1stcX4tOHT7utPzFG/ReDFQt0O/GLlzVwB0d1sn3SKMO4XLjhZdncrtF9jljpg7xjMIlnWJUqxDo7TQkTytJmUl0kcM7bndBLerAdJFGaXc6oSY4eNy/IGDluLCQR3KZEQsy/mLeV1ggQ44MFr7XOM+rd+4/314q/deQbjHqjWFuVr8iIaKbq+R63ShAgMBAAEo8CISgAMii2Mw6z+Qs1bvvxGStie9tpcgoO2uAt5Zvv0CDXvrFlwnSbo+qR71Ru2IlZWVSbN5XYSIDwcwBzHjY8rNr3fgsXtSJty425djNQtF5+J2jrAhf3Q2m7EI5aohZGpD2E0cr+dVj9o8x0uJR2NWR8FVoVQSXZpad3M/4QzBLNto/tz+UKyZwa7Sc/eTQc2+ZcDS3ZEO3lGRsH864Kf/cEGvJRBBqcpJXKfG+ItqEW1AAPptjuggzmZEzRq5xTGf6or+bXrKjCpBS9G1SOyvCNF1k5z6lG8KsXhgQxL6ADHMoulxvUIihyPY5MpimdXfUdEQ5HA2EqNiNVNIO4qP007jW51yAeThOry4J22xs8RdkIClOGAauLIl0lLA4flMzW+VfQl5xYxP0E5tuhn0h+844DslU8ZF7U1dU2QprIApffXD9wgAACk26Rggy8e96z8i86/+YYyZQkc9hIdCAERrgEYCEbByzONrdRDs1MrS/ch1moV5pJv63BIKvQHGvLkaFwoMY29tcGFueV9uYW1lEgd1bmtub3duGioKCm1vZGVsX25hbWUSHEFuZHJvaWQgU0RLIGJ1aWx0IGZvciB4ODZfNjQaGwoRYXJjaGl0ZWN0dXJlX25hbWUSBng4Nl82NBodCgtkZXZpY2VfbmFtZRIOZ2VuZXJpY194ODZfNjQaIAoMcHJvZHVjdF9uYW1lEhBzZGtfcGhvbmVfeDg2XzY0GmMKCmJ1aWxkX2luZm8SVUFuZHJvaWQvc2RrX3Bob25lX3g4Nl82NC9nZW5lcmljX3g4Nl82NDo5L1BTUjEuMTgwNzIwLjAxMi80OTIzMjE0OnVzZXJkZWJ1Zy90ZXN0LWtleXMaHgoUd2lkZXZpbmVfY2RtX3ZlcnNpb24SBjE0LjAuMBokCh9vZW1fY3J5cHRvX3NlY3VyaXR5X3BhdGNoX2xldmVsEgEwMg4QASAAKA0wAEAASABQAA=="""
DEFAULT_SONG_DECRYPTION_KEY = "32b8ade1769e26b1ffb8986352793fc6"


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
    def islegacy(self): return self.value in LEGACY_SONG_CODECS


'''MusicVideoCodec'''
class MusicVideoCodec(Enum):
    H264 = "h264"
    H265 = "h265"
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
            "\xa9alb": self.album, "aART": self.album_artist, "plID": self.album_id, "soal": self.album_sort, "\xa9ART": self.artist, "atID": self.artist_id,
            "soar": self.artist_sort, "\xa9cmt": self.comment, "cpil": bool(self.compilation) if self.compilation is not None else None, "\xa9wrt": self.composer,
            "cmID": self.composer_id, "soco": self.composer_sort, "cprt": self.copyright, "\xa9day": date_mp4, "disk": disc_mp4, "pgap": bool(self.gapless) if self.gapless is not None else None,
            "\xa9gen": self.genre, "\xa9lyr": self.lyrics, "geID": self.genre_id, "stik": int(self.media_type) if self.media_type is not None else None, "rtng": int(self.rating) if self.rating is not None else None,
            "sfID": self.storefront, "\xa9nam": self.title, "cnID": self.title_id, "sonm": self.title_sort, "trkn": track_mp4, "xid ": self.xid,
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
    lyrics_results: dict = None
    media_tags: MediaTags = None
    playlist_tags: PlaylistTags = None
    stream_info: StreamInfoAv = None
    decryption_key: DecryptionKeyAv = None
    cover_url_template: str = None
    staged_path: str = None
    final_path: str = None
    playlist_file_path: str = None
    synced_lyrics_path: str = None
    cover_path: str = None
    flat_filter_result: Any = None
    error: Exception = None


'''AppleMusicClientUtils'''
class AppleMusicClientUtils:
    '''_parsedate'''
    @staticmethod
    def _parsedate(date: str):
        return datetime.datetime.fromisoformat(date.split("Z")[0])
    '''getsonglyrics'''
    @staticmethod
    def getsonglyrics(song_metadata: dict, synced_lyrics_format: SyncedLyricsFormat = SyncedLyricsFormat.LRC):
        # no lyrics
        if not song_metadata["attributes"]["hasLyrics"]: return None
        # lyrics parser functions definition
        def _parsettmltimestamp(timestamp_ttml: str):
            mins_secs_ms = re.findall(r"\d+", timestamp_ttml)
            ms, secs, mins = 0, 0, 0
            if len(mins_secs_ms) == 2 and ":" in timestamp_ttml:
                secs, mins = int(mins_secs_ms[-1]), int(mins_secs_ms[-2])
            elif len(mins_secs_ms) == 1:
                ms = int(mins_secs_ms[-1])
            else:
                secs = float(f"{mins_secs_ms[-2]}.{mins_secs_ms[-1]}")
                if len(mins_secs_ms) > 2: mins = int(mins_secs_ms[-3])
            return datetime.datetime.fromtimestamp((mins * 60) + secs + (ms / 1000), tz=datetime.timezone.utc)
        def _getlyricslinelrc(element: ElementTree.Element):
            timestamp_ttml, text = element.attrib.get("begin"), element.text
            timestamp = _parsettmltimestamp(timestamp_ttml)
            ms_new = timestamp.strftime("%f")[:-3]
            if int(ms_new[-1]) >= 5:
                ms = int(f"{int(ms_new[:2]) + 1}") * 10
                timestamp += datetime.timedelta(milliseconds=ms) - datetime.timedelta(microseconds=timestamp.microsecond)
            return f"[{timestamp.strftime('%M:%S.%f')[:-4]}]{text}"
        def _getlyricslinesrt(index: int, element: ElementTree.Element):
            timestamp_begin_ttml, timestamp_end_ttml, text = element.attrib.get("begin"), element.attrib.get("end"), element.text
            timestamp_begin = _parsettmltimestamp(timestamp_begin_ttml)
            timestamp_end = _parsettmltimestamp(timestamp_end_ttml)
            return (
                f"{index}\n"
                f"{timestamp_begin.strftime('%H:%M:%S,%f')[:-3]} --> "
                f"{timestamp_end.strftime('%H:%M:%S,%f')[:-3]}\n"
                f"{text}\n"
            )
        # fetch lyrics
        try:
            lyrics_result = song_metadata["relationships"]["lyrics"]
            lyrics_ttml = lyrics_result["data"][0]["attributes"]["ttml"]
            lyrics_ttml_et = ElementTree.fromstring(lyrics_ttml)
            unsynced_lyrics, synced_lyrics, index = [], [], 1
            for div in lyrics_ttml_et.iter("{http://www.w3.org/ns/ttml}div"):
                stanza = []
                unsynced_lyrics.append(stanza)
                for p in div.iter("{http://www.w3.org/ns/ttml}p"):
                    if p.text is not None: stanza.append(p.text)
                    if p.attrib.get("begin"):
                        if synced_lyrics_format == SyncedLyricsFormat.LRC:
                            synced_lyrics.append(_getlyricslinelrc(p))
                        if synced_lyrics_format == SyncedLyricsFormat.SRT:
                            synced_lyrics.append(_getlyricslinesrt(index, p))
                        if synced_lyrics_format == SyncedLyricsFormat.TTML:
                            if not synced_lyrics: synced_lyrics.append(minidom.parseString(lyrics_ttml).toprettyxml())
                        index += 1
            lyrics = Lyrics(synced="\n".join(synced_lyrics + ["\n"]) if synced_lyrics else None, unsynced=("\n\n".join(["\n".join(lyric_group) for lyric_group in unsynced_lyrics]) if unsynced_lyrics else None))
        except:
            lyrics_result, lyrics = {}, None
        # return
        return lyrics, lyrics_result
    '''getsongtags'''
    @staticmethod
    def getsongtags(webplayback: dict, lyrics: str | None = None):
        webplayback_metadata = webplayback["songList"][0]["assets"][0]["metadata"]
        tags = MediaTags(
            album=webplayback_metadata["playlistName"], album_artist=webplayback_metadata["playlistArtistName"], album_id=int(webplayback_metadata["playlistId"]),
            album_sort=webplayback_metadata["sort-album"], artist=webplayback_metadata["artistName"], artist_id=int(webplayback_metadata["artistId"]),
            artist_sort=webplayback_metadata["sort-artist"], comment=webplayback_metadata.get("comments"), compilation=webplayback_metadata["compilation"],
            composer=webplayback_metadata.get("composerName"), composer_id=(int(webplayback_metadata.get("composerId")) if webplayback_metadata.get("composerId") else None),
            composer_sort=webplayback_metadata.get("sort-composer"), copyright=webplayback_metadata.get("copyright"),
            date=(AppleMusicClientUtils._parsedate(webplayback_metadata["releaseDate"]) if webplayback_metadata.get("releaseDate") else None),
            disc=webplayback_metadata["discNumber"], disc_total=webplayback_metadata["discCount"], gapless=webplayback_metadata["gapless"],
            genre=webplayback_metadata.get("genre"), genre_id=int(webplayback_metadata["genreId"]), lyrics=lyrics if lyrics else None,
            media_type=MediaType.SONG, rating=MediaRating(webplayback_metadata["explicit"]), storefront=webplayback_metadata["s"],
            title=webplayback_metadata["itemName"], title_id=int(webplayback_metadata["itemId"]), title_sort=webplayback_metadata["sort-name"],
            track=webplayback_metadata["trackNumber"], track_total=webplayback_metadata["trackCount"], xid=webplayback_metadata.get("xid"),
        )
        return tags
    '''getsongstreaminfolegacy'''
    @staticmethod
    def getsongstreaminfolegacy(webplayback: dict, codec: SongCodec):
        flavor = "32:ctrp64" if codec == SongCodec.AAC_HE_LEGACY else "28:ctrp256"
        stream_info = StreamInfo()
        stream_info.stream_url = next(i for i in webplayback["songList"][0]["assets"] if i["flavor"] == flavor)["URL"]
        m3u8_obj = m3u8.loads(requests.get(stream_info.stream_url).text)
        stream_info.widevine_pssh = m3u8_obj.keys[0].uri
        stream_info_av = StreamInfoAv(media_id=webplayback["songList"][0]["songId"], audio_track=stream_info, file_format=MediaFileFormat.M4A)
        return stream_info_av
    '''getsongdecryptionkeylegacy'''
    @staticmethod
    def getsongdecryptionkeylegacy(stream_info: StreamInfoAv, cdm: Cdm, get_license_exchange_func = None, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        stream_info_audio = stream_info.audio_track
        try:
            cdm_session = cdm.open()
            widevine_pssh_data = WidevinePsshData()
            widevine_pssh_data.algorithm = 1
            widevine_pssh_data.key_ids.append(base64.b64decode(stream_info_audio.widevine_pssh.split(",")[1]))
            pssh_obj = PSSH(widevine_pssh_data.SerializeToString())
            challenge = base64.b64encode(cdm.get_license_challenge(cdm_session, pssh_obj)).decode()
            license_resp = get_license_exchange_func(stream_info.media_id, stream_info.audio_track.widevine_pssh, challenge, request_overrides=request_overrides)
            cdm.parse_license(cdm_session, license_resp["license"])
            decryption_key = next(i for i in cdm.get_keys(cdm_session) if i.type == "CONTENT")
        finally:
            cdm.close(cdm_session)
        decryption_key = DecryptionKeyAv(audio_track=DecryptionKey(kid=decryption_key.kid.hex, key=decryption_key.key.hex()))
        return decryption_key
    '''getsongstreaminfo'''
    @staticmethod
    def getsongstreaminfo(song_metadata: dict, codec: SongCodec):
        m3u8_master_url: str = song_metadata["attributes"]["extendedAssetUrls"].get("enhancedHls")
        if not m3u8_master_url: return None
        m3u8_master_obj = m3u8.loads(requests.get(m3u8_master_url).text)
        m3u8_master_data = m3u8_master_obj.data
        playlist = AppleMusicClientUtils._getsongplaylistfromcodec(m3u8_master_data, codec)
        if playlist is None: return None
        stream_info = StreamInfo()
        stream_info.stream_url = (f"{m3u8_master_url.rpartition('/')[0]}/{playlist['uri']}")
        stream_info.codec = playlist["stream_info"]["codecs"]
        is_mp4 = any(stream_info.codec.startswith(codec) for codec in MP4_FORMAT_CODECS)
        session_key_metadata = AppleMusicClientUtils._getaudiosessionkeymetadata(m3u8_master_data)
        if session_key_metadata:
            asset_metadata = AppleMusicClientUtils._getassetmetadata(m3u8_master_data)
            variant_id = playlist["stream_info"]["stable_variant_id"]
            drm_ids = asset_metadata[variant_id]["AUDIO-SESSION-KEY-IDS"]
            stream_info.widevine_pssh = AppleMusicClientUtils._getdrmurifromsessionkey(session_key_metadata, drm_ids, "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed")
            stream_info.playready_pssh = AppleMusicClientUtils._getdrmurifromsessionkey(session_key_metadata, drm_ids, "com.microsoft.playready")
            stream_info.fairplay_key = AppleMusicClientUtils._getdrmurifromsessionkey(session_key_metadata, drm_ids, "com.apple.streamingkeydelivery")
        else:
            m3u8_obj = m3u8.loads(requests.get(stream_info.stream_url).text)
            stream_info.widevine_pssh = AppleMusicClientUtils._getdrmurifromm3u8keys(m3u8_obj, "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed")
            stream_info.playready_pssh = AppleMusicClientUtils._getdrmurifromm3u8keys(m3u8_obj, "com.microsoft.playready")
            stream_info.fairplay_key = AppleMusicClientUtils._getdrmurifromm3u8keys(m3u8_obj, "com.apple.streamingkeydelivery")
        stream_info_av = StreamInfoAv(audio_track=stream_info, file_format=MediaFileFormat.MP4 if is_mp4 else MediaFileFormat.M4A)
        return stream_info_av
    '''getsongdecryptionkey'''
    @staticmethod
    def getsongdecryptionkey(stream_info: StreamInfoAv, cdm: Cdm, get_license_exchange_func = None, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        def _getsongdecryptionkey(track_uri: str, track_id: str, cdm: Cdm, get_license_exchange_func = None, request_overrides: dict = None):
            try:
                cdm_session = cdm.open()
                pssh_obj = PSSH(track_uri.split(",")[-1])
                challenge = base64.b64encode(cdm.get_license_challenge(cdm_session, pssh_obj)).decode()
                license = get_license_exchange_func(track_id, track_uri, challenge, request_overrides=request_overrides)
                cdm.parse_license(cdm_session, license["license"])
                decryption_key_info = next(i for i in cdm.get_keys(cdm_session) if i.type == "CONTENT")
            finally:
                cdm.close(cdm_session)
            decryption_key = DecryptionKey(key=decryption_key_info.key.hex(), kid=decryption_key_info.kid.hex)
            return decryption_key
        decryption_key = DecryptionKeyAv(audio_track=_getsongdecryptionkey(stream_info.audio_track.widevine_pssh, stream_info.media_id, cdm, get_license_exchange_func, request_overrides))
        return decryption_key
    '''_getm3u8metadata'''
    @staticmethod
    def _getm3u8metadata(m3u8_data: dict, data_id: str):
        for session_data in m3u8_data.get("session_data", []):
            if session_data["data_id"] == data_id:
                return json.loads(base64.b64decode(session_data["value"]).decode("utf-8"))
        return None
    '''_getaudiosessionkeymetadata'''
    @staticmethod
    def _getaudiosessionkeymetadata(m3u8_data: dict):
        return AppleMusicClientUtils._getm3u8metadata(m3u8_data, "com.apple.hls.AudioSessionKeyInfo")
    '''_getassetmetadata'''
    @staticmethod
    def _getassetmetadata(m3u8_data: dict):
        return AppleMusicClientUtils._getm3u8metadata(m3u8_data, "com.apple.hls.audioAssetMetadata")
    '''_getsongplaylistfromcodec'''
    @staticmethod
    def _getsongplaylistfromcodec(m3u8_data: dict, codec: SongCodec):
        matching_playlists = [playlist for playlist in m3u8_data["playlists"] if re.fullmatch(SONG_CODEC_REGEX_MAP[codec.value], playlist["stream_info"]["audio"])]
        if not matching_playlists: return None
        return max(matching_playlists, key=lambda x: x["stream_info"]["average_bandwidth"])
    '''_getdrmurifromsessionkey'''
    @staticmethod
    def _getdrmurifromsessionkey(drm_infos: dict, drm_ids: list, drm_key: str):
        for drm_id in drm_ids:
            if drm_id != "1" and drm_key in drm_infos.get(drm_id, {}):
                return drm_infos[drm_id][drm_key]["URI"]
        return None
    '''_getdrmurifromm3u8keys'''
    @staticmethod
    def _getdrmurifromm3u8keys(m3u8_obj: m3u8.M3U8, drm_key: str):
        default_uri = DRM_DEFAULT_KEY_MAPPING[drm_key]
        for key in m3u8_obj.keys:
            if key.keyformat == drm_key and key.uri != default_uri: return key.uri
        return None
    @staticmethod
    def _getrandomuuid():
        return uuid.uuid4().hex[:8]
    '''getsongdownloaditem'''
    @staticmethod
    def getsongdownloaditem(song_metadata: dict, webplayback: dict, synced_lyrics_format: SyncedLyricsFormat = SyncedLyricsFormat.LRC, codec: SongCodec = SongCodec.AAC_LEGACY,
                            get_license_exchange_func = None, request_overrides: dict = None):
        # init
        download_item = DownloadItem()
        download_item.media_metadata = song_metadata
        request_overrides = request_overrides or {}
        # lyrics
        download_item.lyrics, download_item.lyrics_results = AppleMusicClientUtils.getsonglyrics(song_metadata, synced_lyrics_format=synced_lyrics_format)
        # get webplayback
        download_item.media_tags = AppleMusicClientUtils.getsongtags(webplayback, download_item.lyrics.unsynced if download_item.lyrics else None)
        # auto set after searching
        download_item.final_path = None
        download_item.synced_lyrics_path = None
        download_item.staged_path = None
        # stream info and decryption key
        cdm = Cdm.from_device(Device.loads(HARDCODED_WVD))
        if codec.islegacy():
            download_item.stream_info = AppleMusicClientUtils.getsongstreaminfolegacy(webplayback, codec)
            download_item.decryption_key = AppleMusicClientUtils.getsongdecryptionkeylegacy(download_item.stream_info, cdm, get_license_exchange_func, request_overrides=request_overrides)
        else:
            download_item.stream_info = AppleMusicClientUtils.getsongstreaminfo(song_metadata, codec)
            if (download_item.stream_info and download_item.stream_info.audio_track.widevine_pssh):
                download_item.decryption_key = AppleMusicClientUtils.getsongdecryptionkey(download_item.stream_info, cdm, get_license_exchange_func, request_overrides=request_overrides)
            else:
                download_item.decryption_key = None
        # uuid for tmp results saving
        download_item.random_uuid = AppleMusicClientUtils._getrandomuuid()
        # return
        return download_item
    '''download'''
    @staticmethod
    def download(download_item: DownloadItem, work_dir: str = './', silent: bool = False, codec: SongCodec = SongCodec.AAC_LEGACY, wrapper_decrypt_ip: str = "127.0.0.1:10020"):
        ext = download_item.stream_info.file_format.value
        encrypted_path = os.path.join(work_dir, f"{download_item.random_uuid}_encrypted.{ext}")
        is_success = AppleMusicClientUtils.downloadstream(download_item.stream_info.audio_track.stream_url, encrypted_path, silent=silent, random_uuid=download_item.random_uuid)
        decrypted_path = os.path.join(work_dir, f"{download_item.random_uuid}_decrypted.{ext}")
        download_item.staged_path = os.path.join(work_dir, f"{download_item.random_uuid}_staged.{ext}")
        is_success = AppleMusicClientUtils.decrypt(
            encrypted_path=encrypted_path, decrypted_path=decrypted_path, final_path=download_item.final_path, decryption_key=download_item.decryption_key,
            codec=codec, media_id=download_item.media_metadata["id"], fairplay_key=download_item.stream_info.audio_track.fairplay_key, silent=silent,
            artist=download_item.media_tags.artist, wrapper_decrypt_ip=wrapper_decrypt_ip,
        )
        assert is_success
    '''_fixkeyid'''
    @staticmethod
    def _fixkeyid(input_path: str):
        count = 0
        with open(input_path, "rb+") as file:
            while data := file.read(4096):
                pos, i = file.tell(), 0
                while tenc := max(0, data.find(b"tenc", i)):
                    kid = tenc + 12
                    file.seek(max(0, pos - 4096) + kid, 0)
                    file.write(bytes.fromhex(f"{count:032}"))
                    count += 1
                    i = kid + 1
                file.seek(pos, 0)
    '''_remuxmp4box'''
    @staticmethod
    def _remuxmp4box(input_path: str, output_path: str, silent: bool = False, artist: str = ''):
        cmd = ["MP4Box", "-quiet", "-add", input_path, "-itags", f"artist={artist}", "-keep-utc", "-new", output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''_decryptmp4decrypt'''
    @staticmethod
    def _decryptmp4decrypt(input_path: str, output_path: str, decryption_key: str, legacy: bool, silent: bool = False):
        if legacy:
            keys = ["--key", f"1:{decryption_key}"]
        else:
            AppleMusicClientUtils._fixkeyid(input_path)
            keys = ["--key", "0" * 31 + "1" + f":{decryption_key}", "--key", "0" * 32 + f":{DEFAULT_SONG_DECRYPTION_KEY}"]
        cmd = ["mp4decrypt", *keys, input_path, output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''_decryptamdecrypt'''
    @staticmethod
    def _decryptamdecrypt(input_path: str, output_path: str, media_id: str, fairplay_key: str, wrapper_decrypt_ip: str = "127.0.0.1:10020", silent: bool = False):
        cmd = ['amdecrypt', wrapper_decrypt_ip, shutil.which('mp4decrypt'), media_id, fairplay_key, input_path, output_path]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)
    '''decrypt'''
    @staticmethod
    def decrypt(encrypted_path: str, decrypted_path: str, final_path: str, decryption_key: DecryptionKeyAv, codec: SongCodec, media_id: str, fairplay_key: str, silent: bool = False, wrapper_decrypt_ip: str = "127.0.0.1:10020", artist: str = ""):
        try:
            is_success = AppleMusicClientUtils._decryptmp4decrypt(encrypted_path, decrypted_path, decryption_key.audio_track.key, codec.islegacy(), silent=silent)
            is_success = AppleMusicClientUtils._remuxmp4box(decrypted_path, final_path, silent=silent, artist=artist)
        except:
            assert fairplay_key
            is_success = AppleMusicClientUtils._decryptamdecrypt(encrypted_path, final_path, media_id, fairplay_key, wrapper_decrypt_ip=wrapper_decrypt_ip, silent=silent)
        return is_success
    '''downloadstream'''
    @staticmethod
    def downloadstream(stream_url: str, download_path: str, silent: bool = False, random_uuid: str = ''):
        download_path_obj = Path(download_path)
        download_path_obj.parent.mkdir(parents=True, exist_ok=True)
        log_dir = user_log_dir(appname='musicdl', appauthor='zcjin')
        log_file_path = os.path.join(log_dir, f"musicdl_{random_uuid}.log")
        cmd = [
            "N_m3u8DL-RE", stream_url, "--binary-merge", "--ffmpeg-binary-path", shutil.which('ffmpeg'),
            "--save-name", download_path_obj.stem, "--save-dir", download_path_obj.parent, "--tmp-dir", download_path_obj.parent,
            '--log-file-path', log_file_path,
        ]
        capture_output = True if silent else False
        ret = subprocess.run(cmd, check=True, capture_output=capture_output, text=True, encoding='utf-8', errors='ignore')
        return (ret.returncode == 0)