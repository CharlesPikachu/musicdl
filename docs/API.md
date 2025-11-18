# Musicdl APIs


#### `musicdl.musicdl.MusicClient`

A unified interface encapsulated for all supported music platforms.

Arguments supported when initializing this class include:

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
      "logger_handle": self.logger_handle,
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






#### musicdl.musicdl.modules.sources.fivesing.FiveSingMusicClient


#### musicdl.musicdl.modules.sources.joox.JooxMusicClient


#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient


#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient


#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient


#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient



#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient



#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient




#### musicdl.musicdl.modules.sources.kugou.KugouMusicClient