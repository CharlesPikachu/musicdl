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


## `musicdl.modules.sources.BaseMusicClient`

`BaseMusicClient` defines the common workflow for searching, downloading, and playlist parsing across different music sources.
Concrete clients only need to implement the source-specific parsing and URL construction logic, while the base class handles concurrency, progress display, deduplication, working-directory creation, and result serialization.
To put it simply, `BaseMusicClient` is the abstract base class for all concrete music clients, including,

- `musicdl.modules.sources.AppleMusicClient`
- `musicdl.modules.sources.BilibiliMusicClient`
- `musicdl.modules.sources.DeezerMusicClient`
- `musicdl.modules.sources.FiveSingMusicClient`
- `musicdl.modules.sources.JamendoMusicClient`
- `musicdl.modules.sources.JooxMusicClient`
- `musicdl.modules.sources.KugouMusicClient`
- `musicdl.modules.sources.KuwoMusicClient`
- `musicdl.modules.sources.MiguMusicClient`
- `musicdl.modules.sources.NeteaseMusicClient`
- `musicdl.modules.sources.QianqianMusicClient`
- `musicdl.modules.sources.QQMusicClient`
- `musicdl.modules.sources.QobuzMusicClient`
- `musicdl.modules.sources.SodaMusicClient`
- `musicdl.modules.sources.StreetVoiceMusicClient`
- `musicdl.modules.sources.SoundCloudMusicClient`
- `musicdl.modules.sources.SpotifyMusicClient`
- `musicdl.modules.sources.TIDALMusicClient`
- `musicdl.modules.sources.YouTubeMusicClient`
- `musicdl.modules.thirdpartysites.BuguyyMusicClient`
- `musicdl.modules.thirdpartysites.FiveSongMusicClient`
- `musicdl.modules.thirdpartysites.FangpiMusicClient`
- `musicdl.modules.thirdpartysites.FLMP3MusicClient`
- `musicdl.modules.thirdpartysites.GequbaoMusicClient`
- `musicdl.modules.thirdpartysites.GequhaiMusicClient`
- `musicdl.modules.thirdpartysites.HTQYYMusicClient`
- `musicdl.modules.thirdpartysites.JCPOOMusicClient`
- `musicdl.modules.thirdpartysites.KKWSMusicClient`
- `musicdl.modules.thirdpartysites.LivePOOMusicClient`
- `musicdl.modules.thirdpartysites.MituMusicClient`
- `musicdl.modules.thirdpartysites.TwoT58MusicClient`
- `musicdl.modules.thirdpartysites.YinyuedaoMusicClient`
- `musicdl.modules.thirdpartysites.ZhuolinMusicClient`
- `musicdl.modules.common.GDStudioMusicClient`
- `musicdl.modules.common.JBSouMusicClient`
- `musicdl.modules.common.MP3JuiceMusicClient`
- `musicdl.modules.common.MyFreeMP3MusicClient`
- `musicdl.modules.common.TuneHubMusicClient`
- `musicdl.modules.audiobooks.LizhiMusicClient`
- `musicdl.modules.audiobooks.LRTSMusicClient`
- `musicdl.modules.audiobooks.QingtingMusicClient`
- `musicdl.modules.audiobooks.XimalayaMusicClient`

End users usually **do not** instantiate `BaseMusicClient` directly, but instead use one of the specific clients above.
The methods documented here describe the common behavior of all these clients.
Arguments supported when initializing this class include:

- **search_size_per_source** (`int`, default `5`):  
  Maximum number of search results to fetch per source.
  
- **auto_set_proxies** (`bool`, default `False`):  
  If `True`, randomly assign a free proxy fetched by `freeproxy.ProxiedSessionClient` (details refer to [FreeProxy](https://github.com/CharlesPikachu/freeproxy/tree/master)) for each request (not work for `AppleMusicClient`, `TIDALMusicClient` and `YouTubeMusicClient`).

- **random_update_ua** (`bool`, default `False`):  
  If `True`, randomly refresh the `User-Agent` header on each request (not work for `AppleMusicClient`, `TIDALMusicClient`, `KugouMusicClient` and `YouTubeMusicClient`).

- **enable_search_curl_cffi** (`bool`, default `False`):  
  If `True`, `curl_cffi.requests.Session` is used for each search request (not work for `AppleMusicClient`, `TIDALMusicClient` and `YouTubeMusicClient`).

- **enable_download_curl_cffi** (`bool`, default `False`):  
  If `True`, `curl_cffi.requests.Session` is used for each download request (not work for `AppleMusicClient`, `TIDALMusicClient` and `YouTubeMusicClient`).

- **enable_parse_curl_cffi** (`bool`, default `False`):  
  If `True`, `curl_cffi.requests.Session` is used for each parseplaylist request (not work for `AppleMusicClient`, `TIDALMusicClient` and `YouTubeMusicClient`).

- **max_retries** (`int`, default `3`):  
  Maximum number of retry attempts for each HTTP request in `BaseMusicClient.get()` / `BaseMusicClient.post()`.

- **maintain_session** (`bool`, default `False`):  
  If `False`, a new `requests.Session` is created before each request;  
  if `True`, the same session is reused across requests (not work for `AppleMusicClient`, `TIDALMusicClient`, `KugouMusicClient` and `YouTubeMusicClient`).

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

#### `BaseMusicClient.search(keyword: str, num_threadings=5, request_overrides=None, rule=None, main_process_context=None, main_progress_id=None, main_progress_lock=None)`

Search for audio resources from the current music source, such as Netease, Kugou, QQ, and others.
This method delegates platform-specific logic to `_constructsearchurls()` and `_search()`, then merges and deduplicates the results.

- **Arguments**:

  - **keyword** (`str`)  
  Search keyword, such as a song name, artist name, album title, or other query text.
  
  - **num_threadings** (`int`, default: `5`)  
  Number of worker threads used to search across all constructed search URLs concurrently.

  - **request_overrides** (`dict | None`, default: `None`)  
  Extra request options forwarded to the underlying search requests, such as `headers`, `cookies`, `proxies`, `timeout`, or `verify`.  
  If `None`, it is treated as an empty dictionary.

  - **rule** (`dict | None`, default: `None`)  
  Client-specific search options passed into `_constructsearchurls()`.  
  This may include filters such as page rules, quality constraints, sort preferences, or other source-specific search parameters.  
  If `None`, it is treated as an empty dictionary.
  
  - **main_process_context** (`rich.progress.Progress | None`, default: `None`)  
  Optional external Rich `Progress` instance. If provided, the search task is attached to that progress context instead of creating a new one internally.

  - **main_progress_id** (`int | None`, default: `None`)  
  Optional task ID in `main_process_context` used to update a shared global progress bar across multiple sources.
  
  - **main_progress_lock** (`threading.Lock | None`, default: `None`)  
  Optional lock used to synchronize progress updates when multiple clients share the same progress context.

- **Returns**:

  - **`list[SongInfo]`**  
  A deduplicated list of `SongInfo` objects returned by the source-specific `_search()` implementation.

After searching, this method also assigns a generated `work_dir` to each result. For episodic items, episode-level working directories may also be assigned.

- **Behavior**

  - Logs the start and end of the search process.
  - Calls `_constructsearchurls()` to generate one or more search URLs.
  - Uses a thread pool to run `_search()` concurrently on all generated URLs.
  - Merges results from all threads.
  - Removes duplicates using the `SongInfo.identifier` field.
  - Creates a unique working directory for the current search.
  - Saves search results to `search_results.pkl` inside the corresponding working directory.
  - Returns all valid `SongInfo` results.

- **Notes**

  - Concrete subclasses must implement:
    - `BaseMusicClient._constructsearchurls()`
    - `BaseMusicClient._search()`
  - Deduplication is based on `song_info.identifier`.
  - The returned items are `SongInfo` objects, not plain dictionaries, although they are serialized as dictionaries when saved to disk.

#### `BaseMusicClient.download(song_infos: list[SongInfo], num_threadings=5, request_overrides=None, auto_supplement_song=True)`

Download one or more audio items represented by `SongInfo` objects.

This method supports both standard HTTP downloads and HLS downloads, depending on `song_info.protocol`.

- **Arguments**:
  
  - **song_infos** (`list[SongInfo]`)  
  A list of `SongInfo` objects to download, typically returned by `BaseMusicClient.search()` or `BaseMusicClient.parseplaylist()`.
  
  - **num_threadings** (`int`, default: `5`)  
  Number of worker threads used for concurrent downloading.
  
  - **request_overrides** (`dict | None`, default: `None`)  
  Extra request options forwarded to the underlying download request, such as `headers`, `cookies`, `proxies`, `timeout`, or `verify`.  
  If `None`, it is treated as an empty dictionary.
  
  - **auto_supplement_song** (`bool`, default: `True`)  
  Whether to post-process successfully downloaded items with `SongInfoUtils.supplsonginfothensavelyricsthenwritetags(...)`.  
  When enabled, the downloader may supplement metadata, save lyrics, and write tags after download.
  
- **Returns**:

  - **`list[SongInfo]`**  
  A list of successfully downloaded `SongInfo` objects.

- **Behavior**
  
  - Logs the start and end of the download process.
  - Shortens paths in `song_infos` before downloading.
  - Creates a Rich progress display with:
    - an overall audio progress bar
    - per-song progress bars
    - transfer speed and estimated remaining time
  - Downloads items concurrently using a thread pool.
  - Supports:
    - *HLS* downloads through `HLSDownloader`
    - *HTTP* downloads from in-memory `downloaded_contents`
    - *HTTP* streamed downloads from `download_url`
  - Saves successful results to `download_results.pkl` in the corresponding working directory.

- **Protocol-specific behavior**

  - If `song_info.protocol == "HLS"`:
    - Uses `HLSDownloader`
    - Downloads the best quality stream
    - Removes temporary segments after completion

  - If `song_info.protocol == "HTTP"` and `song_info.downloaded_contents` is already available:
    - Writes the in-memory bytes directly to `song_info.save_path`

  - If `song_info.protocol == "HTTP"` and `downloaded_contents` is not available:
    - Streams the file from `song_info.download_url`

- **Notes**

  - Individual download failures do not stop the entire batch.
  - Failed items are skipped from the returned list.
  - Per-item headers may override global request headers if `song_info.default_download_headers` is set.

#### `BaseMusicClient.parseplaylist(playlist_url: str, request_overrides=None)`

Parse a playlist URL and extract downloadable audio items from it.

This method is intended for source-specific playlist parsing, such as album pages, playlist pages, episode collections, or shared links.

- **Arguments**

  - **playlist_url** (`str`)  
    URL of the playlist or collection page to parse.

  - **request_overrides** (`dict | None`, default: `None`)  
    Extra request options forwarded to the underlying parsing requests, such as `headers`, `cookies`, `proxies`, `timeout`, or `verify`.  
    If `None`, it is treated as an empty dictionary.

- **Returns**

  - Usually **`list[SongInfo]`**  
    A list of parsed `SongInfo` objects representing the items in the playlist.
