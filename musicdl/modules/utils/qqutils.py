'''
Function:
    Implementation of QQMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import time
import orjson
import base64
import random
import string
import hashlib
import requests
import binascii
from enum import Enum
from uuid import uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import ClassVar, TypedDict, Any, cast
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''settings'''
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDEIxgwoutfwoJxcGQeedgP7FG9qaIuS0qzfR8gWkrkTZKM2iWHn2ajQpBRZjMSoSf6+KJGvar2ORhBfpDXyVtZCKpqLQ+FLkpncClKVIrBwv6PHyUvuCb0rIarmgDnzkfQAqVufEtR64iazGDKatvJ9y6B9NMbHddGSAUmRTCrHQIDAQAB
-----END PUBLIC KEY-----"""
SECRET = "ZdJqM15EeO2zWc08"
APP_KEY = "0AND0HD6FE4HY80F"


'''SongFileType'''
class SongFileType(Enum):
    MASTER = ("AI00", ".flac")
    ATMOS_2 = ("Q000", ".flac")
    ATMOS_51 = ("Q001", ".flac")
    FLAC = ("F000", ".flac")
    OGG_640 = ("O801", ".ogg")
    OGG_320 = ("O800", ".ogg")
    OGG_192 = ("O600", ".ogg")
    OGG_96 = ("O400", ".ogg")
    MP3_320 = ("M800", ".mp3")
    MP3_128 = ("M500", ".mp3")
    ACC_192 = ("C600", ".m4a")
    ACC_96 = ("C400", ".m4a")
    ACC_48 = ("C200", ".m4a")
    SORTED_QUALITIES = [
        ("AI00", ".flac"), ("Q000", ".flac"), ("Q001", ".flac"), ("F000", ".flac"), ("O801", ".ogg"), ("O800", ".ogg"), ("O600", ".ogg"), ("O400", ".ogg"),
        ("M800", ".mp3"), ("M500", ".mp3"), ("C600", ".m4a"), ("C400", ".m4a"), ("C200", ".m4a")
    ]


'''EncryptedSongFileType'''
class EncryptedSongFileType(Enum):
    MASTER = ("AIM0", ".mflac")
    ATMOS_2 = ("Q0M0", ".mflac")
    ATMOS_51 = ("Q0M1", ".mflac")
    FLAC = ("F0M0", ".mflac")
    OGG_640 = ("O801", ".mgg")
    OGG_320 = ("O800", ".mgg")
    OGG_192 = ("O6M0", ".mgg")
    OGG_96 = ("O4M0", ".mgg")
    SORTED_QUALITIES = [
        ("AIM0", ".mflac"), ("Q0M0", ".mflac"), ("Q0M1", ".mflac"), ("F0M0", ".mflac"), ("O801", ".mgg"), ("O800", ".mgg"), ("O6M0", ".mgg"), ("O4M0", ".mgg")
    ]


'''ThirdPartVKeysAPISongFileType'''
class ThirdPartVKeysAPISongFileType(Enum):
    TRIAL_LISTEN = (0,)
    LOSSY_QUALITY = (1, 2, 3)
    STANDARD_QUALITY = (4, 5, 6, 7)
    HQ_QUALITY = (8,)
    HQ_QUALITY_ENHANCED = (9,)
    SQ_LOSSLESS_QUALITY = (10,)
    HI_RES_QUALITY = (11,)
    DOLBY_ATMOS = (12,)
    PREMIUM_SPATIAL_AUDIO = (13,)
    PREMIUM_MASTER_2_0 = (14,)
    AI_ACCOMPANIMENT_MODE_4TRACK = (15,)
    AI_5_1_QUALITY_6TRACK = (16,)
    ID_TO_NAME = {
        0: "TRIAL_LISTEN", 1: "LOSSY_QUALITY", 2: "LOSSY_QUALITY", 3: "LOSSY_QUALITY", 4: "STANDARD_QUALITY", 5: "STANDARD_QUALITY", 6: "STANDARD_QUALITY", 7: "STANDARD_QUALITY",
        8: "HQ_QUALITY", 9: "HQ_QUALITY_ENHANCED", 10: "SQ_LOSSLESS_QUALITY", 11: "HI_RES_QUALITY", 12: "DOLBY_ATMOS", 13: "PREMIUM_SPATIAL_AUDIO", 14: "PREMIUM_MASTER_2_0",
        15: "AI_ACCOMPANIMENT_MODE_4TRACK", 16: "AI_5_1_QUALITY_6TRACK",
    }


'''SearchType'''
class SearchType(Enum):
    SONG = 0
    SINGER = 1
    ALBUM = 2
    SONGLIST = 3
    MV = 4
    LYRIC = 7
    USER = 8
    AUDIO_ALBUM = 15
    AUDIO = 18


'''QimeiResult'''
class QimeiResult(TypedDict):
    q16: str
    q36: str


'''OSVersion'''
@dataclass
class OSVersion:
    incremental: str = "5891938"
    release: str = "10"
    codename: str = "REL"
    sdk: int = 29


'''Device'''
@dataclass
class Device:
    display: str = field(default_factory=lambda: f"QMAPI.{random.randint(100000, 999999)}.001")
    product: str = "iarim"
    device: str = "sagit"
    board: str = "eomam"
    model: str = "MI 6"
    fingerprint: str = field(default_factory=lambda: f"xiaomi/iarim/sagit:10/eomam.200122.001/{random.randint(1000000, 9999999)}:user/release-keys")
    boot_id: str = field(default_factory=lambda: str(uuid4()))
    proc_version: str = field(default_factory=lambda: f"Linux 5.4.0-54-generic-{''.join(random.choices(string.ascii_letters + string.digits, k=8))} (android-build@google.com)")
    imei: str = field(default_factory=lambda: (lambda d: "".join(map(str, d)) + str(sum((x * 2 // 10 + x * 2 % 10) if i % 2 == 0 else x for i, x in enumerate(d)) * 9 % 10))([random.randint(0, 9) for _ in range(14)]))
    brand: str = "Xiaomi"
    bootloader: str = "U-boot"
    base_band: str = ""
    version: OSVersion = field(default_factory=OSVersion)
    sim_info: str = "T-Mobile"
    os_type: str = "android"
    mac_address: str = "00:50:56:C0:00:08"
    ip_address: ClassVar[list[int]] = [10, 0, 1, 3]
    wifi_bssid: str = "00:50:56:C0:00:08"
    wifi_ssid: str = "<unknown ssid>"
    imsi_md5: list[int] = field(default_factory=lambda: list(hashlib.md5(bytes([random.randint(0, 255) for _ in range(16)])).digest()))
    android_id: str = field(default_factory=lambda: binascii.hexlify(bytes([random.randint(0, 255) for _ in range(8)])).decode("utf-8"))
    apn: str = "wifi"
    vendor_name: str = "MIUI"
    vendor_os_name: str = "qmapi"
    qimei: None | str = None


'''Credential'''
@dataclass
class Credential:
    openid: str = ""
    refresh_token: str = ""
    access_token: str = ""
    expired_at: int = 0
    musicid: int = 0
    musickey: str = ""
    unionid: str = ""
    str_musicid: str = ""
    refresh_key: str = ""
    encrypt_uin: str = ""
    login_type: int = 0
    extra_fields: dict[str, Any] = field(default_factory=dict)
    '''postinit'''
    def __post_init__(self):
        if not self.login_type: self.login_type = 1 if self.musickey and self.musickey.startswith("W_X") else 2
    '''todict'''
    def todict(self) -> dict:
        d = asdict(self)
        d["loginType"], d["encryptUin"] = d.pop("login_type"), d.pop("encrypt_uin")
        return d
    '''asjson'''
    def asjson(self) -> str:
        data = self.todict()
        data.update(data.pop("extra_fields"))
        return orjson.dumps(data).decode()
    '''fromcookiesdict'''
    @classmethod
    def fromcookiesdict(cls, cookies: dict[str, Any]):
        return cls(
            openid=cookies.get("openid") or cookies.get("psrf_qqopenid") or cookies.get("wxopenid"), refresh_token=cookies.get("refresh_token") or cookies.get("psrf_qqrefresh_token") or cookies.get("wxrefresh_token"),
            access_token=cookies.get("access_token") or cookies.get("psrf_qqaccess_token") or cookies.get("wxaccess_token"), expired_at=cookies.get("expired_at") or cookies.get("psrf_access_token_expiresAt"), extra_fields=cookies,
            musicid=int(cookies.get("musicid", 0) or cookies.get("uin", 0)), musickey=cookies.get("musickey") or cookies.get("qqmusic_key"), unionid=cookies.get("unionid") or cookies.get("psrf_qqunionid") or cookies.get("wxunionid"),
            str_musicid=cookies.get("str_musicid") or cookies.get("musicid") or cookies.get("uin"), refresh_key=cookies.get("refresh_key"), encrypt_uin=cookies.get("encryptUin"), login_type=cookies.get("loginType") or cookies.get("tmeLoginType"), 
        )


'''QQMusicClientUtils'''
class QQMusicClientUtils(object):
    version, version_code, qimei_result, device = "13.2.5.8", 13020508, {}, Device()
    endpoint = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    enc_endpoint = "https://u.y.qq.com/cgi-bin/musics.fcg"
    music_domain = "https://isure.stream.qqmusic.qq.com/"
    COMMON_DEFAULTS: ClassVar[dict[str, str]] = {"ct": "11", "tmeAppID": "qqmusic", "format": "json", "inCharset": "utf-8", "outCharset": "utf-8", "uid": "3931641530"}
    @property
    def qimei(self) -> QimeiResult:
        if self.qimei_result: return self.qimei_result
        self.qimei_result = QQMusicClientUtils.obtainqimei(version=QQMusicClientUtils.version, device=QQMusicClientUtils.device)
        return self.qimei_result
    '''rsaencrypt'''
    @staticmethod
    def rsaencrypt(content: bytes):
        key = cast(RSAPublicKey, serialization.load_pem_public_key(PUBLIC_KEY.encode()))
        return key.encrypt(content, padding.PKCS1v15())
    '''aesencrypt'''
    @staticmethod
    def aesencrypt(key: bytes, content: bytes):
        cipher = Cipher(algorithms.AES(key), modes.CBC(key))
        padding_size = 16 - len(content) % 16
        encryptor = cipher.encryptor()
        return encryptor.update(content + (padding_size * chr(padding_size)).encode()) + encryptor.finalize()
    '''calcmd5'''
    @staticmethod
    def calcmd5(*strings: str | bytes):
        md5 = hashlib.md5()
        for item in strings:
            assert isinstance(item, (str, bytes))
            if isinstance(item, bytes): md5.update(item)
            elif isinstance(item, str): md5.update(item.encode())
        return md5.hexdigest()
    '''hash33'''
    @staticmethod
    def hash33(s: str, h: int = 0) -> int:
        for c in s: h = (h << 5) + h + ord(c)
        return 2147483647 & h
    '''sign'''
    @staticmethod
    def sign(request: dict) -> str:
        PART_1_INDEXES = [23, 14, 6, 36, 16, 40, 7, 19]
        PART_2_INDEXES = [16, 1, 32, 12, 19, 27, 8, 5]
        SCRAMBLE_VALUES = [89, 39, 179, 150, 218, 82, 58, 252, 177, 52, 186, 123, 120, 64, 242, 133, 143, 161, 121, 179]
        PART_1_INDEXES = filter(lambda x: x < 40, PART_1_INDEXES)
        hash = hashlib.sha1(orjson.dumps(request)).hexdigest().upper()
        part1, part2, part3 = "".join(hash[i] for i in PART_1_INDEXES), "".join(hash[i] for i in PART_2_INDEXES), bytearray(20)
        for i, v in enumerate(SCRAMBLE_VALUES): part3[i] = v ^ int(hash[i * 2 : i * 2 + 2], 16)
        b64_part = re.sub(rb"[\\/+=]", b"", base64.b64encode(part3)).decode("utf-8")
        return f"zzc{part1}{b64_part}{part2}".lower()
    '''randombeaconid'''
    @staticmethod
    def randombeaconid():
        beacon_id, time_month, rand1, rand2 = "", datetime.now().strftime("%Y-%m-") + "01", random.randint(100000, 999999), random.randint(100000000, 999999999)
        for i in range(1, 41):
            if i in [1, 2, 13, 14, 17, 18, 21, 22, 25, 26, 29, 30, 33, 34, 37, 38]: beacon_id += f"k{i}:{time_month}{rand1}.{rand2}"
            elif i == 3: beacon_id += "k3:0000000000000000"
            elif i == 4: beacon_id += f"k4:{''.join(random.choices('123456789abcdef', k=16))}"
            else: beacon_id += f"k{i}:{random.randint(0, 9999)}"
            beacon_id += ";"
        return beacon_id
    '''randompayloadbydevice'''
    @staticmethod
    def randompayloadbydevice(device: Device, version: str):
        fixed_rand = random.randint(0, 14400)
        reserved = {
            "harmony": "0", "clone": "0", "containe": "", "oz": "UhYmelwouA+V2nPWbOvLTgN2/m8jwGB+yUB5v9tysQg=", "oo": "Xecjt+9S1+f8Pz2VLSxgpw==",
            "kelong": "0", "uptimes": (datetime.now() - timedelta(seconds=fixed_rand)).strftime("%Y-%m-%d %H:%M:%S"), "multiUser": "0", "bod": device.brand, 
            "dv": device.device, "firstLevel": "", "manufact": device.brand, "name": device.model, "host": "se.infra", "kernel": device.proc_version,
        }
        return {
            "androidId": device.android_id, "platformId": 1, "appKey": APP_KEY, "appVersion": version, "beaconIdSrc": QQMusicClientUtils.randombeaconid(),
            "brand": device.brand, "channelId": "10003505", "cid": "", "imei": device.imei, "imsi": "", "mac": "", "model": device.model, "networkType": "unknown",
            "oaid": "", "osVersion": f"Android {device.version.release},level {device.version.sdk}", "qimei": "", "qimei36": "", "sdkVersion": "1.2.13.6",
            "targetSdkVersion": "33", "audit": "", "userId": "{}", "packageId": "com.tencent.qqmusic", "deviceType": "Phone", "sdkName": "", "reserved": orjson.dumps(reserved).decode(),
        }
    '''obtainqimei'''
    @staticmethod
    def obtainqimei(version: str, device: Device):
        try:
            payload, ts = QQMusicClientUtils.randompayloadbydevice(device, version), int(time.time())
            crypt_key, nonce = "".join(random.choices("adbcdef1234567890", k=16)), "".join(random.choices("adbcdef1234567890", k=16))
            key = base64.b64encode(QQMusicClientUtils.rsaencrypt(crypt_key.encode())).decode()
            params = base64.b64encode(QQMusicClientUtils.aesencrypt(crypt_key.encode(), orjson.dumps(payload))).decode()
            extra = '{"appKey":"' + APP_KEY + '"}'
            sign = QQMusicClientUtils.calcmd5(key, params, str(ts * 1000), nonce, SECRET, extra)
            resp = requests.post("https://api.tencentmusic.com/tme/trpc/proxy",
                headers={
                    "Host": "api.tencentmusic.com", "method": "GetQimei", "service": "trpc.tme_datasvr.qimeiproxy.QimeiProxy", "appid": "qimei_qq_android",
                    "sign": QQMusicClientUtils.calcmd5("qimei_qq_androidpzAuCmaFAaFaHrdakPjLIEqKrGnSOOvH", str(ts)), "user-agent": "QQMusic", "timestamp": str(ts),
                },
                json={"app": 0, "os": 1, "qimeiParams": {"key": key, "params": params, "time": str(ts), "nonce": nonce, "sign": sign, "extra": extra}},
            )
            data = orjson.loads(orjson.loads(resp.content)["data"])["data"]
            device.qimei = data["q36"]
            return QimeiResult(q16=data["q16"], q36=data["q36"])
        except:
            result = QimeiResult(q16="", q36="6c9d3cd110abca9b16311cee10001e717614")
        return result
    '''randomguid'''
    @staticmethod
    def randomguid():
        return "".join(random.choices("abcdef1234567890", k=32))
    '''randomsearchid'''
    @staticmethod
    def randomsearchid():
        e = random.randint(1, 20)
        t = e * 18014398509481984
        n = random.randint(0, 4194304) * 4294967296
        a = time.time()
        r = round(a * 1000) % (24 * 60 * 60 * 1000)
        return str(t + n + r)
    '''buildcommonparams'''
    @staticmethod
    def buildcommonparams(credential: Credential = None, common_override: dict = None) -> dict[str, Any]:
        common_override, credential = common_override or {}, credential or Credential()
        qimei_result = QQMusicClientUtils().qimei
        common = {"cv": QQMusicClientUtils.version_code, "v": QQMusicClientUtils.version_code, "QIMEI36": qimei_result['q36']}
        common.update(QQMusicClientUtils.COMMON_DEFAULTS)
        if bool(credential.musicid) and bool(credential.musickey): common.update({"qq": str(credential.musicid), "authst": credential.musickey, "tmeLoginType": str(credential.login_type)})
        common.update(common_override)
        return common
    '''builddata'''
    @staticmethod
    def builddata(params: dict, module: str, method: str, process_bool: bool = True):
        params = {k: int(v) if isinstance(v, bool) else v for k, v in params.items()} if process_bool else params
        return {"module": module, "method": method, "param": params}
    '''buildrequestdata'''
    @staticmethod
    def buildrequestdata(params: dict, module: str, method: str, credential: Credential = None, common_override: dict = None, process_bool: bool = True) -> dict[str, Any]:
        return {"comm": QQMusicClientUtils.buildcommonparams(credential, common_override), f"{module}.{method}": QQMusicClientUtils.builddata(params, module, method, process_bool)}