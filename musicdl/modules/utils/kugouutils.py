'''
Function:
    Implementation of KugouMusicClient Utils
    >>> old api: https://trackercdn.kugou.com/i/?cmd=4&pid=1&forceDown=0&vip=1&hash={file_hash}&key={MD5(file_hash+kgcloud)}
    >>> webv2 play: https://trackercdnbj.kugou.com/i/v2/?cmd=23&pid=1&behavior=play&hash={file_hash}&key={MD5(file_hash+kgcloudv2)}
    >>> appv2 play: https://trackercdn.kugou.com/i/v2/?appid=1005&pid=2&cmd=25&behavior=play&hash={file_hash}&key={MD5(file_hash+kgcloudv2)}
    >>> appv2 download: https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={file_hash}&key={MD5(file_hash+kgcloudv2)}
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import json
import uuid
import time
import random
import base64
import hashlib
import requests
from Crypto.PublicKey import RSA
from .misc import safeextractfromdict
from typing import Any, Dict, Optional
from Crypto.Cipher import AES, PKCS1_v1_5


'''settings'''
IS_LITE = True
APPID = 3116 if IS_LITE else 1005
CLIENTVER = 11440 if IS_LITE else 20489
MUSIC_QUALITIES = ('viper_tape', 'viper_clear', 'viper_atmos', 'flac', 'high', '320', '128')
SIGNATURE_WEB_SECRET = "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt"
SIGN_KEY_SECRET = "185672dd44712f60bb1736df5a377e82" if IS_LITE else "57ae12eb6890223e355ccfcb74edf70d"
SIGNATURE_ANDROID_SECRET = "LnT6xpN3khm36zse0QzvmgTZ3waWdRSA" if IS_LITE else "OIlwieks28dk2k092lksi2UIkp"
PUBLIC_RSA_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDECi0Np2UR87scwrvTr72L6oO01rBbbBPriSDFPxr3Z5syug0O24QyQO8bg27+0+4kBzTBTBOZ/WWU0WryL1JSXRTXLgFVxtzIY41Pe7lPOgsfTCn5kZcvKhYKJesKnnJDNr5/abvTGf+rHG3YRwsCHcQ08/q6ifSioBszvb3QiwIDAQAB
-----END PUBLIC KEY-----""" if IS_LITE else """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDIAG7QOELSYoIJvTFJhMpe1s/gbjDJX51HBNnEl5HXqTW6lQ7LC8jr9fWZTwusknp+sVGzwd40MwP6U5yDE27M/X1+UR4tvOGOqp94TJtQ1EPnWGWXngpeIW5GxoQGao1rmYWAu6oi1z9XkChrsUdC6DJE5E221wf/4WLFxwAtRQIDAQAB
-----END PUBLIC KEY-----"""


'''KugouMusicClientUtils'''
class KugouMusicClientUtils:
    '''md5hex'''
    @staticmethod
    def md5hex(data: Any) -> str:
        if isinstance(data, (dict, list)): data = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        if isinstance(data, str): data = data.encode("utf-8")
        return hashlib.md5(data).hexdigest()
    '''randomstring'''
    @staticmethod
    def randomstring(length=16) -> str:
        chars = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(random.choice(chars) for _ in range(length))
    '''calculatemid'''
    @staticmethod
    def calculatemid(seed: str) -> str:
        return str(int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16))
    '''pad'''
    @staticmethod
    def pad(data: bytes, block_size: int = 16) -> bytes:
        pad_len = block_size - len(data) % block_size
        return data + bytes([pad_len]) * pad_len
    '''unpad'''
    @staticmethod
    def unpad(data: bytes) -> bytes:
        pad_len = data[-1]
        return data[:-pad_len]
    '''rsaencryptpkcs1'''
    @staticmethod
    def rsaencryptpkcs1(data: Any, public_key_pem: str = PUBLIC_RSA_KEY) -> str:
        if isinstance(data, (dict, list)): data = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        if isinstance(data, str): data = data.encode("utf-8")
        rsa_key = RSA.import_key(public_key_pem)
        cipher = PKCS1_v1_5.new(rsa_key)
        enc = cipher.encrypt(data)
        return enc.hex()
    '''signatureandroid'''
    @staticmethod
    def signatureandroid(params: Dict[str, Any], data: str = "") -> str:
        params_string = "".join(f"{k}={json.dumps(params[k], separators=(',', ':'), ensure_ascii=False) if isinstance(params[k], (dict, list)) else params[k]}" for k in sorted(params.keys()))
        return KugouMusicClientUtils.md5hex(f"{SIGNATURE_ANDROID_SECRET}{params_string}{data}{SIGNATURE_ANDROID_SECRET}")
    '''signatureandroidwithsecret'''
    @staticmethod
    def signatureandroidwithsecret(params: Dict[str, Any], data: str, secret: str = "OIlwieks28dk2k092lksi2UIkp") -> str:
        params_string = "".join(f"{k}={json.dumps(params[k], separators=(',', ':'), ensure_ascii=False) if isinstance(params[k], (dict, list)) else params[k]}" for k in sorted(params.keys()))
        return KugouMusicClientUtils.md5hex(f"{secret}{params_string}{data}{secret}")
    '''signatureweb'''
    @staticmethod
    def signatureweb(params: Dict[str, Any]) -> str:
        params_string = "".join(f"{k}={params[k]}" for k in sorted(params.keys()))
        return KugouMusicClientUtils.md5hex(f"{SIGNATURE_WEB_SECRET}{params_string}{SIGNATURE_WEB_SECRET}")
    '''signkey'''
    @staticmethod
    def signkey(hash_value: str, mid: str, userid: str, appid: str) -> str:
        return KugouMusicClientUtils.md5hex(f"{hash_value}{SIGN_KEY_SECRET}{appid}{mid}{userid or 0}")
    '''initdevice'''
    @staticmethod
    def initdevice(cookies: dict = None):
        cookies = cookies or {}
        guid = str(uuid.uuid4())
        mid = KugouMusicClientUtils.calculatemid(guid)
        cookies["KUGOU_API_GUID"] = guid
        cookies["KUGOU_API_MID"] = mid
        cookies["KUGOU_API_MAC"] = KugouMusicClientUtils.randomstring(12)
        cookies["KUGOU_API_DEV"] = KugouMusicClientUtils.randomstring(16)
        return cookies
    '''updatecookies'''
    @staticmethod
    def updatecookies(resp: requests.Response, cookies: dict):
        for k, v in resp.cookies.items(): cookies[k] = v
        return cookies
    '''sendrequest'''
    @staticmethod
    def sendrequest(session: requests.Session, method: str, url: str, params: Optional[Dict[str, Any]] = None, data: Optional[Any] = None, headers: Optional[Dict[str, str]] = None, encrypt_type: str = "android", base_url: str = "https://gateway.kugou.com", encrypt_key: bool = False, not_sign: bool = False, response_type: Optional[str] = None, cookies: Optional[Dict[str, str]] = None, cookies_override: Optional[Dict[str, str]] = None, request_overrides: dict = None):
        # init
        clienttime = int(time.time())
        params, headers, used_cookies, request_overrides = params or {}, headers or {}, dict(cookies), request_overrides or {}
        if cookies_override: used_cookies.update(cookies_override)
        token, dfid, userid, mid = used_cookies.get("token", ""), used_cookies.get("dfid", "-"), used_cookies.get("userid", 0), used_cookies.get("KUGOU_API_MID", "-")
        # construct params
        default_params = {"dfid": dfid, "mid": mid, "uuid": "-", "appid": APPID, "clientver": CLIENTVER, "clienttime": clienttime}
        if token: default_params["token"] = token
        if userid: default_params["userid"] = userid
        params = {**default_params, **params}
        # encrypt key
        if encrypt_key: params["key"] = KugouMusicClientUtils.signkey(params["hash"], params["mid"], params.get("userid"), params["appid"])
        # signature
        data_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False) if isinstance(data, (dict, list)) else (data or "")
        if not_sign:
            if "signature" in params: params.pop("signature", None)
        else:
            if "signature" not in params: params["signature"] = KugouMusicClientUtils.signatureweb(params) if encrypt_type == "web" else KugouMusicClientUtils.signatureandroid(params, data_str)
        # construct headers
        base_headers = {"User-Agent": "Android15-1070-11083-46-0-DiscoveryDRADProtocol-wifi", "dfid": dfid, "clienttime": str(params["clienttime"]), "mid": mid, "kg-rc": "1", "kg-thash": "5d816a0", "kg-rec": "1", "kg-rf": "B9EDA08A64250DEFFBCADDEE00F8F25F"}
        final_headers = {**base_headers, **headers}
        # send request
        resp = session.request(method, f"{base_url}{url}", params=params, json=data, headers=final_headers, **request_overrides) if isinstance(data, (dict, list)) else session.request(method, f"{base_url}{url}", params=params, data=data, headers=final_headers, **request_overrides)
        resp.raise_for_status()
        KugouMusicClientUtils.updatecookies(resp, cookies)
        # return
        if response_type == "arraybuffer": return resp.content
        try: return resp.json()
        except Exception: return resp.text
    '''registerdevice'''
    @staticmethod
    def registerdevice(session: requests.Session, cookies: dict, request_overrides: dict = None):
        # construct
        data_map = {
            "availableRamSize": 4983533568, "availableRomSize": 48114719, "availableSDSize": 48114717, "basebandVer": "", "batteryLevel": 100, "batteryStatus": 3, "brand": "Redmi", "buildSerial": "unknown", 
            "device": "marble", "imei": cookies.get("KUGOU_API_GUID"), "imsi": "", "manufacturer": "Xiaomi", "uuid": cookies.get("KUGOU_API_GUID"), "accelerometer": False, "accelerometerValue": "", 
            "gravity": False, "gravityValue": "", "gyroscope": False, "gyroscopeValue": "", "light": False, "lightValue": "", "magnetic": False, "magneticValue": "", "orientation": False, "orientationValue": "", 
            "pressure": False, "pressureValue": "", "step_counter": False, "step_counterValue": "", "temperature": False, "temperatureValue": "",
        }
        # aes
        aes_key = KugouMusicClientUtils.randomstring(6).lower(); encrypt_key = KugouMusicClientUtils.md5hex(aes_key)[:16]; encrypt_iv = KugouMusicClientUtils.md5hex(aes_key)[16: 32]
        cipher = AES.new(encrypt_key.encode("utf-8"), AES.MODE_CBC, encrypt_iv.encode("utf-8"))
        raw = json.dumps(data_map, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        enc = cipher.encrypt(KugouMusicClientUtils.pad(raw))
        aes_body = base64.b64encode(enc).decode("utf-8")
        p = KugouMusicClientUtils.rsaencryptpkcs1({"aes": aes_key, "uid": cookies.get("userid", 0), "token": cookies.get("token", "")})
        # send request and return result
        resp_raw: bytes = KugouMusicClientUtils.sendrequest(session, "POST", "/risk/v2/r_register_dev", params={"part": 1, "platid": 1, "p": p}, data=aes_body, base_url="https://userservice.kugou.com", encrypt_type="android", response_type="arraybuffer", cookies=cookies, request_overrides=request_overrides)
        try:
            text: str = resp_raw.decode("utf-8"); result = json.loads(text) if text.startswith("{") else None
            if result: return result
        except Exception:
            pass
        dec_cipher = AES.new(encrypt_key.encode("utf-8"), AES.MODE_CBC, encrypt_iv.encode("utf-8"))
        decrypted = KugouMusicClientUtils.unpad(dec_cipher.decrypt(resp_raw)).decode("utf-8")
        result: dict = json.loads(decrypted)
        if result.get("status") == 1 and safeextractfromdict(result, ['data', 'dfid'], None): cookies["dfid"] = result["data"]["dfid"]
        return result
    '''getsongurl'''
    @staticmethod
    def getsongurl(session: requests.Session, hash_value: str, album_id: int = 0, album_audio_id: int = 0, quality: str = "128", free_part: bool = False, cookies: dict = None, request_overrides: dict = None):
        params = {
            "album_id": int(album_id), "area_code": 1, "hash": hash_value.lower(), "ssa_flag": "is_fromtrack", "version": 11436, "page_id": 151369488 if not IS_LITE else 967177915,
            "quality": quality, "album_audio_id": int(album_audio_id), "behavior": "play", "pid": 2 if not IS_LITE else 411, "cmd": 26, "pidversion": 3001, "IsFreePart": 1 if free_part else 0,
            "ppage_id": "463467626,350369493,788954147" if not IS_LITE else "356753938,823673182,967485191", "cdnBackup": 1, "kcard": 0, "module": "",
        }
        return KugouMusicClientUtils.sendrequest(session, "GET", "/v5/url", params=params, headers={"x-router": "trackercdn.kugou.com"}, encrypt_type="android", encrypt_key=True, cookies=cookies, cookies_override={'dfid': KugouMusicClientUtils.randomstring(24)}, request_overrides=request_overrides)