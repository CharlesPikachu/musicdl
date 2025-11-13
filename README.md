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
</div>


# What's New

- 2025-11-12: Release musicdl v2.4.0 — Complete code refactor; reintroduced support for music search and downloads on major platforms.


# Introduction

A lightweight music downloader written in pure Python. Like it? ⭐ Star the repository to stay up to date. Thanks!


# Disclaimer

This project is for educational use only and is not intended for commercial purposes. It interacts with publicly available web endpoints and does not host or distribute copyrighted content.
To access paid tracks, please purchase or subscribe to the relevant music service—do not use this project to bypass paywalls or DRM.
If you are a rights holder and believe this repository infringes your rights, please contact me and I will promptly address it.


# Supported Music Client

|  MusicClient (EN)              |  MusicClient (CN)       |   Search           |  Download            |    Code Snippet                                                                                                    |
|  :----:                        |  :----:                 |   :----:           |  :----:              |    :----:                                                                                                          |
|  FiveSingMusicClient           |  5SING音乐              |   ✓                |  ✓                   |    [fivesing.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/fivesing.py)        |
|  KugouMusicClient              |  酷狗音乐               |   ✓                |  ✓                   |    [kugou.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kugou.py)              |
|  KuwoMusicClient               |  酷我音乐               |   ✓                |  ✓                   |    [kuwo.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kuwo.py)                |
|  LizhiMusicClient              |  荔枝FM                 |   ✓                |  ✓                   |    [lizhi.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/lizhi.py)              |
|  MiguMusicClient               |  咪咕音乐               |   ✓                |  ✓                   |    [migu.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/migu.py)                |
|  NeteaseMusicClient            |  网易云音乐             |   ✓                |  ✓                   |    [netease.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/netease.py)          |
|  QianqianMusicClient           |  千千音乐               |   ✓                |  ✓                   |    [qianqian.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qianqian.py)        |
|  QQMusicClient                 |  QQ音乐                 |   ✓                |  ✓                   |    [qq.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py)                    |
|  XimalayaMusicClient           |  喜马拉雅               |   ✓                |  ✓                   |    [ximalaya.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/ximalaya.py)        |
|  JooxMusicClient               |  JOOX (QQ音乐海外版)    |   ✓                |  ✓                   |    [joox.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/joox.py)                |


# Playground

|  Project (EN)                         |   Introduction                                               |  Code                                         |  Project (CN)        |
|  :----:                               |   :----:                                                     |  :----:                                       |  :----:              |
|  musicdlgui                           |   [click](https://mp.weixin.qq.com/s/fN1ORyI6lzQFqxf6Zk1oIg) |  [click](./examples/musicdlgui)               |  音乐下载器GUI界面   |
|  singerlyricsanalysis                 |   [click](https://mp.weixin.qq.com/s/I8Dy7CoM2ThnSpjoUaPtig) |  [click](./examples/singerlyricsanalysis)     |  歌手歌词分析        |
|  searchlyrics                         |   [click](https://mp.weixin.qq.com/s/Vmc1IhuhMJ6C5vBwBe43Pg) |  [click](./examples/searchlyrics)             |  歌词获取歌曲片段    |


# Install

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

# Quick Start

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


# Recommended Projects

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


# Citation

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


# WeChat Official Account (微信公众号):

Charles的皮卡丘 (*Charles_pikachu*)  
![img](https://raw.githubusercontent.com/CharlesPikachu/musicdl/master/docs/pikachu.jpg)