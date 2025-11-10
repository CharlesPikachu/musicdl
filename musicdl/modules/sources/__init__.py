'''initialize'''
from .base import BaseMusicClient
from .kuwo import KuwoMusicClient
from .kugou import KugouMusicClient
from ..utils import BaseModuleBuilder
from .fivesing import FiveSingMusicClient


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'FiveSingMusicClient': FiveSingMusicClient, 'KuwoMusicClient': KuwoMusicClient, 'KugouMusicClient': KugouMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build