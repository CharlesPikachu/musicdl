<div align="center">
  <img src="https://raw.githubusercontent.com/CharlesPikachu/musicdl/master/docs/logo.png" width="600" alt="musicdl logo" />
  <br />

  <a href="https://musicdl.readthedocs.io/">
    <img src="https://img.shields.io/badge/docs-latest-blue" alt="docs" />
  </a>
  <a href="https://pypi.org/project/musicdl/">
    <img src="https://img.shields.io/pypi/pyversions/musicdl" alt="PyPI - Python Version" />
  </a>
  <a href="https://pypi.org/project/musicdl">
    <img src="https://img.shields.io/pypi/v/musicdl" alt="PyPI" />
  </a>
  <a href="https://github.com/CharlesPikachu/musicdl/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/CharlesPikachu/musicdl.svg" alt="license" />
  </a>
  <a href="https://pypi.org/project/musicdl/">
    <img src="https://pepy.tech/badge/musicdl" alt="PyPI - Downloads" />
  </a>
  <a href="https://pypi.org/project/musicdl/">
    <img src="https://img.shields.io/pypi/dm/musicdl?style=flat-square" alt="downloads" />
  </a>
  <a href="https://github.com/CharlesPikachu/musicdl/issues">
    <img src="https://isitmaintained.com/badge/resolution/CharlesPikachu/musicdl.svg" alt="issue resolution" />
  </a>
  <a href="https://github.com/CharlesPikachu/musicdl/issues">
    <img src="https://isitmaintained.com/badge/open/CharlesPikachu/musicdl.svg" alt="open issues" />
  </a>

  <p><a href="https://musicdl.readthedocs.io/">Documents: musicdl.readthedocs.io</a></p>
  
  <p>
    <strong>🎧 Live Demo · MusicSquare</strong><br />
    <a href="https://charlespikachu.github.io/musicsquare/" target="_blank">
      https://charlespikachu.github.io/musicsquare/
    </a>
  </p>
  <p>
    <em>
      A browser-based music playground — search, play, and download tracks directly in your browser.  
      ⚠️ For learning and testing only: please respect copyright and the terms of each music platform.
    </em>
  </p>

  <p>
    <strong>🛠 Source Code:</strong><br />
    <a href="https://github.com/CharlesPikachu/musicsquare" target="_blank">
      https://github.com/CharlesPikachu/musicsquare
    </a>
  </p>
</div>


# 🎉 What's New

- 2025-11-15: Released musicdl v2.4.3 — migu and netease have introduced an automatic audio quality enhancement feature, which significantly increases the chances of getting lossless quality, Hi-Res audio, JyEffect (HD surround sound), Sky (immersive surround sound), and JyMaster (ultra-clear master quality).
- 2025-11-15: Released musicdl v2.4.2 — save meta info to music files from TIDAL, fix user input bugs and migu search bugs.
- 2025-11-14: Released musicdl v2.4.1 — beautify print, add support for TIDAL (TIDAL is an artist-first, fan-centered music streaming platform that delivers over 110 million songs in HiFi sound quality to the global music community).
- 2025-11-12: Released musicdl v2.4.0 — complete code refactor; reintroduced support for music search and downloads on major platforms.


# 🎵 Introduction

A lightweight music downloader written in pure Python. Like it? ⭐ Star the repository to stay up to date. Thanks!


# ⚠️ Disclaimer

This project is for educational use only and is not intended for commercial purposes. It interacts with publicly available web endpoints and does not host or distribute copyrighted content.
To access paid tracks, please purchase or subscribe to the relevant music service—do not use this project to bypass paywalls or DRM.
If you are a rights holder and believe this repository infringes your rights, please contact me and I will promptly address it.


# 🎧 Supported Music Client

|  MusicClient (EN)              |  MusicClient (CN)                   |   Search           |  Download            |    Code Snippet                                                                                                    |
|  :----:                        |  :----:                             |   :----:           |  :----:              |    :----:                                                                                                          |
|  FiveSingMusicClient           |  5SING音乐                          |   ✓                |  ✓                   |    [fivesing.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/fivesing.py)        |
|  KugouMusicClient              |  酷狗音乐                           |   ✓                |  ✓                   |    [kugou.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kugou.py)              |
|  KuwoMusicClient               |  酷我音乐                           |   ✓                |  ✓                   |    [kuwo.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kuwo.py)                |
|  LizhiMusicClient              |  荔枝FM                             |   ✓                |  ✓                   |    [lizhi.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/lizhi.py)              |
|  MiguMusicClient               |  咪咕音乐                           |   ✓                |  ✓                   |    [migu.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/migu.py)                |
|  NeteaseMusicClient            |  网易云音乐                         |   ✓                |  ✓                   |    [netease.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/netease.py)          |
|  QianqianMusicClient           |  千千音乐                           |   ✓                |  ✓                   |    [qianqian.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qianqian.py)        |
|  QQMusicClient                 |  QQ音乐                             |   ✓                |  ✓                   |    [qq.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py)                    |
|  XimalayaMusicClient           |  喜马拉雅                           |   ✓                |  ✓                   |    [ximalaya.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/ximalaya.py)        |
|  JooxMusicClient               |  JOOX (QQ音乐海外版)                |   ✓                |  ✓                   |    [joox.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/joox.py)                |
|  TIDALMusicClient              |  TIDAL (提供HiFi音质的流媒体平台)   |   ✓                |  ✓                   |    [tidal.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/tidal.py)              |


# 🧪 Playground

Here are some projects built on top of musicdl,

|  Project (EN)                                  |   Project (CN)          |   WeChat Article                                             |  Project Location                                                                                                         |
|  :----:                                        |   :----:                |   :----:                                                     |  :----:                                                                                                                   |
|  Music downloader GUI                          |   音乐下载器GUI界面     |   [click](https://mp.weixin.qq.com/s/fN1ORyI6lzQFqxf6Zk1oIg) |  [musicdlgui](https://github.com/CharlesPikachu/musicdl/tree/master/examples/examples/musicdlgui)                         |
|  Singer lyrics analysis                        |   歌手歌词分析          |   [click](https://mp.weixin.qq.com/s/I8Dy7CoM2ThnSpjoUaPtig) |  [singerlyricsanalysis](https://github.com/CharlesPikachu/musicdl/tree/master/examples/examples/singerlyricsanalysis)     |
|  Lyric-based song snippet retrieval            |   歌词获取歌曲片段      |   [click](https://mp.weixin.qq.com/s/Vmc1IhuhMJ6C5vBwBe43Pg) |  [searchlyrics](https://github.com/CharlesPikachu/musicdl/tree/master/examples/examples/searchlyrics)                     |

For example, the Music Downloader GUI looks/works like this,

<div align="center">
  <img src="https://raw.githubusercontent.com/CharlesPikachu/musicdl/master/examples/musicdlgui/screenshot.png" width="600" alt="musicdl logo" />
</div>


# 📦 Install

You have three installation methods to choose from,

```sh
# from pip
pip install musicdl
# from github repo method-1
pip install git+https://github.com/CharlesPikachu/musicdl.git@master
# from github repo method-2
git clone https://github.com/CharlesPikachu/musicdl.git
cd musicdl
python setup.py install
```

Some music platforms require [FFmpeg](https://www.ffmpeg.org/) to be directly callable in your environment in order to obtain higher-quality audio. 
You can choose whether to install [FFmpeg](https://www.ffmpeg.org/) depending on your needs.

# 🚀 Quick Start

After a successful installation, you can run the snippet below,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['MiguMusicClient', 'NeteaseMusicClient', 'KuwoMusicClient', 'KugouMusicClient', 'QQMusicClient', 'QianqianMusicClient'])
music_client.startcmdui()
```

Or just run `musicdl` (maybe `musicdl --help` to show usage information) from the terminal.

```
Usage: musicdl [OPTIONS]

Options:
  --version                       Show the version and exit.
  -k, --keyword TEXT              The keywords for the music search. If left
                                  empty, an interactive terminal will open
                                  automatically.
  -m, --music-sources, --music_sources TEXT
                                  The music search and download sources.
                                  [default: MiguMusicClient,NeteaseMusicClient
                                  ,KuwoMusicClient,KugouMusicClient,QQMusicCli
                                  ent,QianqianMusicClient]
  -i, --init-music-clients-cfg, --init_music_clients_cfg TEXT
                                  Config such as `work_dir` for each music
                                  client as a JSON string.
  -r, --requests-overrides, --requests_overrides TEXT
                                  Requests.get kwargs such as `headers` and
                                  `proxies` for each music client as a JSON
                                  string.
  -c, --clients-threadings, --clients_threadings TEXT
                                  Number of threads used for each music client
                                  as a JSON string.
  -s, --search-rules, --search_rules TEXT
                                  Search rules for each music client as a JSON
                                  string.
  --help                          Show this message and exit.
```

The demonstration is as follows,

<div align="center">
  <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot.gif" width="600"/>
</div>
<br />

If you are a VIP user on each music platform, for example, a VIP user of Netease Cloud Music, 
you can pass in the cookies from your logged-in account so that musicdl can download more tracks with higher quality (*e.g.*, flac music files). 
Example code is as follows:

```python
from musicdl import musicdl

your_vip_cookies_with_str_format = ""
your_vip_cookies_with_dict_format = dict(item.split("=", 1) for item in your_vip_cookies_with_str_format.split("; "))
init_music_clients_cfg = dict()
init_music_clients_cfg['NeteaseMusicClient'] = {'default_search_cookies': your_vip_cookies_with_dict_format, 'default_download_cookies': your_vip_cookies_with_dict_format, 'search_size_per_source': 20}
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

If you want to download lossless-quality music from [TIDAL](https://tidal.com/), 
you need to make sure that [PyAV](https://github.com/PyAV-Org/PyAV) is available or that [FFmpeg](https://www.ffmpeg.org/) is in your environment variables, 
and then use musicdl as follows,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['TIDALMusicClient'])
music_client.startcmdui()
```

For more practical examples, please refer to the usage documentation.


# ⭐ Recommended Projects

- [Games](https://github.com/CharlesPikachu/Games): Create interesting games in pure python.
- [DecryptLogin](https://github.com/CharlesPikachu/DecryptLogin): APIs for loginning some websites by using requests.
- [Musicdl](https://github.com/CharlesPikachu/musicdl): A lightweight music downloader written in pure python.
- [Videodl](https://github.com/CharlesPikachu/videodl): A lightweight video downloader written in pure python.
- [Pytools](https://github.com/CharlesPikachu/pytools): Some useful tools written in pure python.
- [PikachuWeChat](https://github.com/CharlesPikachu/pikachuwechat): Play WeChat with itchat-uos.
- [Pydrawing](https://github.com/CharlesPikachu/pydrawing): Beautify your image or video.
- [ImageCompressor](https://github.com/CharlesPikachu/imagecompressor): Image compressors written in pure python.
- [FreeProxy](https://github.com/CharlesPikachu/freeproxy): Collecting free proxies from internet.
- [Paperdl](https://github.com/CharlesPikachu/paperdl): Search and download paper from specific websites.
- [Sciogovterminal](https://github.com/CharlesPikachu/sciogovterminal): Browse "The State Council Information Office of the People's Republic of China" in the terminal.
- [CodeFree](https://github.com/CharlesPikachu/codefree): Make no code a reality.
- [DeepLearningToys](https://github.com/CharlesPikachu/deeplearningtoys): Some deep learning toys implemented in pytorch.
- [DataAnalysis](https://github.com/CharlesPikachu/dataanalysis): Some data analysis projects in charles_pikachu.
- [Imagedl](https://github.com/CharlesPikachu/imagedl): Search and download images from specific websites.
- [Pytoydl](https://github.com/CharlesPikachu/pytoydl): A toy deep learning framework built upon numpy.
- [NovelDL](https://github.com/CharlesPikachu/noveldl): Search and download novels from some specific websites.


# 📚 Citation

If you use this project in your research, please cite the repository.

```
@misc{musicdl2020,
    author = {Zhenchao Jin},
    title = {Musicdl: A lightweight music downloader written in pure python},
    year = {2020},
    publisher = {GitHub},
    journal = {GitHub repository},
    howpublished = {\url{https://github.com/CharlesPikachu/musicdl}},
}
```


# 📢 WeChat Official Account (微信公众号):

Charles的皮卡丘 (*Charles_pikachu*)  
![img](https://raw.githubusercontent.com/CharlesPikachu/musicdl/master/docs/pikachu.jpg)