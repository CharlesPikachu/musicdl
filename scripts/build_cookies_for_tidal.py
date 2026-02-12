'''
Function:
    Implementation of KugouMusicClient Cookies Builder
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from musicdl.modules.utils.tidalutils import TidalTvSession


'''buildtidalcookies'''
def buildtidalcookies():
    cli = TidalTvSession()
    cli.auth()
    return cli.getstorage().tojson()


'''tests'''
if __name__ == '__main__':
    print(buildtidalcookies())