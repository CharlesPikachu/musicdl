'''initialize'''
from .downloader import Downloader
from .speech import SpeechRecognition
from .logger import Logger, printTable, colorize
from .misc import touchdir, seconds2hms, loadConfig, filterBadCharacter