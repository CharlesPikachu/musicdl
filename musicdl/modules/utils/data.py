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
from .misc import sanitize_filepath
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, fields


'''SongInfo'''
@dataclass
class SongInfo:
    # raw data replied by requested APIs
    raw_data: Dict[str, Any] = field(default_factory=dict)
    # from which music client
    source: Optional[str] = None
    root_source: Optional[str] = None
    # song information
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
    # episodes, each item in episodes is SongInfo object, used by FM site like MissEvanMusicClient
    episodes: Optional[list[SongInfo]] = None
    # download url related variables
    download_url: Optional[Any] = None
    download_url_status: Optional[Any] = None
    default_download_headers: Dict[str, Any] = field(default_factory=dict)
    downloaded_contents: Optional[Any] = None
    chunk_size: Optional[int] = 1024 * 1024
    @property
    def with_valid_download_url(self) -> bool:
        if self.episodes: return all([eps.with_valid_download_url for eps in self.episodes])
        if isinstance(self.download_url, str): is_valid_format = self.download_url and self.download_url.startswith('http')
        else: is_valid_format = self.download_url
        is_downloadable = isinstance(self.download_url_status, dict) and self.download_url_status.get('ok')
        return bool(is_valid_format and is_downloadable)
    # save info
    work_dir: Optional[str] = './'
    _save_path: Optional[str] = None
    @property
    def save_path(self) -> str:
        if self._save_path is not None: return self._save_path
        sp, same_name_file_idx = os.path.join(self.work_dir, f"{self.song_name} - {self.identifier}.{self.ext.removeprefix('.')}"), 1
        while os.path.exists(sp):
            sp = os.path.join(self.work_dir, f"{self.song_name} - {self.identifier} ({same_name_file_idx}).{self.ext.removeprefix('.')}")
            same_name_file_idx += 1
        sp = sanitize_filepath(sp)
        self._save_path = sp
        return sp
    # identifier
    identifier: Optional[str] = None
    '''fieldnames'''
    @classmethod
    def fieldnames(cls) -> set[str]:
        return {f.name for f in fields(cls)}
    '''fromdict'''
    @classmethod
    def fromdict(cls, data: Dict[str, Any]) -> "SongInfo":
        field_names = cls.fieldnames()
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)
    '''todict'''
    def todict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}
    '''update'''
    def update(self, data: Dict[str, Any] = None, **kwargs: Any) -> "SongInfo":
        if data is None: data = {}
        merged: Dict[str, Any] = {**data, **kwargs}
        field_names = self.fieldnames()
        for k, v in merged.items():
            if k in field_names: setattr(self, k, v)
        return self
    '''getitem'''
    def __getitem__(self, key: str) -> Any:
        field_names = self.fieldnames()
        if key not in field_names: raise KeyError(key)
        return getattr(self, key)
    '''setitem'''
    def __setitem__(self, key: str, value: Any) -> None:
        field_names = self.fieldnames()
        if key not in field_names: raise KeyError(key)
        setattr(self, key, value)
    '''contains'''
    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self.fieldnames()
    '''get'''
    def get(self, key: str, default: Any = None) -> Any:
        if key in self.fieldnames(): return getattr(self, key)
        return default