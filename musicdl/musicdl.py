'''
Function:
    Implementation of MusicClient
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import sys
import click
import json_repair
if __name__ == '__main__':
    from __init__ import __version__
    from modules import BuildMusicClient, LoggerHandle, MusicClientBuilder, colorize, printtable
else:
    from .__init__ import __version__
    from .modules import BuildMusicClient, LoggerHandle, MusicClientBuilder, colorize, printtable


'''BASIC_INFO'''
BASIC_INFO = '''************************************************************
Function: Music Downloader v%s
Author: Zhenchao Jin
WeChat Official Account (微信公众号): Charles_pikachu (Charles的皮卡丘)
Instructions:
    Enter r: reinitialize the program (i.e., return to the main menu)
    Enter q: exit the program
    Download multiple songs: when selecting songs to download, enter "1,2,5" to download songs 1, 2, and 5 simultaneously
Music Files Save Path:
    Inside the %s folder (root dir is the current directory if using relative path).
************************************************************'''


'''MusicClient'''
class MusicClient():
    def __init__(self, music_sources: list = [], init_music_clients_cfg: dict = {}, clients_threadings: dict = {}, requests_overrides: dict = {}, search_rules: dict = {}):
        # assert
        assert isinstance(music_sources, list) and isinstance(init_music_clients_cfg, dict) and isinstance(clients_threadings, dict) and \
               isinstance(requests_overrides, dict) and isinstance(search_rules, dict)
        # set attributes
        self.work_dirs = {}
        self.search_rules = search_rules
        self.clients_threadings = clients_threadings
        self.requests_overrides = requests_overrides
        self.music_sources = music_sources if music_sources else ['MiguMusicClient', 'NeteaseMusicClient', 'KuwoMusicClient', 'KugouMusicClient', 'QQMusicClient', 'QianqianMusicClient']
        # init
        self.logger_handle, self.music_clients = LoggerHandle(), dict()
        for music_source in self.music_sources:
            if music_source not in MusicClientBuilder.REGISTERED_MODULES.keys(): continue
            init_music_client_cfg = {
                'search_size_per_source': 5, 'auto_set_proxies': False, 'random_update_ua': False, 'max_retries': 5,
                'maintain_session': False, 'logger_handle': self.logger_handle, 'disable_print': True, 'work_dir': 'musicdl_outputs',
                'proxy_sources': None, 'default_search_cookies': {}, 'default_download_cookies': {}, 'type': music_source
            }
            init_music_client_cfg.update(init_music_clients_cfg.get(music_source, {}))
            self.music_clients[music_source] = BuildMusicClient(module_cfg=init_music_client_cfg)
            self.work_dirs[music_source] = init_music_client_cfg['work_dir']
            if music_source not in self.clients_threadings:
                self.clients_threadings[music_source] = 5
            if music_source not in self.requests_overrides:
                self.requests_overrides[music_source] = {}
            if music_source not in self.search_rules:
                self.search_rules[music_source] = {}
    '''startcmdui'''
    def startcmdui(self):
        while True:
            print(BASIC_INFO % (__version__, self.work_dirs))
            # process user inputs, music file search
            user_input_keyword = self.processinputs('Please enter keywords to search for songs: ')
            search_results = self.search(keyword=user_input_keyword)
            # print search_results
            print_titles, print_items, song_infos, song_info_pointer = ['ID', 'Singers', 'Songname', 'Filesize', 'Duration', 'Album', 'Source'], [], {}, 0
            for music_source, per_search_results in search_results.items():
                for search_result in per_search_results:
                    song_info_pointer += 1
                    song_infos[str(song_info_pointer)] = search_result
                    print_items.append([
                        colorize(str(song_info_pointer), 'number'), colorize(search_result['singers'], 'singer'), search_result['song_name'], 
                        search_result['file_size'] if search_result['ext'] not in ['flac', 'ogg'] else colorize(search_result['file_size'], 'flac'), 
                        search_result['duration'], search_result['album'], colorize(search_result['source'], 'highlight'),
                    ])
            printtable(titles=print_titles, items=print_items)
            # process user inputs, music file download
            user_input_select_song_info_pointer = self.processinputs('Please enter music IDs to download (e.g., "1,2"): ').replace(' ', '').split(',')
            user_input_select_song_info_pointer = [idx for idx in user_input_select_song_info_pointer if idx in song_infos]
            selected_song_infos = []
            for idx in user_input_select_song_info_pointer: selected_song_infos.append(song_infos[idx])
            self.download(selected_song_infos)
    '''search'''
    def search(self, keyword):
        self.logger_handle.info(f'Searching {colorize(keyword, "highlight")} From {colorize("|".join(self.music_sources), "highlight")}')
        search_results = dict()
        for music_source in self.music_sources:
            search_results[music_source] = self.music_clients[music_source].search(
                keyword=keyword, num_threadings=self.clients_threadings[music_source], 
                request_overrides=self.requests_overrides[music_source], rule=self.search_rules[music_source]
            )
        return search_results
    '''download'''
    def download(self, song_infos):
        classified_song_infos = {}
        for song_info in song_infos:
            if song_info['source'] in classified_song_infos:
                classified_song_infos[song_info['source']].append(song_info)
            else:
                classified_song_infos[song_info['source']] = [song_info]
        for source, source_song_infos in classified_song_infos.items():
            self.music_clients[source].download(
                song_infos=source_song_infos, num_threadings=self.clients_threadings[song_info['source']], request_overrides=self.requests_overrides[song_info['source']]
            )
    '''processinputs'''
    def processinputs(self, input_tip=''):
        # accept user inputs
        user_input = input(input_tip)
        # quit
        if user_input.lower() == 'q':
            self.logger_handle.info('Goodbye — thanks for using musicdl; come back anytime!')
            sys.exit()
        # restart
        elif user_input.lower() == 'r':
            self.startcmdui()
        # common inputs
        else:
            return user_input
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
    '-m', '--music-sources', '--music_sources', default='MiguMusicClient,NeteaseMusicClient,KuwoMusicClient,KugouMusicClient,QQMusicClient,QianqianMusicClient', help='The music search and download sources.', type=str, show_default=True, 
)
@click.option(
    '-i', '--init-music-clients-cfg', '--init_music_clients_cfg', default=None, help='Config such as `work_dir` for each music client as a JSON string.', type=str, show_default=True,
)
@click.option(
    '-r', '--requests-overrides', '--requests_overrides', default=None, help='Requests.get kwargs such as `headers` and `proxies` for each music client as a JSON string.', type=str, show_default=True,
)
@click.option(
    '-c', '--clients-threadings', '--clients_threadings', default=None, help='Number of threads used for each music client as a JSON string.', type=str, show_default=True,
)
@click.option(
    '-s', '--search-rules', '--search_rules', default=None, help='Search rules for each music client as a JSON string.', type=str, show_default=True,
)
def MusicClientCMD(keyword: str, music_sources: str, init_music_clients_cfg: str, requests_overrides: str, clients_threadings: str, search_rules: str):
    # load json string
    def _safe_load(string):
        if string is not None:
            result = json_repair.loads(string) or {}
        else:
            result = {}
        return result
    init_music_clients_cfg = _safe_load(init_music_clients_cfg)
    requests_overrides = _safe_load(requests_overrides)
    clients_threadings = _safe_load(clients_threadings)
    search_rules = _safe_load(search_rules)
    # instance music client
    music_sources = music_sources.replace(' ', '').split(',')
    music_client = MusicClient(
        music_sources=music_sources, init_music_clients_cfg=init_music_clients_cfg, clients_threadings=clients_threadings, 
        requests_overrides=requests_overrides, search_rules=search_rules,
    )
    # switch according to keyword
    if keyword is None:
        music_client.startcmdui()
    else:
        print(music_client)
        # --search
        search_results = music_client.search(keyword=keyword)
        song_infos = []
        for song_infos_per_source in list(search_results.values()):
            song_infos.extend(song_infos_per_source)
        # --download
        music_client.download(song_infos=song_infos)


'''tests'''
if __name__ == '__main__':
    music_client = MusicClient()
    music_client.startcmdui()