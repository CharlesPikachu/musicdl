'''initialize'''
from .lyric import WhisperLRC
from .modulebuilder import BaseModuleBuilder
from .logger import LoggerHandle, colorize, printtable, printfullline, smarttrunctable
from .misc import (
    AudioLinkTester, legalizestring, touchdir, seconds2hms, byte2mb, cachecookies, resp2json, isvalidresp, safeextractfromdict, replacefile,
    usedownloadheaderscookies, useparseheaderscookies, usesearchheaderscookies
)