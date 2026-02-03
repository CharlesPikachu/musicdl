'''
Function:
    Implementation of HLSDownloader
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import time
import math
import m3u8
import base64
import shutil
import hashlib
import requests
import threading
import concurrent.futures as cf
from pathlib import Path
from .misc import touchdir
from .logger import LoggerHandle
from urllib.parse import urljoin
from dataclasses import dataclass
from rich.progress import Progress
from typing import Optional, Dict, Any, Tuple, List, Union, Callable
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''SegmentJob'''
@dataclass(frozen=True)
class SegmentJob:
    index: int
    uri: str
    byterange: Optional[str]
    key_method: Optional[str]
    key_uri: Optional[str]
    key_iv: Optional[str]
    keyformat: Optional[str]
    media_sequence: int
    map_uri: Optional[str]
    map_byterange: Optional[str]


'''HLSDownloader'''
class HLSDownloader:
    def __init__(self, output_dir: str = "downloads", proxies: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None, timeout: Tuple[float, float] = (10.0, 30.0), logger_handle: LoggerHandle = None,
                 verify_tls: bool = True, concurrency: int = 16, max_retries: int = 8, backoff_base: float = 0.6, backoff_cap: float = 10.0, chunk_size: int = 1024 * 256, strict_key_length: bool = False, disable_print: bool = False, request_overrides: dict = None):
        # work dir
        self.output_dir = output_dir
        touchdir(self.output_dir)
        # logger
        self.logger_handle = logger_handle
        self.disable_print = disable_print
        # http requests
        self.proxies = proxies or {}
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.chunk_size = int(chunk_size)
        self.backoff_cap = float(backoff_cap)
        self.backoff_base = float(backoff_base)
        self.concurrency = max(1, int(concurrency))
        self.max_retries = max(1, int(max_retries))
        self.strict_key_length = bool(strict_key_length)
        self.request_overrides = request_overrides or {}
        # threading
        self._tls = threading.local()
        self._key_cache: Dict[str, bytes] = {}
        self._key_cache_lock = threading.Lock()
    '''download'''
    def download(self, m3u8_url: str, output_path: str, quality: Union[str, int, Callable[[List[Dict[str, Any]]], int]] = "best", keep_segments: bool = False, temp_subdir: Optional[str] = None, progress: Progress = None, progress_id: int = 0) -> str:
        master_or_media = self._loadm3u8(m3u8_url)
        if master_or_media.is_variant:
            variant_url = self._selectvariant(master_or_media, quality)
            self.logger_handle.info(f"Selected variant: {variant_url}", disable_print=self.disable_print)
            playlist = self._loadm3u8(variant_url)
        else:
            playlist = master_or_media
        jobs, global_init_map = self._buildjobs(playlist)
        temp_folder, global_init_path = os.path.join(self.output_dir, temp_subdir or f".hls_tmp_{self._safenamefromurl(m3u8_url)}"), None
        touchdir(temp_folder)
        if global_init_map:
            global_init_path = os.path.join(temp_folder, "_global_init.bin")
            if not self._fileok(global_init_path): self._atomicwrite(global_init_path, self._fetchbytes(global_init_map["uri"], global_init_map.get("byterange")))
        seg_paths = self._downloadallsegments(jobs, temp_folder, progress=progress, progress_id=progress_id)
        touchdir(os.path.dirname(os.path.abspath(output_path)) or ".")
        self._mergefiles(global_init_path, seg_paths, output_path)
        if not keep_segments: shutil.rmtree(temp_folder, ignore_errors=True)
        return output_path
    '''_getsession'''
    def _getsession(self) -> requests.Session:
        sess = getattr(self._tls, "session", None)
        if sess is None:
            sess = requests.Session()
            sess.headers.update(self.headers)
            if self.cookies: sess.cookies.update(self.cookies)
            self._tls.session = sess
        return sess
    '''_request'''
    def _request(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, stream: bool = False, **kwargs) -> requests.Response:
        kwargs.update(copy.deepcopy(self.request_overrides))
        sess, last_exc = self._getsession(), None
        hdrs = dict(self.headers)
        if headers: hdrs.update(headers)
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = sess.request(method=method, url=url, headers=hdrs, proxies=self.proxies, timeout=self.timeout, verify=self.verify_tls, stream=stream, **kwargs)
                if resp.status_code in (429, 500, 502, 503, 504): resp.close(); raise requests.HTTPError(f"HTTP {resp.status_code} for {url}")
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_exc = e
                t = min(self.backoff_cap, self.backoff_base * (2 ** (attempt - 1)))
                t = t + (0.1 * t * (0.5 - (time.time() % 1)))
                time.sleep(max(0.0, t))
        raise RuntimeError(f"Request failed after retries: {url}\nLast error: {last_exc}")
    '''_gettext'''
    def _gettext(self, url: str) -> str:
        resp = self._request(url, stream=False)
        return resp.text
    '''_getbytes'''
    def _getbytes(self, url: str, headers: Optional[Dict[str, str]] = None) -> bytes:
        resp = self._request(url, headers=headers, stream=True)
        chunks = []
        for c in resp.iter_content(chunk_size=self.chunk_size):
            if c: chunks.append(c)
        resp.close()
        return b"".join(chunks)
    '''_fetchbytes'''
    def _fetchbytes(self, url: str, byterange: Optional[str]) -> bytes:
        headers = {}
        if byterange:
            length, offset = self._parsebyterange(byterange)
            headers["Range"] = f"bytes={offset}-{offset + length - 1}"
        return self._getbytes(url, headers=headers)
    '''_loadm3u8'''
    def _loadm3u8(self, url: str) -> m3u8.M3U8:
        text = self._gettext(url)
        return m3u8.loads(text, uri=url)
    '''_selectvariant'''
    def _selectvariant(self, master: m3u8.M3U8, quality: Union[str, int, Callable[[List[Dict[str, Any]]], int]]) -> str:
        variants, bw_func = [], lambda v: int(v.get("average_bandwidth") or v.get("bandwidth") or 0)
        for i, p in enumerate(master.playlists or []):
            si = getattr(p, "stream_info", None)
            variants.append({
                "index": i, "absolute_uri": getattr(p, "absolute_uri", None) or urljoin(master.base_uri or master.uri, p.uri), "uri": p.uri, "bandwidth": getattr(si, "bandwidth", None) if si else None,
                "average_bandwidth": getattr(si, "average_bandwidth", None) if si else None, "resolution": getattr(si, "resolution", None) if si else None, "codecs": getattr(si, "codecs", None) if si else None,
                "frame_rate": getattr(si, "frame_rate", None) if si else None,
            })
        if not variants: raise ValueError("Master playlist has no variants.")
        if callable(quality): idx = int(quality(variants)); idx = max(0, min(idx, len(variants) - 1)); return variants[idx]["absolute_uri"]
        if isinstance(quality, str):
            q = quality.lower().strip()
            if q == "best":
                chosen = max(variants, key=bw_func)
            elif q == "lowest":
                chosen = min(variants, key=bw_func)
            else:
                m = re.search(r"(\d+)", q)
                if m: target = int(m.group(1)); chosen = min(variants, key=lambda v: abs(bw_func(v) - target))
                else: chosen = max(variants, key=bw_func)
        else:
            target = int(quality)
            chosen = min(variants, key=lambda v: abs(bw_func(v) - target))
        return chosen["absolute_uri"]
    '''_buildjobs'''
    def _buildjobs(self, playlist: m3u8.M3U8) -> Tuple[List[SegmentJob], Optional[Dict[str, Any]]]:
        media_seq = int(getattr(playlist, "media_sequence", 0) or 0)
        global_init, seg_map = None, getattr(playlist, "segment_map", None)
        if seg_map:
            try: sm0 = seg_map[0]; global_init = {"uri": getattr(sm0, "absolute_uri", None) or urljoin(playlist.base_uri, sm0.uri), "byterange": getattr(sm0, "byterange", None)}
            except Exception: global_init = None
        jobs: List[SegmentJob] = []
        session_keys = getattr(playlist, "session_keys", None) or []
        fallback_session_key, last_key_obj = session_keys[-1] if session_keys else None, None
        for i, seg in enumerate(playlist.segments or []):
            seg_uri, key_obj = getattr(seg, "absolute_uri", None) or urljoin(playlist.base_uri, seg.uri), getattr(seg, "key", None) or last_key_obj or fallback_session_key
            if getattr(seg, "key", None) is not None: last_key_obj = getattr(seg, "key", None)
            key_method, key_uri, key_iv, keyformat = (getattr(key_obj, k, None) for k in ("method", "uri", "iv", "keyformat")) if key_obj else (None, None, None, None)
            key_uri_abs = (key_uri if key_uri and (key_uri.startswith("data:") or key_uri.startswith("skd://")) else (urljoin(playlist.base_uri, key_uri) if key_uri else None))
            init_section = getattr(seg, "init_section", None)
            map_uri, map_byterange = ((getattr(init_section, "absolute_uri", None) or (urljoin(playlist.base_uri, getattr(init_section, "uri", "")) if getattr(init_section, "uri", None) else None)), getattr(init_section, "byterange", None)) if init_section is not None else (None, None)
            jobs.append(SegmentJob(index=i, uri=seg_uri, byterange=getattr(seg, "byterange", None), key_method=key_method, key_uri=key_uri_abs, key_iv=key_iv, keyformat=keyformat, media_sequence=media_seq, map_uri=map_uri, map_byterange=map_byterange))
        return jobs, global_init
    '''_downloadallsegments'''
    def _downloadallsegments(self, jobs: List[SegmentJob], temp_folder: str, progress: Progress, progress_id: int) -> List[str]:
        progress.update(progress_id, description=f"HLSDownloader._downloadallsegments >>> completed (0/{len(jobs)})", total=len(jobs), kind='hls')
        byterange_cursor: Dict[str, int] = {}; seg_paths: List[Optional[str]] = [None] * len(jobs)
        init_cache: Dict[str, str] = {}; init_inflight: Dict[str, threading.Event] = {}; init_cache_lock = threading.Lock()
        def _ensureinitsection(map_uri: str, map_byterange: Optional[str]) -> bytes:
            key = f"{map_uri}|{map_byterange or ''}"
            with init_cache_lock:
                cached = init_cache.get(key)
                if cached and self._fileok(cached): return Path(cached).read_bytes()
                leader = (evt := init_inflight.get(key)) is None; evt = init_inflight[key] = threading.Event() if leader else evt
            if not leader:
                evt.wait()
                with init_cache_lock: cached = init_cache.get(key)
                return Path(cached).read_bytes() if cached and self._fileok(cached) else (_ for _ in ()).throw(RuntimeError(f"init_section download failed: {key}"))
            try:
                data = self._fetchbytes(map_uri, map_byterange)
                path = os.path.join(temp_folder, f"_initsec_{abs(hash(key)) & 0xffffffff:08x}.bin")
                self._atomicwrite(path, data)
                with init_cache_lock: init_cache[key] = path
                return data
            finally:
                with init_cache_lock: (evt := init_inflight.pop(key, None)) and evt.set()
        def _worker(job: SegmentJob) -> Tuple[int, str]:
            seg_path = os.path.join(temp_folder, f"seg_{job.index:06d}.bin")
            if self._fileok(seg_path): return job.index, seg_path
            prepend = _ensureinitsection(job.map_uri, job.map_byterange) if job.map_uri else b""
            eff_byterange = self._normalizebyterange(job.uri, job.byterange, byterange_cursor) if job.byterange else job.byterange
            data = self._fetchandmaybedecrypt(job, eff_byterange)
            self._atomicwrite(seg_path, prepend + data)
            return job.index, seg_path
        exceptions: List[Exception] = []
        with cf.ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            futures = [ex.submit(_worker, j) for j in jobs]
            for fut in cf.as_completed(futures):
                try:
                    idx, path = fut.result()
                    seg_paths[idx] = path
                except Exception as e:
                    exceptions.append(e)
                finally:
                    progress.advance(progress_id, 1)
                    num_downloaded_segs = int(progress.tasks[progress_id].completed)
                    progress.update(progress_id, description=f"HLSDownloader._downloadallsegments >>> completed ({num_downloaded_segs}/{len(jobs)})")
        if exceptions: raise exceptions[0]
        return [p for p in seg_paths if p is not None]
    '''_fetchandmaybedecrypt'''
    def _fetchandmaybedecrypt(self, job: SegmentJob, eff_byterange: Optional[str]) -> bytes:
        method_raw, keyformat = (job.key_method or "").strip(), (job.keyformat or "").strip().lower()
        if not method_raw or method_raw.upper() == "NONE": return self._fetchbytes(job.uri, eff_byterange)
        if keyformat and keyformat not in ("identity",): raise NotImplementedError(f"Unsupported KEYFORMAT={job.keyformat} (likely DRM).")
        method = method_raw.upper().replace("_", "-")
        dec_mode = self._classifyencryptionmethod(method)
        if dec_mode in ("DRM", "UNSUPPORTED"): raise NotImplementedError(f"Unsupported encryption method: {method_raw}")
        if not job.key_uri: raise RuntimeError(f"Encrypted segment missing key URI at seg {job.index}")
        key, base_iv = self._prepareaeskey(method, self._getkeybytes(job.key_uri)), self._deriveiv(job.key_iv, job.media_sequence + job.index)
        if not eff_byterange: ciphertext = self._fetchbytes(job.uri, None); return self._decryptwhole(ciphertext, dec_mode, key, base_iv)
        length, offset = self._parsebyterange(eff_byterange)
        block, end = 16, offset + length
        aligned_start, aligned_end = (offset // block) * block, int(math.ceil(end / block) * block)
        if dec_mode == "CBC":
            fetch_start, drop = ((aligned_start - block, offset - aligned_start + block) if aligned_start > 0 else (aligned_start, offset - aligned_start)); fetch_len = aligned_end - fetch_start; fetch_range = f"{fetch_len}@{fetch_start}"
            ciphertext = self._fetchbytes(job.uri, fetch_range)
            iv = (b"\x00" * 16) if fetch_start > 0 else base_iv
            plaintext = self._aescbcdecrypt(ciphertext, key, iv)
            return plaintext[drop: drop+length]
        else:
            fetch_start, drop, fetch_len, fetch_range = aligned_start, offset - aligned_start, aligned_end - aligned_start, f"{aligned_end - aligned_start}@{aligned_start}"
            ciphertext = self._fetchbytes(job.uri, fetch_range)
            block_index = fetch_start // block
            iv_int = int.from_bytes(base_iv, "big")
            adj_iv = ((iv_int + block_index) % (1 << 128)).to_bytes(16, "big")
            plaintext = self._aesctrcrypt(ciphertext, key, adj_iv)
            return plaintext[drop: drop+length]
    '''_decryptwhole'''
    def _decryptwhole(self, ciphertext: bytes, dec_mode: str, key: bytes, iv: bytes) -> bytes:
        if dec_mode == "CBC": return self._aescbcdecrypt(ciphertext, key, iv)
        if dec_mode == "CTR": return self._aesctrcrypt(ciphertext, key, iv)
        raise NotImplementedError(f"decrypt mode {dec_mode} not supported")
    '''_classifyencryptionmethod'''
    def _classifyencryptionmethod(self, method: str) -> str:
        m = method.strip().upper()
        if m in ("AES-128", "AES-128-CBC", "AES-CBC", "CBC"): return "CBC"
        if m in ("AES-CTR", "AES-128-CTR", "AES-192-CTR", "AES-256-CTR"): return "CTR"
        if m.startswith("SAMPLE-AES") or "SKD" in m: return "DRM"
        return "UNSUPPORTED"
    '''_getkeybytes'''
    def _getkeybytes(self, key_uri: str) -> bytes:
        if key_uri.startswith("data:"):
            if "base64," in key_uri: b64 = key_uri.split("base64,", 1)[1]; return base64.b64decode(b64)
            if "," in key_uri: raw = key_uri.split(",", 1)[1]; return raw.encode("utf-8", errors="ignore")
            raise ValueError("Unsupported data: key URI")
        if key_uri.startswith("skd://"): raise NotImplementedError("skd:// indicates DRM (FairPlay). Not supported.")
        with self._key_cache_lock:
            if key_uri in self._key_cache: return self._key_cache[key_uri]
        b = self._getbytes(key_uri)
        with self._key_cache_lock: self._key_cache[key_uri] = b
        return b
    '''_decodekeyguess'''
    def _decodekeyguess(self, key_bytes: bytes) -> bytes:
        b = key_bytes.strip()
        if b"\x00" in b: return b
        b2 = b
        if b2.lower().startswith(b"0x"): b2 = b2[2:]
        if re.fullmatch(rb"[0-9a-fA-F]+", b2) and len(b2) in (32, 48, 64):
            try: return bytes.fromhex(b2.decode("ascii"))
            except Exception: pass
        if re.fullmatch(rb"[A-Za-z0-9+/=\r\n]+", b) and (len(b) % 4 == 0):
            try:
                dec = base64.b64decode(b, validate=False)
                if len(dec) in (16, 24, 32): return dec
            except Exception:
                pass
        return b
    '''_expectedkeylen'''
    def _expectedkeylen(self, method: str) -> int:
        m = method.upper()
        if "256" in m: return 32
        if "192" in m: return 24
        return 16
    '''_prepareaeskey'''
    def _prepareaeskey(self, method: str, key_bytes: bytes) -> bytes:
        k = self._decodekeyguess(key_bytes)
        want = self._expectedkeylen(method)
        if len(k) == want: return k
        if self.strict_key_length: raise ValueError(f"Bad key length for {method}: got {len(k)} bytes, expected {want}")
        self.logger_handle.warning(f"Key length mismatch for {method}: got {len(k)}, expected {want}. Best-effort fix.", disable_print=self.disable_print)
        if len(k) > want: return k[:want]
        return (k + b"\x00" * want)[:want]
    '''_deriveiv'''
    def _deriveiv(self, iv_str: Optional[str], seq_num: int) -> bytes:
        if not iv_str: return seq_num.to_bytes(16, byteorder="big", signed=False)
        s = str(iv_str).strip().lower()
        if s.startswith("0x"): s = s[2:]
        try: iv = bytes.fromhex(s)
        except Exception: iv = s.encode("utf-8", errors="ignore")
        if len(iv) < 16: iv = (b"\x00" * (16 - len(iv))) + iv
        if len(iv) > 16: iv = iv[-16:]
        return iv
    '''_aescbcdecrypt'''
    def _aescbcdecrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        if len(ciphertext) % 16 != 0: raise ValueError(f"CBC ciphertext length not multiple of 16: {len(ciphertext)} bytes")
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        dec = cipher.decryptor()
        return dec.update(ciphertext) + dec.finalize()
    '''_aesctrcrypt'''
    def _aesctrcrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        dec = cipher.decryptor()
        return dec.update(data) + dec.finalize()
    '''_parsebyterange'''
    def _parsebyterange(self, s: str) -> Tuple[int, int]:
        s = s.strip()
        if "@" in s: a, b = s.split("@", 1); return int(a), int(b)
        raise ValueError(f"BYTERANGE missing offset: {s}")
    '''_normalizebyterange'''
    def _normalizebyterange(self, uri: str, byterange: str, cursor: Dict[str, int]) -> str:
        s = byterange.strip()
        if "@" in s: length, offset = s.split("@", 1); length_i, offset_i = int(length), int(offset); cursor[uri] = offset_i + length_i; return f"{length_i}@{offset_i}"
        length_i = int(s)
        prev = cursor.get(uri, 0)
        cursor[uri] = prev + length_i
        return f"{length_i}@{prev}"
    '''_mergefiles'''
    def _mergefiles(self, global_init_path: Optional[str], seg_paths: List[str], output_path: str) -> None:
        tmp_out = output_path + ".part"
        with open(tmp_out, "wb") as out:
            if global_init_path and self._fileok(global_init_path):
                with open(global_init_path, "rb") as fp: shutil.copyfileobj(fp, out, length=1024 * 1024)
            for p in seg_paths:
                with open(p, "rb") as fp: shutil.copyfileobj(fp, out, length=1024 * 1024)
        os.replace(tmp_out, output_path)
    '''_safenamefromurl'''
    def _safenamefromurl(self, url: str, max_len: int = 20) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:max_len]
    '''_fileok'''
    def _fileok(self, path: str) -> bool:
        return os.path.exists(path) and os.path.getsize(path) > 0
    '''_atomicwrite'''
    def _atomicwrite(self, path: str, data: bytes) -> None:
        touchdir(os.path.dirname(os.path.abspath(path)) or ".")
        pid, tid = os.getpid(), threading.get_ident()
        tmp, last = f"{path}.tmp.{pid}.{tid}.{time.time_ns()}", None
        with open(tmp, "wb") as fp:
            fp.write(data)
            try: fp.flush(); os.fsync(fp.fileno())
            except Exception: pass
        for i in range(12):
            try: os.replace(tmp, path); return
            except PermissionError as e: last = e; time.sleep(min(0.5, 0.03 * (2 ** i)))
            except OSError as e: last = e; time.sleep(min(0.5, 0.03 * (2 ** i)))
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception:
            pass
        raise last