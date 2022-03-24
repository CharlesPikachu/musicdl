# 直接使用


#### 项目下载

运行如下命令下载项目:

```sh
git clone https://github.com/CharlesPikachu/musicdl.git
```


#### 配置文件

在musicdl文件夹中有config.json文件, 该文件为配置文件, 文件中各参数含义如下:

- logfilepath: 日志文件保存路径;
- proxies: 设置代理, 支持的代理格式参见[Requests](https://requests.readthedocs.io/en/master/user/advanced/#proxies);
- search_size_per_source: 在各个平台搜索时的歌曲搜索数量;
- savedir: 下载的音乐保存路径;
- page: 部分搜索源支持指定搜索结果的页码。


#### 项目运行

在终端执行如下命令(确保自己的python已经安装了requirements.txt里的所有第三方包):

```sh
# 默认为手动输入版本, 语音版本需要自行修改musicdl.py最后一行, 改成dl_client.runbyspeech()
python musicdl.py 
```

然后根据相应的提示进行操作即可，效果如下：

<div align="center">
  <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot.gif" width="600"/>
</div>
<br />