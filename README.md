# Music Downloader
```
A lightweight music downloader written by pure python.
You can star this repository to keep track of the project if it's helpful for you, thank you for your support.
```

# Documents
#### In Chinese
https://musicdl.readthedocs.io/

# Statement
```
This repository is created just for learning python(Commercial prohibition).
All the apis used in this repository are from public network. So, if you want to download the paid songs, 
please open a paid member on corresponding music platform by yourself (respect the music copyright please).
Finally, if there are any infringements, please contact me to delete this repository.
```

# Support List
|  Websites                             |   Support Search?  |  Support Download?   |  in Chinese          |
|  :----:                               |   :----:           |  :----:              |  :----:              |
|  [QQ](https://y.qq.com/)              |   ✓                |  ✓                   |  QQ音乐              |
|  [Lizhi](http://m.lizhi.fm)           |   ✓                |  ✓                   |  荔枝FM              |
|  [Yiting](https://h5.1ting.com/)      |   ✓                |  ✓                   |  一听音乐            |
|  [Kuwo](http://yinyue.kuwo.cn/)       |   ✓                |  ✓                   |  酷我音乐            |
|  [Kugou](http://www.kugou.com/)       |   ✓                |  ✓                   |  酷狗音乐            |
|  [Xiami](https://www.xiami.com/)      |   ✓                |  ✓                   |  虾米音乐            |
|  [Qianqian](http://music.taihe.com/)  |   ✓                |  ✓                   |  千千音乐            |
|  [Migu](http://www.migu.cn/)          |   ✓                |  ✓                   |  咪咕音乐            |
|  [JOOX](https://www.joox.com/limits)  |   ✓                |  ✓                   |  JOOX音乐            |
|  [Fivesing](http://5sing.kugou.com/)  |   ✓                |  ✓                   |  5SING音乐           |
|  [Netease](https://music.163.com/)    |   ✓                |  ✓                   |  网易云音乐          |
|  [baiduFlac](http://music.baidu.com/) |   ✓                |  ✓                   |  百度无损音乐        |

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
```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'baiduFlac', 'kugou', 'kuwo', 'qq', 'qianqian', 
    'netease', 'migu', 'xiami', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
client.run(target_srcs)
```

# Screenshot
![img](./screenshot/screenshot.jpg)

# More
#### WeChat Official Accounts
*Charles_pikachu*  
![img](pikachu.jpg)