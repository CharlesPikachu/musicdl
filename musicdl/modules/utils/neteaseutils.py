'''
Function:
    Implementation of NeteaseMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import json
import base64
import urllib
import codecs
import urllib.parse
from hashlib import md5
from Crypto.Cipher import AES
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''settings'''
MUSIC_QUALITIES = ['jymaster', 'dolby', 'sky', 'jyeffect', 'hires', 'lossless', 'exhigh', 'standard']
DEFAULT_COOKIES = {'MUSIC_U': '1eb9ce22024bb666e99b6743b2222f29ef64a9e88fda0fd5754714b900a5d70d993166e004087dd3b95085f6a85b059f5e9aba41e3f2646e3cebdbec0317df58c119e5'}


'''EapiCryptoUtils'''
class EapiCryptoUtils(object):
    '''hexdigest'''
    @staticmethod
    def hexdigest(data: bytes):
        return "".join([hex(d)[2:].zfill(2) for d in data])
    '''hashdigest'''
    @staticmethod
    def hashdigest(text: str):
        return md5(text.encode("utf-8")).digest()
    '''hashhexdigest'''
    @staticmethod
    def hashhexdigest(text: str):
        return EapiCryptoUtils.hexdigest(EapiCryptoUtils.hashdigest(text))
    '''encryptparams'''
    @staticmethod
    def encryptparams(url: str, payload: dict, aes_key: bytes = b"e82ckenh8dichen8"):
        url_path = urllib.parse.urlparse(url).path.replace("/eapi/", "/api/")
        digest = EapiCryptoUtils.hashhexdigest(f"nobody{url_path}use{json.dumps(payload)}md5forencrypt")
        params = f"{url_path}-36cd479b6b5-{json.dumps(payload)}-36cd479b6b5-{digest}"
        padder = padding.PKCS7(algorithms.AES(aes_key).block_size).padder()
        padded_data = padder.update(params.encode()) + padder.finalize()
        cipher = Cipher(algorithms.AES(aes_key), modes.ECB())
        encryptor = cipher.encryptor()
        enc = encryptor.update(padded_data) + encryptor.finalize()
        return EapiCryptoUtils.hexdigest(enc)


'''WeapiCryptoUtils'''
class WeapiCryptoUtils(object):
    '''createsecretkey'''
    @staticmethod
    def createsecretkey(size: int):
        return (''.join(map(lambda xx: (hex(ord(xx))[2:]), str(os.urandom(size)))))[0: 16]
    '''aesencrypt'''
    @staticmethod
    def aesencrypt(string: str, sec_key: str):
        pad = 16 - len(string) % 16
        if isinstance(string, bytes): string = string.decode('utf-8')
        string = string + str(pad * chr(pad))
        sec_key = sec_key.encode('utf-8')
        encryptor = AES.new(sec_key, 2, b'0102030405060708')
        string = string.encode('utf-8')
        ciphertext = encryptor.encrypt(string)
        ciphertext = base64.b64encode(ciphertext)
        return ciphertext
    '''rsaencrypt'''
    @staticmethod
    def rsaencrypt(string: str, pub_key: str = '010001', modulus: str = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'):
        string = string[::-1]
        rs = int(codecs.encode(string.encode('utf-8'), 'hex_codec'), 16) ** int(pub_key, 16) % int(modulus, 16)
        return format(rs, 'x').zfill(256)
    '''encryptparams'''
    @staticmethod
    def encryptparams(params: dict):
        string = json.dumps(params)
        sec_key = WeapiCryptoUtils.createsecretkey(16)
        enc_string = WeapiCryptoUtils.aesencrypt(string=WeapiCryptoUtils.aesencrypt(string=string, sec_key='0CoJUm6Qyw8W8jud'), sec_key=sec_key)
        enc_sec_key = WeapiCryptoUtils.rsaencrypt(string=sec_key)
        post_data = {'params': enc_string, 'encSecKey': enc_sec_key}
        return post_data