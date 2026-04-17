'''
Function:
    Implementation of Cookies Related Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import pickle
from http.cookies import SimpleCookie


'''cookies2dict'''
def cookies2dict(cookies: str | dict = None):
    if not cookies: cookies = {}
    if isinstance(cookies, dict): return cookies
    if isinstance(cookies, str): (c := SimpleCookie()).load(cookies); return {k: morsel.value for k, morsel in c.items()}
    raise TypeError(f'cookies type is "{type(cookies)}", expect cookies to "str" or "dict" or "None".')


'''cookies2string'''
def cookies2string(cookies: str | dict = None):
    if not cookies: cookies = ""
    if isinstance(cookies, str): return cookies
    if isinstance(cookies, dict): return (lambda c: ([c.__setitem__(k, "" if v is None else str(v)) for k, v in cookies.items()], "; ".join(m.OutputString() for m in c.values()))[1])(SimpleCookie())
    raise TypeError(f'cookies type is "{type(cookies)}", expect cookies to "str" or "dict" or "None".')


'''cachecookies'''
def cachecookies(client_name: str = '', cache_cookie_path: str = '', client_cookies: dict = None):
    cookies = pickle.load((fp := open(cache_cookie_path, 'rb'))) if os.path.exists(cache_cookie_path) else dict(); fp.close()
    with open(cache_cookie_path, 'wb') as fp: cookies[client_name] = client_cookies; pickle.dump(cookies, fp)