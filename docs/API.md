# Musicdl APIs

This document describes the main public interfaces of `MusicClient`, `MusicClientCMD`, and `BaseMusicClient` based on the latest code version.

## `musicdl.musicdl.MusicClient`

`MusicClient` is the high-level entry point for end users. It manages multiple source-specific clients, sends search and download requests to the correct source, and provides both programmatic and interactive workflows.

Constructor:

```python
musicdl.musicdl.MusicClient(
    music_sources: list = [],
    init_music_clients_cfg: dict = {},
    clients_threadings: dict = {},
    requests_overrides: dict = {},
    search_rules: dict = {},
)
```

Arguments:

- **`music_sources`**

  A list of source client names to enable. You can pass a list such as `["NeteaseMusicClient", "QQMusicClient"]`.
  You can also pass a single string, it will be converted into a one-item list internally.
  If empty, the default sources are: 
  ```python
  ["MiguMusicClient", "NeteaseMusicClient", "QQMusicClient", "KuwoMusicClient", "QianqianMusicClient"]
  ```

- **`init_music_clients_cfg`**

  Per-source initialization settings. The key is the source name, and the value is a config dictionary used when building that source client.
  
  Example:

  ```python
  {
    "NeteaseMusicClient": {"work_dir": "outputs", "search_size_per_source": 10, "maintain_session": True},
    "QQMusicClient": {"search_size_per_source": 5, "default_search_cookies": {"foo": "bar"}},
  }
  ```
  
  Common fields include:

  - `search_size_per_source`
  - `auto_set_proxies`
  - `random_update_ua`
  - `max_retries`
  - `maintain_session`
  - `disable_print`
  - `work_dir`
  - `default_search_cookies`
  - `default_download_cookies`
  - `default_parse_cookies`
  - `search_size_per_page`
  - `strict_limit_search_size_per_page`
  - `quark_parser_config`
  - `freeproxy_settings`
  - `enable_search_curl_cffi`
  - `enable_download_curl_cffi`
  - `enable_parse_curl_cffi`

  Notes:
  
  - `logger_handle` is injected automatically by `MusicClient`.
  - `type` is also set automatically to the current source name.
  - Some sources use a smaller default `search_size_per_source` internally.
  
- **`clients_threadings`**

  Per-source thread counts used during search and download.
  
  Example:
  
  ```python
  {"NeteaseMusicClient": 8, "QQMusicClient": 4}
  ```
  
  If a source is not provided here, `MusicClient` uses its internal default thread count.

- **`requests_overrides`**

  Per-source request overrides forwarded to the underlying source client.
  
  Typical values include:
  
  - `headers`
  - `cookies`
  - `proxies`
  - `timeout`
  - `verify`
  
  Example:
  
  ```python
  {"NeteaseMusicClient": {"timeout": (10, 30), "headers": {"User-Agent": "..."},}}
  ```

- **`search_rules`**

  Per-source search rules passed into each source client’s `search()` implementation.
  
  Example:
  
  ```python
  {"FiveSingMusicClient": {"sort": 1, "filter": 0, "type": 0}}
  ```
  
  Use this when a source supports custom search filters or paging rules.
  
#### `MusicClient.search(keyword) -> dict[str, list[SongInfo]]`

Searches all enabled music sources in parallel.

What it does:

- Starts one search task per enabled source.
- Uses the per-source thread count from `clients_threadings`.
- Passes `requests_overrides[source]` and `search_rules[source]` to each source client.
- Returns a dictionary keyed by source name.

Example:

```python
music_client = MusicClient(
    music_sources=["NeteaseMusicClient", "QQMusicClient"]
)

results = music_client.search("Jay Chou")
```

Typical return shape:

```python
{
    "NeteaseMusicClient": [SongInfo(...), SongInfo(...)],
    "QQMusicClient": [SongInfo(...)]
}
```

#### `MusicClient.download(song_infos) -> list[SongInfo]`

Downloads songs by routing them to the correct underlying source client.

Accepted input:

- a flat list of `SongInfo`
- or a dictionary like `dict[str, list[SongInfo]]`

What it does:

- Groups songs by `song_info.source`
- Calls the matching source client’s `download()` method
- Merges all successful downloads into one list

Example with a flat list:

```python
results = music_client.search("Faded")
selected = results["NeteaseMusicClient"][:2]
downloaded = music_client.download(selected)
```

Example with the full search result dictionary:

```python
results = music_client.search("Faded")
downloaded = music_client.download(results)
```

Return value:

```python
list[SongInfo]
```

Only successfully downloaded items are returned.

#### `MusicClient.parseplaylist(playlist_url: str) -> list[SongInfo]`

Tries to parse a playlist URL by asking enabled source clients one by one.

What it does:

- Iterates through all initialized clients
- Calls each client’s `parseplaylist()`
- Stops at the first client that returns a non-empty result

Example:

```python
songs = music_client.parseplaylist(
    "https://music.163.com/#/playlist?id=7583298906"
)
downloaded = music_client.download(songs)
```

This is useful when the caller does not want to manually determine which source owns the playlist URL.

#### `MusicClient.startcmdui()`

Starts the interactive terminal UI.

What it does:

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

Special inputs at the main prompt:

- `q`: quit the program
- `r`: restart the interactive flow

This method runs in a loop until the user exits.

## `musicdl.musicdl.MusicClientCMD`

`MusicClientCMD` is the Click-based command-line entry point.

It supports three modes:

1. **Interactive mode**  
   If both `keyword` and `playlist_url` are empty, it launches `startcmdui()`.

2. **Playlist mode**  
   If `playlist_url` is provided, it parses the playlist and downloads all parsed tracks.

3. **Keyword mode**  
   If `keyword` is provided, it searches by keyword, opens the selection UI, and downloads the chosen tracks.

Signature:

```python
musicdl.musicdl.MusicClientCMD(
    keyword: str,
    playlist_url: str,
    music_sources: str,
    init_music_clients_cfg: str,
    requests_overrides: str,
    clients_threadings: str,
    search_rules: str,
)
```

CLI Options:

- **`-k, --keyword`**

  Search keyword. If omitted and no playlist URL is given, the program enters interactive mode.
  
  Example:
  
  ```bash
  musicdl -k "Taylor Swift"
  ```

- **`-p, --playlist-url, --playlist_url`**

  Playlist URL to parse and download.
  
  Example:
  
  ```bash
  musicdl -p "https://music.163.com/#/playlist?id=7583298906"
  ```
  
- **`-m, --music-sources, --music_sources`**

  Comma-separated list of source names.
  
  Example:
  
  ```bash
  musicdl -k "Adele" -m "NeteaseMusicClient,QQMusicClient"
  ```

- **`-i, --init-music-clients-cfg, --init_music_clients_cfg`**

  JSON string for per-source client initialization config.
  
  Example:
  
  ```bash
  musicdl -k "Adele" -i '{"NeteaseMusicClient": {"work_dir": "outputs", "search_size_per_source": 10}}'
  ```

- **`-r, --requests-overrides, --requests_overrides`**

  JSON string for per-source request overrides.
  
  Example:
  
  ```bash
  musicdl -k "Adele" -r '{"NeteaseMusicClient": {"timeout": [10, 30]}}'
  ```

- **`-c, --clients-threadings, --clients_threadings`**

  JSON string for per-source thread counts.
  
  Example:
  
  ```bash
  musicdl -k "Adele" -c '{"NeteaseMusicClient": 8, "QQMusicClient": 4}'
  ```

- **`-s, --search-rules, --search_rules`**

  JSON string for per-source search rules.
  
  Example:
  
  ```bash
  musicdl -k "Adele" -s '{"FiveSingMusicClient": {"sort": 1, "type": 0}}'
  ```

Important Behavior:

- `keyword` and `playlist_url` cannot be set at the same time.
- The JSON-like CLI strings are parsed with `json_repair.loads`, which is more tolerant than strict `json.loads`.
- `music_sources` is split by commas after removing extra spaces.

## `musicdl.modules.sources.BaseMusicClient`

`BaseMusicClient` is the common base class for source-specific music clients.

End users usually do not create this class directly. Instead, they use subclasses such as,

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

For developers, this class provides the shared workflow for:

- search URL construction
- concurrent searching
- deduplication
- work directory creation
- progress display
- downloading with HTTP or HLS
- playlist parsing hooks
- HTTP session / retry handling

Constructor:

```python
musicdl.modules.sources.BaseMusicClient(
    search_size_per_source: int = 5,
    auto_set_proxies: bool = False,
    random_update_ua: bool = False,
    enable_search_curl_cffi: bool = False,
    enable_parse_curl_cffi: bool = False,
    enable_download_curl_cffi: bool = False,
    maintain_session: bool = False,
    logger_handle: LoggerHandle = None,
    disable_print: bool = False,
    work_dir: str = "musicdl_outputs",
    max_retries: int = 3,
    freeproxy_settings: dict = None,
    default_search_cookies: dict | str = None,
    default_download_cookies: dict | str = None,
    default_parse_cookies: dict | str = None,
    strict_limit_search_size_per_page: bool = True,
    search_size_per_page: int = 10,
    quark_parser_config: dict = None,
)
```

Arguments:

- `search_size_per_source`: maximum number of results to keep for this source
- `search_size_per_page`: page size used when building paginated search requests
- `strict_limit_search_size_per_page`: whether to strictly cap returned results
- `maintain_session`: reuse one session across requests
- `max_retries`: retry count for `get()` and `post()`
- `random_update_ua`: randomly refresh `User-Agent`
- `enable_search_curl_cffi`
- `enable_parse_curl_cffi`
- `enable_download_curl_cffi`
- `auto_set_proxies`: auto-fetch proxies through `freeproxy`
- `freeproxy_settings`: config for the proxy client
- `default_search_cookies`
- `default_download_cookies`
- `default_parse_cookies`
- `work_dir`: root output directory
- `logger_handle`: logger instance
- `disable_print`: disable supported logger prints
- `quark_parser_config`: configuration used when a source needs Quark Netdisk cookies or related settings

Methods Subclasses Usually Override:

- **`_constructsearchurls(keyword, rule=None, request_overrides=None) -> list`**

  Must be implemented by each subclass. This method should build the list of search URLs or search request targets for the given keyword.
  
  Example idea:

  ```python
  def _constructsearchurls(self, keyword, rule=None, request_overrides=None):
      return [f"https://example.com/search?q={keyword}&page=1"]
  ```

- **`_search(keyword="", search_url="", request_overrides=None, song_infos=[], progress=None, progress_id=0)`**

  Must be implemented by each subclass. This method should:
  
  - fetch data from one search URL
  - parse the source response
  - create `SongInfo` objects
  - append valid results into the provided `song_infos` list
  - update progress text if needed
  
- **`parseplaylist(playlist_url, request_overrides=None)`**
  
  Optional for subclasses. The base implementation raises `NotImplementedError`.
  A subclass should override it if the source supports albums, playlists, episode collections, or other grouped URLs.

#### `BaseMusicClient.search(keyword, num_threadings=5, request_overrides=None, rule=None, main_process_context=None, main_progress_id=None, main_progress_lock=None) -> list[SongInfo]`

Searches this source only. 

What it does:

1. Builds search URLs using `_constructsearchurls()`
2. Searches those URLs concurrently with `_search()`
3. Merges results from all worker threads
4. Removes duplicates by `song_info.identifier`
5. Creates a unique work directory for this search
6. Assigns `work_dir` to returned songs
7. Saves serialized results to `search_results.pkl`

Example:

```python
client = SomeMusicClient(search_size_per_source=10)
songs = client.search("Imagine Dragons")
```

Return value:

```python
list[SongInfo]
```

Only valid downloadable items are kept in the final result.

#### `BaseMusicClient.download(song_infos, num_threadings=5, request_overrides=None, auto_supplement_song=True) -> list[SongInfo]`

Downloads songs from this source only.

What it does:

- filters invalid items before downloading
- creates an overall progress bar and per-song progress bars
- downloads with multiple threads
- supports different download paths depending on protocol
- saves serialized results to `download_results.pkl`

Example:

```python
songs = client.search("Imagine Dragons")
downloaded = client.download(songs[:3])
```

Return value:

```python
list[SongInfo]
```

Only successful downloads are returned.

When `auto_supplement_song=True`, each successful download is post-processed through:

```python
SongInfoUtils.supplsonginfothensavelyricsthenwritetags(...)
```

This may supplement metadata, save lyrics, and write tags.

#### `BaseMusicClient.get(url, **kwargs)`

A retry-aware wrapper around `session.get()`.

Features:

- applies default cookies when not explicitly provided
- optionally uses auto proxies
- optionally uses `curl_cffi` impersonation
- optionally refreshes `User-Agent`
- retries up to `max_retries`

#### `BaseMusicClient.post(url, **kwargs)`

Same idea as `get()`, but for POST requests.
