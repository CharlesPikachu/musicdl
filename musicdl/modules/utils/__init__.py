'''initialize'''
from .lyric import WhisperLRC
from .modulebuilder import BaseModuleBuilder
from .logger import LoggerHandle, colorize, printtable
from .misc import (
    AudioLinkTester, legalizestring, touchdir, seconds2hms, byte2mb, cachecookies, resp2json, isvalidresp, safeextractfromdict
)