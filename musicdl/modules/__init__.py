'''initialize'''
from .sources import MusicClientBuilder, BaseMusicClient, BuildMusicClient
from .utils import (
    # classes
    BaseModuleBuilder, LoggerHandle, AudioLinkTester, WhisperLRC, QuarkParser, SongInfo, SongInfoUtils, RandomIPGenerator, LanZouYParser, HLSDownloader, LyricSearchClient,
    # functions
    cachecookies, resp2json, isvalidresp, safeextractfromdict, replacefile, printfullline, smarttrunctable, usesearchheaderscookies, byte2mb, printtable, usedownloadheaderscookies, 
    useparseheaderscookies, cookies2dict, cookies2string, touchdir, estimatedurationwithfilesizebr, estimatedurationwithfilelink, extractdurationsecondsfromlrc, optionalimportfrom, 
    searchdictbykey, colorize, legalizestring, shortenpathsinsonginfos, cursorpickintable, optionalimport, obtainhostname, hostmatchessuffix, seconds2hms, naiveguessextfromaudiobytes,
    # lambda functions
    cleanlrc,
)