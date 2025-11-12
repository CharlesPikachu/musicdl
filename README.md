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

  <p><a href="https://musicdl.readthedocs.io/">Documents</a></p>
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

|  MusicClient (EN)              |  MusicClient (CN)  |   Search           |  Download            |    Code Snippet                                                                                                    |
|  :----:                        |  :----:            |   :----:           |  :----:              |    :----:                                                                                                          |
|  FiveSingMusicClient           |  5SING音乐         |   ✓                |  ✓                   |    [fivesing.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/fivesing.py)        |
|  KugouMusicClient              |  酷狗音乐          |   ✓                |  ✓                   |    [kugou.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kugou.py)              |
|  KuwoMusicClient               |  酷我音乐          |   ✓                |  ✓                   |    [kuwo.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kuwo.py)                |
|  LizhiMusicClient              |  荔枝FM            |   ✓                |  ✓                   |    [lizhi.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/lizhi.py)              |
|  MiguMusicClient               |  咪咕音乐          |   ✓                |  ✓                   |    [migu.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/migu.py)                |
|  NeteaseMusicClient            |  网易云音乐        |   ✓                |  ✓                   |    [netease.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/netease.py)          |
|  QianqianMusicClient           |  千千音乐          |   ✓                |  ✓                   |    [qianqian.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qianqian.py)        |
|  QQMusicClient                 |  QQ音乐            |   ✓                |  ✓                   |    [qq.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py)                    |
|  XimalayaMusicClient           |  喜马拉雅          |   ✓                |  ✓                   |    [ximalaya.py](https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/ximalaya.py)        |


# Playground

|  Project_EN                           |   Introduction                                               |  Code                                         |  Project_CN          |
|  :----:                               |   :----:                                                     |  :----:                                       |  :----:              |
|  musicdlgui                           |   [click](https://mp.weixin.qq.com/s/fN1ORyI6lzQFqxf6Zk1oIg) |  [click](./examples/musicdlgui)               |  音乐下载器GUI界面   |
|  singerlyricsanalysis                 |   [click](https://mp.weixin.qq.com/s/I8Dy7CoM2ThnSpjoUaPtig) |  [click](./examples/singerlyricsanalysis)     |  歌手歌词分析        |
|  searchlyrics                         |   [click](https://mp.weixin.qq.com/s/Vmc1IhuhMJ6C5vBwBe43Pg) |  [click](./examples/searchlyrics)             |  歌词获取歌曲片段    |


# Install
#### Pip install
```
run "pip install musicdl"
```
#### Source code install
```sh
(1) Offline
Step1: git clone https://github.com/CharlesPikachu/musicdl.git
Step2: cd musicdl -> run "python setup.py install"
(2) Online
run "pip install git+https://github.com/CharlesPikachu/musicdl.git@master"
```


# Quick Start
#### Run by leveraging the API
```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'kugou', 'kuwo', 'qqmusic', 'qianqian', 'fivesing',
    'netease', 'migu', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
client.run(target_srcs)
```
#### Run by leveraging compiled file
```
Usage: musicdl [OPTIONS]

Options:
  --version               Show the version and exit.
  -k, --keyword TEXT      搜索的歌曲关键字, 若不指定, 则进入musicdl终端版
  -l, --logfilepath TEXT  日志文件保存的路径
  -p, --proxies TEXT      设置的代理
  -s, --savedir TEXT      下载的音乐保存路径
  -c, --count TEXT        在各个平台搜索时的歌曲搜索数量
  -t, --targets TEXT      指定音乐搜索的平台, 例如"migu,joox"
  --help                  Show this message and exit.
```


# Screenshot
![img](./docs/screenshot.gif)


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
![img](https://raw.githubusercontent.com/CharlesPikachu/musicdl/main/docs/pikachu.jpg)