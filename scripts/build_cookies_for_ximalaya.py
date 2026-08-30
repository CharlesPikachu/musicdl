'''
Function:
    Implementation of XimalayaMusicClient Cookies Builder
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import time
import base64
import requests
import webbrowser
from pathlib import Path


'''XimalayaLogin'''
class XimalayaLogin:
    BASE = 'https://www.ximalaya.com'
    BASE_PASSPORT = 'https://passport.ximalaya.com'
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.UA, 'Accept': 'application/json, text/plain, */*',})
    '''createqrcode'''
    def createqrcode(self):
        (resp := self.session.get(f'{self.BASE_PASSPORT}/web/qrCode/gen', params={'level': 'L', 'source': 'ximalaya-web'}, timeout=15,)).raise_for_status(); data: dict = resp.json()
        if data.get('ret') != 0: raise RuntimeError(f"Fail to generate qrcode: {data.get('msg') or data.get('ret')}")
        qr_id, image = data.get('qrId'), data.get('img')
        if not qr_id or not image: raise RuntimeError('Fail to generate qrcode as qrId or img missed')
        return qr_id, base64.b64decode(image)
    '''showqrcode'''
    def showqrcode(self, image):
        (path := Path('ximalaya_login_qrcode.png').resolve()).write_bytes(image)
        try:
            if os.name == 'nt': os.startfile(str(path))
            else: webbrowser.open(path.as_uri())
        except Exception: pass
        print(f'Please use the Ximalaya app to scan the QR code and log in: {path}')
        return path
    '''checkqrcode'''
    def checkqrcode(self, qr_id) -> dict:
        (resp := self.session.get(f'{self.BASE_PASSPORT}/web/qrCode/check/{qr_id}/{int(time.time() * 1000)}', timeout=15,)).raise_for_status()
        return resp.json()
    '''getcurrentuser'''
    def getcurrentuser(self, cookies):
        try:
            (resp := self.session.get(f'{self.BASE}/revision/main/getCurrentUser', cookies=cookies, headers={'Referer': f'{self.BASE}/'}, timeout=15,)).raise_for_status(); data: dict = resp.json()
            if data.get('ret') != 200: return None
            return data.get('data') or {}
        except Exception:
            return None
    '''login'''
    def login(self, timeout=180, interval=2):
        qr_id, image = self.createqrcode()
        qrcode_path, start = self.showqrcode(image), time.time()
        try:
            while time.time() - start < timeout:
                if self.checkqrcode(qr_id).get('ret') == 0:
                    if (cookies := requests.utils.dict_from_cookiejar(self.session.cookies)).get('1&_token'):
                        if (user := self.getcurrentuser(cookies)): print(f"Login successful: {user.get('nickname', '')}")
                        else: print('Login successful')
                        return cookies
                time.sleep(interval)
            raise TimeoutError('The QR code has expired. Please log in again.')
        finally:
            try: qrcode_path.unlink()
            except Exception: pass


'''tests'''
if __name__ == '__main__':
    print(XimalayaLogin().login())