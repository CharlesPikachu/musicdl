'''
Function:
    Implementation of JooxMusicClient Cookies Builder
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import time
import hashlib
import requests
from urllib.parse import quote


'''settings'''
USERNAME = 'Your Email Here'
PASSWORD = 'Your Password Here'


'''buildjooxcookies'''
def buildjooxcookies():
    session, epoch = requests.Session(), int(time.time()) - 60
    encoded_email, md5_password = quote(quote(USERNAME)), hashlib.md5(PASSWORD.encode('utf-8')).hexdigest()
    url_auth = f"https://api.joox.com/web-fcgi-bin/web_wmauth?country=id&lang=id&wxopenid={encoded_email}&password={md5_password}&wmauth_type=0&authtype=2&time={epoch}294&_={epoch}295&callback=axiosJsonpCallback1"
    resp = session.get(url_auth)
    cookies: dict = requests.utils.dict_from_cookiejar(resp.cookies)
    cookies.update(requests.utils.dict_from_cookiejar(session.cookies))
    return cookies


'''tests'''
if __name__ == '__main__':
    print(buildjooxcookies())