'''
Function:
    Implementation of QobuzMusicClient Cookies Builder
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import requests
from urllib.parse import urljoin


'''settings'''
USERNAME = 'Your Email or UserID Here'
PASSWORD = 'Your Password or Token Here'
LOGIN_BY_PASSWORD = True # modify as False if you use token to login in Qobuz


'''buildqobuzcookies'''
def buildqobuzcookies():
    (session := requests.Session()).headers.update({"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"})
    (resp := session.get("https://play.qobuz.com/login")).raise_for_status()
    bundle_url = re.search(r'<script src="(/resources/\d+\.\d+\.\d+-[a-z]\d{3}/bundle\.js)"></script>', resp.text).group(1)
    (resp := session.get(urljoin("https://play.qobuz.com", bundle_url))).raise_for_status()
    app_id = str(re.search(r'production:{api:{appId:"(?P<app_id>\d{9})",appSecret:"(\w{32})', resp.text).group("app_id"))
    session.headers.update({"X-App-Id": str(app_id)})
    params = {"user_id": USERNAME, "user_auth_token": PASSWORD, "app_id": str(app_id),} if not LOGIN_BY_PASSWORD else {"email": USERNAME, "password": PASSWORD,  "app_id": str(app_id),}
    (resp := session.get("https://www.qobuz.com/api.json/0.2/user/login", params=params)).raise_for_status()
    cookies: dict = requests.utils.dict_from_cookiejar(resp.cookies)
    cookies.update(requests.utils.dict_from_cookiejar(session.cookies))
    cookies.update(resp.json()); cookies['x-user-auth-token'] = cookies['user_auth_token']
    return cookies


'''tests'''
if __name__ == '__main__':
    print(buildqobuzcookies())