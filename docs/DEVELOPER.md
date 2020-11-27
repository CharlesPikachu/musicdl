# 安装使用

## PIP安装
在终端运行如下命令即可(请保证python在环境变量中):
```sh
pip install musicdl --upgrade
```

## 源代码安装
#### 在线安装
运行如下命令即可在线安装:
```sh
pip install git+https://github.com/CharlesPikachu/musicdl.git@master
```
#### 离线安装
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

## 快速开始
#### 歌曲搜索
实现音乐搜索功能的示例代码如下:
```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'baiduFlac', 'kugou', 'kuwo', 'qq', 'qianqian', 
	'netease', 'migu', 'xiami', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
search_results = client.search('说好不哭', target_srcs)
```
其中config是一个字典对象, 字典内各参数含义:
```
logfilepath: 日志文件保存路径
proxies: 设置代理, 支持的代理格式参见https://requests.readthedocs.io/en/master/user/advanced/#proxies
search_size_per_source: 在各个平台搜索时的歌曲搜索数量
savedir: 下载的音乐保存路径  
```
target_srcs是一个列表对象, 用于指定音乐搜索的平台:
```
qq: qq音乐
lizhi: 荔枝FM
migu: 咪咕音乐
kuwo: 酷我音乐
joox: JOOX音乐
kugou: 酷狗音乐
xiami: 虾米音乐
yiting: 一听音乐
qianqian: 千千音乐
fivesing: 5SING音乐
netease: 网易云音乐
baiduFlac: 百度无损音乐
```
search_results为歌曲搜索的结果, 是一个字典对象, 格式如下:
```python
{
    搜索平台: 歌曲信息
}
```
#### 歌曲下载
下载各平台音乐搜索结果的示例代码如下:
```python
from musicdl import musicdl

config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 5, 'proxies': {}}
target_srcs = [
    'baiduFlac', 'kugou', 'kuwo', 'qq', 'qianqian', 
    'netease', 'migu', 'xiami', 'joox', 'yiting',
]
client = musicdl.musicdl(config=config)
search_results = client.search('说好不哭', target_srcs)
for key, value in search_results.items():
    client.download(value)
```
当然你也可以自己打印搜索结果, 并自己选择想要下载的歌曲, 例如:
```
print(search_results)
client.download([search_results['migu'][0]])
```
注意, download函数传入的参数必须是一个列表对象.
#### 自定义平台
通过安装musicdl, 你可以自定义平台进行音乐搜索和下载, 示例代码如下:
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
target_srcs是一个列表对象, 用于自定义平台:
```
qq: qq音乐
lizhi: 荔枝FM
migu: 咪咕音乐
kuwo: 酷我音乐
joox: JOOX音乐
kugou: 酷狗音乐
xiami: 虾米音乐
yiting: 一听音乐
qianqian: 千千音乐
fivesing: 5SING音乐
netease: 网易云音乐
baiduFlac: 百度无损音乐
```