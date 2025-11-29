# Quick Start

#### Uniform MusicClient

Here, we provide several practical examples of the `musicdl.MusicClient` class to help users get started quickly.

After a successful installation, you can run the snippet below,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient'])
music_client.startcmdui()
```

Or just run `musicdl -m NeteaseMusicClient` (maybe `musicdl --help` to show usage information) from the terminal.

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
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot.png" width="600"/>
  </div>
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot.gif" width="600"/>
  </div>
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

If you want to use the [pyfreeproxy](https://github.com/CharlesPikachu/freeproxy) library to automatically leverage free online proxies for music search and download, you can do it as follows.

```python
from musicdl import musicdl

init_music_clients_cfg = dict()
init_music_clients_cfg['NeteaseMusicClient'] = {'search_size_per_source': 10, 'auto_set_proxies': True, 'proxy_sources': ['QiyunipProxiedSession']}
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Separate the search and download steps to obtain intermediate results, you can do it as follows.

```python
from musicdl import musicdl

# instance
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'])
# search
search_results = music_client.search(keyword='尾戒')
song_infos = []
for song_infos_per_source in list(search_results.values()):
    song_infos.extend(song_infos_per_source)
# download
music_client.download(song_infos=song_infos)
```

If you want to download lossless-quality music from [TIDAL](https://tidal.com/), 
you need to make sure that [PyAV](https://github.com/PyAV-Org/PyAV) is available or that [FFmpeg](https://www.ffmpeg.org/) is in your environment variables, 
and then use musicdl as follows,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['TIDALMusicClient'])
music_client.startcmdui()
```

For searching and downloading from YouTube Music, an example usage is shown below,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['YouTubeMusicClient'])
music_client.startcmdui()
```

#### Dedicated MusicClient

Example code for searching and downloading music files on different platforms such as NeteaseMusicClient and QQMusicClient is as follows,

```python
from musicdl.modules.sources.qq import QQMusicClient
from musicdl.modules.sources.tidal import TIDALMusicClient
from musicdl.modules.sources.netease import NeteaseMusicClient

# QQMusicClient
qq_music_client = QQMusicClient()
search_results = qq_music_client.search(keyword='那些年')
print(search_results)
qq_music_client.download(song_infos=search_results)
# TIDALMusicClient
tidal_music_client = TIDALMusicClient()
search_results = tidal_music_client.search(keyword='Something Just Like This')
print(search_results)
tidal_music_client.download(song_infos=search_results)
# NeteaseMusicClient
netease_music_client = NeteaseMusicClient()
search_results = netease_music_client.search(keyword='那些年')
print(search_results)
netease_music_client.download(song_infos=search_results)
```

#### WhisperLRC

musicdl also provides a faster-whisper interface, which can automatically generate lyrics for audio files whose lyrics cannot be downloaded.

```python
from musicdl.modules.utils import WhisperLRC

WhisperLRC(model_size_or_path='base').fromfilepath('your music file')
WhisperLRC(model_size_or_path='base').fromurl('your music file link')
```