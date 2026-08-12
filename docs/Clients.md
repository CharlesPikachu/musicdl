# Music Clients

This section explains how to use all music clients supported by musicdl, covering two main scenarios: direct use from the terminal and integration within Python code.

## Platforms in Greater China

#### BilibiliMusicClient

[Bilibili Music](https://www.bilibili.com/audio/home/?type=9) is Bilibili’s dedicated audio platform, where users can discover, stream, and enjoy a wide variety of music, podcasts, and original audio content.

We can use BilibiliMusicClient to download music from the above music platform.

BilibiliMusicClient requires no additional CLI tools such as ffmpeg or N_m3u8DL-RE. Just install musicdl via pip and it is ready to use out of the box.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m BilibiliMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m BilibiliMusicClient -i "{'BilibiliMusicClient': {'default_search_cookies': 'YOUR_COOKIES', 'default_download_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['BilibiliMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'BilibiliMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
        'default_download_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['BilibiliMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### BodianMusicClient (Built-in Premium Account)

[Bodian Music](https://bodian.kuwo.cn/) is a streamlined QQ Music app offering over 100 million licensed songs, one-tap listening, personalized recommendations, scene-based radio, customizable players, and immersive music backgrounds.

BodianMusicClient supports downloading music from the platform mentioned above.

BodianMusicClient requires no additional command-line tools such as ffmpeg or N_m3u8DL-RE, just install it with pip install musicdl and start using it right away.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m BodianMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m BodianMusicClient -i "{'BodianMusicClient': {'default_search_cookies': {'uid': 'xxx', 'token': 'xxx', 'dev_id': 'xxx'}}}"`
  
  Please be aware that BodianMusicClient only accepts VIP membership cookies in the following format:
  
  `default_search_cookies = {"uid": "xxx", "token": "xxx", "dev_id": "xxx-xxx-xxx-xxx-xxx"}`
  
  The `uid`, `token`, and `dev_id` can be obtained by packet capturing the Bodian Music desktop client or mobile app.

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://h5app.kuwo.cn/m/bodian/collection.html?uid=45780003&playlistId=86749638&source=5&owerId=" -m BodianMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:
  
  `musicdl -p "https://h5app.kuwo.cn/m/bodian/collection.html?uid=45780003&playlistId=86749638&source=5&owerId=" -m BodianMusicClient -i "{'BodianMusicClient': {'default_parse_cookies': {'uid': 'xxx', 'token': 'xxx', 'dev_id': 'xxx'}}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['BodianMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'BodianMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['BodianMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['BodianMusicClient'])
  song_infos = music_client.parseplaylist("https://h5app.kuwo.cn/m/bodian/collection.html?uid=45780003&playlistId=86749638&source=5&owerId=")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'BodianMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['BodianMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://h5app.kuwo.cn/m/bodian/collection.html?uid=45780003&playlistId=86749638&source=5&owerId=")
  music_client.download(song_infos=song_infos)
  ```

#### FiveSingMusicClient

[5SING Music](https://5sing.kugou.com/index.html) is a KuGou-affiliated online music platform where users can upload and discover original songs, covers, instrumentals, playlists, videos, and independent musicians.

FiveSingMusicClient can be used to download music from the music platform mentioned above.

Using FiveSingMusicClient does not require installing any extra command-line tools like ffmpeg or N_m3u8DL-RE. Simply run pip install musicdl and you can start using it right away.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m FiveSingMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m FiveSingMusicClient -i "{'FiveSingMusicClient': {'default_search_cookies': 'YOUR_COOKIES', 'default_download_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://5sing.kugou.com/yeluoluo/dj/631b3fa72418b11003089b8d.html" -m FiveSingMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:
  
  `musicdl -p "https://5sing.kugou.com/yeluoluo/dj/631b3fa72418b11003089b8d.html" -m FiveSingMusicClient -i "{'FiveSingMusicClient': {'default_parse_cookies': 'YOUR_COOKIES', 'default_download_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['FiveSingMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'FiveSingMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
        'default_download_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['FiveSingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['FiveSingMusicClient'])
  song_infos = music_client.parseplaylist("https://5sing.kugou.com/yeluoluo/dj/631b3fa72418b11003089b8d.html")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'FiveSingMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
        'default_download_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['FiveSingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://5sing.kugou.com/yeluoluo/dj/631b3fa72418b11003089b8d.html")
  music_client.download(song_infos=song_infos)
  ```

#### KugouMusicClient (Built-in Premium Account)

[KuGou Music](http://www.kugou.com/) is a major Chinese online music platform that offers songs, charts, playlists, music videos, audiobooks, and live content.

Music from the above platform can be downloaded using KugouMusicClient.

KugouMusicClient works out of the box with no need for extra CLI dependencies such as ffmpeg or N_m3u8DL-RE — all you need is pip install musicdl.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m KugouMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  Kugou Music membership cookies copied directly from the web page can easily cause issues, so we provide the script [build_cookies_for_kugou.py](https://github.com/CharlesPikachu/musicdl/blob/master/scripts/build_cookies_for_kugou.py) in the repository to help you directly obtain valid cookies for your member account. 
  The output format is as follows:
  
  ```python
  {'KUGOU_API_GUID': 'xxx', 'KUGOU_API_MID': 'xxx', 'KUGOU_API_MAC': 'xxx', 'KUGOU_API_DEV': 'xxx', 'token': 'xxx', 'userid': 'xxx', 'dfid': 'xxx'}
  ```
  
  Then, you can use KugouMusicClient just like other music clients by passing the membership cookies as follows,
  
  `musicdl -m KugouMusicClient -i "{'KugouMusicClient': {'default_search_cookies': 'YOUR_COOKIES', 'default_download_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.kugou.com/yy/special/single/18170.html" -m KugouMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.kugou.com/yy/special/single/18170.html" -m KugouMusicClient -i "{'KugouMusicClient': {'default_parse_cookies': 'YOUR_COOKIES', 'default_download_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['KugouMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'KugouMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
        'default_download_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['KugouMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['KugouMusicClient'])
  song_infos = music_client.parseplaylist("https://www.kugou.com/yy/special/single/18170.html")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'KugouMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
        'default_download_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['KugouMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.kugou.com/yy/special/single/18170.html")
  music_client.download(song_infos=song_infos)
  ```

#### KuwoMusicClient (Built-in Premium Account)

[Kuwo Music](http://www.kuwo.cn/) is a major Chinese online music platform that offers high-quality music streaming, charts, playlists, radio, and downloadable songs.

We can download music from the aforementioned platform with KuwoMusicClient.

No additional command-line tools, including ffmpeg or N_m3u8DL-RE, are needed to use KuwoMusicClient. Installing musicdl with pip is enough to get started immediately.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m KuwoMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m KuwoMusicClient -i "{'KuwoMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.kuwo.cn/playlist_detail/2648040171" -m KuwoMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.kuwo.cn/playlist_detail/2648040171" -m KuwoMusicClient -i "{'KuwoMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['KuwoMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'KuwoMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['KuwoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['KuwoMusicClient'])
  song_infos = music_client.parseplaylist("https://www.kuwo.cn/playlist_detail/2648040171")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'KuwoMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['KuwoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.kuwo.cn/playlist_detail/2648040171")
  music_client.download(song_infos=song_infos)
  ```

#### MiguMusicClient

[Migu Music](https://music.migu.cn/v5/#/musicLibrary) is a Chinese music streaming platform that offers a large library of songs, albums, playlists, and other digital music content.

MiguMusicClient allows us to download music from the platform above.

MiguMusicClient can be used directly without installing any extra CLI utilities like ffmpeg or N_m3u8DL-RE. Just install musicdl via pip and it is good to go.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m MiguMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m MiguMusicClient -i "{'MiguMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://music.migu.cn/v5/#/playlist?playlistId=208219194&playlistType=create" -m MiguMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://music.migu.cn/v5/#/playlist?playlistId=208219194&playlistType=create" -m MiguMusicClient -i "{'MiguMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['MiguMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MiguMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['MiguMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['MiguMusicClient'])
  song_infos = music_client.parseplaylist("https://music.migu.cn/v5/#/playlist?playlistId=208219194&playlistType=create")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MiguMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['MiguMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://music.migu.cn/v5/#/playlist?playlistId=208219194&playlistType=create")
  music_client.download(song_infos=song_infos)
  ```

#### MOOVMusicClient

[MOOV Music](https://moov.hk/) is a Hong Kong music streaming platform known for its strong Cantopop catalogue, 24-bit lossless audio, and rich collection of music videos and concert content.

MOOVMusicClient provides music download support for the platform mentioned above.

MOOVMusicClient works out of the box without requiring additional command-line tools such as ffmpeg or N_m3u8DL-RE. Simply install musicdl via pip, and you are ready to use it.

(1) Command-Line Usage

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m MOOVMusicClient -i "{'MOOVMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  The cookies must include the `MOOVUUID` and `MTGSESSIONID` fields, like this:
  
  `MOOVUUID=7A1DA713-6CC7-461F-91BD-595DF18C159F; MTGSESSIONID=xxx`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://app.moov.hk/xIeFa" -m MOOVMusicClient -i "{'MOOVMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`
  
  Please note that if the playlist was created by yourself, for example "https://moov.hk/#/collection/UPL/list/7574202", it is recommended to click Share and use the shared link to parse and download the playlist.

(2) Invoke It in Python

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MOOVMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['MOOVMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MOOVMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['MOOVMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://app.moov.hk/xIeFa")
  music_client.download(song_infos=song_infos)
  ```

#### NeteaseMusicClient (Built-in Premium Account)

[NetEase Cloud Music](https://music.163.com/) is one of China’s most popular music streaming platforms, known for its vast song library, personalized recommendations, and active user community.

NeteaseMusicClient makes it possible to download music from the above platform.

There is no need to install extra tools such as ffmpeg or N_m3u8DL-RE to use NeteaseMusicClient. A simple pip install musicdl is all it takes.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m NeteaseMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m NeteaseMusicClient -i "{'NeteaseMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://music.163.com/#/my/m/music/playlist?id=7583298906" -m NeteaseMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://music.163.com/#/my/m/music/playlist?id=7583298906" -m NeteaseMusicClient -i "{'NeteaseMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'NeteaseMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'])
  song_infos = music_client.parseplaylist("https://music.163.com/#/my/m/music/playlist?id=7583298906")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'NeteaseMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['NeteaseMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://music.163.com/#/my/m/music/playlist?id=7583298906")
  music_client.download(song_infos=song_infos)
  ```

#### QianqianMusicClient

[Qianqian Music](https://music.91q.com/) is an online music platform offering a large library of songs, popular playlists, artist content, and curated videos.

We use QianqianMusicClient to download music from the above-mentioned platform.

QianqianMusicClient comes ready to use without relying on additional CLI tools like ffmpeg or N_m3u8DL-RE. Just install musicdl through pip and you are all set.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m QianqianMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m QianqianMusicClient -i "{'QianqianMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://music.91q.com/songlist/309421" -m QianqianMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://music.91q.com/songlist/309421" -m QianqianMusicClient -i "{'QianqianMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['QianqianMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'QianqianMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['QianqianMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['QianqianMusicClient'])
  song_infos = music_client.parseplaylist("https://music.91q.com/songlist/309421")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'QianqianMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['QianqianMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://music.91q.com/songlist/309421")
  music_client.download(song_infos=song_infos)
  ```

#### QQMusicClient (Built-in Premium Account)

[QQ Music](https://y.qq.com/) is a high-quality music streaming platform offering a vast licensed song library, new releases, charts, playlists, MVs, and digital albums. 

QQMusicClient enables music downloads from the platform mentioned above.

To use QQMusicClient, you do not need any extra command-line tools such as ffmpeg or N_m3u8DL-RE. Once musicdl is installed with pip, it works immediately.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m QQMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m QQMusicClient -i "{'QQMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://y.qq.com/n/ryqq_v2/playlist/8740590963" -m QQMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://y.qq.com/n/ryqq_v2/playlist/8740590963" -m QQMusicClient -i "{'QQMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['QQMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'QQMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['QQMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['QQMusicClient'])
  song_infos = music_client.parseplaylist("https://y.qq.com/n/ryqq_v2/playlist/8740590963")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'QQMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['QQMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://y.qq.com/n/ryqq_v2/playlist/8740590963")
  music_client.download(song_infos=song_infos)
  ```

#### SodaMusicClient (Built-in Premium Account)

[Soda Music](https://www.douyin.com/qishui/) is Douyin’s official music streaming app, designed to help users discover and enjoy personalized songs anytime, anywhere.

Music from the above-mentioned platform can be fetched using SodaMusicClient.

SodaMusicClient offers an out-of-the-box experience: no extra CLI tools like ffmpeg or N_m3u8DL-RE are required, and pip install musicdl is all you need.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m SodaMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m SodaMusicClient -i "{'SodaMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  Please note that the cookies must be captured from the network requests of the [desktop version of Soda Music](https://www.douyin.com/qishui/), and they must be provided in the following format:
  
  ```python
  SODA_MUSIC_REQUIRED_COOKIES = {
    'cookies': 'ttwid=1|fqVX...5a72; passport_csrf_token=87b410...207c; passport_csrf_token_default=87b410...207c; d_ticket=b654f9...b1f; passport_mfa_token=CjahRQ...s5rw; odin_tt=5f5c92...f1dd; passport_assist_user=CkGoZ3...y3rT; n_mh=geOcP6...6gMI; passport_auth_status=ca3fdc...07f,; passport_auth_status_ss=ca3fdc...07f,; sid_guard=e28737...GMT; uid_tt=bfc1f3...eca0; uid_tt_ss=bfc1f3...eca0; sid_tt=e28737...6850; sessionid=e28737...6850; sessionid_ss=e28737...6850; session_tlb_tag=sttt|6...aI; is_staff_user=fa...se; has_biz_token=fa...se; sid_ucp_v1=1.0.0...Njg1MA; ssid_ucp_v1=1.0.0...Njg1MA', 
	'device_id': 'xxx',
	'x_helios': 'xxx',
	'x_medusa': 'xxx',
  }
  ```
  
  I recommend using [Reqable](https://reqable.com/zh-CN/) to capture network traffic and obtain cookies that meet the above requirements.

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://qishui.douyin.com/s/ix9JA2oW" -m SodaMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://qishui.douyin.com/s/ix9JA2oW" -m SodaMusicClient -i "{'SodaMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SodaMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SodaMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['SodaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SodaMusicClient'])
  song_infos = music_client.parseplaylist("https://qishui.douyin.com/s/ix9JA2oW")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SodaMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['SodaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://qishui.douyin.com/s/ix9JA2oW")
  music_client.download(song_infos=song_infos)
  ```

#### StreetVoiceMusicClient

[StreetVoice](https://www.streetvoice.cn/) is a music platform that helps independent artists share their work, reach new listeners, and grow through playlists, charts, discovery features, and a creator-focused community.

To download music from the platform above, we can use StreetVoiceMusicClient.

Since StreetVoice audio files are delivered in HLS format, downloading music from the platform with StreetVoiceMusicClient requires the command-line tool [FFmpeg](https://www.ffmpeg.org/).

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m StreetVoiceMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m StreetVoiceMusicClient -i "{'StreetVoiceMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.streetvoice.cn/svmusic_cn/playlists/964546/" -m StreetVoiceMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.streetvoice.cn/svmusic_cn/playlists/964546/" -m StreetVoiceMusicClient -i "{'StreetVoiceMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['StreetVoiceMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'StreetVoiceMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['StreetVoiceMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['StreetVoiceMusicClient'])
  song_infos = music_client.parseplaylist("https://www.streetvoice.cn/svmusic_cn/playlists/964546/")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'StreetVoiceMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['StreetVoiceMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.streetvoice.cn/svmusic_cn/playlists/964546/")
  music_client.download(song_infos=song_infos)
  ```

## Global Streaming / Indie

#### AppleMusicClient

[Apple Music](https://music.apple.com/) is Apple’s music streaming platform, offering songs, albums, playlists, radio, and other audio content through its web player and apps.

Music available on the platform above can be retrieved by means of AppleMusicClient.

To use AppleMusicClient, you will need extra CLI tools such as [FFmpeg](https://www.ffmpeg.org/), [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases/tag/v0.5.1-beta), [Bento4](https://www.bento4.com/) and [amdecrypt](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools), in addition to musicdl.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m AppleMusicClient`
  
  Without configured Apple Music subscriber cookies, AppleMusicClient is limited to downloading 30–90-second preview clips instead of full tracks.

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m AppleMusicClient -i "{'AppleMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  A few important things to keep in mind:
  
  - The cookies you provide must include the `media-user-token` field, for example: `{'media-user-token': 'xxx'}`.
  - In this case, you only need to make sure [FFmpeg](https://www.ffmpeg.org/) and [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases/tag/v0.5.1-beta) are installed.
  - musicdl currently supports downloading Apple Music tracks in the following audio formats/quality variants:
  
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
	
    However, if you are downloading with subscriber cookies alone, the highest quality currently available is `aac-legacy`.

- Using the wrapper server to search for and download songs:

  `musicdl -m AppleMusicClient -i "{'AppleMusicClient': {'search_size_per_source': 3, 'language': 'en-US', 'use_wrapper': True, 'wrapper_account_url': 'http://127.0.0.1:30020/', 'wrapper_decrypt_ip': '127.0.0.1:10020'}}"`
  
  Using the wrapper server enables musicdl to download higher-quality audio, such as `alac`, although the setup is a bit more complex.
  
  - To get started, follow the guide in the [WorldObservationLog/wrapper](https://github.com/WorldObservationLog/wrapper) repository and launch the wrapper server.
  - If you are on Windows, be aware that decryption will very likely fail unless the wrapper server is run inside Ubuntu on WSL. In other words, you will need to install WSL, set up Ubuntu within it, and start the wrapper server from the Ubuntu environment.
  - You should also ensure that the `wrapper_account_url` and `wrapper_decrypt_ip` settings are consistent with the corresponding arguments used by your wrapper server.
  - Besides [FFmpeg](https://www.ffmpeg.org/) and [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases/tag/v0.5.1-beta), you will also need to install [Bento4](https://www.bento4.com/downloads/) and [amdecrypt](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools).

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://music.apple.com/cn/playlist/%E6%9C%80%E6%96%B0%E7%83%AD%E6%9B%B2/pl.24cc3e1bd436415e93d801bccbebdf05" -m AppleMusicClient -i "{'AppleMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

- Using the wrapper server to parse and download songs from a playlist:
  
  `musicdl -p "https://music.apple.com/cn/playlist/%E6%9C%80%E6%96%B0%E7%83%AD%E6%9B%B2/pl.24cc3e1bd436415e93d801bccbebdf05" -m AppleMusicClient -i "{'AppleMusicClient': {'search_size_per_source': 3, 'language': 'en-US', 'use_wrapper': True, 'wrapper_account_url': 'http://127.0.0.1:30020/', 'wrapper_decrypt_ip': '127.0.0.1:10020'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  from musicdl.modules.sources.apple import SongCodec

  cookies = {'media-user-token': 'xxx'}
  init_music_clients_cfg = {'AppleMusicClient': {'default_search_cookies': cookies, 'search_size_per_source': 10, 'language': 'en-US', 'codec': SongCodec.AAC_LEGACY}}
  music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Using the wrapper server to search for and download songs:

  ```python
  from musicdl import musicdl
  from musicdl.modules.sources.apple import SongCodec

  init_music_clients_cfg = {'AppleMusicClient': {'search_size_per_source': 3, 'language': 'en-US', 'use_wrapper': True, 'wrapper_account_url': 'http://127.0.0.1:30020/', 'wrapper_decrypt_ip': '127.0.0.1:10020'}}
  music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'AppleMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://music.apple.com/cn/playlist/%E6%9C%80%E6%96%B0%E7%83%AD%E6%9B%B2/pl.24cc3e1bd436415e93d801bccbebdf05")
  music_client.download(song_infos=song_infos)
  ```

- Using the wrapper server to parse and download songs from a playlist:

  ```python
  from musicdl import musicdl
  
  init_music_clients_cfg = {'AppleMusicClient': {'search_size_per_source': 3, 'language': 'en-US', 'use_wrapper': True, 'wrapper_account_url': 'http://127.0.0.1:30020/', 'wrapper_decrypt_ip': '127.0.0.1:10020'}}
  music_client = musicdl.MusicClient(music_sources=['AppleMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://music.apple.com/cn/playlist/%E6%9C%80%E6%96%B0%E7%83%AD%E6%9B%B2/pl.24cc3e1bd436415e93d801bccbebdf05")
  music_client.download(song_infos=song_infos)
  ```

#### AudiusMusicClient

[Audius](https://audius.co/) is a decentralized music streaming platform that connects artists directly with listeners.

AudiusMusicClient provides access to the music available on the platform described above.

AudiusMusicClient works out of the box and requires no external command-line dependencies such as ffmpeg or N_m3u8DL-RE; installing musicdl is all you need.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:
  
  `musicdl -m AudiusMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m AudiusMusicClient -i "{'AudiusMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://audius.co/shakdiselekta/playlist/selekta-vs-rvssian-songs-of-flesh-fire" -m AudiusMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://audius.co/shakdiselekta/playlist/selekta-vs-rvssian-songs-of-flesh-fire" -m AudiusMusicClient -i "{'AudiusMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['AudiusMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'AudiusMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['AudiusMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['AudiusMusicClient'])
  song_infos = music_client.parseplaylist("https://audius.co/shakdiselekta/playlist/selekta-vs-rvssian-songs-of-flesh-fire")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'AudiusMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['AudiusMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://audius.co/shakdiselekta/playlist/selekta-vs-rvssian-songs-of-flesh-fire")
  music_client.download(song_infos=song_infos)
  ```

#### CCMixterMusicClient

[ccMixter](https://ccmixter.org/) is a Creative Commons music community where artists share, remix, and reuse vocals, samples, and original tracks for collaborative and royalty-friendly music creation.

CCMixterMusicClient lets you access the music hosted on the platform introduced above.

CCMixterMusicClient works out of the box without relying on external command-line tools such as ffmpeg or N_m3u8DL-RE; simply installing musicdl is sufficient.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:
  
  `musicdl -m CCMixterMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m CCMixterMusicClient -i "{'CCMixterMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://ccmixter.org/playlist/browse/57965" -m CCMixterMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://ccmixter.org/playlist/browse/57965" -m CCMixterMusicClient -i "{'CCMixterMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['CCMixterMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'CCMixterMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['CCMixterMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['CCMixterMusicClient'])
  song_infos = music_client.parseplaylist("https://ccmixter.org/playlist/browse/57965")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'CCMixterMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['CCMixterMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://ccmixter.org/playlist/browse/57965")
  music_client.download(song_infos=song_infos)
  ```

#### DeezerMusicClient (Built-in Premium Account)

[Deezer](https://www.deezer.com/us/) is a music streaming platform that lets users listen to over 120 million tracks, podcasts, playlists, and other audio content online.

Songs hosted on the platform above can be accessed using DeezerMusicClient.

DeezerMusicClient comes with no extra CLI tool requirements such as ffmpeg or N_m3u8DL-RE, and only musicdl needs to be installed.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:
  
  `musicdl -m DeezerMusicClient`
  
  Please note that if you use DeezerMusicClient without configuring your account cookies, you will only be able to download roughly a 30-second preview clip for each song (if the built-in premium account expires, which happens quite easily).

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m DeezerMusicClient -i "{'DeezerMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  Configured cookies must include the "arl" field, for example `{'arl': xxx, ...}` or `arl=xxx; ...`.
  In addition, if the account cookies you provide are not from a Deezer Premium subscriber, you will only be able to download songs at 128 kbps.

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.deezer.com/en/playlist/9221517042" -m DeezerMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.deezer.com/en/playlist/9221517042" -m DeezerMusicClient -i "{'DeezerMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['DeezerMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'DeezerMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['DeezerMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['DeezerMusicClient'])
  song_infos = music_client.parseplaylist("https://www.deezer.com/en/playlist/9221517042")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'DeezerMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['DeezerMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.deezer.com/en/playlist/9221517042")
  music_client.download(song_infos=song_infos)
  ```

#### FMAMusicClient

[Free Music Archive (FMA)](https://freemusicarchive.org/) is a curated online library offering free, legal access to independent music that users can play, download, and share.

FMAMusicClient provides access to the songs available on the platform mentioned above.

FMAMusicClient works out of the box without relying on external CLI dependencies like ffmpeg or N_m3u8DL-RE, installing musicdl is sufficient.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:
  
  `musicdl -m FMAMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m FMAMusicClient -i "{'FMAMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://freemusicarchive.org/member/meghan-admin/meet-policy-mix/" -m FMAMusicClient -i "{'FMAMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['FMAMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'FMAMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['FMAMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'FMAMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['FMAMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://freemusicarchive.org/member/meghan-admin/meet-policy-mix/")
  music_client.download(song_infos=song_infos)
  ```

#### JamendoMusicClient

[Jamendo](https://www.jamendo.com/) is a music platform that offers free music streaming and downloads, with a focus on independent artists and royalty-free music.

JamendoMusicClient supports fetching music from the platform noted above.

JamendoMusicClient requires only a pip installation of musicdl, with no additional setup for tools like ffmpeg or N_m3u8DL-RE.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m JamendoMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m JamendoMusicClient -i "{'JamendoMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.jamendo.com/playlist/500362331/demo" -m JamendoMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.jamendo.com/playlist/500362331/demo" -m JamendoMusicClient -i "{'JamendoMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JamendoMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'JamendoMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['JamendoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JamendoMusicClient'])
  song_infos = music_client.parseplaylist("https://www.jamendo.com/playlist/500362331/demo")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'JamendoMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['JamendoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.jamendo.com/playlist/500362331/demo")
  music_client.download(song_infos=song_infos)
  ```

#### JooxMusicClient (Built-in Premium Account)

[JOOX](https://www.joox.com/intl) is a music streaming platform by Tencent that offers over 40 million songs, playlists, karaoke, live broadcasting, and social audio features.

JooxMusicClient allows you to obtain music from the platform referenced above.

With JooxMusicClient, there is no extra dependency on CLI tools such as ffmpeg or N_m3u8DL-RE. Just install musicdl and you are ready to go.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m JooxMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m JooxMusicClient -i "{'JooxMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  If you’re unsure which cookies to use, you can run the [build_cookies_for_joox.py](https://github.com/CharlesPikachu/musicdl/blob/master/scripts/build_cookies_for_joox.py) script included in this repository to generate cookies in the format required by musicdl. 
  Just fill in your own premium account credentials in the appropriate section of the script.

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.joox.com/hk/playlist/5HTvfy7AAW9QJHPqM+T0+w==" -m JooxMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.joox.com/hk/playlist/5HTvfy7AAW9QJHPqM+T0+w==" -m JooxMusicClient -i "{'JooxMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JooxMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'JooxMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['JooxMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JooxMusicClient'])
  song_infos = music_client.parseplaylist("https://www.joox.com/hk/playlist/5HTvfy7AAW9QJHPqM+T0+w==")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'JooxMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['JooxMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.joox.com/hk/playlist/5HTvfy7AAW9QJHPqM+T0+w==")
  music_client.download(song_infos=song_infos)
  ```

#### JioSaavnMusicClient

[JioSaavn](https://www.jiosaavn.com/) is an Indian music streaming platform that offers songs, playlists, podcasts, and regional music across multiple Indian languages.

JioSaavnMusicClient allows access to music from the previously discussed platform.

JioSaavnMusicClient works out of the box without requiring external command-line tools such as FFmpeg or N_m3u8DL-RE; installing musicdl is sufficient to start using it.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m JioSaavnMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m JioSaavnMusicClient -i "{'JioSaavnMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.jiosaavn.com/featured/o-saathiya/PROeDetW3ZWMQv7FkH9rjg__" -m JioSaavnMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.jiosaavn.com/featured/o-saathiya/PROeDetW3ZWMQv7FkH9rjg__" -m JioSaavnMusicClient -i "{'JioSaavnMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JioSaavnMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'JioSaavnMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['JioSaavnMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JioSaavnMusicClient'])
  song_infos = music_client.parseplaylist("https://www.jiosaavn.com/featured/o-saathiya/PROeDetW3ZWMQv7FkH9rjg__")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'JioSaavnMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['JioSaavnMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.jiosaavn.com/featured/o-saathiya/PROeDetW3ZWMQv7FkH9rjg__")
  music_client.download(song_infos=song_infos)
  ```

#### OpenGameArtMusicClient

[OpenGameArt](https://opengameart.org/) is a community-driven platform that provides free and open-licensed game assets, including sprites, textures, music, and sound effects for game developers.

You can use OpenGameArtMusicClient to download music from the platform mentioned above.

OpenGameArtMusicClient does not require any additional CLI tools, such as ffmpeg or N_m3u8DL-RE. Simply install musicdl via pip, and it is ready to use out of the box.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m OpenGameArtMusicClient`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['OpenGameArtMusicClient'])
  music_client.startcmdui()
  ```

#### QobuzMusicClient (Built-in Premium Account)

[Qobuz](https://play.qobuz.com/discover) is a high-resolution music streaming and download platform that offers more than 100 million tracks in CD-quality and Hi-Res audio for music listening and discovery.

Music from the platform referenced above can be fetched through QobuzMusicClient.

With QobuzMusicClient, you do not need extra CLI tools like ffmpeg or N_m3u8DL-RE. A simple musicdl installation is sufficient.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m QobuzMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m QobuzMusicClient -i "{'QobuzMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  The cookies should be provided either as a dictionary in the format `{"x-user-auth-token": "xxx", ...}` or as a cookie string such as `x-user-auth-token=xxx; ...`. 
  The `x-user-auth-token` field is required, while any other fields are optional. 
  
  For convenience, the GitHub repo also includes a script named [build_cookies_for_qobuz.py](https://github.com/CharlesPikachu/musicdl/blob/master/scripts/build_cookies_for_qobuz.py), which can generate subscriber cookies in the format required by musicdl in one go. 
  All you need to do is enter your own subscriber account credentials in the appropriate section of the code and run the script.

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://www.qobuz.com/us-en/playlists/next-up-at-sam-first/21512061" -m QobuzMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://www.qobuz.com/us-en/playlists/next-up-at-sam-first/21512061" -m QobuzMusicClient -i "{'QobuzMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['QobuzMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'QobuzMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['QobuzMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['QobuzMusicClient'])
  song_infos = music_client.parseplaylist("https://www.qobuz.com/us-en/playlists/next-up-at-sam-first/21512061")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'QobuzMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['QobuzMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://www.qobuz.com/us-en/playlists/next-up-at-sam-first/21512061")
  music_client.download(song_infos=song_infos)
  ```

#### SoundCloudMusicClient

[SoundCloud](https://soundcloud.com/discover) is a music streaming and sharing platform where users can discover tracks, playlists, and podcasts, while artists can upload and share their work with listeners worldwide.

Songs offered by the platform above can be retrieved through SoundCloudMusicClient.

To use SoundCloudMusicClient, you will need a few extra CLI tools, including [FFmpeg](https://www.ffmpeg.org/), [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases/tag/v0.5.1-beta), and [Bento4](https://www.bento4.com/). After installing them together with musicdl, you are ready to go.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m SoundCloudMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m SoundCloudMusicClient -i "{'SoundCloudMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`
  
  Note that the cookies must be provided in the format `{'oauth_token': 'OAuth xxx', 'client_id': 'xxx'}`. 
  When the `oauth_token` is obtained by capturing it from the web client of your own membership account rather than through the official channel, the corresponding `client_id` is also required.

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://soundcloud.com/raudymithut/sets/sets-from-dj-raudy-mit-hut" -m SoundCloudMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://soundcloud.com/raudymithut/sets/sets-from-dj-raudy-mit-hut" -m SoundCloudMusicClient -i "{'SoundCloudMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SoundCloudMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SoundCloudMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['SoundCloudMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SoundCloudMusicClient'])
  song_infos = music_client.parseplaylist("https://soundcloud.com/raudymithut/sets/sets-from-dj-raudy-mit-hut")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SoundCloudMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['SoundCloudMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://soundcloud.com/raudymithut/sets/sets-from-dj-raudy-mit-hut")
  music_client.download(song_infos=song_infos)
  ```

#### SpotifyMusicClient (Built-in Premium Account)

[Spotify](https://open.spotify.com/) is a global audio streaming platform where users can listen to music, podcasts, and playlists through its web player and apps.

SpotifyMusicClient allows users to pull music from the platform referred to above.

SpotifyMusicClient works out of the box with just musicdl installed, without requiring extra CLI tools like ffmpeg or N_m3u8DL-RE.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m SpotifyMusicClient`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://open.spotify.com/playlist/36S7vjbqxUnzEGg9pBJ6p3" -m SpotifyMusicClient`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SpotifyMusicClient'])
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SpotifyMusicClient'])
  song_infos = music_client.parseplaylist("https://open.spotify.com/playlist/36S7vjbqxUnzEGg9pBJ6p3")
  music_client.download(song_infos=song_infos)
  ```

#### SunoMusicClient

[Suno](https://suno.com/discover) is a music company built to amplify imagination, making it possible for anyone to turn ideas, emotions, and stories into original songs and explore new ways of creating music with AI.

SunoMusicClient provides a simple way to fetch music from the platform mentioned above.

SunoMusicClient works out of the box with only musicdl installed and does not require extra command-line tools such as ffmpeg or N_m3u8DL-RE.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m SunoMusicClient`

- Simple usage for searching and downloading songs, with login cookies:

  `musicdl -m SunoMusicClient -i "{'SunoMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

  The cookies config for SunoMusicClient should only include `auth_token`. 
  This value can be obtained from the network requests: look for the authorization header in Request Headers and copy the long token after Bearer. 
  For example:
  
  `{'auth_token': xxx}`

- Basic usage for playlist parsing and downloading, without login cookies:

  `musicdl -p "https://suno.com/playlist/176ff485-6f66-4701-ac01-d55f194c325e" -m SunoMusicClient`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://suno.com/playlist/176ff485-6f66-4701-ac01-d55f194c325e" -m SunoMusicClient -i "{'SunoMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SunoMusicClient'])
  music_client.startcmdui()
  ```

- Simple usage for searching and downloading songs, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SunoMusicClient': {
        'default_search_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['SunoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Basic usage for playlist parsing and downloading, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SunoMusicClient'])
  song_infos = music_client.parseplaylist("https://suno.com/playlist/176ff485-6f66-4701-ac01-d55f194c325e")
  music_client.download(song_infos=song_infos)
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_vip_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SunoMusicClient': {
        'default_parse_cookies': your_vip_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['SunoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://suno.com/playlist/176ff485-6f66-4701-ac01-d55f194c325e")
  music_client.download(song_infos=song_infos)
  ```

#### TIDALMusicClient (Built-in Premium Account)

[TIDAL](https://tidal.com/) is a music streaming platform that offers millions of tracks, albums, playlists, and videos, with a focus on high-fidelity audio quality.

TIDALMusicClient is designed to fetch music from the platform referenced above.

With TIDALMusicClient, additional CLI tools such as [FFmpeg](https://www.ffmpeg.org/), [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases/tag/v0.5.1-beta), and [Bento4](https://www.bento4.com/) are required to perform audio decryption.

(1) Command-Line Usage

- Basic usage for song search and download, with login cookies:

  Unlike other music clients that come with built-in membership accounts, TIDALMusicClient requires cookies from your own account. 
  However, because a membership account is already built in, the account used to obtain the cookies does not need to be a paid subscription account, cookies from a normally registered free account are enough.
  
  To make sure your account cookies meet musicdl’s requirements, we recommend using the [build_cookies_for_tidal.py](https://github.com/CharlesPikachu/musicdl/blob/master/scripts/build_cookies_for_tidal.py) script included in the repository to obtain the cookies needed by musicdl. 
  The generated cookies will look roughly as follows:
  
  `{"access_token": "xxx", "refresh_token": "xxx", "expires": "2026-02-10T07:32:18.102233", "user_id": xxx, "country_code": "SG", "client_id": "7m7Ap0JC9j1cOM3n", "client_secret": "vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY="}`
  
  After that, you can simply provide the membership cookies in the same way as with other music clients:
  
  `musicdl -m TIDALMusicClient -i "{'TIDALMusicClient': {'default_search_cookies': 'YOUR_COOKIES'}}"`

- Simple usage for playlist parsing and downloading, with login cookies:

  `musicdl -p "https://tidal.com/playlist/7aa5d764-192f-45cb-ab9b-3692975e1f88" -m TIDALMusicClient -i "{'TIDALMusicClient': {'default_parse_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Basic usage for song search and download, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'TIDALMusicClient': {
        'default_search_cookies': your_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['TIDALMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Simple usage for playlist parsing and downloading, with login cookies:

  ```python
  from musicdl import musicdl
  
  your_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'TIDALMusicClient': {
        'default_parse_cookies': your_cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['TIDALMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  song_infos = music_client.parseplaylist("https://tidal.com/playlist/7aa5d764-192f-45cb-ab9b-3692975e1f88")
  music_client.download(song_infos=song_infos)
  ```

#### WikimediaCommonsMusicClient

[Wikimedia Commons](https://commons.wikimedia.org/) is a free media repository offering openly licensed audio files, images, videos, and other multimedia content.

WikimediaCommonsMusicClient allows you to download music directly from Wikimedia Commons.

No external command-line dependencies, including ffmpeg and N_m3u8DL-RE, are required. After installing musicdl with pip, WikimediaCommonsMusicClient works immediately.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m WikimediaCommonsMusicClient`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['WikimediaCommonsMusicClient'])
  music_client.startcmdui()
  ```

#### YouTubeMusicClient (Built-in Premium Account)

[YouTube Music](https://music.youtube.com/) is Google’s music streaming platform, offering access to over 100 million songs, albums, playlists, remixes, and music videos for listening and discovery.

The retrieval of music from the aforementioned platform can be handled by YouTubeMusicClient.

YouTubeMusicClient comes with an extra dependency on [Node.js](https://nodejs.org/en), so a separate [Node.js installation](https://nodejs.org/en/download) is required before use.

(1) Command-Line Usage

- Basic usage for song search and download, without login cookies:

  `musicdl -m YouTubeMusicClient`

(2) Invoke It in Python

- Basic usage for song search and download, without login cookies:

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['YouTubeMusicClient'])
  music_client.startcmdui()
  ```

## Audio / Radio

#### ITunesMusicClient

[iTunes Podcasts](https://www.apple.com/itunes/) is a digital platform where users can discover, subscribe to, and listen to audio shows across a wide range of topics.

ITunesMusicClient is the go-to tool for downloading audio from the above platform.

With ITunesMusicClient, all you need is pip install musicdl; there are no extra CLI dependencies or complicated configuration steps.

(1) Command-Line Usage

- Search and Download Podcasts from This Platform

  `musicdl -m ITunesMusicClient -i "{'ITunesMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['podcast']}}"`

(2) Invoke It in Python

- Search and Download Podcasts from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'ITunesMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['podcast']}}
  music_client = musicdl.MusicClient(music_sources=['ITunesMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### LizhiMusicClient

[Lizhi FM](https://www.lizhi.fm/) is a Chinese audio-sharing platform and podcast community built around the idea that "Everyone can be a podcaster."

LizhiMusicClient is the right tool for downloading audio content from the platform above.

LizhiMusicClient works out of the box with just pip install musicdl — no extra CLI tools or complicated setup required.

(1) Command-Line Usage

- Search and Download Tracks from This Platform

  `musicdl -m LizhiMusicClient -i "{'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}"`

- Search and Download Albums from This Platform

  `musicdl -m LizhiMusicClient -i "{'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}"`

- Search and Download User Works from This Platform

  `musicdl -m LizhiMusicClient -i "{'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['user']}}"`

- Search for and Download Tracks, Albums and User Works from This Platform

  `musicdl -m LizhiMusicClient -i "{'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album', 'user']}}"`

- Search & Download Tracks, Albums and User Works Using Your Own Premium Account Cookies

  `musicdl -m LizhiMusicClient -i "{'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album', 'user'], 'default_search_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Search and Download Tracks from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}
  music_client = musicdl.MusicClient(music_sources=['LizhiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search and Download Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}
  music_client = musicdl.MusicClient(music_sources=['LizhiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search and Download User Works from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['user']}}
  music_client = musicdl.MusicClient(music_sources=['LizhiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search for and Download Tracks, Albums and User Works from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album', 'user']}}
  music_client = musicdl.MusicClient(music_sources=['LizhiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search & Download Tracks, Albums and User Works Using Your Own Premium Account Cookies

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LizhiMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album', 'user'], 'default_search_cookies': 'YOUR_COOKIES'}}
  music_client = musicdl.MusicClient(music_sources=['LizhiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### LRTSMusicClient

[LRTS.me](https://www.lrts.me/) is the official website of Lanrentingshu, a leading Chinese audio reading platform that offers audiobooks, podcasts, radio-style programs, and other spoken-word content.

LRTSMusicClient is the recommended client for downloading audio from the platform above.

You can start using LRTSMusicClient right after installing musicdl via pip, without having to install tools like ffmpeg or N_m3u8DL-RE.

(1) Command-Line Usage

- Search and Download Books from This Platform

  `musicdl -m LRTSMusicClient -i "{'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['book']}}"`

- Search and Download Albums from This Platform

  `musicdl -m LRTSMusicClient -i "{'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}"`

- Search for and Download Books and Albums from This Platform

  `musicdl -m LRTSMusicClient -i "{'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['book', 'album']}}"`

- Search & Download Books and Albums Using Your Own Premium Account Cookies

  `musicdl -m LRTSMusicClient -i "{'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['book', 'album'], 'default_search_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Search and Download Books from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['book']}}
  music_client = musicdl.MusicClient(music_sources=['LRTSMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search and Download Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}
  music_client = musicdl.MusicClient(music_sources=['LRTSMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search for and Download Books and Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['book', 'album']}}
  music_client = musicdl.MusicClient(music_sources=['LRTSMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search & Download Books and Albums Using Your Own Premium Account Cookies

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'LRTSMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['book', 'album'], 'default_search_cookies': 'YOUR_COOKIES'}}
  music_client = musicdl.MusicClient(music_sources=['LRTSMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### QingtingMusicClient

[Qingting FM](https://www.qtfm.cn/) is a major Chinese audio streaming platform that offers podcasts, radio broadcasts, audiobooks, news, music, education, and other spoken-word content.

With QingtingMusicClient, audio from the platform above can be downloaded easily.

QingtingMusicClient keeps things easy: no additional CLI tools to install, just pip install musicdl and you’re all set.

(1) Command-Line Usage

- Search and Download Tracks from This Platform

  `musicdl -m QingtingMusicClient -i "{'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}"`

- Search and Download Albums from This Platform

  `musicdl -m QingtingMusicClient -i "{'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}"`

- Search for and Download Tracks and Albums from This Platform

  `musicdl -m QingtingMusicClient -i "{'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album']}}"`

- Search & Download Tracks and Albums Using Your Own Premium Account Cookies
  
  Manually extracting the cookies for a QingTing FM VIP account from the browser can be cumbersome and error-prone 
  (have to capture the network traffic yourself on the QingTing FM web client. Look for an AJAX request with the keyword "auth"). 
  To simplify the process, we provide the [build_cookies_for_qingtingfm.py](https://github.com/CharlesPikachu/musicdl/tree/master/scripts/build_cookies_for_qingtingfm.py) script, which helps generate the QingTing FM VIP account cookies in the format expected by musicdl.
  A successful output will look roughly like this:
  `{"errorno": 0, "errormsg": "", "data": {"qingting_id": "xxx", "access_token": "xxx", "refresh_token": "xxx", "expires_in": 7200}}`
  
  Then, you can use QingtingMusicClient in the same way as any other music client by simply passing in the membership cookies, as shown below:

  `musicdl -m QingtingMusicClient -i "{'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album'], 'default_search_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Search and Download Tracks from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}
  music_client = musicdl.MusicClient(music_sources=['QingtingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search and Download Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}
  music_client = musicdl.MusicClient(music_sources=['QingtingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search for and Download Tracks and Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album']}}
  music_client = musicdl.MusicClient(music_sources=['QingtingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search & Download Tracks and Albums Using Your Own Premium Account Cookies

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'QingtingMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album'], 'default_search_cookies': 'YOUR_COOKIES'}}
  music_client = musicdl.MusicClient(music_sources=['QingtingMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### XimalayaMusicClient

[Ximalaya](https://www.ximalaya.com/) is a leading Chinese online audio platform where users can listen to podcasts, audiobooks, radio-style programs, and other spoken-word content.

Audio content from the platform above can be downloaded with XimalayaMusicClient.

XimalayaMusicClient is ready to use after a simple pip install. No extra command-line tools like ffmpeg or N_m3u8DL-RE are needed.

(1) Command-Line Usage

- Search and Download Tracks from This Platform

  `musicdl -m XimalayaMusicClient -i "{'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}"`

- Search and Download Albums from This Platform

  `musicdl -m XimalayaMusicClient -i "{'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}"`

- Search for and Download Tracks and Albums from This Platform

  `musicdl -m XimalayaMusicClient -i "{'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album']}}"`

- Search & Download Tracks and Albums Using Your Own Premium Account Cookies

  `musicdl -m XimalayaMusicClient -i "{'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album'], 'default_search_cookies': 'YOUR_COOKIES'}}"`

(2) Invoke It in Python

- Search and Download Tracks from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track']}}
  music_client = musicdl.MusicClient(music_sources=['XimalayaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search and Download Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['album']}}
  music_client = musicdl.MusicClient(music_sources=['XimalayaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search for and Download Tracks and Albums from This Platform

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album']}}
  music_client = musicdl.MusicClient(music_sources=['XimalayaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

- Search & Download Tracks and Albums Using Your Own Premium Account Cookies

  ```python
  from musicdl import musicdl

  init_music_clients_cfg = {'XimalayaMusicClient': {'search_size_per_source': 2, 'allowed_search_types': ['track', 'album'], 'default_search_cookies': 'YOUR_COOKIES'}}
  music_client = musicdl.MusicClient(music_sources=['XimalayaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

(3) Screenshots of Running Results

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/ximalayascreenshot.gif" width="600"/>
  </div>
</div>
<br />

## Aggregators / Multi-Source Gateways

#### GDStudioMusicClient

[GD Music Station](https://music.gdstudio.xyz/) is an online music platform that lets users search, stream, and download music across multiple music sources through a simple web interface.

GDStudioMusicClient is the right tool for downloading music from the platform above.

The table below shows all music platforms currently supported by GDStudioMusicClient via GD Music Station,

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

There’s no need to set up extra CLI tools such as ffmpeg or N_m3u8DL-RE. Just install musicdl via pip and start using GDStudioMusicClient right away.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m GDStudioMusicClient`
  
- Restrict Music Sources and Number of Results

  `musicdl -m GDStudioMusicClient -i "{'GDStudioMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['kuwo', 'netease', 'tidal', 'apple']}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['GDStudioMusicClient'])
  music_client.startcmdui()
  ```

- Restrict Music Sources and Number of Results

  ```python
  from musicdl import musicdl

  # allowed_music_sources can be set to any subset (i.e., any combination) of ['spotify', 'tencent', 'netease', 'kuwo', 'tidal', 'qobuz', 'joox', 'bilibili', 'apple', 'ytmusic']
  init_music_clients_cfg = {'GDStudioMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['kuwo', 'netease', 'tidal', 'apple']}}
  music_client = musicdl.MusicClient(music_sources=['GDStudioMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

(3) Screenshots of Running Results

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/gdstudioscreenshot.png" width="600"/>
  </div>
</div>
<br />

#### JBSouMusicClient

[JBSou](https://www.jbsou.cn/) is a free online music search and download site that lets users look up tracks across multiple Chinese music platforms, including NetEase, QQ Music, Kugou, Kuwo, Migu, and Qianqian. 

JBSouMusicClient is designed for downloading music from the platform above, with a focus on searching and downloading 320 kbps MP3 audio files.

The following table summarizes all music platforms currently supported by JBSouMusicClient via JBSou,

| Source (EN)             | Source (CN)                        | Official Websites                     | `allowed_music_sources`      |
| -----------------       | -------------------                | -----------------------------------   | -------------------          |
| Tencent (QQ Music)      | QQ音乐                             | https://y.qq.com                      | `qq`                         |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 | `netease`                    |
| Kuwo                    | 酷我音乐                           | https://www.kuwo.cn                   | `kuwo`                       |
| Kugou                   | 酷狗音乐                           | https://www.kugou.com/                | `kugou`                      |

Using JBSouMusicClient is simple: just pip install musicdl. No additional tools like ffmpeg or N_m3u8DL-RE are required.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m JBSouMusicClient`

- Restrict Music Sources and Number of Results

  `musicdl -m JBSouMusicClient -i "{'JBSouMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['qq', 'netease', 'kugou']}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['JBSouMusicClient'])
  music_client.startcmdui()
  ```

- Restrict Music Sources and Number of Results

  ```python
  from musicdl import musicdl

  # allowed_music_sources can be set to any subset (i.e., any combination) of ['qq', 'netease', 'kuwo', 'kugou']
  init_music_clients_cfg = {'JBSouMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['qq', 'netease', 'kugou']}}
  music_client = musicdl.MusicClient(music_sources=['JBSouMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

(3) Screenshots of Running Results

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/jbsouscreenshot.png" width="600"/>
  </div>
</div>
<br />

#### MP3JuiceMusicClient

[MP3Juice](https://mp3juice.co/) is a free online music search and download platform that lets users find tracks across multiple sources and save them as MP3 or MP4 files without sign-up or extra software.

For music downloads from the platform above, MP3JuiceMusicClient is the go-to option.

The following table details the music platforms currently accessible through MP3JuiceMusicClient via MP3Juice,

| Source (EN)             | Source (CN)                        | Official Websites                     |
| -----------------       | -------------------                | -----------------------------------   |
| SoundCloud              | 声云                               | https://soundcloud.com/discover       |
| YouTube Music           | 油管音乐                           | https://music.youtube.com             |

MP3JuiceMusicClient doesn’t rely on external CLI tools like ffmpeg or N_m3u8DL-RE. Once you install musicdl, it’s ready to use.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m MP3JuiceMusicClient`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['MP3JuiceMusicClient'])
  music_client.startcmdui()
  ```

#### MyFreeMP3MusicClient

[MyFreeMP3](https://www.myfreemp3.com.cn/) is a free online music search and download site that lets users look up songs from multiple sources and download high-quality audio through a simple web interface.

If you're looking to download music from the aforementioned platform, MyFreeMP3MusicClient is the way to go.

The table below outlines the music platforms currently supported by MyFreeMP3MusicClient through MyFreeMP3,

| Source (EN)             | Source (CN)                        | Official Websites                     |
| -----------------       | -------------------                | -----------------------------------   |
| Quark Cloud Disk        | 夸克网盘                           | https://pan.quark.cn/list#/list/all   |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 |

No extra setup is needed for MyFreeMP3MusicClient — just install musicdl with pip and it will work out of the box.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m MyFreeMP3MusicClient -i "{'MyFreeMP3MusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MyFreeMP3MusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['MyFreeMP3MusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### TuneHubMusicClient

[TuneHub](https://tunehub.sayqz.com/docs) is a music parsing API platform that lets developers search and retrieve playable links from multiple music services through a unified interface.

Music from the platform above can be downloaded using TuneHubMusicClient.

The following table shows all music platforms that TuneHubMusicClient currently supports via TuneHub,

| Source (EN)             | Source (CN)                        | Official Websites                     | `allowed_music_sources`      |
| -----------------       | -------------------                | -----------------------------------   | -------------------          |
| Tencent (QQ Music)      | QQ音乐                             | https://y.qq.com                      | `qq`                         |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 | `netease`                    |
| Kuwo                    | 酷我音乐                           | https://www.kuwo.cn                   | `kuwo`                       |

To use TuneHubMusicClient, all you need is pip install musicdl. You don’t have to install ffmpeg, N_m3u8DL-RE, or any other CLI tools.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m TuneHubMusicClient`

- Restrict Music Sources and Number of Results

  `musicdl -m TuneHubMusicClient -i "{'TuneHubMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['qq', 'netease'], 'tunehub_api_key': 'YOUR_OWN_API_KEY'}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['TuneHubMusicClient'])
  music_client.startcmdui()
  ```

- Restrict Music Sources and Number of Results

  ```python
  from musicdl import musicdl

  # allowed_music_sources can be set to any subset (i.e., any combination) of ['qq', 'netease', 'kuwo']
  init_music_clients_cfg = {'TuneHubMusicClient': {'search_size_per_source': 5, 'allowed_music_sources': ['qq', 'netease'], 'tunehub_api_key': 'YOUR_OWN_API_KEY'}}
  music_client = musicdl.MusicClient(music_sources=['TuneHubMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

(3) Screenshots of Running Results

<div align="center">
  <div>
    <img src="https://github.com/CharlesPikachu/musicdl/raw/master/docs/screenshot/tunehubscreenshot.png" width="600"/>
  </div>
</div>
<br />

#### XiaoBaiMusicClient

[XiaoBai Music](https://music.90svip.cn/) is a clean, multi-platform music search webpage that lets users query songs by name, ID, or URL across NetEase, QQ Music, Kugou, Kuwo, Migu, and Qianqian Music.

For music-related operations on the platform above, XiaoBaiMusicClient provides a simple client implementation for interacting with XiaoBai Music.

The table below lists the music sources currently supported by XiaoBaiMusicClient through XiaoBai Music:

| Source (EN)             | Source (CN)                        | Official Websites                     | `allowed_music_sources`      |
| -----------------       | -------------------                | -----------------------------------   | -------------------          |
| Tencent (QQ Music)      | QQ音乐                             | https://y.qq.com                      | `qq`                         |
| NetEase Cloud Music     | 网易云音乐                         | https://music.163.com                 | `netease`                    |
| Kuwo                    | 酷我音乐                           | https://www.kuwo.cn                   | `kuwo`                       |
| Kugou                   | 酷狗音乐                           | https://www.kugou.com/                | `kugou`                      |

XiaoBaiMusicClient does not depend on external command-line tools such as ffmpeg or N_m3u8DL-RE. Once musicdl is installed, it is ready to use.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m XiaoBaiMusicClient`

- Restrict Music Sources and Number of Results

  `musicdl -m XiaoBaiMusicClient -i "{'XiaoBaiMusicClient': {'search_size_per_source': 3, 'allowed_music_sources': ['joox']}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['XiaoBaiMusicClient'])
  music_client.startcmdui()
  ```

- Restrict Music Sources and Number of Results

  ```python
  from musicdl import musicdl

  # allowed_music_sources can be set to any subset (i.e., any combination) of ['qobuz', 'joox', 'migu']
  init_music_clients_cfg = {'XiaoBaiMusicClient': {'search_size_per_source': 3, 'allowed_music_sources': ['qobuz']}}
  music_client = musicdl.MusicClient(music_sources=['XiaoBaiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

## Unofficial Download Sites / Scrapers

#### BuguyyMusicClient

[Buguyy](https://buguyy.top/) is an online music platform that lets users browse, stream, and download songs, with a focus on popular and curated tracks.

When downloading music from the platform above, BuguyyMusicClient is the tool to use.

No extra CLI tools like ffmpeg or N_m3u8DL-RE are needed. Just run pip install musicdl and start using BuguyyMusicClient right away.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m BuguyyMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m BuguyyMusicClient -i "{'BuguyyMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['BuguyyMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'BuguyyMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['BuguyyMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### FangpiMusicClient

[Fangpi.net](https://www.fangpi.net/) is a music website that offers online streaming and free MP3 downloads, along with charts, recommendations, and song collections.

FangpiMusicClient makes it easy to download music from the platform above.

FangpiMusicClient works out of the box with just pip install musicdl — no ffmpeg, no N_m3u8DL-RE, and no other CLI tools required.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m FangpiMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m FangpiMusicClient -i "{'FangpiMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['FangpiMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'FangpiMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['FangpiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### FiveSongMusicClient

[5song.xyz](https://www.5song.xyz/index.html) is a music website that offers searchable MP3 and lossless music downloads across multiple genres, artists, and curated collections.

For downloading music from the platform above, FiveSongMusicClient can be used.

Using FiveSongMusicClient does not require the installation of any additional command-line tools, such as ffmpeg or N_m3u8DL-RE. Installing musicdl via pip is sufficient for immediate use.

(1) Command-Line Usage

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  `musicdl -m FiveSongMusicClient -i "{'FiveSongMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'FiveSongMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['FiveSongMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### GequbaoMusicClient

[gequbao.com](https://www.gequbao.com/) is a music website for searching, streaming, and downloading high-quality MP3 songs, with charts, updates, and curated collections.

Downloading music from the platform above is possible with GequbaoMusicClient.

GequbaoMusicClient saves you from dealing with extra CLI dependencies like ffmpeg or N_m3u8DL-RE — a simple pip install musicdl is all it takes.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m GequbaoMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m GequbaoMusicClient -i "{'GequbaoMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['GequbaoMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'GequbaoMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['GequbaoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### GequhaiMusicClient

[gequhai.com](https://www.gequhai.com/) is a music download platform that lets users quickly search for and download high-quality MP3 songs, while also browsing charts, singers, and song bundles.

GequhaiMusicClient provides a way to download music from the platform above.

GequhaiMusicClient is truly plug-and-play: no external CLI tools such as ffmpeg or N_m3u8DL-RE are required. Just install musicdl and use it instantly.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m GequhaiMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m GequhaiMusicClient -i "{'GequhaiMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['GequhaiMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'GequhaiMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['GequhaiMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### HTQYYMusicClient

[htqyy.com](http://www.htqyy.com/) is a light music platform focused on instrumental, relaxing, and background music, offering online listening, recommendations, and MP3 downloads.

You may use HTQYYMusicClient to download music from the platform above.

There is no need to set up external command-line tools like ffmpeg or N_m3u8DL-RE when using HTQYYMusicClient. A single pip install musicdl is enough.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m HTQYYMusicClient`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['HTQYYMusicClient'])
  music_client.startcmdui()
  ```

#### ITingWaMusicClient

[itingwa.com](https://www.itingwa.com/) is a Chinese community-driven pure-music website where users can discover, stream, download, recommend, and discuss instrumental tracks, albums, and radio content.

ITingWaMusicClient provides built-in support for downloading tracks from iTingWa.

ITingWaMusicClient does not require external command-line tools such as ffmpeg or N_m3u8DL-RE. Simply install musicdl with pip, and you’re ready to go.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m ITingWaMusicClient`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['ITingWaMusicClient'])
  music_client.startcmdui()
  ```

#### KKWSMusicClient

[kkws.cc](https://www.kkws.cc/) is a lossless music sharing website that provides free MP3 and high-quality music downloads, including trending songs and curated music collections.

KKWSMusicClient allows us to download music from the platform above.

KKWSMusicClient now works without requiring extra CLI tools like ffmpeg or N_m3u8DL-RE. After installing musicdl with pip, it is ready to use straight away.

(1) Command-Line Usage

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  `musicdl -m KKWSMusicClient -i "{'KKWSMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'KKWSMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['KKWSMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### LivePOOMusicClient

[livepoo.cn](https://www.livepoo.cn/) is a music download website that offers free MP3 and lossless songs, with categories such as trending tracks, classic songs, DJ music, and regional music.

To get music from the platform above, we can rely on LivePOOMusicClient.

LivePOOMusicClient operates without reliance on supplementary CLI tools, including ffmpeg and N_m3u8DL-RE. Installation of musicdl via pip alone enables out-of-the-box usage.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m LivePOOMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m LivePOOMusicClient -i "{'LivePOOMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['LivePOOMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'LivePOOMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['LivePOOMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### LiziYYMusicClient

[liziyy.top](https://liziyy.top/) is a free music search and sharing platform where users can discover songs, view lyrics, and access available MP3 and lossless audio resources.

To retrieve music from the platform above, we can use LiziYYMusicClient.

LiziYYMusicClient works without additional command-line tools such as FFmpeg or N_m3u8DL-RE; installing musicdl via pip is sufficient for out-of-the-box use.

(1) Command-Line Usage

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  `musicdl -m LiziYYMusicClient -i "{'LiziYYMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'LiziYYMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['LiziYYMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### MituMusicClient

[qqmp3.vip](https://www.qqmp3.vip/) is an online music player that offers free streaming and high-quality downloads in formats such as MP3, FLAC, and WAV.

We can download songs from the platform above through MituMusicClient.

No extra setup. No external CLI tools. Just pip install musicdl and MituMusicClient is ready to use.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m MituMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m MituMusicClient -i "{'MituMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['MituMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MituMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['MituMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### MGMP3MusicClient

[mgmp3.top](https://www.mgmp3.top/) is a music resource platform distinguished by its convenient search experience and flexible download options, including both packaged archives and individual MP3 links.

Songs from the platform above can be downloaded using MGMP3MusicClient.

No extra setup or external CLI tools are required; simply install musicdl via pip, and MGMP3MusicClient is ready to use.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m MGMP3MusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m MGMP3MusicClient -i "{'MGMP3MusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['MGMP3MusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'MGMP3MusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['MGMP3MusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### SgogoMusicClient

[sgogo.com](https://www.sgogo.com/) is a streamlined music discovery platform offering fast song and artist search, online previews, lyrics, detailed track information, and curated music resources in one place.

SgogoMusicClient enables direct downloading of songs available on the platform above.

Getting started is straightforward: install musicdl with pip, and SgogoMusicClient works immediately without any additional configuration or third-party command-line tools.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m SgogoMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m SgogoMusicClient -i "{'SgogoMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['SgogoMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'SgogoMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['SgogoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### TwoT58MusicClient

[2t58.com](https://www.2t58.com/) is a music portal featuring charts, artists, playlists, albums, radio, MV content, and free MP3 downloads.

TwoT58MusicClient is available for downloading music from the platform above.

TwoT58MusicClient is designed for hassle-free use: no additional CLI tools like ffmpeg or N_m3u8DL-RE are needed, and a simple pip install musicdl gets everything ready.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m TwoT58MusicClient`

- If It Fails, Try Capturing and Adding the Website’s Cookies

  `musicdl -m TwoT58MusicClient -i "{'TwoT58MusicClient': {'default_search_cookies': 'Hm_tf_hx9umupwu8o=1766942296; 9be49c0fcbd87e6a36f944af3f638e63=701e0362d41fe970a431ab4e7e0a8260; server_name_session=8e658a40df8491e40010dc3307caacde; Hm_lvt_hx9umupwu8o=1775811750,1776490879; Hm_lpvt_hx9umupwu8o=1776492031'}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['TwoT58MusicClient'])
  music_client.startcmdui()
  ```

- If It Fails, Try Capturing and Adding the Website’s Cookies

  ```python
  from musicdl import musicdl
  
  cookies_with_str_or_dict_format = 'Hm_tf_hx9umupwu8o=1766942296; 9be49c0fcbd87e6a36f944af3f638e63=701e0362d41fe970a431ab4e7e0a8260; server_name_session=8e658a40df8491e40010dc3307caacde; Hm_lvt_hx9umupwu8o=1775811750,1776490879; Hm_lpvt_hx9umupwu8o=1776492031'
  init_music_clients_cfg = {
    'TwoT58MusicClient': {
        'default_search_cookies': cookies_with_str_or_dict_format,
    }
  }
  music_client = musicdl.MusicClient(music_sources=['TwoT58MusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### XiagebaMusicClient

[xiageba.liumingye.cn](https://xiageba.liumingye.cn/) is a music aggregation platform for searching, streaming, and finding high-quality MP3 and lossless FLAC tracks shared across the web.

Music from the platform mentioned above can be accessed using XiagebaMusicClient.

XiagebaMusicClient does not rely on external command-line utilities such as FFmpeg or N_m3u8DL-RE. After installing musicdl with pip, it can be used directly without any additional setup.

(1) Command-Line Usage

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  `musicdl -m XiagebaMusicClient -i "{'XiagebaMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Configure Quark Drive Cookies to Search for and Download High-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'XiagebaMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['XiagebaMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### XMFWAVMusicClient

[xmfwav.com](https://www.xmfwav.com/) is a streamlined music platform known for its extensive song library, fast search, online playback, and high-quality lossless FLAC/APE downloads.

XMFWAVMusicClient provides seamless access to music downloads from the platform above, with no external CLI tooling required.

Unlike workflows that rely on utilities such as ffmpeg or N_m3u8DL-RE, XMFWAVMusicClient works out of the box with a simple pip install musicdl.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m XMFWAVMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m XMFWAVMusicClient -i "{'XMFWAVMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['XMFWAVMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'XMFWAVMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['XMFWAVMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### YinyuedaoMusicClient

[1mp3.top](https://1mp3.top/) is a music download website that provides free MP3 and lossless tracks, searchable song pages, and bundled music collections.

Music downloads from the platform above can be handled by YinyuedaoMusicClient.

You don’t need to install any extra tools like ffmpeg or N_m3u8DL-RE to use YinyuedaoMusicClient — just pip install musicdl and you’re good to go.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m YinyuedaoMusicClient`

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  `musicdl -m YinyuedaoMusicClient -i "{'YinyuedaoMusicClient': {'quark_parser_config': {'cookies': 'Your Quark Drive Login Cookies'}}}"`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['YinyuedaoMusicClient'])
  music_client.startcmdui()
  ```

- Configure Quark Drive Cookies to Search for and Download Higher-Quality Music Files

  ```python
  from musicdl import musicdl
  
  your_quark_drive_login_cookies_with_str_or_dict_format = ''
  init_music_clients_cfg = {
    'YinyuedaoMusicClient': {'quark_parser_config': {'cookies': your_quark_drive_login_cookies_with_str_or_dict_format}},
  }
  music_client = musicdl.MusicClient(music_sources=['YinyuedaoMusicClient'], init_music_clients_cfg=init_music_clients_cfg)
  music_client.startcmdui()
  ```

#### ZhuolinMusicClient

[music.zhuolin.wang](https://music.zhuolin.wang/) is an online music service for searching, playing, and downloading VIP tracks, with synced lyrics and playlist synchronization features.

To fetch music from the platform above, we can use ZhuolinMusicClient.

ZhuolinMusicClient works right out of the box. No ffmpeg, no N_m3u8DL-RE, and no other CLI tools needed — just install musicdl with pip.

(1) Command-Line Usage

- Search for and Download Playable Music Files from Websites

  `musicdl -m ZhuolinMusicClient`

(2) Invoke It in Python

- Search for and Download Playable Music Files from Websites

  ```python
  from musicdl import musicdl

  music_client = musicdl.MusicClient(music_sources=['ZhuolinMusicClient'])
  music_client.startcmdui()
  ```

