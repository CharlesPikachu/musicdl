'''initialize'''
from .qq import QQMusicClient
from .mitu import MituMusicClient
from .joox import JooxMusicClient
from .base import BaseMusicClient
from .kuwo import KuwoMusicClient
from .migu import MiguMusicClient
from .kkws import KKWSMusicClient
from .soda import SodaMusicClient
from .jcpoo import JCPOOMusicClient
from .flmp3 import FLMP3MusicClient
from .htqyy import HTQYYMusicClient
from .tidal import TIDALMusicClient
from .lizhi import LizhiMusicClient
from .apple import AppleMusicClient
from .kugou import KugouMusicClient
from .twot58 import TwoT58MusicClient
from .fangpi import FangpiMusicClient
from .buguyy import BuguyyMusicClient
from ..utils import BaseModuleBuilder
from .netease import NeteaseMusicClient
from .youtube import YouTubeMusicClient
from .gequbao import GequbaoMusicClient
from .jamendo import JamendoMusicClient
from .gequhai import GequhaiMusicClient
from .livepoo import LivePOOMusicClient
from .zhuolin import ZhuolinMusicClient
from .fivesong import FiveSongMusicClient
from .fivesing import FiveSingMusicClient
from .qianqian import QianqianMusicClient
from .ximalaya import XimalayaMusicClient
from .bilibili import BilibiliMusicClient
from .missevan import MissEvanMusicClient
from .yinyuedao import YinyuedaoMusicClient
from ..common import GDStudioMusicClient, TuneHubMusicClient, MP3JuiceMusicClient, MyFreeMP3MusicClient


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'QQMusicClient': QQMusicClient, 'MituMusicClient': MituMusicClient, 'BuguyyMusicClient': BuguyyMusicClient, 'GequbaoMusicClient': GequbaoMusicClient,
        'MP3JuiceMusicClient': MP3JuiceMusicClient, 'YinyuedaoMusicClient': YinyuedaoMusicClient, 'LizhiMusicClient': LizhiMusicClient, 'XimalayaMusicClient': XimalayaMusicClient,
        'JooxMusicClient': JooxMusicClient, 'KuwoMusicClient': KuwoMusicClient, 'KugouMusicClient': KugouMusicClient, 'FiveSingMusicClient': FiveSingMusicClient,
        'QianqianMusicClient': QianqianMusicClient, 'MiguMusicClient': MiguMusicClient, 'NeteaseMusicClient': NeteaseMusicClient, 'YouTubeMusicClient': YouTubeMusicClient,
        'TIDALMusicClient': TIDALMusicClient, 'AppleMusicClient': AppleMusicClient, 'FangpiMusicClient': FangpiMusicClient, 'GDStudioMusicClient': GDStudioMusicClient,
        'JamendoMusicClient': JamendoMusicClient, 'BilibiliMusicClient': BilibiliMusicClient, 'TuneHubMusicClient': TuneHubMusicClient, 'GequhaiMusicClient': GequhaiMusicClient,
        'MissEvanMusicClient': MissEvanMusicClient, 'HTQYYMusicClient': HTQYYMusicClient, 'FiveSongMusicClient': FiveSongMusicClient, 'FLMP3MusicClient': FLMP3MusicClient,
        'JCPOOMusicClient': JCPOOMusicClient, 'KKWSMusicClient': KKWSMusicClient, 'MyFreeMP3MusicClient': MyFreeMP3MusicClient, 'LivePOOMusicClient': LivePOOMusicClient,
        'TwoT58MusicClient': TwoT58MusicClient, 'SodaMusicClient': SodaMusicClient, 'ZhuolinMusicClient': ZhuolinMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build