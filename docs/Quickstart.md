# Quick Start

This guide explains the most common ways to use musicdl in both the command line and Python.
It is written for practical, day-to-day usage, so the focus is on the workflows most users need first: searching songs, choosing music sources, downloading playlists, saving files to custom folders, and passing cookies or request settings when needed.

#### Typical Usage

(1) Run Musicdl in Interactive Mode

The quickest way to verify that musicdl is installed correctly is to start the interactive terminal UI.

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(
    music_sources=['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'QianqianMusicClient']
)
music_client.startcmdui()
```

Equivalent command-line usage:

```bash
musicdl -m MiguMusicClient,NeteaseMusicClient,QQMusicClient,KuwoMusicClient,QianqianMusicClient
```

By default, musicdl uses five Mainland China sources for search and download:

```python
MiguMusicClient, NeteaseMusicClient, QQMusicClient, KuwoMusicClient, QianqianMusicClient
```

If you want overseas sources, specify them explicitly each time, for example:

```bash
musicdl -m QobuzMusicClient,JamendoMusicClient,YouTubeMusicClient
```

If you already know where a song is likely to be available, it is usually better to search a small number of sources:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient
```

Interactive selection keys:

- `↑` / `↓`: move cursor
- `Space`: toggle selection
- `a`: select all
- `i`: invert selection
- `Enter`: confirm and download
- `Esc` or `q`: cancel selection
- `r`: restart the program
- `q` at the main prompt: exit

The demonstration is as follows:

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/screenshot.png" width="600"/>
  </div>
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/screenshot.gif" width="600"/>
  </div>
</div>
<br />

(2) Search Directly from The Command Line

Use `-k` / `--keyword` when you already know the query text.
This still opens the selection UI before downloading.

```bash
musicdl -k "Jay Chou"
```

Use a specific set of sources if needed:

```bash
musicdl -k "Jay Chou" -m NeteaseMusicClient,QQMusicClient
```

(3) Parse and Download A Playlist

Use `-p` / `--playlist-url` to parse a supported playlist URL and download all recognized tracks.

```bash
musicdl -p "https://music.163.com/#/playlist?id=3039971654" -m NeteaseMusicClient
```

In Python:

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'])
song_infos = music_client.parseplaylist("https://music.163.com/#/playlist?id=7583298906")
music_client.download(song_infos=song_infos)
```

Note:

- `--keyword` and `--playlist-url` cannot be used at the same time.

#### CLI Help

You can always inspect the full command-line interface with:

```bash
musicdl --help
```

<details style="margin-bottom: 24px;">
<summary><em>Show CLI help output</em></summary>
<br>

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
                                  ,QQMusicClient,KuwoMusicClient,QianqianMusic
                                  Client]
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

</details>

#### Common Configuration

(1) Save Files to Custom Folders

Python:

```python
from musicdl import musicdl

init_music_clients_cfg = {
    'MiguMusicClient': {'work_dir': 'migu'},
    'NeteaseMusicClient': {'work_dir': 'netease'},
    'QQMusicClient': {'work_dir': 'qq'},
}

music_client = musicdl.MusicClient(
    music_sources=['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)
music_client.startcmdui()
```

Command line:

```bash
musicdl -m MiguMusicClient,NeteaseMusicClient,QQMusicClient \
  -i '{"MiguMusicClient": {"work_dir": "migu"}, "NeteaseMusicClient": {"work_dir": "netease"}, "QQMusicClient": {"work_dir": "qq"}}'
```

(2) Pass Cookies for VIP or Logged-in Access

If a source works better when logged in, provide cookies from that platform's web session, *e.g.*, `QQMusicClient`:

```python
from musicdl import musicdl

your_vip_cookies_with_str_or_dict_format = ""

init_music_clients_cfg = {
    'QQMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
        'default_download_cookies': your_vip_cookies_with_str_or_dict_format,
    }
}

music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient', 'QQMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)
music_client.startcmdui()
```

Command line:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient \
  -i '{"QQMusicClient": {"default_search_cookies": "YOUR_COOKIES", "default_download_cookies": "YOUR_COOKIES"}}'
```

(3) Increase The Number of Search Results from One Source

```python
from musicdl import musicdl

init_music_clients_cfg = {
    'QQMusicClient': {'search_size_per_source': 20}
}

music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient', 'QQMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)
music_client.startcmdui()
```

Equivalent command:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient \
  -i '{"QQMusicClient": {"search_size_per_source": 20}}'
```

(4) Use Free Proxies Automatically

If you want to use the [pyfreeproxy](https://github.com/CharlesPikachu/freeproxy) library to fetch free proxies automatically:

```python
from musicdl import musicdl

init_music_clients_cfg = {
    'NeteaseMusicClient': {
        'search_size_per_source': 1000,
        'auto_set_proxies': True,
        'freeproxy_settings': {
            'proxy_sources': ["ProxyScrapeProxiedSession", "ProxylistProxiedSession"],
            'init_proxied_session_cfg': {
                'max_pages': 2,
                'filter_rule': {
                    'country_code': ["CN"],
                    'anonymity': ["elite"],
                    'protocol': ["http", "https"],
                },
            },
            'disable_print': True,
            'max_tries': 20,
        },
    }
}

music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)
music_client.startcmdui()
```

Command line:

```bash
musicdl -m NeteaseMusicClient \
  -i '{"NeteaseMusicClient": {"search_size_per_source": 1000, "auto_set_proxies": true, "freeproxy_settings": {"proxy_sources": ["ProxyScrapeProxiedSession", "ProxylistProxiedSession"], "init_proxied_session_cfg": {"max_pages": 2, "filter_rule": {"country_code": ["CN"], "anonymity": ["elite"], "protocol": ["http", "https"]}}, "disable_print": true, "max_tries": 20}}}'
```

(5) Override Request Settings Per Source

Use `requests_overrides` when you need to pass extra request options such as `proxies`, `timeout`, or `verify`.

```python
from musicdl import musicdl

requests_overrides = {
    'NeteaseMusicClient': {
        'timeout': (10, 30),
        'verify': False,
        'headers': {'User-Agent': 'Mozilla/5.0'},
    }
}

music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient'],
    requests_overrides=requests_overrides,
)

search_results = music_client.search(keyword='tail ring')
music_client.download(song_infos=search_results)
```

Command line:

```bash
musicdl -k "tail ring" -m NeteaseMusicClient \
  -r '{"NeteaseMusicClient": {"timeout": [10, 30], "verify": false, "headers": {"User-Agent": "Mozilla/5.0"}}}'
```

(6) Pass Source-Specific Search Rules

Use `search_rules` when a source supports extra search options.
Behavior is implementation-specific.

```python
from musicdl import musicdl

search_rules = {
    'FiveSingMusicClient': {
        'sort': 1,
        'filter': 0,
        'type': 0,
    }
}

music_client = musicdl.MusicClient(
    music_sources=['FiveSingMusicClient'],
    search_rules=search_rules,
)
music_client.startcmdui()
```

Command line:

```bash
musicdl -m FiveSingMusicClient \
  -s '{"FiveSingMusicClient": {"sort": 1, "filter": 0, "type": 0}}'
```

(7) Adjust Thread Counts Per Source

```python
from musicdl import musicdl

clients_threadings = {
    'NeteaseMusicClient': 8,
    'QQMusicClient': 4,
}

music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient', 'QQMusicClient'],
    clients_threadings=clients_threadings,
)
music_client.startcmdui()
```

Command line:

```bash
musicdl -m NeteaseMusicClient,QQMusicClient \
  -c '{"NeteaseMusicClient": 8, "QQMusicClient": 4}'
```

#### Separate Search and Download

You can call `.search()` and `.download()` separately to inspect intermediate results or build custom workflows.

```python
from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'])

search_results = music_client.search(keyword='尾戒')
print(search_results)

song_infos = []
for song_infos_per_source in search_results.values():
    song_infos.extend(song_infos_per_source)

music_client.download(song_infos=song_infos)
```

#### Secondary Development

You can also bypass the unified `MusicClient` and use a specific client directly.
For example:

```python
from musicdl.modules.sources import NeteaseMusicClient

netease_music_client = NeteaseMusicClient()

search_results = netease_music_client.search(keyword='那些年')
print(search_results)

netease_music_client.download(song_infos=search_results)
```

To inspect all registered client classes:

```python
from musicdl.modules import MusicClientBuilder

print(MusicClientBuilder.REGISTERED_MODULES)
```

#### Download Playlist Items

From musicdl v2.9.0 onward, support for playlist parsing and downloading is being added gradually, now including,

```python
AppleMusicClient,      DeezerMusicClient,       FiveSingMusicClient,    JamendoMusicClient,      JooxMusicClient,
KuwoMusicClient,       KugouMusicClient,        MiguMusicClient,        NeteaseMusicClient,      QQMusicClient,
QianqianMusicClient,   QobuzMusicClient,        SoundCloudMusicClient,  StreetVoiceMusicClient,  SodaMusicClient,
SpotifyMusicClient,    TIDALMusicClient
```

You can download a supported playlist directly from the terminal:

```sh
# Parse and Download Apple Music Playlist
# >>> not use wrapper
musicdl -p "https://music.apple.com/cn/playlist/%E5%8D%81%E5%A4%A7%E4%B8%93%E8%BE%91/pl.u-mJy81mECzBL49zM" -m AppleMusicClient -i "{'AppleMusicClient': {'default_parse_cookies': your_vip_cookies_with_str_or_dict_format}}"
# >>> use wrapper
musicdl -p "https://music.apple.com/cn/playlist/%E5%8D%81%E5%A4%A7%E4%B8%93%E8%BE%91/pl.u-mJy81mECzBL49zM" -m AppleMusicClient -i "{'AppleMusicClient': {'use_wrapper': True, 'wrapper_account_url': 'http://127.0.0.1:30020/', 'wrapper_decrypt_ip': '127.0.0.1:10020'}}"
# Parse and Download Deezer Music Playlist
musicdl -p "https://www.deezer.com/us/playlist/4697225044" -m DeezerMusicClient -i "{'DeezerMusicClient': {'default_parse_cookies': your_vip_cookies_with_str_or_dict_format}}"
# Parse and Download 5SING Music Playlist
musicdl -p "https://5sing.kugou.com/yeluoluo/dj/631b3fa72418b11003089b8d.html" -m FiveSingMusicClient
# Parse and Download Jamendo Music Playlist
musicdl -p "https://www.jamendo.com/playlist/500544876/best-of-february-2020" -m JamendoMusicClient
# Parse and Download Joox Music Playlist
musicdl -p "https://www.joox.com/hk/playlist/MqgK_LYD3Sb3I9Iziq+8NA==" -m JooxMusicClient
# Parse and Download Kuwo Music Playlist
musicdl -p "https://www.kuwo.cn/playlist_detail/2358858706" -m KuwoMusicClient
# Parse and Download Kugou Music Playlist
musicdl -p "https://www.kugou.com/yy/special/single/3280341.html" -m KugouMusicClient
# Parse and Download Migu Music Playlist
musicdl -p "https://music.migu.cn/v5/#/playlist?playlistId=228114498&playlistType=ordinary" -m MiguMusicClient
# Parse and Download NetEase Music Playlist
musicdl -p "https://music.163.com/#/playlist?id=3039971654" -m NeteaseMusicClient
# Parse and Download QQ Music Playlist
musicdl -p "https://y.qq.com/n/ryqq_v2/playlist/8740590963" -m QQMusicClient
# Parse and Download QianQian Music Playlist
musicdl -p "https://music.91q.com/songlist/295893" -m QianqianMusicClient
# Parse and Download Qobuz Music Playlist
musicdl -p "https://open.qobuz.com/playlist/22318381" -m QobuzMusicClient
# Parse and Download StreetVoice Music Playlist
musicdl -p "https://www.streetvoice.cn/morgan22/playlists/436444/" -m StreetVoiceMusicClient
# Parse and Download SoundCloud Music Playlist
musicdl -p "https://soundcloud.com/pandadub/sets/the-lost-ship" -m SoundCloudMusicClient
# Parse and Download Soda Music Playlist
musicdl -p "https://qishui.douyin.com/s/iHFSgNKw/" -m SodaMusicClient
# Parse and Download Spotify Music Playlist
musicdl -p "https://open.spotify.com/playlist/37i9dQZF1E8NWHOpySOxQd" -m SpotifyMusicClient
# Parse and Download TIDAL Music Playlist
musicdl -p "https://tidal.com/playlist/a94e7dce-da66-413d-81a5-990328afa3c9" -m TIDALMusicClient -i "{'TIDALMusicClient': {'default_parse_cookies': your_vip_cookies_with_str_or_dict_format}}"
```

Alternatively, in Python:

```python
from musicdl import musicdl

init_music_clients_cfg = {
    'NeteaseMusicClient': {'default_parse_cookies': YOUR_VIP_COOKIES}
}

music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)

song_infos = music_client.parseplaylist("https://music.163.com/#/playlist?id=7583298906")
music_client.download(song_infos=song_infos)
```

#### WhisperLRC

On some music platforms, it is not possible to obtain lyric files directly, for example `XimalayaMusicClient`, `LizhiMusicClient`, `LRTSMusicClient`, `QingtingMusicClient` and `MituMusicClient`.
To handle this, musicdl provides a faster-whisper-based interface that can generate lyrics automatically.

Generate lyrics from a local file:

```python
from musicdl.modules import WhisperLRC

your_local_music_file_path = 'xxx.flac'
print(WhisperLRC(model_size_or_path='base').fromfilepath(your_local_music_file_path))
```

Available `model_size_or_path` values:

```python
tiny, tiny.en, base, base.en, small, small.en, distil-small.en, medium, medium.en, distil-medium.en, large-v1, large-v2, large-v3, large, distil-large-v2, distil-large-v3, large-v3-turbo, turbo
```

In general, larger models generate better lyrics but take longer to run.

Use the environment variable `ENABLE_WHISPERLRC=True` to toggle on-the-fly lyric generation for all music downloads.
For example:

```bash
export ENABLE_WHISPERLRC=True
```

This is usually *not recommended* for normal downloading workflows, because it can make one run take a very long time unless you keep `search_size_per_source=1` and use a very small Whisper model such as `tiny`.

You can also generate lyrics from a direct audio URL:

```python
from musicdl.modules import WhisperLRC

music_link = ''
print(WhisperLRC(model_size_or_path='base').fromurl(music_link))
```

#### Scenarios Where Quark Netdisk Login Cookies Are Required

Some websites share high-quality or lossless music through [Quark Netdisk](https://pan.quark.cn/) links, for example:

```python
MituMusicClient, GequbaoMusicClient, YinyuedaoMusicClient, BuguyyMusicClient
```

If you want to download high-quality or lossless files from these sources, provide the cookies from your logged-in Quark Netdisk web session.

```python
from musicdl import musicdl

init_music_clients_cfg = {
    'YinyuedaoMusicClient': {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}},
    'GequbaoMusicClient': {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}},
    'MituMusicClient': {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}},
    'BuguyyMusicClient': {'quark_parser_config': {'cookies': your_cookies_with_str_or_dict_format}},
}

music_client = musicdl.MusicClient(
    music_sources=['MituMusicClient', 'YinyuedaoMusicClient', 'GequbaoMusicClient', 'BuguyyMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)
music_client.startcmdui()
```

Please note:

- musicdl does not provide any speed-limit bypass for Quark Netdisk.
- If the cookies belong to a non-VIP Quark account, the download speed may be only a few hundred KB/s.
- Quark may first save the file into your own account before downloading it.
- If your Quark storage is insufficient, the download may fail.

#### Common Issues and Solutions (FAQ)

<details style="margin-bottom: 24px;">
<summary><em>How to Parse New Kugou Web Playlist URLs?</em></summary>
<br>

If you have a new playlist link, for example,
`https://www.kugou.com/songlist/gcid_3zs9qlpmzdz003/`,
you need to manually extract the `special ID` via your browser.

1. Open the playlist link in your browser and make sure you are logged into Kugou Music.
2. Open Developer Tools (`F12`) and inspect the returned HTML page in the Network panel.
3. Search for the keyword `"specialid"`.
4. The number immediately after it is the special ID.
5. Construct a new URL in the form:
   `https://www.kugou.com/yy/special/single/{YOUR_SPECIAL_ID}.html`
6. Use that new URL as the playlist input for musicdl.

</details>

<details style="margin-bottom: 24px;">
<summary><em>Why is The Downloaded Apple Music Playlist Incomplete?</em></summary>
<br>

musicdl currently only supports parsing Apple Music playlists with a maximum of 300 tracks.

If your playlist exceeds this limit, split it into several smaller playlists and download them separately.

</details>

