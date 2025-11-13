'''
Function:
    Implementation of SearchLyrics
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
from pydub import AudioSegment
from pydub.playback import play
from musicdl.modules.sources import NeteaseMusicClient
from musicdl.modules.utils.misc import sanitize_filepath


'''SearchLyrics'''
class SearchLyrics():
    def __init__(self):
        self.music_client = NeteaseMusicClient(search_size_per_source=1)
    '''start'''
    def start(self):
        # inputs
        keyword = input('Input lyrics: ')
        # search and download music files
        print('[INFO]: Searching and downloading music files by lyrics')
        song_infos = self.music_client.search(keyword)[:1]
        self.music_client.download(song_infos)
        # extract audio clips
        print('[INFO]: Extract the corresponding audio clip and play')
        lyrics: str = song_infos[0]['lyric']
        start, end = None, None
        for lyric in lyrics.split('\n'):
            if start is not None and end is not None:
                break
            if keyword in lyric:
                start: str = re.findall(r'\[(.*?)\]', lyric)[0]
                start = int(float(start.split(':')[0])) * 1000 * 60 + int(float(start.split(':')[1])) * 1000 - 1000
            elif start is not None:
                end: str = re.findall(r'\[(.*?)\]', lyric)[0]
                end = int(float(end.split(':')[0])) * 1000 * 60 + int(float(end.split(':')[1])) * 1000 + 1000
        # play
        file_path = os.path.join(song_infos[0]['work_dir'], f"{song_infos[0]['song_name']}.{song_infos[0]['ext']}")
        music = AudioSegment.from_mp3(file=sanitize_filepath(file_path))
        music_cut = music[start: end]
        music_cut.export(out_f=os.path.join(song_infos[0]['work_dir'], f"{song_infos[0]['song_name']}_cut.{song_infos[0]['ext']}"), format='mp3')
        play(music_cut)


'''tests'''
if __name__ == '__main__':
    client = SearchLyrics()
    client.start()