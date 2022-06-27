'''
Function:
    根据歌词获取对应的mp3文件片段
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import re
import os
from musicdl import musicdl
from pydub import AudioSegment
from pydub.playback import play


'''根据歌词获取对应的mp3文件片段'''
class SearchLyrics():
    def __init__(self):
        self.rootdir = os.path.split(os.path.abspath(__file__))[0]
        self.target_srcs = ['netease']
        self.config = {'logfilepath': 'musicdl.log', 'savedir': self.rootdir, 'search_size_per_source': 1, 'proxies': {}}
        self.api_client = musicdl.musicdl(config=self.config)
    '''调用运行'''
    def run(self):
        keyword = input('请输入歌词: ')
        print('[INFO]: 正在尝试获取对应的歌曲')
        results = self.api_client.search(keyword, self.target_srcs)[self.target_srcs[0]]
        self.api_client.download(results)
        print('[INFO]: 正在尝试提取对应歌词的音频')
        lyrics = results[0]['lyric']
        start, end = None, None
        for lyric in lyrics.split('\n'):
            if start is not None and end is not None:
                break
            if keyword in lyric:
                start = re.findall(r'\[(.*?)\]', lyric)[0]
                start = int(float(start.split(':')[0])) * 1000 * 60 + int(float(start.split(':')[1])) * 1000 - 1000
            elif start is not None:
                end = re.findall(r'\[(.*?)\]', lyric)[0]
                end = int(float(end.split(':')[0])) * 1000 * 60 + int(float(end.split(':')[1])) * 1000 + 1000
        filepath = os.path.join(self.rootdir, f"{results[0]['savename']}.{results[0]['ext']}")
        music = AudioSegment.from_mp3(file=filepath)
        music_cut = music[start: end]
        music_cut.export(out_f=os.path.join(self.rootdir, f"{results[0]['savename']}_cut.{results[0]['ext']}"), format='mp3')
        play(music_cut)
        

'''run'''
if __name__ == '__main__':
    client = SearchLyrics()
    client.run()