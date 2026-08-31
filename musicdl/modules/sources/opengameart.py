'''
Function:
    Implementation of OpenGameArtMusicClient: https://opengameart.org/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import copy
import hashlib
from pathlib import Path
from typing import Callable
from contextlib import suppress
from rich.progress import Progress
from bs4 import BeautifulSoup, Tag
from typing_extensions import Unpack
from .base import BaseMusicClient, BaseMusicClientKwargs
from itertools import dropwhile, islice, takewhile, chain
from ..utils import legalizestring, usesearchheaderscookies, SongInfo
from urllib.parse import urlencode, urljoin, urlparse, unquote, parse_qs


'''OpenGameArtMusicClient'''
class OpenGameArtMusicClient(BaseMusicClient):
    source = 'OpenGameArtMusicClient'
    BASE_URL = "https://opengameart.org"
    MUSIC_TYPE_ID = "12"
    ARCHIVE_EXTS = {".zip", ".7z", ".rar"}
    LOSSLESS_EXTS = {".flac", ".wav", ".aiff", ".aif"}
    LOSSY_EXTS = {".opus", ".ogg", ".oga", ".m4a", ".mp3"}
    AUDIO_EXTS = {".flac", ".wav", ".aiff", ".aif", ".opus", ".ogg", ".oga", ".m4a", ".mp3", ".mid", ".midi", ".mod", ".xm", ".it", ".s3m"}
    BASE_QUALITY_SCORE = {".flac": 100, ".wav": 95, ".aiff": 95, ".aif": 95, ".opus": 82, ".ogg": 78, ".oga": 78, ".m4a": 74, ".mp3": 70, ".xm": 45, ".it": 43, ".mod": 40, ".s3m": 40, ".mid": 25, ".midi": 25, ".zip": 10, ".7z": 10, ".rar": 10}
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(OpenGameArtMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 OGA-Music-Search/1.0"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 OGA-Music-Search/1.0"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"keys": keyword, "field_art_type_tid[0]": OpenGameArtMusicClient.MUSIC_TYPE_ID, "items_per_page": 24, "page": 0}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], max(self.search_size_per_page, 24), 0, f"{OpenGameArtMusicClient.BASE_URL}/art-search-advanced?"
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['items_per_page'] = page_size
            page_rule['page'] = int(count // page_size)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> SongInfo:
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (page_url := search_result.get('page_url'))): return song_info
        # some necessary lambda function definitions
        normalize_func = lambda text: re.sub(r"\s+", " ", text or "").strip()
        value_after_func = lambda lines, label: (lambda label_lower: next((lines[i + 1] for i, line in enumerate(lines) if str(line).lower() == label_lower and i + 1 < len(lines)), ""))(str(label).lower())
        block_after_func = lambda lines, label, stop_labels: (lambda label_lower, stop_set: list(dict.fromkeys(line for line in takewhile(lambda line: str(line).lower() == label_lower or str(line).lower() not in stop_set, islice(dropwhile(lambda line: str(line).lower() != label_lower, lines), 1, None)) if str(line).lower() != label_lower and line not in {"*", "Image"})))(str(label).lower(), {str(x).lower() for x in stop_labels})
        is_transcoded_preview_func = lambda filename: (lambda filename: filename.endswith(".mp3.ogg") or filename.endswith(".mp3.oga") or ".mp3.ogg" in filename or ".mp3.oga" in filename)(str(filename).lower())
        file_quality_key_func = lambda f: (lambda ext, filename, size: (OpenGameArtMusicClient.BASE_QUALITY_SCORE.get(ext, 0) - (25 if is_transcoded_preview_func(filename) else 0) + (8 if ext == ".mp3" else 0) + (20 if ext in OpenGameArtMusicClient.LOSSLESS_EXTS else 0), size))(f["ext"], (f.get("filename") or f.get("name") or "").lower(), f.get("size") or 0)
        choose_best_file_func = lambda files: None if not files else (lambda audio_files: max(audio_files if audio_files else files, key=file_quality_key_func))([f for f in files if f["ext"] in OpenGameArtMusicClient.AUDIO_EXTS])
        build_file_item_func = lambda file_url, link_text: (lambda parsed: None if "/sites/default/files/" not in parsed.path or "/styles/" in parsed.path else (lambda filename: (lambda ext: None if ext not in OpenGameArtMusicClient.AUDIO_EXTS and ext not in OpenGameArtMusicClient.ARCHIVE_EXTS else (lambda name: {"name": name or filename, "filename": filename, "url": file_url, "ext": ext, "is_transcoded_preview": is_transcoded_preview_func(filename)})(re.sub(r"^Image:\s*", "", normalize_func(link_text) or filename, flags=re.I).strip()))(Path(filename).suffix.lower()))(os.path.basename(unquote(parsed.path))))(urlparse(str(file_url)))
        find_files_func = lambda soup, page_url: (lambda seen: [item for item in chain((build_file_item_func(urljoin(page_url, a["href"]), a.get_text(" ", strip=True)) for a in soup.find_all("a", href=True)), (build_file_item_func(match.group(0), "") for match in re.finditer(r'https?://[^"\']+/sites/default/files/[^"\']+', str(soup)))) if item and not (item["url"] in seen or seen.add(item["url"]))])(set())
        extract_file_id_from_download_url_func = lambda download_url: (lambda parsed: hashlib.sha1(f"{parsed.netloc}{parsed.path}".encode("utf-8")).hexdigest()[:12])(urlparse(str(download_url)))
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get(page_url, **request_overrides)).raise_for_status(); soup = BeautifulSoup(resp.text, "lxml")
            lines = [normalize_func(x) for x in soup.get_text("\n", strip=True).splitlines() if normalize_func(x)]
            download_result = {
                'song_name': search_result["song_name"], 'artist': value_after_func(lines, "Author:"), 'licenses': block_after_func(lines, "License(s):", stop_labels=["Collections:", "Favorites:", "Preview:", "File(s):", "Tags:", "Copyright/Attribution Notice:", "Log in or register to post comments"]), 'collections': block_after_func(lines, "Collections:", stop_labels=["Favorites:", "Preview:", "File(s):", "Tags:", "Copyright/Attribution Notice:", "Log in or register to post comments"]) or [''], 
                'tags': block_after_func(lines, "Tags:", stop_labels=["License(s):", "Collections:", "Favorites:", "Preview:", "File(s):", "Copyright/Attribution Notice:", "Log in or register to post comments"]), 'attribution_lines': block_after_func(lines, "Copyright/Attribution Notice:", stop_labels=["File(s):", "Log in or register to post comments", "Comments"]), 'files': find_files_func(soup, page_url),
            }
            download_url_status: dict = self.audio_link_tester.test(url=choose_best_file_func(download_result['files'])['url'], request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result['song_name']), singers=legalizestring(download_result.get('artist')), album=legalizestring(download_result['collections'][0]), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=extract_file_id_from_download_url_func(download_url_status['download_url']), duration_s=None, duration='-:-:-', lyric=None, cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, seen, normalize_func = request_overrides or {}, set(), lambda text: re.sub(r"\s+", " ", text or "").strip()
        find_heading_func: Callable[[BeautifulSoup | Tag, str], Tag | None] = lambda soup, heading_text: next((tag for tag in soup.find_all(["h1", "h2", "h3"]) if normalize_func(tag.get_text(" ", strip=True)).lower() == heading_text.strip().lower()), None)
        page_no, search_result_idx = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0])) + 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            search_result_tags: list[BeautifulSoup | Tag] = find_heading_func(BeautifulSoup(resp.text, 'lxml'), "Search Art").find_all_next()
            for search_result_idx, search_result_tag in enumerate(search_result_tags):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --invalid search tags
                if search_result_tag.name in {"h1", "h2", "h3"} and normalize_func(search_result_tag.get_text(" ", strip=True)).lower() in {"pages", "chat with us!", "active forum topics - (view more)"}: break
                if search_result_tag.name != "a" or not search_result_tag.get("href") or not (title := normalize_func(search_result_tag.get_text(" ", strip=True))) or title.lower() in {"image", "preview", "first", "previous", "next", "last", "log in", "register", "read more"}: continue
                if (parsed := urlparse(urljoin(OpenGameArtMusicClient.BASE_URL, search_result_tag["href"]))).netloc != "opengameart.org" or not parsed.path.startswith("/content/") or parsed.path in {"/content/faq"}: continue
                if (page_url := OpenGameArtMusicClient.BASE_URL + parsed.path) in seen: continue
                seen.add(page_url); search_result = {"song_name": title, "page_url": page_url}
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: song_infos = song_infos[:self.search_size_per_page]; break
            # --update progress
            progress.update(task_id, description=f'{self.source}._search >>> {search_result_idx+1} search results processed on page {page_no}')
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos