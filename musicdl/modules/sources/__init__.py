'''initialize'''
from .qq import QQMusicClient
from .base import BaseMusicClient
from .kuwo import KuwoMusicClient
from .kugou import KugouMusicClient
from ..utils import BaseModuleBuilder
from .fivesing import FiveSingMusicClient
from .qianqian import QianqianMusicClient


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'FiveSingMusicClient': FiveSingMusicClient, 'KuwoMusicClient': KuwoMusicClient, 'KugouMusicClient': KugouMusicClient,
        'QianqianMusicClient': QianqianMusicClient, 'QQMusicClient': QQMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build