'''
Function:
    网易云音乐下载: https://music.163.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import time
import json
import base64
import codecs
import requests
from .base import Base
from Crypto.Cipher import AES
from ..utils import seconds2hms, filterBadCharacter


'''用于算post的两个参数, 具体原理详见知乎: https://www.zhihu.com/question/36081767'''
class Cracker():
    def __init__(self):
        self.modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
        self.nonce = '0CoJUm6Qyw8W8jud'
        self.pubKey = '010001'
    def get(self, text):
        text = json.dumps(text)
        secKey = self.__createSecretKey(16)
        encText = self.__aesEncrypt(self.__aesEncrypt(text, self.nonce), secKey)
        encSecKey = self.__rsaEncrypt(secKey, self.pubKey, self.modulus)
        post_data = {
            'params': encText,
            'encSecKey': encSecKey
        }
        return post_data
    def __aesEncrypt(self, text, secKey):
        pad = 16 - len(text) % 16
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        text = text + str(pad * chr(pad))
        secKey = secKey.encode('utf-8')
        encryptor = AES.new(secKey, 2, b'0102030405060708')
        text = text.encode('utf-8')
        ciphertext = encryptor.encrypt(text)
        ciphertext = base64.b64encode(ciphertext)
        return ciphertext
    def __rsaEncrypt(self, text, pubKey, modulus):
        text = text[::-1]
        rs = int(codecs.encode(text.encode('utf-8'), 'hex_codec'), 16) ** int(pubKey, 16) % int(modulus, 16)
        return format(rs, 'x').zfill(256)
    def __createSecretKey(self, size):
        return (''.join(map(lambda xx: (hex(ord(xx))[2:]), str(os.urandom(size)))))[0: 16]


'''网易云音乐下载类'''
class Netease(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Netease, self).__init__(config, logger_handle, **kwargs)
        self.source = 'netease'
        self.cracker = Cracker()
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            's': keyword,
            'type': '1',
            'offset': str(cfg.get('page', 0)),
            'sub': 'false',
            'limit': cfg['search_size_per_source']
        }
        response = self.session.post(self.search_url, headers=self.headers, params=params, data=self.cracker.get(params))
        all_items = response.json()['result']['songs']
        songinfos = []
        for item in all_items:
            if item['privilege']['fl'] == 0: continue
            for q in ['h', 'm', 'l']:
                params = {
                    'ids': [item['id']],
                    'br': item[q]['br'],
                    'csrf_token': ''
                }
                response = self.session.post(self.player_url, headers=self.headers, data=self.cracker.get(params))
                response_json = response.json()
                if response_json.get('code') == 200: break
            if response_json.get('code') != 200: continue
            download_url = response_json['data'][0]['url']
            if not download_url: continue
            params = {
                'csrf_token': '',
                'id': item['id'],
                'lv': '-1',
                'tv': '-1'
            }
            response = self.session.post(self.lyric_url, headers=self.headers, data=self.cracker.get(params))
            lyric = response.json().get('lrc', {}).get('lyric', '')
            filesize = str(round(int(item[q]['size'])/1024/1024, 2)) + 'MB'
            ext = download_url.split('.')[-1]
            duration = int(item.get('dt', 0) / 1000)
            songinfo = {
                'source': self.source,
                'songid': str(item['id']),
                'singers': filterBadCharacter(','.join([s.get('name', '') for s in item.get('ar')])),
                'album': filterBadCharacter(item.get('al', {}).get('name', '-')),
                'songname': filterBadCharacter(item.get('name', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('name', f'{keyword}_{int(time.time())}')),
                'download_url': download_url,
                'lyric': lyric,
                'filesize': filesize,
                'ext': ext,
                'duration': seconds2hms(duration)
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
        return songinfos
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'music.163.com',
            'Origin': 'https://music.163.com',
            'Referer': 'https://music.163.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.32 Safari/537.36'
        }
        self.search_url = 'http://music.163.com/weapi/cloudsearch/get/web?csrf_token='
        self.player_url = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='
        self.lyric_url = 'https://music.163.com/weapi/song/lyric'