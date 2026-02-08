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
from .bilibili import BilibiliMusicClient
from .yinyuedao import YinyuedaoMusicClient
from .soundcloud import SoundCloudMusicClient
from .streetvoice import StreetVoiceMusicClient
from ..audiobooks import XimalayaMusicClient, LizhiMusicClient, QingtingMusicClient
from ..common import GDStudioMusicClient, TuneHubMusicClient, MP3JuiceMusicClient, MyFreeMP3MusicClient, JBSouMusicClient


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        # Platforms in Greater China
        'NeteaseMusicClient': NeteaseMusicClient, 'QianqianMusicClient': QianqianMusicClient, 'KuwoMusicClient': KuwoMusicClient, 'KugouMusicClient': KugouMusicClient, 'MiguMusicClient': MiguMusicClient,
        'QQMusicClient': QQMusicClient, 'BilibiliMusicClient': BilibiliMusicClient, 'FiveSingMusicClient': FiveSingMusicClient, 'SodaMusicClient': SodaMusicClient, 'StreetVoiceMusicClient': StreetVoiceMusicClient,
        # Global Streaming / Indie
        'YouTubeMusicClient': YouTubeMusicClient, 'JooxMusicClient': JooxMusicClient, 'AppleMusicClient': AppleMusicClient, 'JamendoMusicClient': JamendoMusicClient, 'TIDALMusicClient': TIDALMusicClient,
        'SoundCloudMusicClient': SoundCloudMusicClient,
        # Audio / Radio
        'XimalayaMusicClient': XimalayaMusicClient, 'LizhiMusicClient': LizhiMusicClient, 'QingtingMusicClient': QingtingMusicClient,
        # Aggregators / Multi-Source Gateways
        'MP3JuiceMusicClient': MP3JuiceMusicClient, 'TuneHubMusicClient': TuneHubMusicClient, 'GDStudioMusicClient': GDStudioMusicClient, 'MyFreeMP3MusicClient': MyFreeMP3MusicClient, 'JBSouMusicClient': JBSouMusicClient,
        # Unofficial Download Sites / Scrapers
        'MituMusicClient': MituMusicClient, 'BuguyyMusicClient': BuguyyMusicClient, 'GequbaoMusicClient': GequbaoMusicClient, 'YinyuedaoMusicClient': YinyuedaoMusicClient, 'FLMP3MusicClient': FLMP3MusicClient,
        'FangpiMusicClient': FangpiMusicClient, 'FiveSongMusicClient': FiveSongMusicClient, 'KKWSMusicClient': KKWSMusicClient, 'GequhaiMusicClient': GequhaiMusicClient, 'LivePOOMusicClient': LivePOOMusicClient,
        'HTQYYMusicClient': HTQYYMusicClient, 'JCPOOMusicClient': JCPOOMusicClient, 'TwoT58MusicClient': TwoT58MusicClient, 'ZhuolinMusicClient': ZhuolinMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build