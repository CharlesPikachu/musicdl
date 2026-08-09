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
APPLE_MUSIC_HOSTS = {"music.apple.com", "geo.music.apple.com", "embed.music.apple.com", "itunes.apple.com", "geo.itunes.apple.com", "apple.com"}
AUDIUS_MUSIC_HOSTS = {'audius.co', 'www.audius.co',}
BODIAN_MUSIC_HOST = {"bodian.kuwo.cn", "h5app.kuwo.cn", "bd-api.kuwo.cn", "ab-bodian.kuwo.cn", "bodiancdn.kuwo.cn", "bodianimgcdn.kuwo.cn"}
CCMIXTER_MUSIC_HOSTS = {"ccmixter.org", "www.ccmixter.org"}
DEEZER_MUSIC_HOSTS = {"deezer.com", "www.deezer.com", "deezer.page.link",}
FIVESING_MUSIC_HOSTS = {"5sing.kugou.com",}
JOOX_MUSIC_HOSTS = {"joox.com",}
JAMENDO_MUSIC_HOSTS = {"jamendo.com",}
KUWO_MUSIC_HOSTS = {"kuwo.cn", "www.kuwo.cn", "m.kuwo.cn", "mobile.kuwo.cn",}
KUGOU_MUSIC_HOSTS = {"www.kugou.com", "m.kugou.com", "kugou.com", "h5.kugou.com",}
MIGU_MUSIC_HOSTS = {"music.migu.cn", "m.music.migu.cn", "h5.nf.migu.cn", "c.migu.cn", "migu.cn"}
NETEASE_MUSIC_HOSTS = {"music.163.com", "y.music.163.com", "m.music.163.com", "3g.music.163.com", "163cn.tv",}
QQ_MUSIC_HOSTS = {"y.qq.com", "i.y.qq.com", "m.y.qq.com", "c.y.qq.com", "c6.y.qq.com", "music.qq.com",}
QIANQIAN_MUSIC_HOSTS = {"music.91q.com", "music.taihe.com", "music.baidu.com"}
QOBUZ_MUSIC_HOSTS = {"open.qobuz.com", "play.qobuz.com", "www.qobuz.com", "qobuz.com"}
STREETVOICE_MUSIC_HOSTS = {"streetvoice.cn"}
SOUNDCLOUD_MUSIC_HOSTS = {"soundcloud.com"}
SODA_MUSIC_HOSTS = {"qishui.douyin.com", "music.douyin.com", "www.qishui.com", "www.douyin.com", "z-qishui.douyin.com", "lf-luna-release.qishui.com", "luna-web.douyin.com", "bubble.qishui.com", "qishui.com", "douyin.com"}
SPOTIFY_MUSIC_HOSTS = {"open.spotify.com", "spotify.link", "play.spotify.com", "spotify.com"}
SUNO_MUSIC_HOSTS = {"suno.com", "app.suno.ai", "alpha.suno.ai"}
TIDAL_MUSIC_HOSTS = {"tidal.com", "listen.tidal.com", "embed.tidal.com",}
YANDEX_MUSIC_HOSTS = {"music.yandex.com", "music.yandex.ru", "music.yandex.kz", "music.yandex.by", "music.yandex.uz"}
FMA_MUSIC_HOSTS = {"freemusicarchive.org"}
JIOSAAVN_MUSIC_HOSTS = {"jiosaavn.com", "www.jiosaavn.com", "saavn.com", "www.saavn.com", "jiosaa.vn",}
MOOV_MUSIC_HOSTS = {"moov.hk", "www.moov.hk", "app.moov.hk", "s.moov.hk", "moov-music.com"}


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