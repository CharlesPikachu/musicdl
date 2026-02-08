# Musicdl APIs


## `musicdl.musicdl.MusicClient`

A unified interface encapsulated for all supported music platforms. Arguments supported when initializing this class include:

- **music_sources** (`list[str]`, optional):  A list of music client names to be enabled. 
  Each name must be a key registered in `MusicClientBuilder.REGISTERED_MODULES`.  
  If left empty, the following default sources are used:  
  `['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'QianqianMusicClient']`.

- **init_music_clients_cfg** (`dict[str, dict]`, optional): Per-client initialization configuration.  
  The outer dict is keyed by music source name (*e.g.*, `"NeteaseMusicClient"`), and each value is a dict that overrides the default config:
  ```python
  {
      "search_size_per_source": 5,
      "auto_set_proxies": False,
      "random_update_ua": False,
      "enable_search_curl_cffi": False,
      "enable_download_curl_cffi": False,
      "enable_parse_curl_cffi": False,
      "max_retries": 3,
      "maintain_session": False,
      "logger_handle": LoggerHandle(),
      "disable_print": True,
      "work_dir": "musicdl_outputs",
      "freeproxy_settings": None,
      "default_search_cookies": {},
      "default_download_cookies": {},
      "default_parse_cookies": {},
      "type": music_source,
      "search_size_per_page": 10,
      "strict_limit_search_size_per_page": True,
      "quark_parser_config": {},
  }
  ```
  Any keys you provide will overwrite the defaults for that specific source only.

- **clients_threadings** (`dict[str, int]`, optional): Number of threads to use for each music client when searching/downloading.
  Keys are music source names; values are integers.
  If a source is missing from this dict, it defaults to `5` threads.

- **requests_overrides** (`dict[str, dict]`, optional): Per-client overrides for HTTP requests.
  Keys are music source names; values are dicts that will be forwarded as `request_overrides` to the underlying clients’ `search` and `download` methods.
  Typical usage is to pass `requests.get`-like kwargs such as custom `headers`, `proxies`, or `timeout`.
  If a source is missing from this dict, it defaults to an empty dict `{}`.

- **search_rules** (`dict[str, dict]`, optional): Per-client search rules.
  Keys are music source names; values are dicts passed as `rule` to the clients’ `search` method to control source-specific search behavior (*e.g.*, quality filters, sort rules, *etc.*, depending on the implementation of each client).
  If a source is missing from this dict, it defaults to an empty dict `{}`.

Once initialized, `MusicClient` exposes high-level `search` and `download` methods that automatically dispatch requests to all configured music sources.

#### `MusicClient.startcmdui()`

Start an interactive command-line interface for searching and downloading music.

This method:

- Prints basic usage information (version, save paths, *etc.*.).
- Prompts the user to input keywords for music search.
- Calls `MusicClient.search()` to retrieve search results from all configured music sources.
- Displays a formatted table of candidate songs with IDs.
- Opens a cursor-based selection UI where the user can choose one or multiple songs:
  - Use "↑/↓" to move the cursor
  - Press "Space" to toggle selection
  - Press "a" to select all, "i" to invert selection
  - Press "Enter" to confirm and start downloading
  - Press "Esc" or "q" to cancel selection
- Collects the corresponding song info entries and calls `MusicClient.download()` to download them.

Special commands (at the main prompt):

- Enter `r` to **reinitialize** the program (*i.e.*, return to the main menu).
- Enter `q` to **exit** the program.

This method runs in a loop and blocks until the user quits.

#### `MusicClient.search(keyword: str)`

Search for songs from all configured music platforms using a given `keyword`.
The results from all sources are collected into a dictionary.
Each per-source result is a list of song info dictionaries, which typically include: `singers`, `song_name`. `file_size`, `duration`, `album`, `source`, `ext` and other client-specific metadata.

- **Arguments**:

  - **keyword** (`str`): Search keyword, *e.g.*, song name, artist name, *etc.*.

- **Returns**:
  
  - `dict[str, list[SongInfo]]`: A mapping from music source name (*e.g.*, `"NeteaseMusicClient"`) to a list of song info dictionaries returned by that source.

#### `MusicClient.download(song_infos: list[SongInfo])`

Download one or more songs given a list of song info dictionaries.
Thread settings and request overrides are automatically taken from `MusicClient.clients_threadings` and `MusicClient.requests_overrides`.

- **Arguments**:

  - **song_infos** (`list[SongInfo]`): A list of song info dictionaries, usually taken from the output of `MusicClient.search()`.
    Each dictionary must contain a source key so that the method can route it to the appropriate client.
  
- **Returns**:
  
  - `None`.


## `musicdl.modules.sources.base.BaseMusicClient`

`BaseMusicClient` is the abstract base class for all concrete music clients, including,

- `musicdl.modules.sources.AppleMusicClient`
- `musicdl.modules.sources.BilibiliMusicClient`
- `musicdl.modules.sources.BuguyyMusicClient`
- `musicdl.modules.sources.FangpiMusicClient`
- `musicdl.modules.sources.FiveSingMusicClient`
- `musicdl.modules.sources.FiveSongMusicClient`
- `musicdl.modules.sources.FLMP3MusicClient`
- `musicdl.modules.sources.GequbaoMusicClient`
- `musicdl.modules.sources.GequhaiMusicClient`
- `musicdl.modules.sources.HTQYYMusicClient`
- `musicdl.modules.sources.JamendoMusicClient`
- `musicdl.modules.sources.JooxMusicClient`
- `musicdl.modules.sources.JCPOOMusicClient`
- `musicdl.modules.sources.KugouMusicClient`
- `musicdl.modules.sources.KuwoMusicClient`
- `musicdl.modules.sources.KKWSMusicClient`
- `musicdl.modules.sources.LivePOOMusicClient`
- `musicdl.modules.sources.MiguMusicClient`
- `musicdl.modules.sources.MituMusicClient`
- `musicdl.modules.sources.NeteaseMusicClient`
- `musicdl.modules.sources.QianqianMusicClient`
- `musicdl.modules.sources.QQMusicClient`
- `musicdl.modules.sources.SodaMusicClient`
- `musicdl.modules.sources.StreetVoiceMusicClient`
- `musicdl.modules.sources.SoundCloudMusicClient`
- `musicdl.modules.sources.TIDALMusicClient`
- `musicdl.modules.sources.TwoT58MusicClient`
- `musicdl.modules.sources.YinyuedaoMusicClient`
- `musicdl.modules.sources.YouTubeMusicClient`
- `musicdl.modules.sources.ZhuolinMusicClient`
- `musicdl.modules.common.GDStudioMusicClient`
- `musicdl.modules.common.JBSouMusicClient`
- `musicdl.modules.common.MP3JuiceMusicClient`
- `musicdl.modules.common.MyFreeMP3MusicClient`
- `musicdl.modules.common.TuneHubMusicClient`
- `musicdl.modules.audiobooks.LizhiMusicClient`
- `musicdl.modules.audiobooks.QingtingMusicClient`
- `musicdl.modules.audiobooks.XimalayaMusicClient`

End users usually **do not** instantiate `BaseMusicClient` directly, but instead use one of the specific clients above.
The methods documented here describe the common behavior of all these clients.
Arguments supported when initializing this class include:

- **search_size_per_source** (`int`, default `5`):  
  Maximum number of search results to fetch per source.
  
- **auto_set_proxies** (`bool`, default `False`):  
  If `True`, randomly assign a free proxy fetched by `freeproxy.ProxiedSessionClient` (details refer to [FreeProxy](https://github.com/CharlesPikachu/freeproxy/tree/master)) for each request (not work for `AppleMusicClient` and `YouTubeMusicClient`).

- **random_update_ua** (`bool`, default `False`):  
  If `True`, randomly refresh the `User-Agent` header on each request (not work for `AppleMusicClient`, `KugouMusicClient` and `YouTubeMusicClient`).

- **enable_search_curl_cffi** (`bool`, default `False`):  
  If `True`, `curl_cffi.requests.Session` is used for each search request (not work for `AppleMusicClient` and `YouTubeMusicClient`).

- **enable_download_curl_cffi** (`bool`, default `False`):  
  If `True`, `curl_cffi.requests.Session` is used for each download request (not work for `AppleMusicClient` and `YouTubeMusicClient`).

- **enable_parse_curl_cffi** (`bool`, default `False`):  
  If `True`, `curl_cffi.requests.Session` is used for each parseplaylist request (not work for `AppleMusicClient` and `YouTubeMusicClient`).

- **max_retries** (`int`, default `3`):  
  Maximum number of retry attempts for each HTTP request in `BaseMusicClient.get()` / `BaseMusicClient.post()`.

- **maintain_session** (`bool`, default `False`):  
  If `False`, a new `requests.Session` is created before each request;  
  if `True`, the same session is reused across requests (not work for `AppleMusicClient`, `KugouMusicClient` and `YouTubeMusicClient`).

- **logger_handle** (`LoggerHandle`, optional):  
  Logger instance used for logging.  
  If `None`, a new `LoggerHandle` is created.

- **disable_print** (`bool`, default `False`):  
  If `True`, suppress printing in `logger_handle` calls where supported.

- **work_dir** (`str`, default `'musicdl_outputs'`):  
  Root directory for saving search and download results.  
  Each search will create its own subdirectory under this path.

- **freeproxy_settings** (`dict` or `None`, default `None`):  
  Arguments passed when instantiating `freeproxy.ProxiedSessionClient`.  
  If `None`, defaults to `dict(disable_print=True, proxy_sources=['ProxiflyProxiedSession'], max_tries=20, init_proxied_session_cfg={})` when `auto_set_proxies=True`.

- **default_search_cookies** (`dict` or `None`, default `{}`):  
  Default cookies used for `BaseMusicClient.search` requests.

- **default_download_cookies** (`dict` or `None`, default `{}`):  
  Default cookies used for `BaseMusicClient.download` requests.

- **default_parse_cookies** (`dict` or `None`, default `{}`):  
  Default cookies used for `BaseMusicClient.parseplaylist` requests.

- **search_size_per_page** (`int`, default `10`):  
  When searching for songs, if `search_size_per_source` is greater than `search_size_per_page`, 
  the downloader will send paginated requests to the corresponding sites to retrieve the search results, 
  with each page containing `search_size_per_page` songs.

- **strict_limit_search_size_per_page** (`bool`, default `True`):  
  Some sites do not allow `search_size_per_page` to control how many songs are returned per request, 
  which may cause the final number of search results from that site to exceed `search_size_per_source`. 
  Setting this parameter to `True` enforces that the total number of results is less than or equal to `search_size_per_source`.

- **quark_parser_config** (`dict` or `None`, default `{}`):  
  Some sites, such as `MituMusicClient`, `GequbaoMusicClient`, `YinyuedaoMusicClient`, and `BuguyyMusicClient`, 
  store their lossless audio files on [Quark Netdisk](https://pan.quark.cn/). 
  For these websites, if you want to download lossless-quality music files using musicdl, 
  you need to configure `quark_parser_config` with the `cookies` from your Quark Netdisk web session after logging in, *e.g.*,
  `quark_parser_config={'cookies': xxxxxx}`.

#### `BaseMusicClient.search(keyword: str, num_threadings=5, request_overrides=None, rule=None)`

Search for songs using the specific music platform (*e.g.*, Netease, Kugou, QQ, *etc.*.).

- **Arguments**:

  - **keyword** (`str`):  Search keyword (*e.g.*, song name, artist, album).
  
  - **num_threadings** (`int`, default `5`): Number of threads used to perform the search across all constructed URLs.

  - **request_overrides** (`dict` or `None`, default `{}`): Extra keyword arguments passed to the underlying HTTP requests (*e.g.*, `headers`, `proxies`, `timeout`). If `None`, treated as an empty dict.

  - **rule** (`dict` or `None`, default `{}`): Search rules used by `BaseMusicClient._constructsearchurls`, *e.g.*, quality filters, sort rules, or other client-specific options. If `None`, treated as an empty dict.

- **Returns**:

  - `list[SongInfo]`:  A list of `song_info` dictionaries. Each dictionary usually contains (but is not limited to):
    `identifier` (used internally for deduplication), `song_name`, `singers`, `album`, `duration`, `file_size`, `download_url`, `ext`, `source`, `work_dir` (added by `BaseMusicClient.search()`).

Concrete clients like `NeteaseMusicClient`, `QQMusicClient`, *etc.*, implement `BaseMusicClient._constructsearchurls()` and `BaseMusicClient._search()` to define how the search is actually performed for each platform.

#### `BaseMusicClient.download(song_infos: list, num_threadings=5, request_overrides=None)`

Download one or more songs from the specific music platform. 

- **Arguments**:
  
  - **song_infos** (`list[SongInfo]`): A list of song information dictionaries (typically the result of `BaseMusicClient.search()`).
  
  - **num_threadings** (`int`, default `5`): Number of threads used for concurrent downloading.
  
  - **request_overrides** (`dict` or `None`, default `{}`): Extra keyword arguments passed to the underlying `BaseMusicClient.get()` method (*e.g.*, `headers`, `proxies`, `timeout`). If `None`, treated as an empty dict.
  
- **Returns**:

  - `list[SongInfo]`: A list of successfully downloaded `song_info` dictionaries.

