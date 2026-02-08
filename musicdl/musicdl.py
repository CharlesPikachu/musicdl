'''
Function:
    Implementation of MusicClient
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import sys
import copy
import click
import json_repair
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
if __name__ == '__main__':
    from __init__ import __version__
    from modules import BuildMusicClient, LoggerHandle, MusicClientBuilder, smarttrunctable, colorize, printfullline, cursorpickintable
    from modules.utils.lddc_adapter import fetch_lyrics_via_lddc
else:
    try:
        from .__init__ import __version__
        from .modules import BuildMusicClient, LoggerHandle, MusicClientBuilder, smarttrunctable, colorize, printfullline
        from .modules.utils.lddc_adapter import fetch_lyrics_via_lddc
    except ImportError:
        from __init__ import __version__
        from modules import BuildMusicClient, LoggerHandle, MusicClientBuilder, smarttrunctable, colorize, printfullline
        from modules.utils.lddc_adapter import fetch_lyrics_via_lddc


'''settings'''
BASIC_INFO = '''Function: Music Downloader v%s
Author: Zhenchao Jin
WeChat Official Account (微信公众号): Charles_pikachu (Charles的皮卡丘)
Instructions:
    Enter r: reinitialize the program (i.e., return to the main menu)
    Enter q: exit the program
    Select songs to download:
        Use ↑/↓ to move the cursor within the table
        Press <space> to toggle selection
        Press a to select all, i to invert selection
        Press <enter> to confirm and start downloading
        Press Esc or q to cancel selection
Music Files Save Path:
    %s (root dir is the current directory if using relative path).'''
DEFAULT_MUSIC_SOURCES = ['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'QianqianMusicClient']
'''SUPPORTED_MUSIC_SOURCES'''
SUPPORTED_MUSIC_SOURCES = list(MusicClientBuilder.REGISTERED_MODULES.keys())


'''MusicClient'''
class MusicClient():
    def __init__(self, music_sources: list = [], init_music_clients_cfg: dict = {}, clients_threadings: dict = {}, requests_overrides: dict = {}, search_rules: dict = {}, logger_handle = None):
        # assert
        assert isinstance(music_sources, list) and isinstance(init_music_clients_cfg, dict) and isinstance(clients_threadings, dict) and \
               isinstance(requests_overrides, dict) and isinstance(search_rules, dict)
        music_sources, init_music_clients_cfg, clients_threadings, requests_overrides, search_rules = \
            copy.deepcopy(music_sources), copy.deepcopy(init_music_clients_cfg), copy.deepcopy(clients_threadings), copy.deepcopy(requests_overrides), copy.deepcopy(search_rules)
        # set attributes
        self.work_dirs = {}
        self.search_rules = search_rules
        self.clients_threadings = clients_threadings
        self.requests_overrides = requests_overrides
        self.music_sources = music_sources if music_sources else DEFAULT_MUSIC_SOURCES
        self.music_sources = list(set(self.music_sources))
        # init
        self.logger_handle = logger_handle if logger_handle else LoggerHandle()
        self.music_clients = dict()
        for music_source in self.music_sources:
            if music_source not in MusicClientBuilder.REGISTERED_MODULES.keys(): continue
            init_music_client_cfg = {
                'search_size_per_source': 5, 'auto_set_proxies': False, 'random_update_ua': False, 'max_retries': 3, 'maintain_session': False, 'logger_handle': self.logger_handle, 
                'disable_print': True, 'work_dir': 'musicdl_outputs', 'freeproxy_settings': None, 'default_search_cookies': {}, 'default_download_cookies': {}, 'type': music_source,
                'search_size_per_page': 10, 'strict_limit_search_size_per_page': True, 'quark_parser_config': {'cookies': 'your_cookies_with_str_or_dict_format','freeproxy_settings': None, 'enable_download_curl_cffi': False,
                'enable_parse_curl_cffi': False, 'enable_search_curl_cffi': False}
            }
            if music_source in {'GDStudioMusicClient', 'XimalayaMusicClient', 'LizhiMusicClient', 'QingtingMusicClient'}: init_music_client_cfg['search_size_per_source'] = 3
            init_music_client_cfg.update(init_music_clients_cfg.get(music_source, {}))
            self.music_clients[music_source] = BuildMusicClient(module_cfg=init_music_client_cfg)
            self.work_dirs[music_source] = init_music_client_cfg['work_dir']
            if music_source not in self.clients_threadings: self.clients_threadings[music_source] = 5 if music_source not in {'GDStudioMusicClient'} else 10
            if music_source not in self.requests_overrides: self.requests_overrides[music_source] = {}
            if music_source not in self.search_rules: self.search_rules[music_source] = {}
    '''printbasicinfo'''
    def printbasicinfo(self):
        printfullline(ch='-')
        print(BASIC_INFO % (__version__, ', '.join([f'"{v} for {k}"' for k, v in self.work_dirs.items()])))
        printfullline(ch='-')
    '''printandselectsearchresults'''
    def printandselectsearchresults(self, search_results: dict):
        print_titles, print_items, song_infos, row_ids, song_info_pointer = ['ID', 'Singers', 'Songname', 'Filesize', 'Duration', 'Album', 'Source'], [], {}, [], 0
        for _, per_search_results in search_results.items():
            for search_result in per_search_results:
                song_info_pointer += 1
                song_infos[str(song_info_pointer)] = search_result
                row_ids.append(str(song_info_pointer))
                print_items.append([
                    colorize(str(song_info_pointer), 'number'), colorize(search_result['singers'][:12] + '...' if len(search_result['singers']) > 15 else search_result['singers'], 'singer'), 
                    search_result['song_name'], search_result['file_size'] if search_result['ext'] not in {'flac', 'wav', 'alac', 'ape', 'wv', 'tta', 'dsf', 'dff'} else colorize(search_result['file_size'], 'flac'),
                    search_result['duration'], search_result['album'], colorize('|'.join([s.upper() for s in [search_result['source'].removesuffix('MusicClient'), search_result['root_source']] if s]), 'highlight'),
                ])
        print(smarttrunctable(headers=print_titles, rows=print_items, no_trunc_cols=[0, 1, 3, 4, 6]))
        picked_ids = cursorpickintable(print_titles, print_items, row_ids, no_trunc_cols=[0, 1, 3, 4, 6])
        id2row = dict(zip(row_ids, print_items))
        selected_rows = [id2row[i] for i in picked_ids if i in id2row]
        if selected_rows: print("\nSelected songs:\n"); print(smarttrunctable(headers=print_titles, rows=selected_rows, no_trunc_cols=[0, 1, 3, 4, 6]))
        else: print("\nNo songs selected.\n")
        selected_song_infos = [song_infos[i] for i in picked_ids if i in song_infos]
        return selected_song_infos
    '''startcmdui'''
    def startcmdui(self):
        while True:
            self.printbasicinfo()
            user_input_keyword = self.processinputs('Please enter keywords to search for songs: ')
            search_results = self.search(keyword=user_input_keyword)
            selected_song_infos, final_selected_song_infos = self.printandselectsearchresults(search_results=search_results), []
            for song_info in selected_song_infos:
                if song_info.episodes: final_selected_song_infos.extend(self.printandselectsearchresults({song_info.source: song_info.episodes}))
                else: final_selected_song_infos.append(song_info)
            self.download(final_selected_song_infos)
    '''search'''
    def search(self, keyword):
        self.logger_handle.info(f'Searching {colorize(keyword, "highlight")} From {colorize("|".join(self.music_sources), "highlight")}')
        max_workers, main_progress_lock = min(len(self.music_sources), 10), Lock()
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"ALL sources >>> completed (0/0)", total=0)
            def _search(ms):
                try:
                    return ms, self.music_clients[ms].search(
                        keyword=keyword, num_threadings=self.clients_threadings[ms], request_overrides=self.requests_overrides[ms], rule=self.search_rules[ms], 
                        main_process_context=main_process_context, main_progress_id=main_progress_id, main_progress_lock=main_progress_lock,
                    )
                except Exception as err:
                    self.logger_handle.error(f'MusicClient.{ms}.search >>> {keyword} (Error: {err})')
                    return ms, []
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                return dict(ex.map(_search, self.music_sources))
    '''download'''
    def download(self, song_infos: list[dict], progress_handler=None):
        classified_song_infos = {}
        for song_info in song_infos:
            if song_info['source'] in classified_song_infos:
                classified_song_infos[song_info['source']].append(song_info)
            else:
                classified_song_infos[song_info['source']] = [song_info]
        all_downloaded_infos = []
        for source, source_song_infos in classified_song_infos.items():
            downloaded_songs = self.music_clients[source].download(
                song_infos=source_song_infos, 
                num_threadings=self.clients_threadings[source], 
                request_overrides=self.requests_overrides[source],
                progress_handler=progress_handler
            )
            
            # Fetch lyrics via LDDC for downloaded songs
            for song_info in downloaded_songs:
                try:
                   self.logger_handle.info(f'Fetching lyrics via LDDC for {song_info.song_name}...')
                   lyrics = fetch_lyrics_via_lddc(song_info, embed=True)
                   if lyrics:
                       self.logger_handle.info(f'LDDC: Successfully fetched lyrics for {song_info.song_name}')
                       song_info.lyric = lyrics
                       # Re-save to txt or update properties if needed by downstream
                       # Note: download() has already saved txt and embedded lyrics (if available previously)
                       # We need to update the txt file and maybe re-embed if fetch_lyrics_via_lddc didn't fully handle it or for consistency.
                       # fetch_lyrics_via_lddc with embed=True handles embedding in the audio file directly via bridge.
                       # We should update the info file.
                       try:
                           import os
                           txt_path = os.path.splitext(song_info.save_path)[0] + ".txt"
                           if os.path.exists(txt_path):
                               # Read existing lines
                               with open(txt_path, 'r', encoding='utf-8') as f:
                                   lines = f.readlines()
                               # Rewrite with new lyrics
                               with open(txt_path, 'w', encoding='utf-8') as f:
                                   in_lyrics = False
                                   for line in lines:
                                       if 'Lyrics' in line and '-'*20 in line:
                                           f.write(line)
                                           f.write(f'{lyrics}\n')
                                           in_lyrics = True
                                       elif in_lyrics and '='*50 in line:
                                           in_lyrics = False
                                           f.write(line)
                                       elif not in_lyrics:
                                           f.write(line)
                       except Exception as e:
                           self.logger_handle.warning(f'Failed to update txt info with LDDC lyrics: {e}')
                   else:
                       self.logger_handle.info(f'LDDC: No lyrics found for {song_info.song_name}')
                except Exception as e:
                    self.logger_handle.error(f'LDDC Lyric Fetch Error for {song_info.song_name}: {e}')
            
            all_downloaded_infos.extend(downloaded_songs)
    '''parseplaylist'''
    def parseplaylist(self, playlist_url):
        song_infos = []
        for source in list(self.music_clients.keys()):
            try:
                self.logger_handle.info(f'MusicClient.parseplaylist >>> Trying source: {source}')
                result = self.music_clients[source].parseplaylist(playlist_url)
                self.logger_handle.info(f'MusicClient.parseplaylist >>> {source} returned {len(result) if result else 0} songs')
                if result and len(result) > 0:
                    song_infos = result
                    self.logger_handle.info(f'MusicClient.parseplaylist >>> Successfully parsed {len(song_infos)} songs from {source}')
                    break  # CRITICAL: Break after first successful parse
            except Exception as e:
                self.logger_handle.error(f'MusicClient.parseplaylist >>> {source} failed: {e}')
                continue
        self.logger_handle.info(f'MusicClient.parseplaylist >>> Final result: {len(song_infos)} songs')
        return (song_infos or [])
    '''processinputs'''
    def processinputs(self, input_tip='', prefix: str = '\n'):
        # accept user inputs
        user_input = input(prefix + input_tip)
        # quit
        if user_input.lower() == 'q': self.logger_handle.info('Goodbye — thanks for using musicdl; come back anytime!'); sys.exit()
        # restart
        elif user_input.lower() == 'r': self.startcmdui()
        # common inputs
        else: return user_input
    '''str'''
    def __str__(self):
        return 'Welcome to use musicdl!\nYou can visit https://github.com/CharlesPikachu/musicdl for more details.'


'''MusicClientCMD'''
@click.command()
@click.version_option()
@click.option(
    '-k', '--keyword', default=None, help='The keywords for the music search. If left empty, an interactive terminal will open automatically.', type=str, show_default=True,
)
@click.option(
    '-p', '--playlist-url', '--playlist_url', default=None, help='Given a playlist URL, e.g., "https://music.163.com/#/playlist?id=7583298906", musicdl automatically parses the playlist and downloads all tracks in it.', type=str, show_default=True,
)
@click.option(
    '-m', '--music-sources', '--music_sources', default=','.join(DEFAULT_MUSIC_SOURCES), help='The music search and download sources.', type=str, show_default=True, 
)
@click.option(
    '-i', '--init-music-clients-cfg', '--init_music_clients_cfg', default=None, help='Config such as `work_dir` for each music client as a JSON string.', type=str, show_default=True,
)
@click.option(
    '-r', '--requests-overrides', '--requests_overrides', default=None, help='Requests.get / Requests.post kwargs such as `headers` and `proxies` for each music client as a JSON string.', type=str, show_default=True,
)
@click.option(
    '-c', '--clients-threadings', '--clients_threadings', default=None, help='Number of threads used for each music client as a JSON string.', type=str, show_default=True,
)
@click.option(
    '-s', '--search-rules', '--search_rules', default=None, help='Search rules for each music client as a JSON string.', type=str, show_default=True,
)
def MusicClientCMD(keyword: str, playlist_url: str, music_sources: str, init_music_clients_cfg: str, requests_overrides: str, clients_threadings: str, search_rules: str):
    # parse playlist url
    assert keyword is None or playlist_url is None, '"playlist_url" and "keyword" could be set simultaneously'
    # load json string
    safe_load_func = lambda s: (json_repair.loads(s) or {}) if s else {}
    init_music_clients_cfg = safe_load_func(init_music_clients_cfg)
    requests_overrides = safe_load_func(requests_overrides)
    clients_threadings = safe_load_func(clients_threadings)
    search_rules = safe_load_func(search_rules)
    # instance music client
    music_sources = music_sources.replace(' ', '').split(',')
    music_client = MusicClient(music_sources=music_sources, init_music_clients_cfg=init_music_clients_cfg, clients_threadings=clients_threadings, requests_overrides=requests_overrides, search_rules=search_rules)
    # switch according to keyword and playlist_url
    if (keyword is None) and (playlist_url is None):
        music_client.startcmdui()
    elif playlist_url is not None:
        print(music_client)
        song_infos = music_client.parseplaylist(playlist_url)
        music_client.download(song_infos=song_infos)
    else:
        print(music_client)
        search_results = music_client.search(keyword=keyword)
        selected_song_infos, final_selected_song_infos = music_client.printandselectsearchresults(search_results=search_results), []
        for song_info in selected_song_infos:
            if song_info.episodes: final_selected_song_infos.extend(music_client.printandselectsearchresults({song_info.source: song_info.episodes}))
            else: final_selected_song_infos.append(song_info)
        music_client.download(song_infos=final_selected_song_infos)


'''tests'''
if __name__ == '__main__':
    music_client = MusicClient()
    music_client.startcmdui()