'''initialize'''
from .base import BaseMusicClient
from .fivesing import FiveSingClient
from ..utils import BaseModuleBuilder


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'FiveSingClient': FiveSingClient, 
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build