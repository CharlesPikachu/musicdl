'''initialize'''
from .qq import QQMusicClient
from .joox import JooxMusicClient
from .base import BaseMusicClient
from .kuwo import KuwoMusicClient
from .migu import MiguMusicClient
from .soda import SodaMusicClient
from .tidal import TIDALMusicClient
from .apple import AppleMusicClient
from .kugou import KugouMusicClient
from .qobuz import QobuzMusicClient
from .deezer import DeezerMusicClient
from ..utils import BaseModuleBuilder
from .spotify import SpotifyMusicClient
from .netease import NeteaseMusicClient
from .youtube import YouTubeMusicClient
from .jamendo import JamendoMusicClient
from .fivesing import FiveSingMusicClient
from .qianqian import QianqianMusicClient
from .bilibili import BilibiliMusicClient
from .soundcloud import SoundCloudMusicClient
from .streetvoice import StreetVoiceMusicClient
from ..audiobooks import XimalayaMusicClient, LizhiMusicClient, QingtingMusicClient, LRTSMusicClient
from ..common import GDStudioMusicClient, TuneHubMusicClient, MP3JuiceMusicClient, MyFreeMP3MusicClient, JBSouMusicClient
from ..thirdpartysites import (
    MituMusicClient, BuguyyMusicClient, YinyuedaoMusicClient, FiveSongMusicClient, FangpiMusicClient, TwoT58MusicClient, ZhuolinMusicClient, HTQYYMusicClient, FLMP3MusicClient,
    GequbaoMusicClient, JCPOOMusicClient, KKWSMusicClient, GequhaiMusicClient, LivePOOMusicClient
)


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        # Platforms in Greater China
        'QQMusicClient': QQMusicClient, 'KugouMusicClient': KugouMusicClient, 'StreetVoiceMusicClient': StreetVoiceMusicClient, 'SodaMusicClient': SodaMusicClient, 'FiveSingMusicClient': FiveSingMusicClient, 
        'NeteaseMusicClient': NeteaseMusicClient, 'QianqianMusicClient': QianqianMusicClient, 'MiguMusicClient': MiguMusicClient, 'KuwoMusicClient': KuwoMusicClient, 'BilibiliMusicClient': BilibiliMusicClient, 
        # Global Streaming / Indie
        'YouTubeMusicClient': YouTubeMusicClient, 'JooxMusicClient': JooxMusicClient, 'AppleMusicClient': AppleMusicClient, 'JamendoMusicClient': JamendoMusicClient, 'SoundCloudMusicClient': SoundCloudMusicClient, 
        'DeezerMusicClient': DeezerMusicClient, 'QobuzMusicClient': QobuzMusicClient, 'SpotifyMusicClient': SpotifyMusicClient, 'TIDALMusicClient': TIDALMusicClient,
        # Audio / Radio
        'XimalayaMusicClient': XimalayaMusicClient, 'LizhiMusicClient': LizhiMusicClient, 'QingtingMusicClient': QingtingMusicClient, 'LRTSMusicClient': LRTSMusicClient,
        # Aggregators / Multi-Source Gateways
        'MP3JuiceMusicClient': MP3JuiceMusicClient, 'TuneHubMusicClient': TuneHubMusicClient, 'GDStudioMusicClient': GDStudioMusicClient, 'MyFreeMP3MusicClient': MyFreeMP3MusicClient, 'JBSouMusicClient': JBSouMusicClient,
        # Unofficial Download Sites / Scrapers
        'MituMusicClient': MituMusicClient, 'BuguyyMusicClient': BuguyyMusicClient, 'GequbaoMusicClient': GequbaoMusicClient, 'YinyuedaoMusicClient': YinyuedaoMusicClient, 'FLMP3MusicClient': FLMP3MusicClient,
        'FangpiMusicClient': FangpiMusicClient, 'FiveSongMusicClient': FiveSongMusicClient, 'KKWSMusicClient': KKWSMusicClient, 'GequhaiMusicClient': GequhaiMusicClient, 'LivePOOMusicClient': LivePOOMusicClient,
        'HTQYYMusicClient': HTQYYMusicClient, 'JCPOOMusicClient': JCPOOMusicClient, 'TwoT58MusicClient': TwoT58MusicClient, 'ZhuolinMusicClient': ZhuolinMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build