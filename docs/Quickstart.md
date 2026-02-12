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
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/screenshot.png" width="600"/>
  </div>
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/screenshot.gif" width="600"/>
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
  -p, --playlist-url, --playlist_url TEXT
                                  Given a playlist URL, e.g., "https://music.1
                                  63.com/#/playlist?id=7583298906", musicdl
                                  automatically parses the playlist and
                                  downloads all tracks in it.
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
Take `NeteaseMusicClient` as an example:

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

#### Download Playlist Items

From musicdl v2.9.0 onward, support for downloading user playlists from each platform will be added gradually. The platforms currently supported are as follows:

- [NeteaseMusicClient | 网易云音乐](https://music.163.com/)
- [QQMusicClient | QQ音乐](https://y.qq.com/)
- [KuwoMusicClient | 酷我音乐](http://www.kuwo.cn/)

Specifically, you only need to run the following command in the terminal, musicdl will automatically detect the playlist in the link and download it in batch:

```sh
musicdl -p "https://music.163.com/#/playlist?id=7583298906" -m NeteaseMusicClient
musicdl -p "https://y.qq.com/n/ryqq_v2/playlist/8740590963" -m QQMusicClient
musicdl -p "https://www.kuwo.cn/playlist_detail/3387576633" -m KuwoMusicClient
```

Alternatively, use the following code to invoke it,

```python
from musicdl import musicdl

init_music_clients_cfg = {'NeteaseMusicClient': {'default_parse_cookies': YOUR_VIP_COOKIES}}
music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
song_infos = music_client.parseplaylist("https://music.163.com/#/playlist?id=7583298906")
music_client.download(song_infos=song_infos)
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

#### Kugou Music Download

Musicdl currently supports searching and downloading from KuGou Music, and it is used in the same way as other music clients. 
The only thing to note is that if you need to configure member cookies to download purchased albums/singles or member-exclusive audio quality, the cookies must be in the following format:

```python
{
  'KUGOU_API_GUID': 'xxxx', 
  'KUGOU_API_MID': 'xxxx', 
  'KUGOU_API_MAC': 'xxxx', 
  'KUGOU_API_DEV': 'xxxx', 
  'token': 'xxxx', 
  'userid': 'xxxx', 
  'dfid': 'xxxx'
}
```

You can either use the [build_cookies_for_kugou.py](https://github.com/CharlesPikachu/musicdl/blob/master/scripts/build_cookies_for_kugou.py) script provided in the repo to obtain them directly, 
or capture the above arguments yourself via network packet capture on the KuGou app or the web client, and then configure musicdl as follows:

```python
from musicdl import musicdl

cookies = {'KUGOU_API_GUID': 'xxxx', 'KUGOU_API_MID': 'xxxx', 'KUGOU_API_MAC': 'xxxx', 'KUGOU_API_DEV': 'xxxx', 'token': 'xxxx', 'userid': 'xxxx', 'dfid': 'xxxx'}
init_music_clients_cfg = {'KugouMusicClient': {'default_search_cookies': cookies, 'search_size_per_source': 5}}
music_client = musicdl.MusicClient(music_sources=['KugouMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Keep in mind that cookie names captured from network traffic may not match the cookie names required by musicdl.
You need to map them correctly to construct valid cookies, otherwise, member-only music downloads won’t work.

#### XimalayaFM and LizhiFM Audio/Radio Download

Musicdl currently also supports searching for and downloading individual audio tracks, as well as entire albums, from long-form audio platforms (*e.g.*, Ximalaya and Lizhi FM) that host podcasts and audiobooks. 
By default, both modes start simultaneously, and the top few search results for each mode are shown based on the input keyword.

A simple usage example is shown below,

```python
from musicdl import musicdl

init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2}}
music_client = musicdl.MusicClient(music_sources=['XimalayaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

The result of running the code above looks like this,

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/ximalayascreenshot.gif" width="600"/>
  </div>
</div>
<br />

You can also choose the search type yourself by setting `allowed_search_types`, for example:

```python
from musicdl import musicdl

# only search by track
init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}
# only search by album
init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}
# instance music_client
music_client = musicdl.MusicClient(music_sources=['XimalayaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
# start
music_client.startcmdui()
```

Please note that the code above only supports downloading free albums and audio. 
If you need to download paid audio, please configure cookies in `init_music_clients_cfg`, just as you would with other music clients.

#### QingtingFM Audio/Radio Download

The usage for searching and downloading on the QingTing FM website is similar to Ximalaya and Lizhi FM. 
The only thing to watch out for is how cookies are set, it differs from typical music client objects.

Specifically, without logging in (*i.e.*, when you don’t need to download paid audio), you can invoke it by running `musicdl -m QingtingMusicClient` in the command line, or by calling it via the following code:

```python
from musicdl import musicdl

# only search by track
init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}
# only search by album
init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}
# search by album and track
init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album', 'track']}}
# instance music_client
music_client = musicdl.MusicClient(music_sources=['QingtingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
# start
music_client.startcmdui()
```

When you need to download paid audio, you’ll have to capture the network traffic yourself on the [QingTing FM web client](https://www.qtfm.cn/).
Look for an AJAX request with the keyword `auth`, its response data will look like:

```python
{
  "errorno": 0,
  "errormsg": "",
  "data": {
    "qingting_id": "xxxx",
    "access_token": "xxx",
    "refresh_token": "xxx",
    "expires_in": 7200
  }
}
```

Or, use the script [build_cookies_for_qingtingfm.py](https://github.com/CharlesPikachu/musicdl/tree/master/scripts/build_cookies_for_qingtingfm) in this repository to retrieve it.

Once you’ve obtained this data, you can configure cookies for `QingtingMusicClient` as follows:

```python
from musicdl import musicdl

cookies = {"qingting_id": "xxxx", "access_token": "xxx", "refresh_token": "xxx"}
init_music_clients_cfg = {'QingtingMusicClient': {'default_search_cookies': cookies, 'default_download_cookies': cookies, 'search_size_per_source': 3}}
music_client = musicdl.MusicClient(music_sources=['QingtingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Of course, it’s worth noting that another prerequisite for downloading paid audio is that your account must already have permission to access (listen to) that audio.

#### TIDAL High-Quality Music Download

Prior to using `TIDALMusicClient`, verify that the following command-line tools are correctly installed and available in your environment,

- [PyAV](https://github.com/PyAV-Org/PyAV)
- [FFmpeg](https://www.ffmpeg.org/)
- [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE)

If you plan to use musicdl to download high-quality lossless audio from TIDAL, you must have an active TIDAL subscription. 
Otherwise, musicdl may fall back to third-party sources, and stable access to the highest-quality lossless files cannot be guaranteed.

After you have a TIDAL membership account, you need to manually capture the cookies of your account from the TIDAL website using network packet capturing. 
The format is as follows:

```python
{
  "access_token": "xxx", 
  "refresh_token": "xxx", 
  "expires": "2026-02-10T07:32:18.102233",
  "user_id": xxx, 
  "country_code": "SG", 
  "client_id": "7m7Ap0JC9j1cOM3n", 
  "client_secret": "vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY="
}
```

Of course, musicdl also provides a script [build_cookies_for_tidal.py](https://github.com/CharlesPikachu/musicdl/blob/master/scripts/build_cookies_for_tidal.py) to automatically obtain your TIDAL membership cookies. 
You can simply run the script and follow the prompts to retrieve the cookies mentioned above.

Once you have successfully obtained your membership cookies, you can use musicdl to download lossless music from TIDAL using the following method,

```python
from musicdl import musicdl

cookies = "YOUR_VIP_COOKIES"
init_music_clients_cfg = {'TIDALMusicClient': {'default_search_cookies': cookies, 'search_size_per_source': 5}}
music_client = musicdl.MusicClient(music_sources=['TIDALMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

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

#### SoundCloud Music Download

Musicdl lets you search for and download your favorite songs from SoundCloud. Specifically, you only need to run the following command:

```
musicdl -m SoundCloudMusicClient
```

Or you can invoke it with the following code:

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['SoundCloudMusicClient'])
music_client.startcmdui()
```

The only thing to note is that `SoundCloudMusicClient` handles login cookies for downloading subscriber-only tracks slightly differently from the other music clients. 
You need to capture packets (*i.e.*, sniff the network requests) from [SoundCloud’s official website](https://soundcloud.com/) yourself to obtain the *Authorization* field in the request headers, then fill it in as follows:

```python
from musicdl import musicdl

cookies = {'oauth_token': 'OAuth x-xxxxxx-xxxxxxxxx-xxxxxxx'}
init_music_clients_cfg = {'SoundCloudMusicClient': {'default_search_cookies': cookies, 'default_download_cookies': cookies, 'search_size_per_source': 5}}
music_client = musicdl.MusicClient(music_sources=['SoundCloudMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

#### Apple Music Download

Before using `AppleMusicClient`, please ensure that the following command-line tools are installed and available in your environment,

- [FFmpeg](https://www.ffmpeg.org/)
- [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE)
- [Bento4](https://www.bento4.com/downloads/)
- [amdecrypt](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools)

Apple Music is like TIDAL, only users with a paid Apple Music subscription can download Apple Music tracks, otherwise, you can only download an approximately 30-90 second preview clip.
Specifically, for paid Apple Music users, musicdl supports downloading music files in the following formats,

- `aac-legacy`
- `aac-he-legacy`
- `aac`
- `aac-he`
- `aac-binaural`
- `aac-downmix`
- `aac-he-binaural`
- `aac-he-downmix`
- `atmos`
- `ac3`
- `alac`

Specifically, if you only need to download tracks in the `aac-legacy` and `aac-he-legacy` quality tiers, you just need to make sure that [FFmpeg](https://www.ffmpeg.org/) and [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE) are already installed and available in your environment variables.
Then, set the `media-user-token` argument you obtained by capturing network traffic from the Apple Music website as follows:

```python
from musicdl import musicdl
from musicdl.modules.sources.apple import SongCodec

cookies = {'media-user-token': xxx}
init_music_clients_cfg = {'AppleMusicClient': {'default_search_cookies': cookies, 'search_size_per_source': 10, 'language': 'en-US', 'codec': SongCodec.AAC_LEGACY}}
music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

However, if you need to download higher-quality audio (*e.g.*, `alac`), the setup is relatively more complex. 
First, follow the [wrapper](https://github.com/WorldObservationLog/wrapper) guide and start the wrapper server (❗ **note that Windows users need to download and install WSL first, followed by installing Ubuntu on WSL, and finally start the wrapper server within Ubuntu, otherwise, decryption will most likely fail** ❗).
Then, in addition to [FFmpeg](https://www.ffmpeg.org/) and [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE), you also need to install [Bento4](https://www.bento4.com/downloads/) and [amdecrypt](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools).
Finally, configure your musicdl as follows:

```python
from musicdl import musicdl
from musicdl.modules.sources.apple import SongCodec

init_music_clients_cfg = {'AppleMusicClient': {
    'search_size_per_source': 10, 
    'language': 'en-US', 
    'codec': SongCodec.ALAC, 
    'use_wrapper': True, 
    'wrapper_account_url': 'http://127.0.0.1:30020/',
    'wrapper_decrypt_ip': '127.0.0.1:10020',
}}
music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

Note that the `wrapper_account_url` and `wrapper_decrypt_ip` settings must match the corresponding arguments configured in your [wrapper server](https://github.com/WorldObservationLog/wrapper).

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
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/gdstudioscreenshot.png" width="600"/>
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
music_client = musicdl.MusicClient(music_sources=['GDStudioMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
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
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/tunehubscreenshot.png" width="600"/>
  </div>
</div>
<br />

#### JBSou Music Download

`JBSouMusicClient`’s functionality is similar to `TuneHubMusicClient`’s. 
Both are third-party APIs that consolidate music search and download functions from multiple platforms into a single interface.
The key difference is that `JBSouMusicClient` focuses on searching and downloading 320 kbps MP3 audio files. 
The list of music platforms it currently supports is as follows:

| Source (EN)             | Source (CN)                        | Official Websites                     | `allowed_music_sources`      |
| -----------------       | -------------------                | -----------------------------------   | -------------------          |
| Tencent (QQ Music)      | QQ音乐                             | https://y.qq.com                      | `qq`                         |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 | `netease`                    |
| Kuwo                    | 酷我音乐                           | https://www.kuwo.cn                   | `kuwo`                       |
| Kugou                   | 酷狗音乐                           | https://www.kugou.com/                | `kugou`                      |

More specifically, its invocation is as follows,

```python
from musicdl import musicdl

init_music_clients_cfg = {'JBSouMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['qq', 'netease', 'kuwo', 'kugou']}}
music_client = musicdl.MusicClient(music_sources=['JBSouMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
music_client.startcmdui()
```

The screenshot of the running result is as follows:

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/jbsouscreenshot.png" width="600"/>
  </div>
</div>
<br />
