'''initialize'''
from .qq import QQMusicClient
from .fma import FMAMusicClient
from .joox import JooxMusicClient
from .moov import MOOVMusicClient
from .kuwo import KuwoMusicClient
from .migu import MiguMusicClient
from .soda import SodaMusicClient
from .suno import SunoMusicClient
from .tidal import TIDALMusicClient
from .apple import AppleMusicClient
from .kugou import KugouMusicClient
from .qobuz import QobuzMusicClient
from .audius import AudiusMusicClient
from .deezer import DeezerMusicClient
from .bodian import BodianMusicClient
from ..utils import BaseModuleBuilder
from .spotify import SpotifyMusicClient
from .netease import NeteaseMusicClient
from .youtube import YouTubeMusicClient
from .jamendo import JamendoMusicClient
from .fivesing import FiveSingMusicClient
from .ccmixter import CCMixterMusicClient
from .qianqian import QianqianMusicClient
from .bilibili import BilibiliMusicClient
from .jiosaavn import JioSaavnMusicClient
from .soundcloud import SoundCloudMusicClient
from .streetvoice import StreetVoiceMusicClient
from .opengameart import OpenGameArtMusicClient
from .base import BaseMusicClient, BaseMusicClientKwargs
from .wikimediacommons import WikimediaCommonsMusicClient
from ..audiobooks import XimalayaMusicClient, LizhiMusicClient, QingtingMusicClient, LRTSMusicClient, ITunesMusicClient
from ..common import GDStudioMusicClient, TuneHubMusicClient, MP3JuiceMusicClient, MyFreeMP3MusicClient, JBSouMusicClient, XiaoBaiMusicClient
from ..thirdpartysites import (
    MituMusicClient, BuguyyMusicClient, YinyuedaoMusicClient, FiveSongMusicClient, FangpiMusicClient, TwoT58MusicClient, ZhuolinMusicClient, HTQYYMusicClient, FLMP3MusicClient, GequbaoMusicClient, 
    KKWSMusicClient, GequhaiMusicClient, LivePOOMusicClient, LiziYYMusicClient, MGMP3MusicClient, ITingWaMusicClient, SgogoMusicClient, XiagebaMusicClient
)


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        # Platforms in Greater China
        'QQMusicClient'      : QQMusicClient,          'KugouMusicClient'      : KugouMusicClient,          'StreetVoiceMusicClient': StreetVoiceMusicClient,    'SodaMusicClient'            : SodaMusicClient,                'FiveSingMusicClient'  : FiveSingMusicClient,
        'NeteaseMusicClient' : NeteaseMusicClient,     'QianqianMusicClient'   : QianqianMusicClient,       'MiguMusicClient'       : MiguMusicClient,           'KuwoMusicClient'            : KuwoMusicClient,                'BilibiliMusicClient'  : BilibiliMusicClient,
        'BodianMusicClient'  : BodianMusicClient,      'MOOVMusicClient'       : MOOVMusicClient,
        # Global Streaming / Indie
        'YouTubeMusicClient' : YouTubeMusicClient,     'JooxMusicClient'       : JooxMusicClient,           'AppleMusicClient'      : AppleMusicClient,          'JamendoMusicClient'         : JamendoMusicClient,             'SoundCloudMusicClient': SoundCloudMusicClient,
        'DeezerMusicClient'  : DeezerMusicClient,      'QobuzMusicClient'      : QobuzMusicClient,          'SpotifyMusicClient'    : SpotifyMusicClient,        'TIDALMusicClient'           : TIDALMusicClient,               'FMAMusicClient'       : FMAMusicClient,
        'JioSaavnMusicClient': JioSaavnMusicClient,    'OpenGameArtMusicClient': OpenGameArtMusicClient,    'SunoMusicClient'       : SunoMusicClient,           'WikimediaCommonsMusicClient': WikimediaCommonsMusicClient,    'AudiusMusicClient'    : AudiusMusicClient,
        'CCMixterMusicClient': CCMixterMusicClient,
        # Audio / Radio
        'XimalayaMusicClient': XimalayaMusicClient,    'LizhiMusicClient'      : LizhiMusicClient,          'QingtingMusicClient'   : QingtingMusicClient,       'LRTSMusicClient'            : LRTSMusicClient,                'ITunesMusicClient'    : ITunesMusicClient,
        # Aggregators / Multi-Source Gateways
        'MP3JuiceMusicClient': MP3JuiceMusicClient,    'TuneHubMusicClient'    : TuneHubMusicClient,        'GDStudioMusicClient'   : GDStudioMusicClient,       'MyFreeMP3MusicClient'       : MyFreeMP3MusicClient,           'JBSouMusicClient'     : JBSouMusicClient,
        'XiaoBaiMusicClient' : XiaoBaiMusicClient,
        # Unofficial Download Sites / Scrapers
        'MituMusicClient'    : MituMusicClient,        'BuguyyMusicClient'     : BuguyyMusicClient,         'GequbaoMusicClient'    : GequbaoMusicClient,        'YinyuedaoMusicClient'       : YinyuedaoMusicClient,           'FLMP3MusicClient'     : FLMP3MusicClient,
        'FangpiMusicClient'  : FangpiMusicClient,      'FiveSongMusicClient'   : FiveSongMusicClient,       'KKWSMusicClient'       : KKWSMusicClient,           'GequhaiMusicClient'         : GequhaiMusicClient,             'LivePOOMusicClient'   : LivePOOMusicClient,
        'HTQYYMusicClient'   : HTQYYMusicClient,       'TwoT58MusicClient'     : TwoT58MusicClient,         'ZhuolinMusicClient'    : ZhuolinMusicClient,        'LiziYYMusicClient'          : LiziYYMusicClient,              'MGMP3MusicClient'     : MGMP3MusicClient,
        'ITingWaMusicClient' : ITingWaMusicClient,     'SgogoMusicClient'      : SgogoMusicClient,          'XiagebaMusicClient'    : XiagebaMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build