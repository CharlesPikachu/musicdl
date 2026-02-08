'''
Function:
    Implementation of URL Domain Related Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from functools import lru_cache
from urllib.parse import urlsplit


'''settings'''
NETEASE_MUSIC_HOSTS = {
    "music.163.com", "y.music.163.com", "m.music.163.com", "3g.music.163.com", "163cn.tv",
}
QQ_MUSIC_HOSTS = {
    "y.qq.com", "i.y.qq.com", "m.y.qq.com", "c.y.qq.com", "c6.y.qq.com", "music.qq.com",
}


'''obtainhostname'''
@lru_cache(maxsize=200_000)
def obtainhostname(url: str) -> str | None:
    if not url: return None
    u = url.strip()
    if "://" not in u: u = "https://" + u
    try: host = urlsplit(u).hostname
    except Exception: return None
    return host.lower().strip(".") if host else None


'''hostmatchessuffix'''
def hostmatchessuffix(host: str | None, suffixes: set[str]) -> bool:
    if not host: return False
    h = host.lower().strip(".")
    for s in suffixes:
        s = s.lower().strip(".")
        if h == s or h.endswith("." + s): return True
    return False