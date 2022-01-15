'''
Function:
    歌手歌词分析
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import jieba
import pickle
import numpy as np
from PIL import Image
from musicdl import musicdl
from snownlp import SnowNLP
from wordcloud import WordCloud


'''歌手歌词分析'''
class SingerLyricsAnalysis():
    def __init__(self):
        self.rootdir = os.path.split(os.path.abspath(__file__))[0]
        self.savedir = None
        self.savename = 'infos.pkl'
        self.target_srcs = ['migu']
        self.config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 20, 'proxies': {}}
    '''运行'''
    def run(self):
        while True:
            singer_name = input('请输入歌手名: ')
            print('[INFO]: 正在爬取歌手%s的相关数据...' % singer_name)
            infos = self.crawler(singer_name)
            print('[INFO]: 正在生成歌手%s的分析结果...' % singer_name)
            self.analysis(infos)
    '''爬虫代码'''
    def crawler(self, singer_name):
        self.savedir, page, infos = singer_name, 0, []
        while True:
            page += 1
            self.config['page'] = page
            api = musicdl.musicdl(config=self.config)
            results = api.search(singer_name, self.target_srcs)
            if len(results[self.target_srcs[0]]) < 1: break
            infos.append(results)
        self.save(infos)
        return infos
    '''数据分析'''
    def analysis(self, infos):
        # 数据清洗
        lyrics = []
        for info in infos:
            for item in info[self.target_srcs[0]]:
                lyric = item['lyric']
                lyric = lyric.split('\r\n')
                lyric_filtered = []
                for sentence in lyric:
                    sentence = sentence[10:]
                    if (not sentence) or ('：' in sentence) or (self.savedir in sentence) or ('[' in sentence) or (']' in sentence) or ('歌曲' in sentence): continue
                    lyric_filtered.append(sentence)
                lyrics += lyric_filtered
        # 词频分析
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
        self.drawbar('%s歌曲中的词语TOP10' % self.savedir, words_freq_top10)
        # 情感分析
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
        self.drawpie('%s的歌词情感分析' % self.savedir, nlp_dict)
    '''画柱状图'''
    def drawbar(self, title, infos):
        from pyecharts.charts import Bar
        from pyecharts import options as opts
        from pyecharts.globals import ThemeType
        bar = Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        bar.add_xaxis([item[0] for item in infos])
        bar.add_yaxis('freq', [item[1] for item in infos])
        bar.set_global_opts(title_opts=opts.TitleOpts(title=title))
        bar.render(os.path.join(self.savedir, title+'.html'))
    '''画饼图'''
    def drawpie(self, title, infos):
        from pyecharts.charts import Pie
        from pyecharts import options as opts
        pie = Pie(init_opts=dict(theme='westeros', page_title=title)).add(title, data_pair=tuple(zip(infos.keys(), infos.values())), rosetype='area')
        pie.set_global_opts(title_opts=opts.TitleOpts(title=title))
        pie.render(os.path.join(self.savedir, '%s.html' % title))
    '''生成词云'''
    def generatewordcloud(self, infos):
        mask = Image.open(os.path.join(self.rootdir, 'resources/mask.jpg'))
        mask = np.array(mask)
        wc = WordCloud(background_color='white', font_path=os.path.join(self.rootdir, 'resources/font_cn.TTF'), mask=mask)
        result = wc.generate_from_frequencies(infos)
        result.to_file(os.path.join(self.savedir, 'wordcloud.png'))
    '''保存数据'''
    def save(self, infos):
        if not os.path.exists(self.savedir): os.mkdir(self.savedir)
        fp = open(os.path.join(self.savedir, self.savename), 'wb')
        pickle.dump(infos, fp)
        fp.close()
        return True
    '''导入数据'''
    def load(self):
        fp = open(os.path.join(self.savedir, self.savename), 'rb')
        return pickle.load(fp)


'''run'''
if __name__ == '__main__':
    client = SingerLyricsAnalysis()
    client.run()