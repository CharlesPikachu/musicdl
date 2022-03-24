# 安装使用

#### 安装方式

**1.PIP安装**

在终端运行如下命令即可(请保证python在环境变量中):

```sh
pip install musicdl --upgrade
```

**2.源代码在线安装**

运行如下命令即可实现源代码在线安装:

```sh
pip install git+https://github.com/CharlesPikachu/musicdl.git@master
```

**3.源代码离线安装**

利用如下命令下载musicdl源代码到本地:

```sh
git clone https://github.com/CharlesPikachu/musicdl.git
```

接着, 切到musicdl目录下:

```sh
cd musicdl
```

最后运行如下命令进行安装:

```sh
python setup.py install
```


#### 快速开始

**1.终端直接调用编译好的文件**

运行方式如下:

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

例如在终端直接输入：

```sh
musicdl -k 那些年
```

这里是一个简单效果演示:

<div align="center">
  <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot.gif" width="600"/>
</div>
<br />

**2.歌曲搜索**

实现音乐搜索功能的示例代码如下:

```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'kugou', 'kuwo', 'qqmusic', 'qianqian', 'fivesing',
    'netease', 'migu', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
search_results = client.search('说好不哭', target_srcs)
```

其中config是一个字典对象, 字典内各参数含义:

- logfilepath: 日志文件保存路径;
- proxies: 设置代理, 支持的代理格式参见[Requests](https://requests.readthedocs.io/en/master/user/advanced/#proxies);
- search_size_per_source: 在各个平台搜索时的歌曲搜索数量;
- savedir: 下载的音乐保存路径;
- page: 部分搜索源支持指定搜索结果的页码。

target_srcs是一个列表对象, 用于指定音乐搜索的平台:

- lizhi: 荔枝FM
- migu: 咪咕音乐
- kuwo: 酷我音乐
- joox: JOOX音乐
- kugou: 酷狗音乐
- yiting: 一听音乐
- qqmusic: QQ音乐
- qianqian: 千千音乐
- fivesing: 5SING音乐
- netease: 网易云音乐

search_results为歌曲搜索的结果, 是一个字典对象, 格式如下:

```python
{
    搜索平台: 歌曲信息
}
```

**3.歌曲下载**

下载各平台音乐搜索结果的示例代码如下:

```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'kugou', 'kuwo', 'qqmusic', 'qianqian', 'fivesing',
    'netease', 'migu', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
search_results = client.search('说好不哭', target_srcs)
for key, value in search_results.items():
    client.download(value)
```

当然你也可以自己打印搜索结果, 并自己选择想要下载的歌曲, 例如:

```python
print(search_results)
client.download([search_results['migu'][0]])
```

注意, download函数传入的参数必须是一个列表对象。

**4.自定义平台**

通过安装musicdl, 你可以自定义平台进行音乐搜索和下载, 示例代码如下:

```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'kugou', 'kuwo', 'qqmusic', 'qianqian', 'fivesing',
    'netease', 'migu', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
# 手动输入版
client.run(target_srcs)
# 语音版
client.runbyspeech(target_srcs)
```

target_srcs是一个列表对象, 用于自定义平台:

- lizhi: 荔枝FM
- migu: 咪咕音乐
- kuwo: 酷我音乐
- joox: JOOX音乐
- kugou: 酷狗音乐
- yiting: 一听音乐
- qqmusic: QQ音乐
- qianqian: 千千音乐
- fivesing: 5SING音乐
- netease: 网易云音乐