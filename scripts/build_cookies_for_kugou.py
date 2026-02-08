'''
Function:
    Implementation of KugouMusicClient Cookies Builder
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import time
import qrcode
import requests
from musicdl.modules.utils.kugouutils import KugouMusicClientUtils, APPID, safeextractfromdict


'''settings'''
session, cookies = requests.Session(), KugouMusicClientUtils.initdevice()


'''loginqrkey'''
def loginqrkey(use_web: bool = False):
    qr_appid = 1014 if use_web else 1001
    params = {"appid": qr_appid, "type": 1, "plat": 4, "qrcode_txt": f"https://h5.kugou.com/apps/loginQRCode/html/index.html?appid={APPID}&", "srcappid": 2919}
    return KugouMusicClientUtils.sendrequest(session, "GET", "/v2/qrcode", params=params, base_url="https://login-user.kugou.com", encrypt_type="web", cookies=cookies)


'''loginqrcheck'''
def loginqrcheck(key: str):
    params = {"plat": 4, "appid": APPID, "srcappid": 2919, "qrcode": key}
    result = KugouMusicClientUtils.sendrequest(session, "GET", "/v2/get_userinfo_qrcode", params=params, base_url="https://login-user.kugou.com", encrypt_type="web", cookies=cookies)
    if isinstance(result, dict) and safeextractfromdict(result, ['data', 'status'], None) == 4:
        token = safeextractfromdict(result, ['data', 'token'], None)
        userid = safeextractfromdict(result, ['data', 'userid'], None)
        if token: cookies["token"] = token
        if userid: cookies["userid"] = str(userid)
    return result


'''buildkugoucookies'''
def buildkugoucookies():
    # prepare for scan qr code
    qr_resp = loginqrkey()
    qr_key = qr_resp["data"]["qrcode"]
    img = qrcode.make(f"https://h5.kugou.com/apps/loginQRCode/html/index.html?qrcode={qr_key}")
    img.save("kugou_login_qr.png"); img.show()
    # wait for scan
    while True:
        check = loginqrcheck(qr_key)
        if safeextractfromdict(check, ['data', 'status'], None) == 4: break
        time.sleep(2)
    # register device
    KugouMusicClientUtils.registerdevice(session, cookies)
    # return
    return cookies


'''tests'''
if __name__ == '__main__':
    print(buildkugoucookies())