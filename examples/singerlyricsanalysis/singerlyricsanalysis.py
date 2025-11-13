'''
Function:
    Implementation of SingerLyricsAnalysis
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import jieba
import pickle
import numpy as np
from PIL import Image
from snownlp import SnowNLP
from wordcloud import WordCloud
from musicdl.modules.sources import MiguMusicClient


'''SingerLyricsAnalysis'''
class SingerLyricsAnalysis():
    def __init__(self):
        self.root_dir = os.path.split(os.path.abspath(__file__))[0]
        self.music_client = MiguMusicClient(search_size_per_source=2000)
    '''start'''
    def start(self):
        while True:
            singer_name = input('Input singer to analyze: ')
            print(f'[INFO]: Searching {singer_name}')
            infos = self.crawler(singer_name)
            print(f'[INFO]: Analyzing {singer_name}')
            self.analysis(infos)
    '''crawler'''
    def crawler(self, singer_name):
        song_infos = self.music_client.search(keyword=singer_name)
        self.save(singer_name=singer_name, song_infos=song_infos)
        return song_infos
    '''analysis'''
    def analysis(self, song_infos):
        # data clean
        lyrics = []
        for song_info in song_infos:
            lyric = song_info['lyric']
            lyric = lyric.split('\r\n')
            lyric_filtered = []
            for sentence in lyric:
                sentence = sentence[10:]
                if (not sentence) or ('：' in sentence) or (self.root_dir in sentence) or ('[' in sentence) or (']' in sentence) or ('歌曲' in sentence): continue
                lyric_filtered.append(sentence)
            lyrics += lyric_filtered
        # generatewordcloud
        words_dict = {}
        for sentence in lyrics:
            words = jieba.cut(sentence)
            for word in words:
                word = word.strip()
                if not word: continue
                if len(word) < 2: continue
                if word in words_dict: words_dict[word] += 1
                else: words_dict[word] = 1
        words_freq_sorted = sorted(words_dict.items(), key=lambda item: item[1])
        words_freq_top10 = words_freq_sorted[-10:]
        self.generatewordcloud(words_dict)
        self.drawbar('%s歌曲中的词语TOP10' % self.root_dir, words_freq_top10)
        # nlp analysis
        nlp_dict = {'内容极度负面': 0, '内容较为负面': 0, '内容中性': 0, '内容较为正面': 0, '内容非常正面': 0}
        for sentence in lyrics:
            score = SnowNLP(sentence).sentiments
            if score < 0.2:
                nlp_dict['内容极度负面'] += 1
            elif score >= 0.2 and score < 0.4:
                nlp_dict['内容较为负面'] += 1 
            elif score >= 0.4 and score < 0.6:
                nlp_dict['内容中性'] += 1 
            elif score >= 0.6 and score < 0.8:
                nlp_dict['内容较为正面'] += 1 
            else:
                nlp_dict['内容非常正面'] += 1 
        self.drawpie('%s的歌词情感分析' % self.root_dir, nlp_dict)
    '''drawbar'''
    def drawbar(self, title, infos):
        from pyecharts.charts import Bar
        from pyecharts import options as opts
        from pyecharts.globals import ThemeType
        bar = Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        bar.add_xaxis([item[0] for item in infos])
        bar.add_yaxis('freq', [item[1] for item in infos])
        bar.set_global_opts(title_opts=opts.TitleOpts(title=title))
        bar.render(os.path.join(self.root_dir, title+'.html'))
    '''drawpie'''
    def drawpie(self, title, infos):
        from pyecharts.charts import Pie
        from pyecharts import options as opts
        pie = Pie(init_opts=dict(theme='westeros', page_title=title)).add(title, data_pair=tuple(zip(infos.keys(), infos.values())), rosetype='area')
        pie.set_global_opts(title_opts=opts.TitleOpts(title=title))
        pie.render(os.path.join(self.root_dir, '%s.html' % title))
    '''generatewordcloud'''
    def generatewordcloud(self, infos):
        mask = Image.open(os.path.join(self.root_dir, 'resources/mask.jpg'))
        mask = np.array(mask)
        wc = WordCloud(background_color='white', font_path=os.path.join(self.root_dir, 'resources/font_cn.TTF'), mask=mask)
        result = wc.generate_from_frequencies(infos)
        result.to_file(os.path.join(self.root_dir, 'wordcloud.png'))
    '''save'''
    def save(self, song_infos, singer_name):
        data_save_path = os.path.join(self.root_dir, f'song_infos_{singer_name}.pkl')
        with open(data_save_path, 'wb') as fp:
            pickle.dump(song_infos, fp)
    '''load'''
    def load(self, singer_name):
        data_save_path = os.path.join(self.root_dir, f'song_infos_{singer_name}.pkl')
        fp = open(data_save_path, 'rb')
        return pickle.load(fp)


'''tests'''
if __name__ == '__main__':
    client = SingerLyricsAnalysis()
    client.start()