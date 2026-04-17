'''
Function:
    Implementation of HLSDownloader
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import os
import re
import time
import math
import m3u8
import copy
import base64
import shutil
import requests
import tempfile
import threading
import subprocess
import concurrent.futures as cf
from pathlib import Path
from .misc import IOUtils
from .logger import LoggerHandle
from urllib.parse import urljoin
from dataclasses import dataclass
from rich.progress import Progress
from collections.abc import Iterable
from .cmd import ExtractAudioFromVideoFFmpegCommand
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''KeySpec'''
@dataclass(frozen=True)
class KeySpec:
    method: Optional[str]
    uri: Optional[str]
    iv: Optional[str]
    keyformat: Optional[str]


'''MapSpec'''
@dataclass(frozen=True)
class MapSpec:
    uri: str
    byterange: Optional[str]


'''SegmentSpec'''
@dataclass(frozen=True)
class SegmentSpec:
    index: int
    uri: str
    byterange: Optional[str]
    key: Optional[KeySpec]
    init_map: Optional[MapSpec]
    media_sequence: int


'''VariantInfo'''
@dataclass(frozen=True)
class VariantInfo:
    index: int
    uri: str
    absolute_uri: str
    bandwidth: Optional[int]
    average_bandwidth: Optional[int]
    resolution: Any
    codecs: Optional[str]
    frame_rate: Any


'''DownloadReport'''
@dataclass(frozen=True)
class DownloadReport:
    playlist_url: str
    media_playlist_url: str
    segment_count: int
    temp_dir: str
    merged_path: str
    final_path: str
    source_extension: str
    final_extension: str
    used_ffmpeg: bool
    selected_variant: Optional[VariantInfo]


'''HLSDownloader'''
class HLSDownloader:
    def __init__(self, output_dir: str = "downloads", proxies: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None, timeout: Tuple[float, float] = (10.0, 30.0), verify_tls: bool = True, concurrency: int = 16, backoff_base: float = 0.6, 
                 max_retries: int = 8, backoff_cap: float = 10.0, chunk_size: int = 1024 * 256, strict_key_length: bool = False, logger_handle: Optional[LoggerHandle] = None, disable_print: bool = False, request_overrides: Optional[Dict[str, Any]] = None, ffmpeg_path: Optional[str] = None) -> None:
        self.output_dir = os.path.abspath(output_dir); IOUtils.touchdir(self.output_dir)
        self.proxies = proxies or {}
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.concurrency = max(1, int(concurrency))
        self.max_retries = max(1, int(max_retries))
        self.backoff_base = float(backoff_base)
        self.backoff_cap = float(backoff_cap)
        self.chunk_size = int(chunk_size)
        self.strict_key_length = bool(strict_key_length)
        self.request_overrides = copy.deepcopy(request_overrides or {})
        self.logger_handle = logger_handle or LoggerHandle()
        self.disable_print = disable_print
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        self._tls = threading.local()
        self._key_cache: Dict[str, bytes] = {}
        self._key_cache_lock = threading.Lock()
        self._map_cache: Dict[str, bytes] = {}
        self._map_cache_lock = threading.Lock()
    '''download'''
    def download(self, m3u8_url: str, output_path: Optional[str] = None, quality: Union[str, int, Callable[[List[VariantInfo]], int]] = "best", keep_temp: bool = False, remux: bool = True, output_format: str = "auto", progress: Progress = None, progress_id: int = 0) -> DownloadReport:
        media_playlist, selected_variant = self.resolvemediaplaylist(self.loadm3u8(m3u8_url), m3u8_url, quality)
        if not (segments := self.buildsegmentplan(media_playlist)): raise ValueError("Playlist has no downloadable segments.")
        segment_dir = os.path.join((temp_dir := tempfile.mkdtemp(prefix="musicdl_hls_", dir=self.output_dir)), "segments"); IOUtils.touchdir(segment_dir, exist_ok=True)
        segment_paths = self.downloadsegments(segments, segment_dir, progress, progress_id); source_extension = self.guesssourceextension(segments, selected_variant)
        self.mergesegments(segments, segment_paths, (merged_path := os.path.join(temp_dir, f"merged{source_extension}")))
        final_path, used_ffmpeg, final_extension = self.finalizeoutput(merged_path=merged_path, segments=segments, selected_variant=selected_variant, requested_output_path=output_path, output_format=output_format, remux=remux)
        temp_dir_for_report = temp_dir if keep_temp else ""; (None if keep_temp else shutil.rmtree(temp_dir, ignore_errors=True))
        return DownloadReport(playlist_url=m3u8_url, media_playlist_url=getattr(media_playlist, "_source_uri", None) or m3u8_url, segment_count=len(segments), temp_dir=temp_dir_for_report, merged_path=merged_path if keep_temp else "", final_path=final_path, source_extension=source_extension, final_extension=final_extension, used_ffmpeg=used_ffmpeg, selected_variant=selected_variant)
    '''loadm3u8'''
    def loadm3u8(self, url: str) -> m3u8.M3U8:
        setattr((playlist := m3u8.loads(self.gettext(url), uri=url)), "_source_uri", url)
        return playlist
    '''resolvemediaplaylist'''
    def resolvemediaplaylist(self, playlist: m3u8.M3U8, original_url: str, quality: Union[str, int, Callable[[List[VariantInfo]], int]]) -> Tuple[m3u8.M3U8, Optional[VariantInfo]]:
        if getattr(playlist, "segments", None): return playlist, None
        if (variants := self.listvariants(playlist)): selected = self.selectvariant(variants, quality); return self.loadm3u8(selected.absolute_uri), selected
        media_entries, audio_candidates = getattr(playlist, "media", None) or [], []
        for item in media_entries:
            if getattr(item, "type", "").upper() != "AUDIO" or not (uri := getattr(item, "uri", None)): continue
            audio_candidates.append(getattr(item, "absolute_uri", None) or urljoin(playlist.base_uri or original_url, uri))
        if audio_candidates: return self.loadm3u8(audio_candidates[0]), None
        raise ValueError("Could not resolve a downloadable media playlist from the provided URL.")
    '''listvariants'''
    def listvariants(self, master: m3u8.M3U8) -> List[VariantInfo]:
        variants: List[VariantInfo] = []
        for i, playlist in enumerate(master.playlists or []):
            stream_info = getattr(playlist, "stream_info", None)
            variants.append(VariantInfo(index=i, uri=playlist.uri, absolute_uri=getattr(playlist, "absolute_uri", None) or urljoin(getattr(master, "base_uri", None) or getattr(master, "_source_uri", None) or "", playlist.uri), bandwidth=getattr(stream_info, "bandwidth", None) if stream_info else None, average_bandwidth=getattr(stream_info, "average_bandwidth", None) if stream_info else None, resolution=getattr(stream_info, "resolution", None) if stream_info else None, codecs=getattr(stream_info, "codecs", None) if stream_info else None, frame_rate=getattr(stream_info, "frame_rate", None) if stream_info else None))
        return variants
    '''selectvariant'''
    def selectvariant(self, variants: List[VariantInfo], quality: Union[str, int, Callable[[List[VariantInfo]], int]]) -> VariantInfo:
        if not variants: raise ValueError("Master playlist has no variants.")
        bandwidth_func = lambda v: int(v.average_bandwidth or v.bandwidth or 0) if isinstance(v, VariantInfo) else 0
        if callable(quality): idx = int(quality(variants)); idx = max(0, min(idx, len(variants) - 1)); return variants[idx]
        if isinstance(quality, str): return (max(variants, key=bandwidth_func) if (q := quality.lower().strip()) == "best" else min(variants, key=bandwidth_func) if q == "lowest" else min(variants, key=lambda v: abs(bandwidth_func(v) - int(q))) if q.isdigit() else min(variants, key=lambda v: abs(bandwidth_func(v) - int(m.group(1)))) if (m := re.search(r"(\d+)", q)) else max(variants, key=bandwidth_func))
        return min(variants, key=lambda v: abs(bandwidth_func(v) - int(quality)))
    '''buildsegmentplan'''
    def buildsegmentplan(self, playlist: m3u8.M3U8) -> List[SegmentSpec]:
        media_sequence, session_keys = int(getattr(playlist, "media_sequence", 0) or 0), getattr(playlist, "session_keys", None) or []
        current_key_obj, global_map_obj, segment_map = session_keys[-1] if session_keys else None, None, getattr(playlist, "segment_map", None)
        global_map_obj = next(iter(segment_map), None) if isinstance(segment_map, Iterable) and not isinstance(segment_map, (str, bytes)) else None
        current_map = self.tomapspec(playlist, global_map_obj); range_cursors: Dict[str, int] = {}; segments: List[SegmentSpec] = []
        for i, seg in enumerate(playlist.segments or []):
            key_spec = self.tokeyspec(playlist, (current_key_obj := getattr(seg, "key", None) if getattr(seg, "key", None) is not None else current_key_obj))
            if (seg_init := getattr(seg, "init_section", None)) is not None: current_map = self.tomapspec(playlist, seg_init)
            seg_uri = getattr(seg, "absolute_uri", None) or urljoin(playlist.base_uri, seg.uri)
            seg_byterange = self.resolvebyterange(uri=seg_uri, byterange=getattr(seg, "byterange", None), cursor=range_cursors)
            resolved_map = MapSpec(uri=current_map.uri, byterange=self.resolvebyterange(uri=current_map.uri, byterange=current_map.byterange, cursor=range_cursors)) if current_map is not None else None
            segments.append(SegmentSpec(index=i, uri=seg_uri, byterange=seg_byterange, key=key_spec, init_map=resolved_map, media_sequence=media_sequence))
        return segments
    '''tokeyspec'''
    def tokeyspec(self, playlist: m3u8.M3U8, key_obj: Any) -> Optional[KeySpec]:
        if key_obj is None: return None
        if (uri := getattr(key_obj, "uri", None)) and isinstance(uri, str) and not (uri.startswith("data:") or uri.startswith("skd://")): uri = urljoin(playlist.base_uri, uri)
        return KeySpec(method=getattr(key_obj, "method", None), uri=uri, iv=getattr(key_obj, "iv", None), keyformat=getattr(key_obj, "keyformat", None))
    '''tomapspec'''
    def tomapspec(self, playlist: m3u8.M3U8, map_obj: Any) -> Optional[MapSpec]:
        if map_obj is None: return None
        if not (uri := getattr(map_obj, "absolute_uri", None)):
            if not (raw_uri := getattr(map_obj, "uri", None)): return None
            uri = urljoin(playlist.base_uri, raw_uri)
        return MapSpec(uri=uri, byterange=getattr(map_obj, "byterange", None))
    '''downloadsegments'''
    def downloadsegments(self, segments: List[SegmentSpec], segment_dir: str, progress: Progress, progress_id: int) -> List[str]:
        progress.update(progress_id, description=f"HLSDownloader._downloadallsegments >>> Completed (0/{len(segments)}) Segments", total=len(segments), kind='hls')
        def worker(spec: SegmentSpec) -> Tuple[int, str]:
            output_file = os.path.join(segment_dir, f"seg_{spec.index:06d}.bin")
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0: return spec.index, output_file
            self.atomicwrite(output_file, self.downloadsegmentpayload(spec))
            return spec.index, output_file
        total = len(segments); segment_paths: List[Optional[str]] = [None] * total; exceptions: List[BaseException] = []
        with cf.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [executor.submit(worker, spec) for spec in segments]
            for future in cf.as_completed(futures):
                try: index, path = future.result(); segment_paths[index] = path
                except BaseException as exc: exceptions.append(exc)
                finally: progress.advance(progress_id, 1); progress.update(progress_id, description=f"HLSDownloader._downloadallsegments >>> Completed ({int(progress.tasks[progress_id].completed)}/{len(segments)}) Segments")
        if exceptions: raise RuntimeError(f"Segment download failed: {exceptions[0]}") from exceptions[0]
        return [p for p in segment_paths if p is not None]
    '''downloadsegmentpayload'''
    def downloadsegmentpayload(self, spec: SegmentSpec) -> bytes:
        raw = self.fetchencryptedorplainsegment(spec)
        return (raw if spec.key is None or not spec.key.method or spec.key.method.upper() == "NONE" else self.decryptsegment(spec, raw))
    '''fetchencryptedorplainsegment'''
    def fetchencryptedorplainsegment(self, spec: SegmentSpec) -> bytes:
        if spec.key is None or not spec.key.method or spec.key.method.upper() == "NONE": return self.fetchbytes(spec.uri, spec.byterange)
        if (mode := self.classifyencryptionmethod(spec.key.method)) in ("DRM", "UNSUPPORTED"): raise NotImplementedError(f"Unsupported encryption method: {spec.key.method}")
        if not spec.byterange: return self.fetchbytes(spec.uri, None)
        if mode == "CTR": length, offset = self.parsebyterange(spec.byterange); block = 16; return self.fetchbytes(spec.uri, f"{int(math.ceil((offset + length) / block) * block) - (offset // block) * block}@{(offset // block) * block}")
        length, offset = self.parsebyterange(spec.byterange); block = 16
        aligned_start = (offset // block) * block; aligned_end = int(math.ceil((offset + length) / block) * block)
        fetch_start = aligned_start - block if aligned_start > 0 else aligned_start
        return self.fetchbytes(spec.uri, f"{aligned_end - fetch_start}@{fetch_start}")
    '''decryptsegment'''
    def decryptsegment(self, spec: SegmentSpec, raw_ciphertext: bytes) -> bytes:
        assert (key_spec := spec.key) is not None
        if (keyformat := (key_spec.keyformat or "").strip().lower()) and keyformat != "identity": raise NotImplementedError(f"Unsupported KEYFORMAT={key_spec.keyformat} (likely DRM).")
        if not key_spec.uri: raise RuntimeError(f"Encrypted segment is missing key URI at index {spec.index}")
        if (mode := self.classifyencryptionmethod(key_spec.method or "")) in ("DRM", "UNSUPPORTED"): raise NotImplementedError(f"Unsupported encryption method: {key_spec.method}")
        key_bytes, base_iv = self.prepareaeskey(key_spec.method or "AES-128", self.getkeybytes(key_spec.uri)), self.deriveiv(key_spec.iv, spec.media_sequence + spec.index)
        if not spec.byterange: plaintext = self.decryptwholesegment(raw_ciphertext, mode, key_bytes, base_iv); return self.mayberemovepkcs7padding(plaintext) if mode == "CBC" else plaintext
        length, offset = self.parsebyterange(spec.byterange); block = 16; aligned_start = (offset // block) * block
        if mode == "CTR": return self.aesctrcrypt(raw_ciphertext, key_bytes, ((int.from_bytes(base_iv, "big") + aligned_start // block) % (1 << 128)).to_bytes(16, "big"))[offset - aligned_start : offset - aligned_start + length]
        iv, drop = (b"\x00" * 16, offset - aligned_start + block) if aligned_start > 0 else (base_iv, offset - aligned_start)
        return self.aescbcdecrypt(raw_ciphertext, key_bytes, iv)[drop : drop + length]
    '''mergesegments'''
    def mergesegments(self, segments: List[SegmentSpec], segment_paths: List[str], merged_path: str) -> None:
        last_map_key: Optional[str] = None
        with open(merged_path, "wb") as out:
            for spec, segment_file in zip(segments, segment_paths):
                if (init_map := spec.init_map) is not None and (map_key := f"{init_map.uri}|{init_map.byterange or ''}") != last_map_key: out.write(self.getmapbytes(init_map)); last_map_key = map_key
                with open(segment_file, "rb") as fp: shutil.copyfileobj(fp, out, length=1024 * 1024)
    '''finalizeoutput'''
    def finalizeoutput(self, merged_path: str, segments: List[SegmentSpec], selected_variant: Optional[VariantInfo], requested_output_path: Optional[str], output_format: str, remux: bool) -> Tuple[str, bool, str]:
        used_ffmpeg, target_extension = False, self.guesstargetextension(segments, selected_variant, output_format)
        destination = self.builddestinationpath(requested_output_path, merged_path, target_extension)
        if remux and self.ffmpeg_path:
            try: self.ffmpegcopyaudio(merged_path, destination); used_ffmpeg = True; return destination, used_ffmpeg, target_extension
            except Exception as exc: self.logger_handle.warning(f"ffmpeg remux failed, falling back to direct copy: {exc}", disable_print=self.disable_print)
        shutil.copyfile(merged_path, destination)
        return destination, used_ffmpeg, Path(destination).suffix.lower()
    '''guesssourceextension'''
    def guesssourceextension(self, segments: List[SegmentSpec], variant: Optional[VariantInfo]) -> str:
        if any(spec.init_map is not None for spec in segments): return ".m4a" if variant and variant.codecs and "mp4a" in variant.codecs.lower() else ".mp4"
        extensions = [Path(spec.uri).suffix.lower() for spec in segments[:10] if Path(spec.uri).suffix]
        codecs = variant.codecs.lower() if variant and variant.codecs else ""
        return ".aac" if ".aac" in extensions or ".adts" in extensions else ".mp3" if ".mp3" in extensions else ".ts" if ".ts" in extensions else ".m4a" if "mp4a" in codecs else ".mp3" if "mp3" in codecs else ".bin"
    '''guesstargetextension'''
    def guesstargetextension(self, segments: List[SegmentSpec], variant: Optional[VariantInfo], output_format: str) -> str:
        if output_format and output_format.lower() != "auto": return f'.{output_format.lower().lstrip(".")}'
        codecs = variant.codecs.lower() if variant and variant.codecs else ""
        return ".m4a" if "mp4a" in codecs else ".mp3" if "mp3" in codecs else ".opus" if "opus" in codecs else ".ogg" if "vorbis" in codecs else self.guesssourceextension(segments, variant)
    '''builddestinationpath'''
    def builddestinationpath(self, requested_output_path: Optional[str], merged_path: str, target_extension: str) -> str:
        if requested_output_path: requested = Path(requested_output_path); return str(requested if requested.suffix else requested.with_suffix(target_extension))
        return str(Path(merged_path).with_name(Path(merged_path).stem + target_extension))
    '''getsession'''
    def getsession(self) -> requests.Session:
        if (session := getattr(self._tls, "session", None)) is None: (session := requests.Session()).headers.update(self.headers); session.cookies.update(dict(self.cookies or {})); self._tls.session = session
        return session
    '''request'''
    def request(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, stream: bool = False, **kwargs: Any) -> requests.Response:
        (extra := copy.deepcopy(self.request_overrides)).update(kwargs)
        session = self.getsession(); (merged_headers := dict(self.headers)).update(headers or {}); last_error: Optional[BaseException] = None
        for attempt in range(1, self.max_retries + 1):
            try: (resp := session.request(method=method, url=url, headers=merged_headers, proxies=self.proxies, timeout=self.timeout, verify=self.verify_tls, stream=stream, **extra)).raise_for_status(); return resp
            except BaseException as exc: last_error = exc; delay = min(self.backoff_cap, self.backoff_base * (2 ** (attempt - 1))); delay += 0.1 * delay * (0.5 - (time.time() % 1)); time.sleep(max(0.0, delay))
        raise RuntimeError(f"Request failed after retries: {url}\nLast error: {last_error}")
    '''gettext'''
    def gettext(self, url: str) -> str:
        try: return (resp := self.request(url, stream=False)).text
        finally: resp.close()
    '''fetchbytes'''
    def fetchbytes(self, url: str, byterange: Optional[str]) -> bytes:
        headers: Dict[str, str] = {} if not byterange else (lambda t: {"Range": f"bytes={t[1]}-{t[1] + t[0] - 1}"})(self.parsebyterange(byterange))
        resp = self.request(url, headers=headers, stream=True)
        try: return b"".join(chunk for chunk in resp.iter_content(chunk_size=self.chunk_size) if chunk)
        finally: resp.close()
    '''getkeybytes'''
    def getkeybytes(self, key_uri: str) -> bytes:
        if key_uri.startswith("data:"): return (base64.b64decode(key_uri.split("base64,", 1)[1]) if "base64," in key_uri else key_uri.split(",", 1)[1].encode("utf-8", errors="ignore") if "," in key_uri else (_ for _ in ()).throw(ValueError("Unsupported data: key URI")))
        if key_uri.startswith("skd://"): raise NotImplementedError("skd:// indicates DRM and is not supported.")
        with self._key_cache_lock:
            if (cached := self._key_cache.get(key_uri)) is not None: return cached
        with self._key_cache_lock: self._key_cache[key_uri] = (data := self.fetchbytes(key_uri, None))
        return data
    '''getmapbytes'''
    def getmapbytes(self, map_spec: MapSpec) -> bytes:
        key = f"{map_spec.uri}|{map_spec.byterange or ''}"
        with self._map_cache_lock:
            if (cached := self._map_cache.get(key)) is not None: return cached
        data = self.fetchbytes(map_spec.uri, map_spec.byterange)
        with self._map_cache_lock: self._map_cache[key] = data
        return data
    '''classifyencryptionmethod'''
    def classifyencryptionmethod(self, method: str) -> str:
        normalized = method.strip().upper().replace("_", "-")
        if normalized in {"AES-128", "AES-128-CBC", "AES-CBC", "CBC"}: return "CBC"
        if normalized in {"AES-CTR", "AES-128-CTR", "AES-192-CTR", "AES-256-CTR"}: return "CTR"
        if normalized.startswith("SAMPLE-AES") or "SKD" in normalized: return "DRM"
        return "UNSUPPORTED"
    '''decodekeyguess'''
    def decodekeyguess(self, key_bytes: bytes) -> bytes:
        if b"\x00" in (raw := key_bytes.strip()): return raw
        if (candidate := raw).lower().startswith(b"0x"): candidate = candidate[2:]
        if re.fullmatch(rb"[0-9a-fA-F]+", candidate) and len(candidate) in {32, 48, 64}:
            try: return bytes.fromhex(candidate.decode("ascii"))
            except Exception: pass
        if re.fullmatch(rb"[A-Za-z0-9+/=\r\n]+", raw) and len(raw) % 4 == 0:
            try:
                if len((decoded := base64.b64decode(raw, validate=False))) in {16, 24, 32}: return decoded
            except Exception: pass
        return raw
    '''expectedkeylength'''
    def expectedkeylength(self, method: str) -> int:
        return 32 if "256" in (upper := method.upper()) else 24 if "192" in upper else 16
    '''prepareaeskey'''
    def prepareaeskey(self, method: str, key_bytes: bytes) -> bytes:
        if len((key := self.decodekeyguess(key_bytes))) == (expected := self.expectedkeylength(method)): return key
        if self.strict_key_length: raise ValueError(f"Bad key length for {method}: got {len(key)} bytes, expected {expected}")
        self.logger_handle.warning(f"Key length mismatch for {method}: got {len(key)}, expected {expected}. Using best-effort fix.", disable_print=self.disable_print)
        return (key[:expected] if len(key) > expected else (key + b"\x00" * expected)[:expected])
    '''deriveiv'''
    def deriveiv(self, iv_string: Optional[str], sequence_number: int) -> bytes:
        if not iv_string: return sequence_number.to_bytes(16, byteorder="big", signed=False)
        if (text := str(iv_string).strip().lower()).startswith("0x"): text = text[2:]
        try: iv = bytes.fromhex(text)
        except Exception: iv = text.encode("utf-8", errors="ignore")
        return iv.rjust(16, b"\x00")[-16:]
    '''decryptwholesegment'''
    def decryptwholesegment(self, ciphertext: bytes, mode: str, key: bytes, iv: bytes) -> bytes:
        if mode == "CBC": return self.aescbcdecrypt(ciphertext, key, iv)
        if mode == "CTR": return self.aesctrcrypt(ciphertext, key, iv)
        raise NotImplementedError(f"Unsupported decrypt mode: {mode}")
    '''aescbcdecrypt'''
    def aescbcdecrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        if len(ciphertext) % 16 != 0: raise ValueError(f"CBC ciphertext length is not a multiple of 16: {len(ciphertext)}")
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    '''aesctrcrypt'''
    def aesctrcrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        decryptor = Cipher(algorithms.AES(key), modes.CTR(iv)).decryptor()
        return decryptor.update(data) + decryptor.finalize()
    '''mayberemovepkcs7padding'''
    def mayberemovepkcs7padding(self, plaintext: bytes) -> bytes:
        if not plaintext: return plaintext
        if (pad_len := plaintext[-1]) < 1 or pad_len > 16: return plaintext
        if plaintext[-pad_len:] != bytes([pad_len]) * pad_len: return plaintext
        return plaintext[:-pad_len]
    ''''parsebyterange'''
    def parsebyterange(self, byterange: str) -> Tuple[int, int]:
        if "@" not in (text := byterange.strip()): raise ValueError(f"BYTERANGE is missing an explicit offset: {byterange}")
        length_text, offset_text = text.split("@", 1)
        return int(length_text), int(offset_text)
    '''resolvebyterange'''
    def resolvebyterange(self, uri: str, byterange: Optional[str], cursor: Dict[str, int]) -> Optional[str]:
        if not byterange or not (text := byterange.strip()): return None
        if "@" in text: length, offset = map(int, text.split("@", 1)); cursor[uri] = offset + length; return f"{length}@{offset}"
        cursor[uri] = (offset := cursor.get(uri, 0)) + (length := int(text))
        return f"{length}@{offset}"
    '''atomicwrite'''
    def atomicwrite(self, path: str, data: bytes) -> None:
        IOUtils.touchdir(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open((temp_path := f"{path}.tmp.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}"), "wb") as fp:
            fp.write(data)
            try: fp.flush(); os.fsync(fp.fileno())
            except Exception: pass
        os.replace(temp_path, path)
    '''ffmpegcopyaudio'''
    def ffmpegcopyaudio(self, input_path: str, output_path: str) -> None:
        IOUtils.touchdir(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        command = ExtractAudioFromVideoFFmpegCommand(self.ffmpeg_path).build(input_path, output_path)
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0: raise RuntimeError(completed.stderr.strip() or "ffmpeg remux failed")