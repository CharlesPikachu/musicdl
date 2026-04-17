'''
Function:
    Implementation of SoundCloudMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import requests
from pathlib import Path
from pywidevine.cdm import Cdm
from pywidevine.pssh import PSSH
from pywidevine.device import Device


'''SoundCloudMusicClientUtils'''
class SoundCloudMusicClientUtils():
    WVD_PATH = Path(__file__).resolve().parents[2] / "modules" / "wvds" / "musicdl_charlespikachu_device_v1.wvd"
    '''getwidevinekeys'''
    @staticmethod
    def getwidevinekeys(m3u8_url: str, headers: dict = None, cookies: dict = None, request_overrides: dict = None):
        cdm = Cdm.from_device(Device.load(SoundCloudMusicClientUtils.WVD_PATH))
        m3u8_text = requests.get(m3u8_url, headers=(headers := headers or {}), cookies=(cookies := cookies or {}), **(request_overrides := request_overrides or {})).text
        license_url = re.search(r'URI="([^"]+widevine[^"]*)"', m3u8_text).group(1)
        pssh_match = re.search(r'URI="data:text/plain;base64,([^"]+)"', m3u8_text)
        pssh_obj = PSSH(pssh_match.group(1)) if pssh_match else PSSH(requests.get(re.search(r'^(http[^\n]+\.m4s|http[^\n]+init[^\n]+)', m3u8_text, re.MULTILINE).group(1), cookies=cookies, headers=headers, **request_overrides).content)
        challenge = cdm.get_license_challenge((session_id := cdm.open()), pssh_obj)
        (license_resp := requests.post(license_url, data=challenge, headers={"Content-Type": "application/octet-stream", **headers}, cookies=cookies, **request_overrides)).raise_for_status()
        cdm.parse_license(session_id, license_resp.content); keys = [f"{key.kid.hex}:{key.key.hex}" for key in cdm.get_keys(session_id) if key.type == 'CONTENT']; cdm.close(session_id)
        return keys