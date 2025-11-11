'''
Function:
    Implementation of QQMusicClient utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import time
import orjson
import base64
import random
import string
import hashlib
import requests
import binascii
from uuid import uuid4
from typing import ClassVar, cast
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''constants'''
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDEIxgwoutfwoJxcGQeedgP7FG9qaIuS0qzfR8gWkrkTZKM2iWHn2ajQpBRZjMSoSf6+KJGvar2ORhBfpDXyVtZCKpqLQ+FLkpncClKVIrBwv6PHyUvuCb0rIarmgDnzkfQAqVufEtR64iazGDKatvJ9y6B9NMbHddGSAUmRTCrHQIDAQAB
-----END PUBLIC KEY-----"""
SECRET = "ZdJqM15EeO2zWc08"
APP_KEY = "0AND0HD6FE4HY80F"
DEFAULT_VIP_QUALITIES = {
    "MASTER": ("AIM0", ".mflac"), "ATMOS_2": ("Q0M0", ".mflac"), "ATMOS_51": ("Q0M1", ".mflac"), "FLAC": ("F0M0", ".mflac"),
    "OGG_640": ("O801", ".mgg"), "OGG_320": ("O800", ".mgg"), "OGG_192": ("O6M0", ".mgg"), "OGG_96": ("O4M0", ".mgg"),
}
DEFAULT_QUALITIES = {
    "MASTER": ("AI00", ".flac"), "ATMOS_2": ("Q000", ".flac"), "ATMOS_51": ("Q001", ".flac"), "FLAC": ("F000", ".flac"), 
    "OGG_640":  ("O801", ".ogg"), "OGG_320": ("O800", ".ogg"), "OGG_192": ("O600", ".ogg"), "OGG_96": ("O400", ".ogg"), 
    "MP3_320": ("M800", ".mp3"), "MP3_128": ("M500", ".mp3"), "ACC_192": ("C600", ".m4a"), "ACC_96": ("C400", ".m4a"),
    "ACC_48":   ("C200", ".m4a"),
}


'''QQMusicClientUtils'''
class QQMusicClientUtils(object):
    '''randomimei'''
    @staticmethod
    def randomimei():
        imei, sum_ = [], 0
        for i in range(14):
            num = random.randint(0, 9)
            if (i + 2) % 2 == 0:
                num *= 2
                if num >= 10: num = (num % 10) + 1
            sum_ += num
            imei.append(str(num))
        ctrl_digit = (sum_ * 9) % 10
        imei.append(str(ctrl_digit))
        return "".join(imei)
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
    '''randombeaconid'''
    @staticmethod
    def randombeaconid():
        beacon_id = ""
        time_month = datetime.now().strftime("%Y-%m-") + "01"
        rand1 = random.randint(100000, 999999)
        rand2 = random.randint(100000000, 999999999)
        for i in range(1, 41):
            if i in [1, 2, 13, 14, 17, 18, 21, 22, 25, 26, 29, 30, 33, 34, 37, 38]:
                beacon_id += f"k{i}:{time_month}{rand1}.{rand2}"
            elif i == 3:
                beacon_id += "k3:0000000000000000"
            elif i == 4:
                beacon_id += f"k4:{''.join(random.choices('123456789abcdef', k=16))}"
            else:
                beacon_id += f"k{i}:{random.randint(0, 9999)}"
            beacon_id += ";"
        return beacon_id
    '''randompayloadbydevice'''
    @staticmethod
    def randompayloadbydevice(device, version: str):
        fixed_rand = random.randint(0, 14400)
        reserved = {
            "harmony": "0", "clone": "0", "containe": "", "oz": "UhYmelwouA+V2nPWbOvLTgN2/m8jwGB+yUB5v9tysQg=", "oo": "Xecjt+9S1+f8Pz2VLSxgpw==",
            "kelong": "0", "uptimes": (datetime.now() - timedelta(seconds=fixed_rand)).strftime("%Y-%m-%d %H:%M:%S"), "multiUser": "0",
            "bod": device.brand, "dv": device.device, "firstLevel": "", "manufact": device.brand, "name": device.model, "host": "se.infra",
            "kernel": device.proc_version,
        }
        return {
            "androidId": device.android_id, "platformId": 1, "appKey": APP_KEY, "appVersion": version, "beaconIdSrc": QQMusicClientUtils.randombeaconid(),
            "brand": device.brand, "channelId": "10003505", "cid": "", "imei": device.imei, "imsi": "", "mac": "", "model": device.model, "networkType": "unknown",
            "oaid": "", "osVersion": f"Android {device.version.release},level {device.version.sdk}", "qimei": "", "qimei36": "", "sdkVersion": "1.2.13.6",
            "targetSdkVersion": "33", "audit": "", "userId": "{}", "packageId": "com.tencent.qqmusic", "deviceType": "Phone", "sdkName": "",
            "reserved": orjson.dumps(reserved).decode(),
        }
    '''obtainqimei'''
    @staticmethod
    def obtainqimei(version: str, device):
        try:
            payload = QQMusicClientUtils.randompayloadbydevice(device, version)
            crypt_key = "".join(random.choices("adbcdef1234567890", k=16))
            nonce = "".join(random.choices("adbcdef1234567890", k=16))
            ts = int(time.time())
            key = base64.b64encode(QQMusicClientUtils.rsaencrypt(crypt_key.encode())).decode()
            params = base64.b64encode(QQMusicClientUtils.aesencrypt(crypt_key.encode(), orjson.dumps(payload))).decode()
            extra = '{"appKey":"' + APP_KEY + '"}'
            sign = QQMusicClientUtils.calcmd5(key, params, str(ts * 1000), nonce, SECRET, extra)
            resp = requests.post(
                "https://api.tencentmusic.com/tme/trpc/proxy",
                headers={
                    "Host": "api.tencentmusic.com", "method": "GetQimei", "service": "trpc.tme_datasvr.qimeiproxy.QimeiProxy", "appid": "qimei_qq_android",
                    "sign": QQMusicClientUtils.calcmd5("qimei_qq_androidpzAuCmaFAaFaHrdakPjLIEqKrGnSOOvH", str(ts)), "user-agent": "QQMusic", "timestamp": str(ts),
                },
                json={
                    "app": 0, "os": 1, "qimeiParams": {"key": key, "params": params, "time": str(ts), "nonce": nonce, "sign": sign, "extra": extra},
                },
            )
            data = orjson.loads(orjson.loads(resp.content)["data"])["data"]
            device.qimei = data["q36"]
            result = {"q16": data["q16"], "q36": data["q36"]}
            return result
        except:
            result = {"q16": "", "q36": "6c9d3cd110abca9b16311cee10001e717614"}
        return result


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
    imei: str = field(default_factory=QQMusicClientUtils.randomimei)
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