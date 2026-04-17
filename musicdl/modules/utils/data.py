'''
Function:
    Implementation of SongInfo
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import os
import uuid
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
from pathvalidate import sanitize_filepath
from dataclasses import dataclass, field, fields


'''SongInfo'''
@dataclass
class SongInfo:
    # raw data replied by requested APIs
    raw_data: Dict[str, Any] = field(default_factory=dict)
    # from which music client
    source: Optional[str] = None
    root_source: Optional[str] = None
    # song meta infos
    song_name: Optional[str] = None
    singers: Optional[str] = None
    album: Optional[str] = None
    ext: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_size: Optional[str] = None
    duration_s: Optional[int] = None
    duration: Optional[str] = None
    bitrate: Optional[int] = None
    codec: Optional[str] = None
    samplerate: Optional[int] = None
    channels: Optional[int] = None
    # lyric
    lyric: Optional[str] = None
    # cover
    cover_url: Optional[str] = None
    # episodes, each item in episodes is SongInfo object, used by FM site like XimalayaMusicClient
    episodes: Optional[list[SongInfo]] = None
    # download url related variables
    download_url: Optional[Any] = None
    download_url_status: Optional[Any] = None
    default_download_headers: Dict[str, Any] = field(default_factory=dict)
    default_download_cookies: Dict[str, Any] = field(default_factory=dict)
    downloaded_contents: Optional[Any] = None
    chunk_size: Optional[int] = 1024 * 1024
    protocol: Optional[str] = 'HTTP' # should be in {'HTTP', 'HLS'}
    @property
    def with_valid_download_url(self) -> bool:
        from ..utils.tidalutils import StreamUrl as TidalStreamObj
        from ..utils.youtubeutils import Stream as YouTubeStreamObj
        from ..utils.appleutils import DownloadItem as AppleStreamObj
        if self.episodes: return all([eps.with_valid_download_url for eps in self.episodes])
        is_valid_download_url_format = self.download_url.startswith('http') if isinstance(self.download_url, str) else isinstance(self.download_url, (TidalStreamObj, YouTubeStreamObj, AppleStreamObj))
        is_downloadable, with_downloaded_contents = isinstance(self.download_url_status, dict) and self.download_url_status.get('ok'), bool(self.downloaded_contents)
        return bool(with_downloaded_contents or (is_valid_download_url_format and is_downloadable))
    # save info
    work_dir: Optional[str] = './'
    _save_path: Optional[str] = None
    @property
    def save_path(self) -> str:
        if self._save_path is not None: return self.legalizepathlength(self._save_path)
        sp, same_name_file_idx = os.path.join(self.work_dir, f"{self.song_name} - {self.identifier}.{self.ext.removeprefix('.')}"), 1
        while os.path.exists(sp): sp = os.path.join(self.work_dir, f"{self.song_name} - {self.identifier} ({same_name_file_idx}).{self.ext.removeprefix('.')}"); same_name_file_idx += 1
        self._save_path = sanitize_filepath(sp)
        return self.legalizepathlength(self._save_path)
    # identifier
    identifier: Optional[str] = None
    '''fieldnames'''
    @classmethod
    def fieldnames(cls) -> set[str]:
        return {f.name for f in fields(cls)}
    '''fromdict'''
    @classmethod
    def fromdict(cls, data: Dict[str, Any]) -> "SongInfo":
        filtered = {k: v for k, v in data.items() if k in cls.fieldnames()}
        if filtered.get("episodes") and isinstance(filtered["episodes"], list): filtered["episodes"] = [cls.fromdict(e) if isinstance(e, dict) else e for e in filtered["episodes"]]
        return cls(**filtered)
    '''todict'''
    def todict(self) -> Dict[str, Any]:
        converted_dict = {f.name: getattr(self, f.name) for f in fields(self)}
        if self.episodes and isinstance(self.episodes, list): converted_dict['episodes'] = [e.todict() for e in self.episodes]
        return converted_dict
    '''update'''
    def update(self, data: Dict[str, Any] = None, **kwargs: Any) -> "SongInfo":
        if data is None or not isinstance(data, dict): data = {}
        merged: Dict[str, Any] = {**data, **kwargs}
        [setattr(self, k, v) for k, v in merged.items() if k in self.fieldnames()]
        return self
    '''getitem'''
    def __getitem__(self, key: str) -> Any:
        if key not in self.fieldnames(): raise KeyError(key)
        return getattr(self, key)
    '''setitem'''
    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self.fieldnames(): raise KeyError(key)
        setattr(self, key, value)
    '''contains'''
    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self.fieldnames()
    '''get'''
    def get(self, key: str, default: Any = None) -> Any:
        if key in self.fieldnames(): return getattr(self, key)
        return default
    '''largerthan'''
    def largerthan(self, song_info: SongInfo):
        # file_size_a
        try: file_size_a = float(self.file_size.removesuffix('MB').strip())
        except Exception: file_size_a = 0.0
        if not isinstance(file_size_a, (int, float)): file_size_a = 0.0
        # file_size_b
        try: file_size_b = float(song_info.file_size.removesuffix('MB').strip())
        except Exception: file_size_b = 0.0
        if not isinstance(file_size_b, (int, float)): file_size_b = 0.0
        # compare
        return bool(file_size_a > file_size_b)
    '''legalizepathlength'''
    def legalizepathlength(self, save_path: str | Path, max_path: int = 240, keep_ext: bool = True, with_hash_suffix: bool = False):
        if (not (raw_path := str((save_path or "")).strip())) or (raw_path in {'NULL', 'null', 'None', 'none'}): return None
        (output_dir := (src_path := Path(raw_path)).parent.resolve()).mkdir(parents=True, exist_ok=True)
        ext, stem, digest = src_path.suffix if keep_ext else "", src_path.stem, hashlib.md5(str(src_path).encode("utf-8")).hexdigest()
        for hash_len in (4, 6, 8, 10, 12):
            hash_suffix = f"-{digest[:hash_len]}" if with_hash_suffix else ""
            max_stem_len = max(1, max_path - (len(str(output_dir)) + 1 + len(hash_suffix) + len(ext)))
            safe_stem = stem[:max_stem_len].rstrip(" .") or str(uuid.uuid4())[:hash_len]
            if not os.path.exists((out_path := str(output_dir / f"{safe_stem}{hash_suffix}{ext}"))): break
        return out_path