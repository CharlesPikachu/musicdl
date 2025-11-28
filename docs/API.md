# Musicdl APIs


## `musicdl.musicdl.MusicClient`

A unified interface encapsulated for all supported music platforms. Arguments supported when initializing this class include:

- **music_sources** (`list[str]`, optional):  A list of music client names to be enabled. 
  Each name must be a key registered in `MusicClientBuilder.REGISTERED_MODULES`.  
  If left empty, the following default sources are used:  
  `["MiguMusicClient", "NeteaseMusicClient", "KuwoMusicClient", "KugouMusicClient", "QQMusicClient", "QianqianMusicClient"]`.

- **init_music_clients_cfg** (`dict[str, dict]`, optional): Per-client initialization configuration.  
  The outer dict is keyed by music source name (e.g. `"NeteaseMusicClient"`), and each value is a dict that overrides the default config:
  ```python
  {
      "search_size_per_source": 5,
      "auto_set_proxies": False,
      "random_update_ua": False,
      "max_retries": 5,
      "maintain_session": False,
      "logger_handle": LoggerHandle(),
      "disable_print": True,
      "work_dir": "musicdl_outputs",
      "proxy_sources": None,
      "default_search_cookies": {},
      "default_download_cookies": {},
      "type": music_source,
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
  Keys are music source names; values are dicts passed as `rule` to the clients’ `search` method to control source-specific search behavior (e.g., quality filters, sort rules, etc., depending on the implementation of each client).
  If a source is missing from this dict, it defaults to an empty dict `{}`.

Once initialized, `MusicClient` exposes high-level `search` and `download` methods that automatically dispatch requests to all configured music sources.

#### `MusicClient.startcmdui()`

Start an interactive command-line interface for searching and downloading music.

This method:

1. Prints basic usage information (version, save paths, etc.).
2. Prompts the user to input keywords for music search.
3. Calls `MusicClient.search()` to retrieve search results from all configured music sources.
4. Displays a formatted table of candidate songs with IDs.
5. Prompts the user to select one or multiple IDs (e.g. `"1,2,5"`).
6. Collects the corresponding song info entries and calls `MusicClient.download()` to download them.

Special commands:

- Enter `r` to **reinitialize** the program (*i.e.*, return to the main menu).
- Enter `q` to **exit** the program.

This method blocks and runs in a loop until the user quits.

#### `MusicClient.search(keyword: str)`

Search for songs from all configured music platforms using a given `keyword`.
The results from all sources are collected into a dictionary.
Each per-source result is a list of song info dictionaries, which typically include: `singers`, `song_name`. `file_size`, `duration`, `album`, `source`, `ext` and other client-specific metadata.

- **Arguments**:

  - **keyword** (`str`): Search keyword, *e.g.*, song name, artist name, *etc*.

- **Returns**:
  
  - `dict[str, list[dict]]:` A mapping from music source name (*e.g.*, `"NeteaseMusicClient"`) to a list of song info dictionaries returned by that source.

#### `MusicClient.download(song_infos: list[dict])`

Download one or more songs given a list of song info dictionaries.
Thread settings and request overrides are automatically taken from `MusicClient.clients_threadings` and `MusicClient.requests_overrides`.

- **Arguments**:

  - **song_infos** (`list[dict]`): A list of song info dictionaries, usually taken from the output of `MusicClient.search()`.
    Each dictionary must contain a source key so that the method can route it to the appropriate client.
  
- **Returns**:
  
  - `None`.


## `musicdl.modules.sources.base.BaseMusicClient`

`BaseMusicClient` is the abstract base class for all concrete music clients, including,

- `musicdl.modules.sources.fivesing.FiveSingMusicClient`
- `musicdl.modules.sources.kugou.KugouMusicClient`
- `musicdl.modules.sources.kuwo.KuwoMusicClient`
- `musicdl.modules.sources.lizhi.LizhiMusicClient`
- `musicdl.modules.sources.migu.MiguMusicClient`
- `musicdl.modules.sources.netease.NeteaseMusicClient`
- `musicdl.modules.sources.qianqian.QianqianMusicClient`
- `musicdl.modules.sources.qq.QQMusicClient`
- `musicdl.modules.sources.ximalaya.XimalayaMusicClient`
- `musicdl.modules.sources.joox.JooxMusicClient`
- `musicdl.modules.sources.tidal.TIDALMusicClient`
- `musicdl.modules.sources.youtube.YouTubeMusicClient`
- `musicdl.modules.sources.apple.AppleMusicClient`

End users usually **do not** instantiate `BaseMusicClient` directly, but instead use one of the specific clients above.
The methods documented here describe the common behavior of all these clients.
Arguments supported when initializing this class include:

- **search_size_per_source** (`int`, default `5`):  
  Maximum number of search results (or pages) to fetch per source.
  
- **auto_set_proxies** (`bool`, default `False`):  
  If `True`, automatically obtain proxies from `proxy_sources` using `freeproxy.ProxiedSessionClient` (details refer to [FreeProxy](https://github.com/CharlesPikachu/freeproxy/tree/master)) for each request.

- **random_update_ua** (`bool`, default `False`):  
  If `True`, randomly refresh the `User-Agent` header on each request.

- **max_retries** (`int`, default `5`):  
  Maximum number of retry attempts for each HTTP request in `BaseMusicClient.get()` / `BaseMusicClient.post()`.

- **maintain_session** (`bool`, default `False`):  
  If `False`, a new `requests.Session` is created before each request;  
  if `True`, the same session is reused across requests.

- **logger_handle** (`LoggerHandle`, optional):  
  Logger instance used for logging.  
  If `None`, a new `LoggerHandle` is created.

- **disable_print** (`bool`, default `False`):  
  If `True`, suppress printing in logger calls where supported.

- **work_dir** (`str`, default `'musicdl_outputs'`):  
  Root directory for saving search and download results.  
  Each search will create its own subdirectory under this path.

- **proxy_sources** (`list[str]` or `None`, default `None`):  
  A list of proxy source names for `freeproxy.ProxiedSessionClient`.  
  If `None`, defaults to `['QiyunipProxiedSession']` when `auto_set_proxies=True`.

- **default_search_cookies** (`dict` or `None`, default `{}`):  
  Default cookies used for `BaseMusicClient.search` requests.

- **default_download_cookies** (`dict` or `None`, default `{}`):  
  Default cookies used for `BaseMusicClient.download` requests.

#### `BaseMusicClient.search(keyword: str, num_threadings=5, request_overrides=None, rule=None)`

Search for songs using the specific music platform (e.g., Netease, Kugou, QQ, etc.).

- **Arguments**:

  - **keyword** (`str`):  Search keyword (e.g., song name, artist, album).
  
  - **num_threadings** (`int`, default `5`): Number of threads used to perform the search across all constructed URLs.

  - **request_overrides** (`dict` or `None`, default `{}`): Extra keyword arguments passed to the underlying HTTP requests (e.g., `headers`, `proxies`, `timeout`). If `None`, treated as an empty dict.

  - **rule** (`dict` or `None`, default `{}`): Search rules used by `BaseMusicClient._constructsearchurls`, e.g., quality filters, sort rules, or other client-specific options. If `None`, treated as an empty dict.

- **Returns**:

  - `list[dict]`:  A list of `song_info` dictionaries. Each dictionary usually contains (but is not limited to):
    `identifier` (used internally for deduplication), `song_name`, `singers`, `album`, `duration`, `file_size`, `download_url`, `ext`, `source`, `work_dir` (added by `BaseMusicClient.search()`).

Concrete clients like `NeteaseMusicClient`, `QQMusicClient`, etc., implement `BaseMusicClient._constructsearchurls()` and `BaseMusicClient._search()` to define how the search is actually performed for each platform.

#### `BaseMusicClient.download(song_infos: list, num_threadings=5, request_overrides=None)`

Download one or more songs from the specific music platform. 

- **Arguments**:
  
  - **song_infos** (`list[dict]`): A list of song information dictionaries (typically the result of `BaseMusicClient.search()`).
  
  - **num_threadings** (`int`, default `5`): Number of threads used for concurrent downloading.
  
  - **request_overrides** (`dict` or `None`, default `{}`): Extra keyword arguments passed to the underlying `BaseMusicClient.get()` method (e.g., `headers`, `proxies`, `timeout`). If `None`, treated as an empty dict.
  
- **Returns**:

  - `list[dict]`: A list of successfully downloaded `song_info` dictionaries.

