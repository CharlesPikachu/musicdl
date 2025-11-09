'''initialize'''
from .base import BaseMusicClient
from ..utils import BaseModuleBuilder
from .fivesing import FiveSingMusicClient


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'FiveSingMusicClient': FiveSingMusicClient, 
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build