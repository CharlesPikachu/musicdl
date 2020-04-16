# Music-Downloader
```
Music Downloader  
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
Finally, if there is any infringement, please contact me to delete this repository.
```

# Support List
|  Websites                             |   Support Search?  |  Support Download?   |  in Chinese          |
|  :----:                               |   :----:           |  :----:              |  :----:              |
|  [QQ](https://y.qq.com/)              |   ✓                |  ✓                   |  QQ音乐              |
|  [Kuwo](http://yinyue.kuwo.cn/)       |   ✓                |  ✓                   |  酷我音乐            |
|  [Kugou](http://www.kugou.com/)       |   ✓                |  ✓                   |  酷狗音乐            |
|  [Xiami](https://www.xiami.com/)      |   ✓                |  ✓                   |  虾米音乐            |
|  [Qianqian](http://music.taihe.com/)  |   ✓                |  ✓                   |  千千音乐            |
|  [Migu](http://www.migu.cn/)          |   ✓                |  ✓                   |  咪咕音乐            |
|  [Netease](https://music.163.com/)    |   ✓                |  ✓                   |  网易云音乐          |
|  [baiduFlac](http://music.baidu.com/) |   ✓                |  ✓                   |  百度无损音乐        |
|  [JOOX](https://www.joox.com/limits)  |   ✓                |  ✓                   |  JOOX音乐            |

# Install
#### Pip install
```
run "pip install musicdl"
```
#### Source code install
```sh
(1) Offline
Step1: git clone https://github.com/CharlesPikachu/Music-Downloader.git
Step2: cd Music-Downloader -> run "python setup.py install"
(2) Online
run "pip install git+https://github.com/CharlesPikachu/Music-Downloader.git@master"
```

# Quick Start
```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = ['baiduFlac', 'kugou', 'kuwo', 'qq', 'qianqian', 'netease', 'migu', 'xiami', 'joox']
client = musicdl.musicdl(config=config)
client.run(target_srcs)
```

# Screenshot
![img](https://github.com/CharlesPikachu/Music-Downloader/blob/master/record/screenshot.jpg)

# More
#### WeChat Official Accounts
*Charles_pikachu*  
![img](https://github.com/CharlesPikachu/Music-Downloader/blob/master/pikachu.jpg)