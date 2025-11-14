'''initialize'''
from .qq import QQMusicClient
from .joox import JooxMusicClient
from .base import BaseMusicClient
from .kuwo import KuwoMusicClient
from .migu import MiguMusicClient
from .tidal import TIDALMusicClient
from .lizhi import LizhiMusicClient
from .kugou import KugouMusicClient
from ..utils import BaseModuleBuilder
from .netease import NeteaseMusicClient
from .fivesing import FiveSingMusicClient
from .qianqian import QianqianMusicClient
from .ximalaya import XimalayaMusicClient


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'FiveSingMusicClient': FiveSingMusicClient, 'KuwoMusicClient': KuwoMusicClient, 'KugouMusicClient': KugouMusicClient,
        'QianqianMusicClient': QianqianMusicClient, 'QQMusicClient': QQMusicClient, 'MiguMusicClient': MiguMusicClient,
        'JooxMusicClient': JooxMusicClient, 'LizhiMusicClient': LizhiMusicClient, 'NeteaseMusicClient': NeteaseMusicClient,
        'XimalayaMusicClient': XimalayaMusicClient, 'TIDALMusicClient': TIDALMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build