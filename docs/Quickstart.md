# Quick Start

#### Typical Examples

Here, we provide some common musicdl use cases to help you quickly get started with the tool.

If you want the quickest way to run musicdl to verify that your environment meets its basic requirements and that musicdl has been installed successfully, you can write and run the following code,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'QianqianMusicClient'])
music_client.startcmdui()
```

The above code runs musicdl using `MiguMusicClient`, `NeteaseMusicClient`, `QQMusicClient`, `KuwoMusicClient` and `QianqianMusicClient` as both the search sources and download sources.

Of course, you can also run musicdl by entering the following equivalent command directly in the command line,

```bash
musicdl -m NeteaseMusicClient,MiguMusicClient,QQMusicClient,KuwoMusicClient,QianqianMusicClient
```

Please note that musicdl uses five Mainland China music sources by default for searching. 
If you need to use overseas music sources, you must manually specify the music platform each time you run the program. 
For example:

```bash
musicdl -m GDStudioMusicClient,JamendoMusicClient
```

In addition, searching and downloading from many music sources simultaneously may be relatively slow. 
Each run may take about 10–30 seconds. 
If you are confident that your song can be found on a specific platform or a few platforms, for example, `NeteaseMusicClient`, `QQMusicClient` or `KuwoMusicClient`,
it is recommended to directly specify those platforms:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient,KuwoMusicClient
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

You can also use `musicdl --help` to see the detailed usage of the musicdl command-line tool, as follows:

```bash
Usage: musicdl [OPTIONS]

Options:
  --version                       Show the version and exit.
  -k, --keyword TEXT              The keywords for the music search. If left
                                  empty, an interactive terminal will open
                                  automatically.
  -m, --music-sources, --music_sources TEXT
                                  The music search and download sources.
                                  [default: MiguMusicClient,NeteaseMusicClient
                                  ,QQMusicClient,KuwoMusicClient,QianqianMusicClient]
  -i, --init-music-clients-cfg, --init_music_clients_cfg TEXT
                                  Config such as `work_dir` for each music
                                  client as a JSON string.
  -r, --requests-overrides, --requests_overrides TEXT
                                  Requests.get / Requests.post kwargs such as
                                  `headers` and `proxies` for each music
                                  client as a JSON string.
  -c, --clients-threadings, --clients_threadings TEXT
                                  Number of threads used for each music client
                                  as a JSON string.
  -s, --search-rules, --search_rules TEXT
                                  Search rules for each music client as a JSON
                                  string.
  --help                          Show this message and exit.
```

If you want to change the download path for the music files, you can write the following code:

```python
from musicdl import musicdl

init_music_clients_cfg = dict()
init_music_clients_cfg['MiguMusicClient'] = {'work_dir': 'migu'}
init_music_clients_cfg['NeteaseMusicClient'] = {'work_dir': 'netease'}
init_music_clients_cfg['QQMusicClient'] = {'work_dir': 'qq'}
music_client = musicdl.MusicClient(music_sources=['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient'])
music_client.startcmdui()
```

Alternatively, you can equivalently run the following command directly in the command line:

```bash
musicdl -m NeteaseMusicClient,MiguMusicClient,QQMusicClient -i "{'MiguMusicClient': {'work_dir': 'migu'}, {'NeteaseMusicClient': {'work_dir': 'netease'}, {'QQMusicClient': {'work_dir': 'qq'}}"
```

If you are a VIP user on a particular music platform, you can pass the cookies from your logged-in web session on that platform to musicdl to improve the quality of song search and downloads. 
Specifically, for example, if you have a membership on `QQMusicClient`, your code can be written as follows:

```python
from musicdl import musicdl

your_vip_cookies_with_str_or_dict_format = ""
init_music_clients_cfg = dict()
init_music_clients_cfg['QQMusicClient'] = {'default_search_cookies': your_vip_cookies_with_str_or_dict_format, 'default_download_cookies': your_vip_cookies_with_str_or_dict_format}
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient', 'QQMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Of course, you can also achieve the same effect by running the following command directly in the command line:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient -i "{'QQMusicClient': {'default_search_cookies': your_vip_cookies_with_str_or_dict_format, 'default_download_cookies': your_vip_cookies_with_str_or_dict_format}}"
```

If you want to search for more songs on a specific music platform (*e.g.*, `QQMusicClient`), you can do the following:

```python
from musicdl import musicdl

init_music_clients_cfg = dict()
init_music_clients_cfg['QQMusicClient'] = {'search_size_per_source': 20}
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient', 'QQMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Or enter the following in the command line:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient -i "{'QQMusicClient': {'search_size_per_source': 20}}"
```

In this way, you can see up to 20 search results from `QQMusicClient`.

If you want to use the [pyfreeproxy](https://github.com/CharlesPikachu/freeproxy) library to automatically leverage free online proxies for music search and download, you can do it as follows:

```python
from musicdl import musicdl

init_music_clients_cfg = dict()
init_music_clients_cfg['NeteaseMusicClient'] = {
    'search_size_per_source': 1000, 'auto_set_proxies': True, 
    'freeproxy_settings': dict(
        proxy_sources=["ProxyScrapeProxiedSession", "ProxylistProxiedSession"], 
        init_proxied_session_cfg={"max_pages": 2, "filter_rule": {"country_code": ["CN"], "anonymity": ["elite"], "protocol": ["http", "https"]}}, 
        disable_print=True, 
        max_tries=20
    )
}
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

The command-line usage is similar:

```bash
musicdl -m NeteaseMusicClient -i "{'NeteaseMusicClient': {'search_size_per_source': 1000, 'auto_set_proxies': True, 'freeproxy_settings': {'proxy_sources':['ProxyScrapeProxiedSession','ProxylistProxiedSession'],'init_proxied_session_cfg':{'max_pages':2,'filter_rule':{'country_code':['CN'],'anonymity':['elite'],'protocol':['http','https']}},'disable_print':True,'max_tries':20}}}"
```

#### Separating Search and Download Results

You can also call the `.search` and `.download` interfaces of musicdl separately to inspect its intermediate results or perform secondary development,

```python
from musicdl import musicdl

# instance
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'])
# search
search_results = music_client.search(keyword='尾戒')
print(search_results)
song_infos = []
for song_infos_per_source in list(search_results.values()):
    song_infos.extend(song_infos_per_source)
# download
music_client.download(song_infos=song_infos)
```

You can also choose not to use the unified `MusicClient` interface and instead directly import the definition class for a specific music platform for secondary development. 
For example, to import the definition class for `NeteaseMusicClient`:

```python
from musicdl.modules.sources import NeteaseMusicClient

netease_music_client = NeteaseMusicClient()
# search
search_results = netease_music_client.search(keyword='那些年')
print(search_results)
# download
netease_music_client.download(song_infos=search_results)
```

All supported classes can be obtained by printing `MusicClientBuilder.REGISTERED_MODULES`, *e.g*,

```python
from musicdl.modules import MusicClientBuilder

print(MusicClientBuilder.REGISTERED_MODULES)
```

#### WhisperLRC

On some music platforms, it’s not possible to obtain the lyric files corresponding to the audio, *e.g*, `XimalayaMusicClient` and `MituMusicClient`. 
To handle this, we provide a faster-whisper interface that can automatically generate lyrics for tracks whose lyrics are unavailable for download.

For audio files that have already been downloaded, you can use the following invocation to automatically generate lyrics for the local file,

```python
from musicdl.modules import WhisperLRC

your_local_music_file_path = 'xxx.flac'
WhisperLRC(model_size_or_path='base').fromfilepath(your_local_music_file_path)
```

The available `model_size_or_path`, ordered from smallest to largest, are:

```python
tiny, tiny.en, base, base.en, small, small.en, distil-small.en, medium, medium.en, distil-medium.en, large-v1, large-v2, large-v3, large, distil-large-v2, distil-large-v3, large-v3-turbo, turbo
```

In general, the larger the model, the better the generated lyrics (transcription/translation) will be, but this also means it will take longer to run.

If you want to automatically generate lyric files during the download process, 
you can set the environment variable `ENABLE_WHISPERLRC=True` (for example, by running `export ENABLE_WHISPERLRC=True`). 
However, this is generally not recommended, as it may cause a single run of the program to take a very long time,
unless you set `search_size_per_source` to `1` and `model_size_or_path` to `tiny`.

Of course, you can also directly call `.fromurl` to generate a lyrics file for a song given by a direct URL:

```python
from musicdl.modules import WhisperLRC

music_file_link = ''
WhisperLRC(model_size_or_path='base').fromurl(music_link)
```

#### Scenarios Where Quark Netdisk Login Cookies Are Required

Some websites share high-quality or lossless music files via [Quark Netdisk](https://pan.quark.cn/) links, for example, `MituMusicClient`, `GequbaoMusicClient`, `YinyuedaoMusicClient`, and `BuguyyMusicClient`.

If you want to download high-quality or lossless audio files from these music platforms, you need to provide the cookies from your logged-in Quark Netdisk web session when calling musicdl. 
For example, you can do the following: 

```python
from musicdl import musicdl

init_music_clients_cfg = dict()
init_music_clients_cfg['YinyuedaoMusicClient'] = {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}}
init_music_clients_cfg['GequbaoMusicClient'] = {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}}
init_music_clients_cfg['MituMusicClient'] = {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}}
init_music_clients_cfg['BuguyyMusicClient'] = {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}}

music_client = musicdl.MusicClient(music_sources=['MituMusicClient', 'YinyuedaoMusicClient', 'GequbaoMusicClient', 'BuguyyMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Please note that musicdl does not provide any speed-limit bypass for Quark Netdisk.
If the cookies you supply belong to a non-VIP Quark account, the download speed may be limited to only a few hundred KB/s.

Also note that Quark Drive will first save the music file to your own Quark account (usually in the "From: Shares (来自: 分享)" folder) and then start the download.
Therefore, if your Quark storage is insufficient, the download may fail.

#### TIDAL High-Quality Music Download

If you want to download lossless-quality music from [TIDAL](https://tidal.com/), you need to make sure that [PyAV](https://github.com/PyAV-Org/PyAV) is available or that [FFmpeg](https://www.ffmpeg.org/) is in your environment variables, 
and then use musicdl as follows:

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['TIDALMusicClient'])
music_client.startcmdui()
```

Running the above code will automatically open your default browser and prompt you to log in to TIDAL. Once you have successfully logged in, musicdl will automatically capture the tokens from your session to support subsequent music search and download.

If you are running on a remote server where the browser cannot be opened automatically, you can instead copy the URL printed in the terminal and open it in your local browser to complete the login process.

Note that if the account you log in with is not a paid TIDAL subscription, you will still be unable to download the full lossless audio files.

#### YouTube Music Download

If you want to use musicdl to search for and download music from `YouTubeMusicClient`, you must have [Node.js](https://nodejs.org/en) installed, *e.g.*, on Linux, you can install Node.js using the following script:

```bash
#!/usr/bin/env bash
set -e

# Install nvm (Node Version Manager)
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash

# Load nvm for this script
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Install and use latest LTS Node.js
nvm install --lts
nvm use --lts

# Print versions
node -v
npm -v
```

On macOS, you can install Node.js using the following script:

```bash
#!/usr/bin/env bash
set -e

# Install nvm (Node Version Manager)
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash

# Load nvm for this script
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Install and use latest LTS Node.js
nvm install --lts
nvm use --lts

# Print versions
node -v
npm -v
```

On Windows (PowerShell), you can install Node.js using the following script:

```bash
# Install Node.js LTS via winget
winget install --id OpenJS.NodeJS.LTS -e --source winget

# Print hint for version check
Write-Output ""
Write-Output "Please reopen PowerShell and run:"
Write-Output "  node -v"
Write-Output "  npm -v"
```

A simple example of searching for and downloading music from `YouTubeMusicClient` is as follows,

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['YouTubeMusicClient'])
music_client.startcmdui()
```

#### Apple Music Download

`AppleMusicClient` works similarly to `TIDALMusicClient`: 
if you are not an Apple Music subscriber or you have not manually set in musicdl the cookies (*i.e.*, the `media-user-token`) from your logged-in Apple Music session in the browser, 
you will only be able to download a partial segment of each track (usually 30–90 seconds). 

If you need to download the full audio and lyrics for each song, you can configure musicdl as follows:

```python
from musicdl import musicdl

cookies = {'media-user-token': xxx}
init_music_clients_cfg = {'AppleMusicClient': {'default_search_cookies': cookies, 'default_download_cookies': cookies, 'search_size_per_source': 10}}
music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

It is important to note that to download Apple Music audio files (including decryption) using musicdl, you must properly install [GPAC](https://gpac.io/downloads/gpac-nightly-builds/),
[Bento4](https://www.bento4.com/downloads/) and [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE).

#### GD Studio Music Download

We’ve added `GDStudioMusicClient` to musicdl as a practical solution for users who are on a tight budget or who find it difficult to configure extra command-line tools/arguments for musicdl. 
With only the basic installation of musicdl, you can search for and download high-quality music files from the following music platforms:

| Source (EN)             | Source (CN)                        | Official Websites                     | `allowed_music_sources`      |
| -----------------       | -------------------                | -----------------------------------   | -------------------          |
| Spotify                 | Spotify                            | https://www.spotify.com               | `spotify`                    |
| Tencent (QQ Music)      | QQ音乐                             | https://y.qq.com                      | `tencent`                    |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 | `netease`                    |
| Kuwo                    | 酷我音乐                           | https://www.kuwo.cn                   | `kuwo`                       |
| TIDAL                   | TIDAL                              | https://tidal.com                     | `tidal`                      |
| Qobuz                   | Qobuz                              | https://www.qobuz.com                 | `qobuz`                      |
| JOOX                    | JOOX                               | https://www.joox.com                  | `joox`                       |
| Bilibili                | 哔哩哔哩                           | https://www.bilibili.com              | `bilibili`                   |
| Apple Music             | 苹果音乐                           | https://www.apple.com/apple-music/    | `apple`                      |
| YouTube Music           | 油管音乐                           | https://music.youtube.com             | `ytmusic`                    |

Specifically, you just need to write and run a few lines of code like this 
(song retrieval from YouTube and Tencent is unstable, so musicdl disables these two sources by default. 
You can manually enable them by setting `allowed_music_sources`.):

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['GDStudioMusicClient'])
music_client.startcmdui()
```

Or, equivalently, run the following command in the command line:

```bash
musicdl -m GDStudioMusicClient
```

By default, the above code will search for and download music from eight music platforms, excluding YouTube and Tencent Music (as using `GDStudioMusicClient` for search and download on both platforms seems to be unstable).
The screenshot of the running result is as follows:

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/gdstudioscreenshot.png" width="600"/>
  </div>
</div>
<br />

However, please note that this way of running is not very stable (*e.g.*, some sources may fail to find any valid songs) and is likely to exceed the limit on the number of requests per minute allowed for a single IP by `GDStudioMusicClient`. 
If you still wish to perform a full-platform search, we recommend modifying the default arguments as follows:

```python
from musicdl import musicdl

init_music_clients_cfg = {'GDStudioMusicClient': {'search_size_per_source': 1}}
music_client = musicdl.MusicClient(music_sources=['GDStudioMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

The equivalent command in the command line is:

```bash
musicdl -m GDStudioMusicClient -i "{'GDStudioMusicClient': {'search_size_per_source': 1}}"
```

Or, an even better option is to manually specify a few platforms where you believe your desired music files are likely to be found, for example:

```python
from musicdl import musicdl

# allowed_music_sources can be set to any subset (i.e., any combination) of ['spotify', 'tencent', 'netease', 'kuwo', 'tidal', 'qobuz', 'joox', 'bilibili', 'apple', 'ytmusic']
init_music_clients_cfg = {'GDStudioMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['spotify', 'qobuz', 'tidal', 'apple']}}
music_client = musicdl.MusicClient(music_sources=['GDStudioMusicClient'], init_music_clients_cfg=init_music_clients_cfg, clients_threadings=clients_threadings)
music_client.startcmdui()
```

The way to run it from the command line is similar:

```bash
musicdl -m GDStudioMusicClient -i "{'GDStudioMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['spotify', 'qobuz', 'tidal', 'apple']}}"
```

#### TuneHub Music Download

`TuneHubMusicClient` is actually quite similar to `GDStudioMusicClient`, as it allows music search and download from multiple music platforms. 
However, it primarily supports music platforms in Mainland China and offers fewer music sources compared to `GDStudioMusicClient`. 
Specifically, the list of platforms it currently supports is as follows:

| Source (EN)             | Source (CN)                        | Official Websites                     | `allowed_music_sources`      |
| -----------------       | -------------------                | -----------------------------------   | -------------------          |
| Tencent (QQ Music)      | QQ音乐                             | https://y.qq.com                      | `qq`                         |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 | `netease`                    |
| Kuwo                    | 酷我音乐                           | https://www.kuwo.cn                   | `kuwo`                       |

Specifically, you can call it using the following code:

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['TuneHubMusicClient'])
music_client.startcmdui()
```

Alternatively, you can directly run the following command in the terminal:

```python
musicdl -m TuneHubMusicClient
```

The screenshot of the running result is as follows:

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/tunehubscreenshot.png" width="600"/>
  </div>
</div>
<br />