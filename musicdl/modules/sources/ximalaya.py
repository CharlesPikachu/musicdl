'''
Function:
    Implementation of XimalayaMusicClient: https://www.ximalaya.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import time
import copy
import base64
import binascii
import json_repair
from Crypto.Cipher import AES
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import byte2mb, resp2json, isvalidresp, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, AudioLinkTester, WhisperLRC


'''XimalayaMusicClient'''
class XimalayaMusicClient(BaseMusicClient):
    source = 'XimalayaMusicClient'
    def __init__(self, **kwargs):
        super(XimalayaMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://api.cenguigui.cn/",
            "Connection": "keep-alive",
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_decrypturl'''
    def _decrypturl(self, ciphertext: str):
        if not ciphertext: return ciphertext
        key = binascii.unhexlify("aaad3e4fd540b0f79dca95606e72bf93")
        ciphertext = base64.urlsafe_b64decode(ciphertext + "=" * (4 - len(ciphertext) % 4))
        cipher = AES.new(key, AES.MODE_ECB)
        plaintext = cipher.decrypt(ciphertext)
        plaintext = re.sub(r"[^\x20-\x7E]", "", plaintext.decode("utf-8"))
        return plaintext
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'msg': keyword, 'n': '', 'num': self.search_size_per_source, 'type': 'json'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.cenguigui.cn/api/music/dg_ximalayamusic.php?'
        search_urls, page_size, count = [], self.search_size_per_source, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['num'] = self.search_size_per_source
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']
            for search_result in search_results:
                # --download results
                if 'trackId' not in search_result:
                    continue
                download_result, download_url, ext, file_size, duration = {}, "", "m4a", "0", "0"
                # ----try http://mobile.ximalaya.com/v1/track/ca/playpage/{trackId} first
                resp = self.get(f'http://mobile.ximalaya.com/v1/track/ca/playpage/{search_result["trackId"]}', **request_overrides)
                if isvalidresp(resp):
                    download_result: dict = json_repair.loads(resp.text)
                    track_info = safeextractfromdict(download_result, ['trackInfo'], {})
                    qualities = [
                        ('playHqSize', 'playPathHq'), ('playPathAacv164Size', 'playPathAacv164'), ('downloadAacSize', 'downloadAacUrl'), ('playUrl64Size', 'playUrl64'), 
                        ('playUrl32Size', 'playUrl32'), ('downloadSize', 'downloadUrl'), ('playPathAacv224Size', 'playPathAacv224'),
                    ]
                    for quality in qualities:
                        file_size, download_url = track_info.get(quality[0], '0'), track_info.get(quality[1], '')
                        if not download_url: continue
                        ext = download_url.split('.')[-1].split('?')[0]
                        duration = seconds2hms(track_info.get('duration', '0'))
                        download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                        if download_url_status['ok']: break
                    if not download_url or not download_url_status['ok']:
                        download_result, download_url, ext, file_size, duration = {}, "", "m4a", "0", "0"
                # ----try https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/ second
                if not download_result or not download_url:
                    params = {"device": "web", "trackId": search_result["trackId"], "trackQualityLevel": 2}
                    resp = self.get(f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}", params=params, **request_overrides)
                    download_result = resp2json(resp)
                    track_info = safeextractfromdict(download_result, ['trackInfo'], {})
                    for encrypted_url in sorted(safeextractfromdict(track_info, ['playUrlList'], []), key=lambda x: int(x['fileSize']), reverse=True):
                        download_url = self._decrypturl(encrypted_url.get('url', ''))
                        if not download_url: continue
                        ext = download_url.split('.')[-1].split('?')[0]
                        duration = seconds2hms(track_info.get('duration', '0'))
                        download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                        if download_url_status['ok']: break
                    if not download_url or not download_url_status['ok']:
                        download_result, download_url, ext, file_size, duration = {}, "", "m4a", "0", "0"
                # ----try https://api.cenguigui.cn/api/music/dg_ximalayamusic.php finally
                if (not download_result or not download_url) and ('n' in search_result):
                    params = {'msg': keyword, 'n': search_result['n'], 'num': self.search_size_per_source, 'type': 'json'}
                    resp = self.get('https://api.cenguigui.cn/api/music/dg_ximalayamusic.php', params=params, **request_overrides)
                    download_result = resp2json(resp)
                    download_url = download_result.get('url', '')
                    if download_url:
                        try:
                            download_result_suppl = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).probe(download_url, request_overrides)
                        except:
                            download_result_suppl = {'download_url': download_url, 'file_size': '0', 'ext': 'NULL'}
                        if download_result_suppl['ext'] == 'NULL':
                            download_result_suppl['ext'] = download_url.split('.')[-1].split('?')[0]
                        download_result['download_result_suppl'] = download_result_suppl
                        download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                        ext, file_size = download_result_suppl['ext'], download_result_suppl['file_size']
                        duration = '-:-:-'
                    else:
                        download_result, download_url, ext, file_size, duration = {}, "", "m4a", "0", "0"
                # ----parse more infos
                if not download_url: continue
                if not download_url_status['ok']: continue
                if byte2mb(file_size) == 'NULL' and 'download_result_suppl' not in download_result:
                    try:
                        download_result_suppl = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).probe(download_url, request_overrides)
                        ext, file_size = download_result_suppl['ext'], download_result_suppl['file_size']
                        download_result['download_result_suppl'] = download_result_suppl
                    except:
                        continue
                else:
                    file_size = byte2mb(file_size)
                # --lyric results
                try:
                    if os.environ.get('ENABLE_WHISPERLRC', 'False').lower() == 'true':
                        lyric_result = WhisperLRC(model_size_or_path='small').fromurl(
                            download_url, headers=self.default_download_headers, cookies=self.default_download_cookies, request_overrides=request_overrides
                        )
                        lyric = lyric_result['lyric']
                    else:
                        lyric_result, lyric = dict(), 'NULL'
                except:
                    lyric_result, lyric = dict(), 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, 
                    lyric=lyric, duration=duration, song_name=legalizestring(search_result.get('title', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(search_result.get('Nickname', 'NULL'), replace_null_string='NULL'), 
                    album=legalizestring(search_result.get('album_title', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['trackId'],
                )
                # --append to song_infos
                song_infos.append(song_info)
            # --update progress
            progress.advance(progress_id, 1)
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos