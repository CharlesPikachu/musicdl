'''
Function:
    Implementation of YouTubeMusicClient Utils (Refer To https://pytubefix.readthedocs.io/en/latest/index.html)
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import sys
import ast
import math
import enum
import json
import time
import shutil
import struct
import base64
import socket
import pathlib
import subprocess
import http.client
from enum import Enum
from pathlib import Path
from urllib import parse
from functools import lru_cache
from collections.abc import Sequence
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from ..js.youtube import JSInterpreter, extractplayerjsglobalvar
from typing import Callable, List, Optional, Union, Callable, BinaryIO, Dict, Any, Tuple


'''settings'''
REPAIDAPI_KEYS = [
    "MTU1NmY2Y2NiMm1zaDY0YjgwNzQ4NTE1NmIzM3AxMmE2NmRqc243ZTE5N2JjMjNmMTk=", "NWE4MTBhODA2ZG1zaDE2NDJmNjEyZTIxNjViN3AxOTYwODRqc244Y2ViNDIxNjlhNTc=", "YmViZDlkMWE1Zm1zaDdkNTJmZGZhNzFkODVlYnAxYTZiMzVqc25lZWYzYjg4MTJiZmI=",
    "NmM5ZGQzNjBiY21zaGJkMjk2MGM2NzY5MzM4MHAxYjY3MjBqc25mMmNhNzdkN2UzZTA=", "MDdmZTg1ZWY0MW1zaGE3MDdkMTgxYzZkZmE5ZXAxZTMyYTNqc25lMDIxNmYxNGI2MWU=", "M2Y3OTQ3MzVlYW1zaDg3NzNlOTY5M2RjYTczMHAxNDNmNWZqc242ZGRiYjY3MGZkNzE=",
    "NWI1YjE2NTBmZG1zaGUxYTlmYjk2NjlkMWQ0MnAxZmZiYmVqc24xN2RiMjgxZGEyMjg=", "NmUzYjhhYjQ5Mm1zaGRmNzJhMzkxMjA4MjczYXAxYzBhODJqc24wNmIxM2EyZWFiMmQ=", "ODMyYzM4ZGRjZm1zaGVlNTNjZTk5ODNiNjJiZnAxODdmZDlqc24xODk3M2ExNDI0NDI=",
    "YTUyODE1MjZjNG1zaGZjOTlmNzJiMzE4MjJmMXAxNThjMTdqc24zZjM0ODJhNDE4NjI=", "NzMyNGRkMDBjNW1zaDc1MDQ3ZTNjNWRjY2ViN3AxMjEwZTJqc25hYzQzMGQ0ZjIxMzM=", "OWUwOTQxOTExYW1zaDU1MzdiZDhiZmYwYTRmNnAxZmFjYzJqc242MWZiNTRmOGI0NzQ=",
]
API_KEYS = ['AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'AIzaSyCtkvNIR1HCEwzsqK6JuE6KqpyjusIRI30', 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w', 'AIzaSyC8UYZpvA2eknNex0Pjid0_eTLJoDu6los', 'AIzaSyCjc_pVEDi4qsv5MtC2dMXzpIaDoRFLsxw', 'AIzaSyDHQ9ipnphqTzDqZsbtd8_Ru4_kiKVQe2k']
CLIENT_ID = '861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com'
CLIENT_SECRET = 'SboVhoG9s0rNafixCSGGKXAT'
DEFAULT_CLIENTS = {
    'WEB': {
        'innertube_context': {'context': {'client': {'clientName': 'WEB', 'osName': 'Windows', 'osVersion': '10.0', 'clientVersion': '2.20251021.01.00', 'platform': 'DESKTOP'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '1', 'X-Youtube-Client-Version': '2.20251021.01.00'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': True
    },
    'WEB_EMBED': {
        'innertube_context': {'context': {'client': {'clientName': 'WEB_EMBEDDED_PLAYER', 'osName': 'Windows', 'osVersion': '10.0', 'clientVersion': '2.20240530.02.00', 'clientScreen': 'EMBED'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '56'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': True
    },
    'WEB_MUSIC': {
        'innertube_context': {'context': {'client': {'clientName': 'WEB_REMIX', 'clientVersion': '1.20251013.03.00'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '67'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': True
    },
    'WEB_CREATOR': {
        'innertube_context': {'context': {'client': {'clientName': 'WEB_CREATOR', 'clientVersion': '1.20220726.00.00'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '62'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': False
    },
    'WEB_SAFARI': {
        'innertube_context': {'context': {'client': {'clientName': 'WEB', 'clientVersion': '2.20240726.00.00'}}},
        'header': {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15,gzip(gfe)', 'X-Youtube-Client-Name': '1'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': True
    },
    'MWEB': {
        'innertube_context': {'context': {'client': {'clientName': 'MWEB', 'clientVersion': '2.20251014.06.00'}}},
        'header': {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 16_7_10 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1,gzip(gfe)', 'X-Youtube-Client-Name': '2'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': True
    },
    'WEB_KIDS': {
        'innertube_context': {'context': {'client': {'clientName': 'WEB_KIDS', 'osName': 'Windows', 'osVersion': '10.0', 'clientVersion': '2.20241125.00.00', 'platform': 'DESKTOP'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '76', 'X-Youtube-Client-Version': '2.20241125.00.00'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': False
    },
    'ANDROID': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID', 'clientVersion': '19.44.38', 'platform': 'MOBILE', 'osName': 'Android', 'osVersion': '14', 'androidSdkVersion': '34'}}},
        'header': {'User-Agent': 'com.google.android.youtube/', 'X-Youtube-Client-Name': '3'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': True
    },
    'ANDROID_VR': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID_VR', 'clientVersion': '1.60.19', 'deviceMake': 'Oculus', 'deviceModel': 'Quest 3', 'osName': 'Android', 'osVersion': '12L', 'androidSdkVersion': '32'}}},
        'header': {'User-Agent': 'com.google.android.apps.youtube.vr.oculus/1.60.19 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip', 'X-Youtube-Client-Name': '28'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'ANDROID_MUSIC': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID_MUSIC', 'clientVersion': '7.27.52', 'androidSdkVersion': '30', 'osName': 'Android', 'osVersion': '11'}}},
        'header': {'User-Agent': 'com.google.android.apps.youtube.music/7.27.52 (Linux; U; Android 11) gzip', 'X-Youtube-Client-Name': '21'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'ANDROID_CREATOR': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID_CREATOR', 'clientVersion': '24.45.100', 'androidSdkVersion': '30', 'osName': 'Android', 'osVersion': '11'}}},
        'header': {'User-Agent': 'com.google.android.apps.youtube.creator/24.45.100 (Linux; U; Android 11) gzip', 'X-Youtube-Client-Name': '14'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'ANDROID_TESTSUITE': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID_TESTSUITE', 'clientVersion': '1.9', 'platform': 'MOBILE', 'osName': 'Android', 'osVersion': '14', 'androidSdkVersion': '34'}}},
        'header': {'User-Agent': 'com.google.android.youtube/', 'X-Youtube-Client-Name': '30', 'X-Youtube-Client-Version': '1.9'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'ANDROID_PRODUCER': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID_PRODUCER', 'clientVersion': '0.111.1', 'androidSdkVersion': '30', 'osName': 'Android', 'osVersion': '11'}}},
        'header': {'User-Agent': 'com.google.android.apps.youtube.producer/0.111.1 (Linux; U; Android 11) gzip', 'X-Youtube-Client-Name': '91'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'ANDROID_KIDS': {
        'innertube_context': {'context': {'client': {'clientName': 'ANDROID_KIDS', 'clientVersion': '7.36.1', 'androidSdkVersion': '30', 'osName': 'Android', 'osVersion': '11'}}},
        'header': {'User-Agent': 'com.google.android.apps.youtube.music/7.27.52 (Linux; U; Android 11) gzip'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'IOS': {
        'innertube_context': {'context': {'client': {'clientName': 'IOS', 'clientVersion': '19.45.4', 'deviceMake': 'Apple', 'platform': 'MOBILE', 'osName': 'iPhone', 'osVersion': '18.1.0.22B83', 'deviceModel': 'iPhone16,2'}}},
        'header': {'User-Agent': 'com.google.ios.youtube/19.45.4 (iPhone16,2; U; CPU iOS 18_1_0 like Mac OS X;)', 'X-Youtube-Client-Name': '5'},
        'api_key': 'AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc', 'require_js_player': False, 'require_po_token': False
    },
    'IOS_MUSIC': {
        'innertube_context': {'context': {'client': {'clientName': 'IOS_MUSIC', 'clientVersion': '7.27.0', 'deviceMake': 'Apple', 'platform': 'MOBILE', 'osName': 'iPhone', 'osVersion': '18.1.0.22B83', 'deviceModel': 'iPhone16,2'}}},
        'header': {'User-Agent': 'com.google.ios.youtubemusic/7.27.0 (iPhone16,2; U; CPU iOS 18_1_0 like Mac OS X;)', 'X-Youtube-Client-Name': '26'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'IOS_CREATOR': {
        'innertube_context': {'context': {'client': {'clientName': 'IOS_CREATOR', 'clientVersion': '24.45.100', 'deviceMake': 'Apple', 'deviceModel': 'iPhone16,2', 'osName': 'iPhone', 'osVersion': '18.1.0.22B83'}}},
        'header': {'User-Agent': 'com.google.ios.ytcreator/24.45.100 (iPhone16,2; U; CPU iOS 18_1_0 like Mac OS X;)', 'X-Youtube-Client-Name': '15'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    },
    'IOS_KIDS': {
        'innertube_context': {'context': {'client': {'clientName': 'IOS_KIDS', 'clientVersion': '7.36.1', 'deviceMake': 'Apple', 'platform': 'MOBILE', 'osName': 'iPhone', 'osVersion': '18.1.0.22B83', 'deviceModel': 'iPhone16,2'}}},
        'header': {'User-Agent': 'com.google.ios.youtube/19.45.4 (iPhone16,2; U; CPU iOS 18_1_0 like Mac OS X;)'},
        'api_key': 'AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc', 'require_js_player': False, 'require_po_token': False
    },
    'TV': {
        'innertube_context': {'context': {'client': {'clientName': 'TVHTML5', 'clientVersion': '7.20240813.07.00', 'platform': 'TV'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '7'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': False
    },
    'TV_EMBED': {
        'innertube_context': {'context': {'client': {'clientName': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER', 'clientVersion': '2.0', 'clientScreen': 'EMBED', 'platform': 'TV'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '85'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': True, 'require_po_token': False
    },
    'MEDIA_CONNECT': {
        'innertube_context': {'context': {'client': {'clientName': 'MEDIA_CONNECT_FRONTEND', 'clientVersion': '0.1'}}},
        'header': {'User-Agent': 'Mozilla/5.0', 'X-Youtube-Client-Name': '95'},
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', 'require_js_player': False, 'require_po_token': False
    }
}


'''assertuint32'''
def assertuint32(value):
    if not (0 <= value <= 0xFFFFFFFF): raise ValueError("Value is not a valid uint32")


'''assertint32'''
def assertint32(value):
    if not (-0x80000000 <= value <= 0x7FFFFFFF): raise ValueError("Value is not a valid int32")


'''varint32write'''
def varint32write(value, buf: list):
    while value > 0x7F:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value)


'''varint64write'''
def varint64write(lo, hi, buf: list):
    for _ in range(9):
        if hi == 0 and lo < 0x80:
            buf.append(lo)
            return
        buf.append((lo & 0x7F) | 0x80)
        lo = ((hi << 25) | (lo >> 7)) & 0xFFFFFFFF
        hi = hi >> 7
    buf.append(lo)


'''readvarint32'''
def readvarint32(buf: bytes, pos: int):
    result = shift = 0
    while True:
        if pos >= len(buf): raise EOFError("Unexpected end of buffer while reading varint32")
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
        if shift > 35: raise ValueError("Varint32 too long")
    return result, pos


'''readvarint64'''
def readvarint64(buf, pos):
    low_bits, high_bits = 0, 0
    for shift in range(0, 28, 7):
        b = buf[pos]
        pos += 1
        low_bits |= (b & 0x7F) << shift
        if (b & 0x80) == 0: return low_bits, high_bits, pos
    middle_byte = buf[pos]
    pos += 1
    low_bits |= (middle_byte & 0x0F) << 28
    high_bits = (middle_byte & 0x70) >> 4
    if (middle_byte & 0x80) == 0: return low_bits, high_bits, pos
    for shift in range(3, 32, 7):
        b = buf[pos]
        pos += 1
        high_bits |= (b & 0x7F) << shift
        if (b & 0x80) == 0: return low_bits, high_bits, pos
    raise ValueError("invalid varint")


'''decodeint64'''
def decodeint64(lo: int, hi: int):
    value = (hi << 32) | lo
    if hi & 0x80000000: value -= 1 << 64
    return value


'''decodeuint64'''
def decodeuint64(lo: int, hi: int):
    return (hi << 32) | lo


'''longtonumber'''
def longtonumber(int64_value):
    value = int(str(int64_value))
    if value > (2 ** 53 - 1): raise OverflowError("Value is larger than 9007199254740991")
    if value < -(2 ** 53 - 1): raise OverflowError("Value is smaller than -9007199254740991")
    return value


'''targetdirectory'''
def targetdirectory(output_path: Optional[str] = None):
    if output_path:
        if not os.path.isabs(output_path): output_path = os.path.join(os.getcwd(), output_path)
    else:
        output_path = os.getcwd()
    os.makedirs(output_path, exist_ok=True)
    return output_path


'''regexsearch'''
def regexsearch(pattern: str, string: str, group: int):
    regex = re.compile(pattern)
    results = regex.search(string)
    return results.group(group)


'''filesystemverify'''
def filesystemverify(file_type):
    # systems
    bsd_unix = ['BSD', 'UFS']
    mac_os = ['macOS', 'APFS', 'HFS+']
    network_filesystems = ['CIFS', 'SMB']
    windows = ['Windows', 'NTFS', 'FAT32', 'exFAT', 'ReFS']
    linux = ['Linux', 'ext2', 'ext3', 'ext4', 'Btrfs', 'XFS', 'ZFS']
    # return translations
    if file_type in windows: return str.maketrans({'\\': '', '/': '', '?': '', ':': '', '*': '', '"': '', '<': '', '>': '', '|': ''})
    elif file_type in linux: return str.maketrans({'/': ''})
    elif file_type in mac_os: return str.maketrans({'/': ''})
    elif file_type in bsd_unix: return str.maketrans({'/': ''})
    elif file_type in network_filesystems: return str.maketrans({'\\': '', '/': '', '?': '', ':': '', '*': '', '"': '', '<': '', '>': '', '|': ''})


'''mimetypecodec'''
def mimetypecodec(mime_type_codec: str):
    pattern = r"(\w+\/\w+)\;\scodecs=\"([a-zA-Z-0-9.,\s]*)\""
    regex = re.compile(pattern)
    results = regex.search(mime_type_codec)
    mime_type, codecs = results.groups()
    return mime_type, [c.strip() for c in codecs.split(",")]


'''getformatprofile'''
def getformatprofile(itag: str):
    # constants
    PROGRESSIVE_VIDEO = {
        5: ("240p", "64kbps"), 6: ("270p", "64kbps"), 13: ("144p", None), 17: ("144p", "24kbps"), 18: ("360p", "96kbps"), 22: ("720p", "192kbps"),
        34: ("360p", "128kbps"), 35: ("480p", "128kbps"), 36: ("240p", None), 37: ("1080p", "192kbps"), 38: ("3072p", "192kbps"), 43: ("360p", "128kbps"),
        44: ("480p", "128kbps"), 45: ("720p", "192kbps"), 46: ("1080p", "192kbps"), 59: ("480p", "128kbps"), 78: ("480p", "128kbps"), 82: ("360p", "128kbps"),
        83: ("480p", "128kbps"), 84: ("720p", "192kbps"), 85: ("1080p", "192kbps"), 91: ("144p", "48kbps"), 92: ("240p", "48kbps"), 93: ("360p", "128kbps"),
        94: ("480p", "128kbps"), 95: ("720p", "256kbps"), 96: ("1080p", "256kbps"), 100: ("360p", "128kbps"), 101: ("480p", "192kbps"), 102: ("720p", "192kbps"),
        132: ("240p", "48kbps"), 151: ("720p", "24kbps"), 300: ("720p", "128kbps"), 301: ("1080p", "128kbps"),
    }
    DASH_VIDEO = {
        133: ("240p", None), 134: ("360p", None), 135: ("480p", None), 136: ("720p", None), 137: ("1080p", None), 138: ("2160p", None), 160: ("144p", None),
        167: ("360p", None), 168: ("480p", None), 169: ("720p", None), 170: ("1080p", None), 212: ("480p", None), 218: ("480p", None), 219: ("480p", None),
        242: ("240p", None), 243: ("360p", None), 244: ("480p", None), 245: ("480p", None), 246: ("480p", None), 247: ("720p", None), 248: ("1080p", None), 
        264: ("1440p", None), 266: ("2160p", None), 271: ("1440p", None), 272: ("4320p", None), 278: ("144p", None), 298: ("720p", None), 299: ("1080p", None),  
        302: ("720p", None), 303: ("1080p", None), 308: ("1440p", None), 313: ("2160p", None), 315: ("2160p", None), 330: ("144p", None), 331: ("240p", None),
        332: ("360p", None), 333: ("480p", None), 334: ("720p", None), 335: ("1080p", None), 336: ("1440p", None), 337: ("2160p", None), 394: ("144p", None), 
        395: ("240p", None), 396: ("360p", None), 397: ("480p", None), 398: ("720p", None), 399: ("1080p", None), 400: ("1440p", None), 401: ("2160p", None), 
        402: ("4320p", None), 571: ("4320p", None), 694: ("144p", None), 695: ("240p", None), 696: ("360p", None), 697: ("480p", None), 698: ("720p", None), 
        699: ("1080p", None), 700: ("1440p", None), 701: ("2160p", None), 702: ("4320p", None),
    }
    DASH_AUDIO = {
        139: (None, "48kbps"), 140: (None, "128kbps"), 141: (None, "256kbps"), 171: (None, "128kbps"), 172: (None, "256kbps"), 249: (None, "50kbps"), 
        250: (None, "70kbps"), 251: (None, "160kbps"), 256: (None, "192kbps"), 258: (None, "384kbps"), 325: (None, None), 328: (None, None), 
    }
    ITAGS = {**PROGRESSIVE_VIDEO, **DASH_VIDEO, **DASH_AUDIO}
    HDR = [330, 331, 332, 333, 334, 335, 336, 337]
    _3D = [82, 83, 84, 85, 100, 101, 102]
    LIVE = [91, 92, 93, 94, 95, 96, 132, 151]
    # parse
    itag = int(itag)
    res, bitrate = ITAGS[itag] if itag in ITAGS else (None, None)
    return {"resolution": res, "abr": bitrate, "is_live": itag in LIVE, "is_3d": itag in _3D, "is_hdr": itag in HDR, "is_dash": (itag in DASH_AUDIO or itag in DASH_VIDEO)}


'''defaultoauthverifier'''
def defaultoauthverifier(verification_url: str, user_code: str):
    print(f'Please open {verification_url} and input code {user_code}')
    input('Press enter when you have completed this step.')


'''defaultpotokenverifier'''
def defaultpotokenverifier():
    print('You can use the tool: https://github.com/YunzheZJU/youtube-po-token-generator, to get the token')
    visitor_data = str(input("Enter with your visitorData: "))
    po_token = str(input("Enter with your po_token: "))
    return visitor_data, po_token


'''isagerestricted'''
def isagerestricted(watch_html: str):
    try:
        regexsearch(r"og:restrictions:age", watch_html, group=0)
    except:
        return False
    return True


'''getytplayerjs'''
def getytplayerjs(html: str):
    js_url_patterns = [r"(/s/player/[\w\d]+/[\w\d_/.]+/base\.js)"]
    for pattern in js_url_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(html)
        if function_match:
            yt_player_js = function_match.group(1)
            return yt_player_js


'''findobjectfromstartpoint'''
def findobjectfromstartpoint(html, start_point):
    html, last_char, curr_char = html[start_point:], '{', None
    stack, i, context_closers = [html[0]], 1, {'{': '}', '[': ']', '"': '"', '\'': '\'', '/': '/'}
    while i < len(html):
        if not stack: break
        if curr_char not in [' ', '\n']: last_char = curr_char
        curr_char = html[i]
        curr_context = stack[-1]
        if curr_char == context_closers[curr_context]:
            stack.pop()
            i += 1
            continue
        if curr_context in ['"', '\'', '/']:
            if curr_char == '\\':
                i += 2
                continue
        else:
            if curr_char in context_closers.keys():
                if not (curr_char == '/' and last_char not in ['(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';']): 
                    stack.append(curr_char)
        i += 1
    full_obj = html[:i]
    return full_obj


'''parseforobjectfromstartpoint'''
def parseforobjectfromstartpoint(html, start_point):
    full_obj = findobjectfromstartpoint(html, start_point)
    try:
        return json.loads(full_obj)
    except:
        try:
            return ast.literal_eval(full_obj)
        except:
            raise Exception


'''parseforobject'''
def parseforobject(html, preceding_regex):
    regex = re.compile(preceding_regex)
    result = regex.search(html)
    start_index = result.end()
    return parseforobjectfromstartpoint(html, start_index)


'''getytplayerconfig'''
def getytplayerconfig(html: str):
    config_patterns = [r"ytplayer\.config\s*=\s*", r"ytInitialPlayerResponse\s*=\s*"]
    for pattern in config_patterns:
        try:
            return parseforobject(html, pattern)
        except:
            continue
    setconfig_patterns = [r"yt\.setConfig\(.*['\"]PLAYER_CONFIG['\"]:\s*"]
    for pattern in setconfig_patterns:
        try:
            return parseforobject(html, pattern)
        except:
            continue


'''extractjsurl'''
def extractjsurl(html: str):
    try:
        base_js = getytplayerconfig(html)['assets']['js']
    except:
        base_js = getytplayerjs(html)
    return f"https://youtube.com{base_js}"


'''extractsignaturetimestamp'''
def extractsignaturetimestamp(js: str):
    return regexsearch(r"signatureTimestamp:(\d*)", js, group=1)


'''extractvisitordata'''
def extractvisitordata(resp_context: str):
    return regexsearch(r"visitor_data[',\"\s]+value['\"]:\s?['\"]([a-zA-Z0-9_%-]+)['\"]", resp_context, group=1)


'''extractinitialdata'''
def extractinitialdata(watch_html: str):
    patterns = [r"window\[['\"]ytInitialData['\"]]\s*=\s*", r"ytInitialData\s*=\s*"]
    for pattern in patterns:
        try:
            return parseforobject(watch_html, pattern)
        except:
            pass


'''extractmetadata'''
def extractmetadata(initial_data):
    try:
        metadata_rows = initial_data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"][1]["videoSecondaryInfoRenderer"]["metadataRowContainer"]["metadataRowContainerRenderer"]["rows"]
    except:
        YouTubeMetadata([])
    metadata_rows = filter(lambda x: "metadataRowRenderer" in x.keys(), metadata_rows)
    metadata_rows = [x["metadataRowRenderer"] for x in metadata_rows]
    return YouTubeMetadata(metadata_rows)


'''applydescrambler'''
def applydescrambler(stream_data: dict):
    if 'url' in stream_data: return None
    formats = []
    if 'formats' in stream_data.keys(): formats.extend(stream_data['formats'])
    if 'adaptiveFormats' in stream_data.keys(): formats.extend(stream_data['adaptiveFormats'])
    for data in formats:
        if 'url' not in data and 'signatureCipher' in data:
            cipher_url = parse_qs(data['signatureCipher'])
            data['url'] = cipher_url['url'][0]
            data['s'] = cipher_url['s'][0]
            data['is_sabr'] = False
        elif 'url' not in data and 'signatureCipher' not in data:
            data['url'] = stream_data['serverAbrStreamingUrl']
            data['is_sabr'] = True
        data['is_otf'] = data.get('type') == 'FORMAT_STREAM_TYPE_OTF'
    return formats


'''applypotoken'''
def applypotoken(stream_manifest, vid_info: dict, po_token: str):
    for i, stream in enumerate(stream_manifest):
        url: str = stream["url"]
        parsed_url = urlparse(url)
        query_params = parse_qs(urlparse(url).query)
        query_params = {k: v[0] for k, v in query_params.items()}
        query_params['pot'] = po_token
        url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{urlencode(query_params)}'
        stream_manifest[i]["url"] = url


'''generatepotoken'''
def generatepotoken(video_id: str):
    import nodejs_wheel.executable
    suffix = ".exe" if os.name == "nt" else ""
    bin_dir = nodejs_wheel.executable.ROOT_DIR if os.name == "nt" else os.path.join(nodejs_wheel.executable.ROOT_DIR, "bin")
    try:
        result = subprocess.check_output([os.path.join(bin_dir, 'node' + suffix), str(Path(__file__).resolve().parent.parent / "js" / "youtube" / "botguard.js"), video_id], stderr=subprocess.PIPE).decode()
        return result.replace("\n", "")
    except Exception as err:
        raise RuntimeError(err)


'''extractsignaturetimestamp'''
def extractsignaturetimestamp(js: str):
    return regexsearch(r"signatureTimestamp:(\d*)", js, group=1)


'''applysignature'''
def applysignature(stream_manifest: Dict, vid_info: Dict, js: str, url_js: str):
    cipher = Cipher(js=js, js_url=url_js)
    discovered_n = dict()
    for i, stream in enumerate(stream_manifest):
        try:
            url: str = stream["url"]
        except KeyError:
            live_stream = (vid_info.get("playabilityStatus", {}, ).get("liveStreamability"))
            if live_stream: raise Exception
        parsed_url = urlparse(url)
        query_params = parse_qs(urlparse(url).query)
        query_params = {k: v[0] for k, v in query_params.items()}
        if "signature" in url or ("s" not in stream and ("&sig=" in url or "&lsig=" in url)):
            pass
        else:
            signature = cipher.getsig(ciphered_signature=stream["s"])
            query_params['sig'] = signature
        if 'n' in query_params.keys():
            initial_n = query_params['n']
            if initial_n not in discovered_n: discovered_n[initial_n] = cipher.getnsig(initial_n)
            else: pass
            new_n = discovered_n[initial_n]
            query_params['n'] = new_n
        url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{urlencode(query_params)}'
        stream_manifest[i]["url"] = url
    cipher.runner_sig.close()
    cipher.runner_nsig.close()


'''ProtoInt64'''
class ProtoInt64:
    '''enc'''
    @staticmethod
    def enc(value: int):
        if value < 0: value += 1 << 64
        lo = value & 0xFFFFFFFF
        hi = (value >> 32) & 0xFFFFFFFF
        return {'lo': lo, 'hi': hi}
    '''uenc'''
    @staticmethod
    def uenc(value: int):
        lo = value & 0xFFFFFFFF
        hi = (value >> 32) & 0xFFFFFFFF
        return {'lo': lo, 'hi': hi}


'''RequestWrapper'''
class RequestWrapper:
    default_range_size = 9437184
    '''_executerequest'''
    @staticmethod
    def _executerequest(url: str, method=None, headers=None, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}
        if headers: base_headers.update(headers)
        if data and not isinstance(data, bytes): data = bytes(json.dumps(data), encoding="utf-8")
        if url.lower().startswith("http"): request = Request(url, headers=base_headers, method=method, data=data)
        else: raise ValueError("Invalid URL")
        return urlopen(request, timeout=timeout)
    '''get'''
    @staticmethod
    def get(url, extra_headers=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        if extra_headers is None: extra_headers = {}
        resp = RequestWrapper._executerequest(url, headers=extra_headers, timeout=timeout)
        return resp.read().decode("utf-8")
    '''post'''
    @staticmethod
    def post(url, extra_headers=None, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        if extra_headers is None: extra_headers = {}
        if data is None: data = {}
        extra_headers.update({"Content-Type": "application/json"})
        resp = RequestWrapper._executerequest(url, headers=extra_headers, data=data, timeout=timeout)
        return resp.read().decode("utf-8")
    '''seqstream'''
    @staticmethod
    def seqstream(url, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, max_retries=0):
        split_url = parse.urlsplit(url)
        base_url = f'{split_url.scheme}://{split_url.netloc}/{split_url.path}?'
        querys = dict(parse.parse_qsl(split_url.query))
        querys['sq'] = 0
        url = base_url + parse.urlencode(querys)
        segment_data = b''
        for chunk in RequestWrapper.stream(url, timeout=timeout, max_retries=max_retries):
            yield chunk
            segment_data += chunk
        stream_info = segment_data.split(b'\r\n')
        segment_count_pattern = re.compile(b'Segment-Count: (\\d+)')
        for line in stream_info:
            match = segment_count_pattern.search(line)
            if match: segment_count = int(match.group(1).decode('utf-8'))
        seq_num = 1
        while seq_num <= segment_count:
            querys['sq'] = seq_num
            url = base_url + parse.urlencode(querys)
            yield from RequestWrapper.stream(url, timeout=timeout, max_retries=max_retries)
            seq_num += 1
        return
    '''stream'''
    @staticmethod
    def stream(url, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, max_retries=0):
        downloaded = 0
        file_size: int = RequestWrapper.default_range_size
        while downloaded < file_size:
            stop_pos, tries = min(downloaded + RequestWrapper.default_range_size, file_size) - 1, 0
            while True:
                if tries >= 1 + max_retries: raise HTTPError()
                try:
                    resp = RequestWrapper._executerequest(f"{url}&range={downloaded}-{stop_pos}", method="GET", timeout=timeout)
                except URLError as e:
                    if not isinstance(e.reason, (socket.timeout, OSError)): raise Exception
                except http.client.IncompleteRead: pass
                else: break
                tries += 1
            if file_size == RequestWrapper.default_range_size:
                try:
                    content_range = RequestWrapper._executerequest(f"{url}&range=0-99999999999", method="GET", timeout=timeout).info()["Content-Length"]
                    file_size = int(content_range)
                except (KeyError, IndexError, ValueError) as e:
                    pass
            while True:
                try: chunk = resp.read()
                except StopIteration: return
                except http.client.IncompleteRead as e: chunk = e.partial
                if not chunk: break
                if chunk: downloaded += len(chunk)
                yield chunk
        return
    '''filesize'''
    @staticmethod
    @lru_cache()
    def filesize(url): return int(RequestWrapper.head(url)["content-length"])
    '''seqfilesize'''
    @staticmethod
    @lru_cache()
    def seqfilesize(url):
        total_filesize = 0
        split_url = parse.urlsplit(url)
        base_url = f'{split_url.scheme}://{split_url.netloc}/{split_url.path}?'
        querys = dict(parse.parse_qsl(split_url.query))
        querys['sq'] = 0
        url = base_url + parse.urlencode(querys)
        resp = RequestWrapper._executerequest(url, method="GET")
        resp_value = resp.read()
        total_filesize += len(resp_value)
        segment_count = 0
        stream_info = resp_value.split(b'\r\n')
        segment_regex = b'Segment-Count: (\\d+)'
        for line in stream_info:
            try: segment_count = int(regexsearch(segment_regex, line, 1))
            except: pass
        if segment_count == 0: raise Exception
        seq_num = 1
        while seq_num <= segment_count:
            querys['sq'] = seq_num
            url = base_url + parse.urlencode(querys)
            total_filesize += int(RequestWrapper.head(url)['content-length'])
            seq_num += 1
        return total_filesize
    '''head'''
    @staticmethod
    def head(url: str):
        resp_headers: dict = RequestWrapper._executerequest(url, method="HEAD").info()
        return {k.lower(): v for k, v in resp_headers.items()}


'''NodeRunner'''
class NodeRunner:
    def __init__(self, code: str):
        self.code = code
        self.function_name = None
        self.proc = subprocess.Popen([self._nodepath(), str(Path(__file__).resolve().parent.parent / "js" / "youtube" / "runner.js")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    '''_nodepath'''
    @staticmethod
    def _nodepath():
        import nodejs_wheel.executable
        suffix = ".exe" if os.name == "nt" else ""
        bin_dir = nodejs_wheel.executable.ROOT_DIR if os.name == "nt" else os.path.join(nodejs_wheel.executable.ROOT_DIR, "bin")
        return os.path.join(bin_dir, 'node' + suffix)
    '''_exposed'''
    @staticmethod
    def _exposed(code: str, fun_name: str):
        exposed = f"_exposed['{fun_name}']={fun_name};" + "})(_yt_player);"
        return code.replace("})(_yt_player);", exposed)
    '''_send'''
    def _send(self, data):
        self.proc.stdin.write(json.dumps(data) + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())
    '''loadfunction'''
    def loadfunction(self, function_name: str):
        self.function_name = function_name
        return self._send({"type": "load", "code": self._exposed(self.code, function_name)})
    '''call'''
    def call(self, args: list):
        return self._send({"type": "call", "fun": self.function_name, "args": args or []})
    '''close'''
    def close(self):
        self.proc.stdin.close()
        self.proc.terminate()
        self.proc.wait()


'''PART'''
class PART(Enum):
    ONESIE_HEADER = 10
    ONESIE_DATA = 11
    MEDIA_HEADER = 20
    MEDIA = 21
    MEDIA_END = 22
    LIVE_METADATA = 31
    HOSTNAME_CHANGE_HINT = 32
    LIVE_METADATA_PROMISE = 33
    LIVE_METADATA_PROMISE_CANCELLATION = 34
    NEXT_REQUEST_POLICY = 35
    USTREAMER_VIDEO_AND_FORMAT_DATA = 36
    FORMAT_SELECTION_CONFIG = 37
    USTREAMER_SELECTED_MEDIA_STREAM = 38
    FORMAT_INITIALIZATION_METADATA = 42
    SABR_REDIRECT = 43
    SABR_ERROR = 44
    SABR_SEEK = 45
    RELOAD_PLAYER_RESPONSE = 46
    PLAYBACK_START_POLICY = 47
    ALLOWED_CACHED_FORMATS = 48
    START_BW_SAMPLING_HINT = 49
    PAUSE_BW_SAMPLING_HINT = 50
    SELECTABLE_FORMATS = 51
    REQUEST_IDENTIFIER = 52
    REQUEST_CANCELLATION_POLICY = 53
    ONESIE_PREFETCH_REJECTION = 54
    TIMELINE_CONTEXT = 55
    REQUEST_PIPELINING = 56
    SABR_CONTEXT_UPDATE = 57
    STREAM_PROTECTION_STATUS = 58
    SABR_CONTEXT_SENDING_POLICY = 59
    LAWNMOWER_POLICY = 60
    SABR_ACK = 61
    END_OF_TRACK = 62
    CACHE_LOAD_POLICY = 63
    LAWNMOWER_MESSAGING_POLICY = 64
    PREWARM_CONNECTION = 65
    PLAYBACK_DEBUG_INFO = 66
    SNACKBAR_MESSAGE = 67


'''PoTokenStatus'''
class PoTokenStatus(Enum):
    UNKNOWN = -1
    OK = enum.auto()
    MISSING = enum.auto()
    INVALID = enum.auto()
    PENDING = enum.auto()
    NOT_REQUIRED = enum.auto()
    PENDING_MISSING = enum.auto()


'''Monostate'''
class Monostate:
    def __init__(self, on_progress: Optional[Callable[[Any, bytes, int], None]], on_complete: Optional[Callable[[Any, Optional[str]], None]], 
                 title: Optional[str] = None, duration: Optional[int] = None, youtube = None):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.title = title
        self.duration = duration
        self.youtube = youtube


'''ChunkedDataBuffer'''
class ChunkedDataBuffer:
    def __init__(self, chunks=None):
        self.chunks = []
        self.current_chunk_index = 0
        self.current_chunk_offset = 0
        self.current_data_view = None
        self.total_length = 0
        chunks = chunks or []
        for chunk in chunks: self.append(chunk)
    '''getlength'''
    def getlength(self):
        return self.total_length
    '''append'''
    def append(self, chunk):
        if self.canmergewithlastchunk(chunk):
            last_chunk = self.chunks[-1]
            merged = bytearray(last_chunk)
            merged.extend(chunk)
            self.chunks[-1] = bytes(merged)
            self.resetfocus()
        else:
            self.chunks.append(chunk)
        self.total_length += len(chunk)
    '''split'''
    def split(self, position):
        extracted_buffer, remaining_buffer, remaining_pos = ChunkedDataBuffer(), ChunkedDataBuffer(), position
        for chunk in self.chunks:
            chunk_len = len(chunk)
            if remaining_pos >= chunk_len:
                extracted_buffer.append(chunk)
                remaining_pos -= chunk_len
            elif remaining_pos > 0:
                extracted_buffer.append(chunk[:remaining_pos])
                remaining_buffer.append(chunk[remaining_pos:])
                remaining_pos = 0
            else:
                remaining_buffer.append(chunk)
        return {"extracted_buffer": extracted_buffer, "remaining_buffer": remaining_buffer}
    '''isfocused'''
    def isfocused(self, position):
        chunk = self.chunks[self.current_chunk_index]
        return self.current_chunk_offset <= position < self.current_chunk_offset + len(chunk)
    '''focus'''
    def focus(self, position):
        if not self.isfocused(position):
            if position < self.current_chunk_offset: self.resetfocus()
            while (self.current_chunk_offset + len(self.chunks[self.current_chunk_index]) <= position and self.current_chunk_index < len(self.chunks) - 1):
                self.current_chunk_offset += len(self.chunks[self.current_chunk_index])
                self.current_chunk_index += 1
            self.current_data_view = None
    '''canreadbytes'''
    def canreadbytes(self, position, length):
        return position + length <= self.total_length
    '''getuint8'''
    def getuint8(self, position):
        self.focus(position)
        chunk = self.chunks[self.current_chunk_index]
        return chunk[position - self.current_chunk_offset]
    '''canmergewithlastchunk'''
    def canmergewithlastchunk(self, chunk):
        if not self.chunks: return False
        last_chunk = self.chunks[-1]
        return (last_chunk is not None and isinstance(last_chunk, (bytes, bytearray)) and isinstance(chunk, (bytes, bytearray)))
    '''resetfocus'''
    def resetfocus(self):
        self.current_data_view = None
        self.current_chunk_index = 0
        self.current_chunk_offset = 0


'''UMP'''
class UMP:
    def __init__(self, chunked_data_buffer: ChunkedDataBuffer):
        self.chunked_data_buffer = chunked_data_buffer
    '''parse'''
    def parse(self, handle_part):
        while True:
            offset = 0
            part_type, new_offset = self.readvarint(offset)
            offset = new_offset
            part_size, final_offset = self.readvarint(offset)
            offset = final_offset
            if part_type < 0 or part_size < 0: break
            if not self.chunked_data_buffer.canreadbytes(offset, part_size):
                if not self.chunked_data_buffer.canreadbytes(offset, 1): break
                return {"type": part_type, "size": part_size, "data": self.chunked_data_buffer}
            split_result = self.chunked_data_buffer.split(offset)['remaining_buffer'].split(part_size)
            offset = 0
            handle_part({"type": part_type, "size": part_size, "data": split_result['extracted_buffer']})
            self.chunked_data_buffer = split_result['remaining_buffer']
    '''readvarint'''
    def readvarint(self, offset):
        if self.chunked_data_buffer.canreadbytes(offset, 1):
            first_byte = self.chunked_data_buffer.getuint8(offset)
            if first_byte < 128: byte_length = 1
            elif first_byte < 192: byte_length = 2
            elif first_byte < 224: byte_length = 3
            elif first_byte < 240: byte_length = 4
            else: byte_length = 5
        else:
            byte_length = 0
        if byte_length < 1 or not self.chunked_data_buffer.canreadbytes(offset, byte_length): return -1, offset
        if byte_length == 1:
            value = self.chunked_data_buffer.getuint8(offset)
            offset += 1
        elif byte_length == 2:
            byte1 = self.chunked_data_buffer.getuint8(offset)
            byte2 = self.chunked_data_buffer.getuint8(offset + 1)
            value = (byte1 & 0x3F) + 64 * byte2
            offset += 2
        elif byte_length == 3:
            byte1 = self.chunked_data_buffer.getuint8(offset)
            byte2 = self.chunked_data_buffer.getuint8(offset + 1)
            byte3 = self.chunked_data_buffer.getuint8(offset + 2)
            value = (byte1 & 0x1F) + 32 * (byte2 + 256 * byte3)
            offset += 3
        elif byte_length == 4:
            byte1 = self.chunked_data_buffer.getuint8(offset)
            byte2 = self.chunked_data_buffer.getuint8(offset + 1)
            byte3 = self.chunked_data_buffer.getuint8(offset + 2)
            byte4 = self.chunked_data_buffer.getuint8(offset + 3)
            value = (byte1 & 0x0F) + 16 * (byte2 + 256 * (byte3 + 256 * byte4))
            offset += 4
        else:
            temp_offset = offset + 1
            self.chunked_data_buffer.focus(temp_offset)
            if self.canreadfromcurrentchunk(temp_offset, 4):
                view = self.getcurrentdataview()
                offset_in_chunk = temp_offset - self.chunked_data_buffer.current_chunk_offset
                value = int.from_bytes(view[offset_in_chunk:offset_in_chunk + 4], byteorder='little')
            else:
                byte3 = (self.chunked_data_buffer.getuint8(temp_offset + 2) + 256 * self.chunked_data_buffer.getuint8(temp_offset + 3))
                value = (self.chunked_data_buffer.getuint8(temp_offset) + 256 * (self.chunked_data_buffer.getuint8(temp_offset + 1) + 256 * byte3))
            offset += 5
        return value, offset
    '''canreadfromcurrentchunk'''
    def canreadfromcurrentchunk(self, offset, length):
        index = self.chunked_data_buffer.current_chunk_index
        current_chunk = self.chunked_data_buffer.chunks[index]
        return (offset - self.chunked_data_buffer.current_chunk_offset + length <= len(current_chunk))
    '''getcurrentdataview'''
    def getcurrentdataview(self):
        if self.chunked_data_buffer.current_data_view is None:
            chunk = self.chunked_data_buffer.chunks[self.chunked_data_buffer.current_chunk_index]
            self.chunked_data_buffer.current_data_view = memoryview(chunk)
        return self.chunked_data_buffer.current_data_view


'''Stream'''
class Stream:
    def __init__(self, stream: Dict, monostate: Monostate, po_token: str, video_playback_ustreamer_config: str):
        self._monostate = monostate
        self.url = stream["url"]
        self.itag = int(stream["itag"])
        self.xtags = stream["xtags"] if "xtags" in stream else None
        self.mime_type, self.codecs = mimetypecodec(stream["mimeType"])
        self.type, self.subtype = self.mime_type.split("/")
        self.video_codec, self.audio_codec = self.parsecodecs()
        self.is_otf: bool = stream["is_otf"]
        self.bitrate: Optional[int] = stream["bitrate"]
        self._filesize: Optional[int] = int(stream.get('contentLength', 0))
        self._filesize_kb: Optional[float] = float(math.ceil(float(stream.get('contentLength', 0)) / 1024 * 1000) / 1000)
        self._filesize_mb: Optional[float] = float(math.ceil(float(stream.get('contentLength', 0)) / 1024 / 1024 * 1000) / 1000)
        self._filesize_gb: Optional[float] = float(math.ceil(float(stream.get('contentLength', 0)) / 1024 / 1024 / 1024 * 1000) / 1000)
        itag_profile = getformatprofile(self.itag)
        self.is_dash = itag_profile["is_dash"]
        self.abr = itag_profile["abr"]
        if 'fps' in stream: self.fps = stream['fps']
        self.resolution = itag_profile["resolution"]
        self._width = stream["width"] if 'width' in stream else None
        self._height = stream["height"] if 'height' in stream else None
        self.is_3d = itag_profile["is_3d"]
        self.is_hdr = itag_profile["is_hdr"]
        self.is_live = itag_profile["is_live"]
        self.is_drc = stream.get('isDrc', False)
        self._is_sabr = stream.get('is_sabr', False)
        self.durationMs = stream['approxDurationMs']
        self.last_Modified = stream['lastModified']
        self.po_token = po_token
        self.video_playback_ustreamer_config = video_playback_ustreamer_config
        self.includes_multiple_audio_tracks: bool = 'audioTrack' in stream
        if self.includes_multiple_audio_tracks:
            self.is_default_audio_track = "original" in stream['audioTrack']['displayName']
            self.audio_track_name_regionalized = str(stream['audioTrack']['displayName']).replace(" original", "")
            self.audio_track_name = self.audio_track_name_regionalized.split(" ")[0]
            self.audio_track_language_id_regionalized= str(stream['audioTrack']['id']).split(".")[0]
            self.audio_track_language_id= self.audio_track_language_id_regionalized.split("-")[0] 
        else:
            self.is_default_audio_track = self.includesaudiotrack and not self.includesvideotrack
            self.audio_track_name_regionalized = None
            self.audio_track_name = None
            self.audio_track_language_id_regionalized = None
            self.audio_track_language_id= None
    '''isadaptive'''
    @property
    def isadaptive(self): return bool(len(self.codecs) % 2)
    '''isprogressive'''
    @property
    def isprogressive(self): return not self.isadaptive
    '''issabr'''
    @property
    def issabr(self): return self._is_sabr
    @issabr.setter
    def issabr(self, value): self._is_sabr = value
    '''includesaudiotrack'''
    @property
    def includesaudiotrack(self): return self.isprogressive or self.type == "audio"
    '''includesvideotrack'''
    @property
    def includesvideotrack(self): return self.isprogressive or self.type == "video"
    '''parsecodecs'''
    def parsecodecs(self):
        video, audio = None, None
        if not self.isadaptive: video, audio = self.codecs
        elif self.includesvideotrack: video = self.codecs[0]
        elif self.includesaudiotrack: audio = self.codecs[0]
        return video, audio
    '''width'''
    @property
    def width(self): return self._width
    '''height'''
    @property
    def height(self): return self._height
    '''filesize'''
    @property
    def filesize(self):
        if self._filesize == 0:
            try:
                self._filesize = RequestWrapper.filesize(self.url)
            except HTTPError as e:
                if e.code != 404: raise Exception
                self._filesize = RequestWrapper.seqfilesize(self.url)
        return self._filesize
    '''filesizekb'''
    @property
    def filesizekb(self):
        if self._filesize_kb == 0:
            try:
                self._filesize_kb = float(math.ceil(RequestWrapper.filesize(self.url) / 1024 * 1000) / 1000)
            except HTTPError as e:
                if e.code != 404: raise Exception
                self._filesize_kb = float(math.ceil(RequestWrapper.seqfilesize(self.url) / 1024 * 1000) / 1000)
        return self._filesize_kb
    '''filesizemb'''
    @property
    def filesizemb(self):
        if self._filesize_mb == 0:
            try:
                self._filesize_mb = float(math.ceil(RequestWrapper.filesize(self.url) / 1024 / 1024 * 1000) / 1000)
            except HTTPError as e:
                if e.code != 404: raise Exception
                self._filesize_mb = float(math.ceil(RequestWrapper.seqfilesize(self.url) / 1024 / 1024 * 1000) / 1000)
        return self._filesize_mb
    '''filesizegb'''
    @property
    def filesizegb(self):
        if self._filesize_gb == 0:
            try:
                self._filesize_gb = float(math.ceil(RequestWrapper.filesize(self.url) / 1024 / 1024 / 1024 * 1000) / 1000)
            except HTTPError as e:
                if e.code != 404: raise Exception
                self._filesize_gb = float(math.ceil(RequestWrapper.seqfilesize(self.url) / 1024 / 1024 / 1024 * 1000) / 1000)
        return self._filesize_gb
    '''title'''
    @property
    def title(self):
        return self._monostate.title or "Unknown YouTube Video Title"
    '''filesizeapprox'''
    @property
    def filesizeapprox(self):
        if self._monostate.duration and self.bitrate:
            bits_in_byte = 8
            return int((self._monostate.duration * self.bitrate) / bits_in_byte)
        return self.filesize
    '''expiration'''
    @property
    def expiration(self):
        expire = parse_qs(self.url.split("?")[1])["expire"][0]
        return datetime.fromtimestamp(int(expire), timezone.utc)
    '''defaultfilename'''
    @property
    def defaultfilename(self):
        if 'audio' in self.mime_type and 'video' not in self.mime_type:
            self.subtype = "m4a"
        return f"{self.title}.{self.subtype}"
    '''download'''
    def download(self, output_path: Optional[str] = None, filename: Optional[str] = None, filename_prefix: Optional[str] = None, skip_existing: bool = True, timeout: Optional[int] = None, max_retries: int = 0, interrupt_checker: Optional[Callable[[], bool]] = None):
        kernel = sys.platform
        if kernel == "linux": file_system = "ext4"
        elif kernel == "darwin": file_system = "APFS"
        else: file_system = "NTFS"  
        translation_table = filesystemverify(file_system)
        if filename is None: filename = self.defaultfilename.translate(translation_table)
        if filename: filename = filename.translate(translation_table)
        file_path = self.getfilepath(filename=filename, output_path=output_path, filename_prefix=filename_prefix, file_system=file_system)
        if skip_existing and self.existsatpath(file_path):
            self.oncomplete(file_path)
            return file_path
        bytes_remaining = self.filesize
        def _writechunk(chunk_, bytes_remaining_): self.onprogress(chunk_, fh, bytes_remaining_)
        with open(file_path, "wb") as fh:
            try:
                if not self.issabr:
                    for chunk in RequestWrapper.stream(self.url, timeout=timeout, max_retries=max_retries):
                        if interrupt_checker is not None and interrupt_checker() == True: return
                        bytes_remaining -= len(chunk)
                        _writechunk(chunk, bytes_remaining)
                else:
                    ServerAbrStream(stream=self, write_chunk=_writechunk, monostate=self._monostate).start()
            except HTTPError as e:
                if e.code != 404: raise Exception
            except StopIteration:
                if not self.issabr:
                    for chunk in RequestWrapper.seqstream(self.url, timeout=timeout, max_retries=max_retries):
                        if interrupt_checker is not None and interrupt_checker() == True: return
                        bytes_remaining -= len(chunk)
                        _writechunk(chunk, bytes_remaining)
                else:
                    ServerAbrStream(stream=self, write_chunk=_writechunk, monostate=self._monostate).start()
            self.oncomplete(file_path)
            return file_path
    '''getfilepath'''
    def getfilepath(self, filename: Optional[str] = None, output_path: Optional[str] = None, filename_prefix: Optional[str] = None, file_system: str = 'NTFS'):
        if not filename:
            translation_table = filesystemverify(file_system)
            filename = self.defaultfilename.translate(translation_table)
        if filename:
            translation_table = filesystemverify(file_system)
            if not ('audio' in self.mime_type and 'video' not in self.mime_type): filename = filename.translate(translation_table)
            else: filename = filename.translate(translation_table)
        if filename_prefix: filename = f"{filename_prefix}{filename}"
        return str(Path(targetdirectory(output_path)) / filename)
    '''existsatpath'''
    def existsatpath(self, file_path: str):
        return (os.path.isfile(file_path) and os.path.getsize(file_path) == self.filesize)
    '''streamtobuffer'''
    def streamtobuffer(self, buffer: BinaryIO):
        bytes_remaining = self.filesize
        for chunk in RequestWrapper.stream(self.url):
            bytes_remaining -= len(chunk)
            self.onprogress(chunk, buffer, bytes_remaining)
        self.oncomplete(None)
    '''onprogress'''
    def onprogress(self, chunk: bytes, file_handler: BinaryIO, bytes_remaining: int):
        file_handler.write(chunk)
        if self._monostate.on_progress: self._monostate.on_progress(self, chunk, bytes_remaining)
    '''oncomplete'''
    def oncomplete(self, file_path: Optional[str]):
        on_complete = self._monostate.on_complete
        if on_complete: on_complete(self, file_path)
    '''onprogressforchunks'''
    def onprogressforchunks(self, chunk: bytes, bytes_remaining: int):
        if self._monostate.on_progress: self._monostate.on_progress(self, chunk, bytes_remaining)
    '''iterchunks'''
    def iterchunks(self, chunk_size: Optional[int] = None):
        bytes_remaining = self.filesize
        if chunk_size: RequestWrapper.default_range_size = chunk_size
        try:
            stream = RequestWrapper.stream(self.url)
        except HTTPError as e:
            if e.code != 404: raise Exception
            stream = RequestWrapper.seqstream(self.url)
        for chunk in stream:
            bytes_remaining -= len(chunk)
            self.onprogressforchunks(chunk, bytes_remaining)
            yield chunk
        self.oncomplete(None)


'''BinaryWriter'''
class BinaryWriter:
    def __init__(self, encode_utf8: Callable[[str], bytes] = lambda s: s.encode('utf-8')):
        self.encode_utf8 = encode_utf8
        self.stack = []
        self.chunks = []
        self.buf = bytearray()
    '''finish'''
    def finish(self):
        if self.buf:
            self.chunks.append(bytes(self.buf))
            self.buf.clear()
        return b''.join(self.chunks)
    '''fork'''
    def fork(self):
        self.stack.append((self.chunks, self.buf))
        self.chunks = []
        self.buf = bytearray()
        return self
    '''join'''
    def join(self):
        chunk = self.finish()
        if not self.stack: raise RuntimeError("Invalid state, fork stack empty")
        self.chunks, self.buf = self.stack.pop()
        self.uint32(len(chunk))
        return self.raw(chunk)
    '''tag'''
    def tag(self, field_no: int, wire_type: int):
        return self.uint32((field_no << 3) | wire_type)
    '''raw'''
    def raw(self, chunk: bytes):
        if self.buf:
            self.chunks.append(bytes(self.buf))
            self.buf.clear()
        self.chunks.append(chunk)
        return self
    '''uint32'''
    def uint32(self, value: int):
        assertuint32(value)
        varint32write(value, self.buf)
        return self
    '''int32'''
    def int32(self, value: int):
        assertint32(value)
        varint32write(value & 0xFFFFFFFF, self.buf)
        return self
    '''bool'''
    def bool(self, value: bool):
        self.buf.append(1 if value else 0)
        return self
    '''bytes'''
    def bytes(self, value: bytes):
        self.uint32(len(value))
        return self.raw(value)
    '''string'''
    def string(self, value: str):
        encoded = self.encode_utf8(value)
        self.uint32(len(encoded))
        return self.raw(encoded)
    '''float'''
    def float(self, value: float):
        self.raw(struct.pack('<f', value))
        return self
    '''double'''
    def double(self, value: float):
        self.raw(struct.pack('<d', value))
        return self
    '''fixed32'''
    def fixed32(self, value: int):
        assertuint32(value)
        self.raw(struct.pack('<I', value))
        return self
    '''sfixed32'''
    def sfixed32(self, value: int):
        assertint32(value)
        self.raw(struct.pack('<i', value))
        return self
    '''sint32'''
    def sint32(self, value: int):
        assertint32(value)
        encoded = (value << 1) ^ (value >> 31)
        varint32write(encoded, self.buf)
        return self
    '''sfixed64'''
    def sfixed64(self, value: int):
        tc = ProtoInt64.enc(value)
        self.raw(struct.pack('<ii', tc['lo'], tc['hi']))
        return self
    '''fixed64'''
    def fixed64(self, value: int):
        tc = ProtoInt64.uenc(value)
        self.raw(struct.pack('<II', tc['lo'], tc['hi']))
        return self
    '''int64'''
    def int64(self, value: int):
        tc = ProtoInt64.enc(value)
        varint64write(tc['lo'], tc['hi'], self.buf)
        return self
    '''sint64'''
    def sint64(self, value: int):
        tc = ProtoInt64.enc(value)
        sign = tc['hi'] >> 31
        lo = (tc['lo'] << 1) ^ sign
        hi = ((tc['hi'] << 1) | (tc['lo'] >> 31)) ^ sign
        varint64write(lo, hi, self.buf)
        return self
    '''uint64'''
    def uint64(self, value: int):
        tc = ProtoInt64.uenc(value)
        varint64write(tc['lo'], tc['hi'], self.buf)
        return self


'''BinaryReader'''
class BinaryReader:
    def __init__(self, buf, decode_utf8: Callable[[bytes], str] = lambda b: b.decode('utf-8')):
        if isinstance(buf, list): buf = bytes(buf)
        elif isinstance(buf, bytearray): buf = bytes(buf)
        elif not isinstance(buf, bytes): raise TypeError(f"Unsupported buffer type: {type(buf)}")
        self.decode_utf8 = decode_utf8
        self.buf = buf
        self.len = len(buf)
        self.pos = 0
    '''tag'''
    def tag(self):
        tag, self.pos = readvarint32(self.buf, self.pos)
        field_no = tag >> 3
        wire_type = tag & 0x7
        if field_no <= 0 or wire_type < 0 or wire_type > 5: raise ValueError(f"Illegal tag: field no {field_no} wire type {wire_type}")
        return field_no, wire_type
    '''skip'''
    def skip(self, wire_type: int, field_no=None):
        start = self.pos
        if wire_type == 0:
            while self.buf[self.pos] & 0x80: self.pos += 1
            self.pos += 1
        elif wire_type == 1:
            self.pos += 8
        elif wire_type == 2:
            length, self.pos = readvarint32(self.buf, self.pos)
            self.pos += length
        elif wire_type == 3:
            while True:
                fn, wt = self.tag()
                if wt == 4:
                    if field_no is not None and fn != field_no: raise ValueError("Invalid end group tag")
                    break
                self.skip(wt, fn)
        elif wire_type == 5:
            self.pos += 4
        else:
            raise ValueError(f"Can't skip unknown wire type {wire_type}")
        self.assertbounds()
        return self.buf[start:self.pos]
    '''assertbounds'''
    def assertbounds(self):
        if self.pos > self.len: raise EOFError("Premature EOF")
    '''uint32'''
    def uint32(self):
        value, self.pos = readvarint32(self.buf, self.pos)
        return value
    '''int32'''
    def int32(self):
        return self.uint32() | 0
    '''sint32'''
    def sint32(self):
        value = self.uint32()
        return (value >> 1) ^ -(value & 1)
    '''varint64'''
    def varint64(self):
        lo, hi, self.pos = readvarint64(self.buf, self.pos)
        return lo, hi
    '''int64'''
    def int64(self):
        return decodeint64(*self.varint64())
    '''uint64'''
    def uint64(self):
        return decodeuint64(*self.varint64())
    '''sint64'''
    def sint64(self):
        lo, hi = self.varint64()
        sign = -(lo & 1)
        lo = ((lo >> 1) | ((hi & 1) << 31)) ^ sign
        hi = (hi >> 1) ^ sign
        return decodeint64(lo, hi)
    '''bool'''
    def bool(self):
        lo, hi = self.varint64()
        return lo != 0 or hi != 0
    '''fixed32'''
    def fixed32(self):
        value = struct.unpack_from('<I', self.buf, self.pos)[0]
        self.pos += 4
        return value
    '''sfixed32'''
    def sfixed32(self):
        value = struct.unpack_from('<i', self.buf, self.pos)[0]
        self.pos += 4
        return value
    '''fixed64'''
    def fixed64(self):
        lo = self.sfixed32()
        hi = self.sfixed32()
        return decodeuint64(lo, hi)
    '''sfixed64'''
    def sfixed64(self):
        lo = self.sfixed32()
        hi = self.sfixed32()
        return decodeint64(lo, hi)
    '''float'''
    def float(self):
        value = struct.unpack_from('<f', self.buf, self.pos)[0]
        self.pos += 4
        return value
    '''double'''
    def double(self):
        value = struct.unpack_from('<d', self.buf, self.pos)[0]
        self.pos += 8
        return value
    '''bytes'''
    def bytes(self):
        length = self.uint32()
        start = self.pos
        self.pos += length
        self.assertbounds()
        return self.buf[start:self.pos]
    '''string'''
    def string(self):
        return self.decode_utf8(self.bytes())


'''ClientAbrState'''
class ClientAbrState:
    '''createbaseclientabrstate'''
    @staticmethod
    def createbaseclientabrstate():
        return {
            "timeSinceLastManualFormatSelectionMs": 0, "lastManualDirection": 0, "lastManualSelectedResolution": 0, "detailedNetworkType": 0, "clientViewportWidth": 0,
            "clientViewportHeight": 0, "clientBitrateCapBytesPerSec": 0, "stickyResolution": 0, "clientViewportIsFlexible": False, "bandwidthEstimate": 0, "minAudioQuality": 0,
            "maxAudioQuality": 0, "videoQualitySetting": 0, "audioRoute": 0, "playerTimeMs": 0, "timeSinceLastSeek": 0, "dataSaverMode": False, "networkMeteredState": 0,
            "visibility": 0, "playbackRate": 0, "elapsedWallTimeMs": 0, "mediaCapabilities": bytearray(), "timeSinceLastActionMs": 0, "enabledTrackTypesBitfield": 0,
            "maxPacingRate": 0, "playerState": 0, "drcEnabled": False, "Jda": 0, "qw": 0, "Ky": 0, "sabrReportRequestCancellationInfo": 0, "l": False, "G7": 0, "preferVp9": False,
            "qj": 0, "Hx": 0, "isPrefetch": False, "sabrSupportQualityConstraints": 0, "sabrLicenseConstraint": bytearray(), "allowProximaLiveLatency": 0, "sabrForceProxima": 0,
            "Tqb": 0, "sabrForceMaxNetworkInterruptionDurationMs": 0, "audioTrackId": ""
        }
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("timeSinceLastManualFormatSelectionMs", 0):
            writer.uint32(104).int64(message["timeSinceLastManualFormatSelectionMs"])
        if message.get("lastManualDirection", 0):
            writer.uint32(112).sint32(message["lastManualDirection"])
        if message.get("lastManualSelectedResolution", 0):
            writer.uint32(128).int32(message["lastManualSelectedResolution"])
        if message.get("detailedNetworkType", 0):
            writer.uint32(136).int32(message["detailedNetworkType"])
        if message.get("clientViewportWidth", 0):
            writer.uint32(144).int32(message["clientViewportWidth"])
        if message.get("clientViewportHeight", 0):
            writer.uint32(152).int32(message["clientViewportHeight"])
        if message.get("clientBitrateCapBytesPerSec", 0):
            writer.uint32(160).int64(message["clientBitrateCapBytesPerSec"])
        if message.get("stickyResolution", 0):
            writer.uint32(168).int32(message["stickyResolution"])
        if message.get("clientViewportIsFlexible", False):
            writer.uint32(176).bool(message["clientViewportIsFlexible"])
        if message.get("bandwidthEstimate", 0):
            writer.uint32(184).int64(message["bandwidthEstimate"])
        if message.get("minAudioQuality", 0):
            writer.uint32(192).int32(message["minAudioQuality"])
        if message.get("maxAudioQuality", 0):
            writer.uint32(200).int32(message["maxAudioQuality"])
        if message.get("videoQualitySetting", 0):
            writer.uint32(208).int32(message["videoQualitySetting"])
        if message.get("audioRoute", 0):
            writer.uint32(216).int32(message["audioRoute"])
        if message.get("playerTimeMs", 0):
            writer.uint32(224).int64(message["playerTimeMs"])
        if message.get("timeSinceLastSeek", 0):
            writer.uint32(232).int64(message["timeSinceLastSeek"])
        if message.get("dataSaverMode", False):
            writer.uint32(240).bool(message["dataSaverMode"])
        if message.get("networkMeteredState", 0):
            writer.uint32(256).int32(message["networkMeteredState"])
        if message.get("visibility", 0):
            writer.uint32(272).int32(message["visibility"])
        if message.get("playbackRate", 0):
            writer.uint32(285).float(message["playbackRate"])
        if message.get("elapsedWallTimeMs", 0):
            writer.uint32(288).int64(message["elapsedWallTimeMs"])
        if message.get("mediaCapabilities", b''):
            writer.uint32(306).bytes(message["mediaCapabilities"])
        if message.get("timeSinceLastActionMs", 0):
            writer.uint32(312).int64(message["timeSinceLastActionMs"])
        if message.get("enabledTrackTypesBitfield", 0):
            writer.uint32(320).int32(message["enabledTrackTypesBitfield"])
        if message.get("maxPacingRate", 0):
            writer.uint32(344).int32(message["maxPacingRate"])
        if message.get("playerState", 0):
            writer.uint32(352).int64(message["playerState"])
        if message.get("drcEnabled", False):
            writer.uint32(368).bool(message["drcEnabled"])
        if message.get("Jda", 0):
            writer.uint32(384).int32(message["Jda"])
        if message.get("qw", 0):
            writer.uint32(400).int32(message["qw"])
        if message.get("Ky", 0):
            writer.uint32(408).int32(message["Ky"])
        if message.get("sabrReportRequestCancellationInfo", 0):
            writer.uint32(432).int32(message["sabrReportRequestCancellationInfo"])
        if message.get("l", False):
            writer.uint32(448).bool(message["l"])
        if message.get("G7", 0):
            writer.uint32(456).int64(message["G7"])
        if message.get("preferVp9", False):
            writer.uint32(464).bool(message["preferVp9"])
        if message.get("qj", 0):
            writer.uint32(472).int32(message["qj"])
        if message.get("Hx", 0):
            writer.uint32(480).int32(message["Hx"])
        if message.get("isPrefetch", False):
            writer.uint32(488).bool(message["isPrefetch"])
        if message.get("sabrSupportQualityConstraints", 0):
            writer.uint32(496).int32(message["sabrSupportQualityConstraints"])
        if message.get("sabrLicenseConstraint", b''):
            writer.uint32(506).bytes(message["sabrLicenseConstraint"])
        if message.get("allowProximaLiveLatency", 0):
            writer.uint32(512).int32(message["allowProximaLiveLatency"])
        if message.get("sabrForceProxima", 0):
            writer.uint32(528).int32(message["sabrForceProxima"])
        if message.get("Tqb", 0):
            writer.uint32(536).int32(message["Tqb"])
        if message.get("sabrForceMaxNetworkInterruptionDurationMs", 0):
            writer.uint32(544).int64(message["sabrForceMaxNetworkInterruptionDurationMs"])
        if message.get("audioTrackId", ""):
            writer.uint32(554).string(message["audioTrackId"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = ClientAbrState.createbaseclientabrstate()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 13 and tag == 104:
                message['timeSinceLastManualFormatSelectionMs'] = longtonumber(reader.int64())
                continue
            elif field_number == 14 and tag == 112:
                message['lastManualDirection'] = reader.sint32()
                continue
            elif field_number == 16 and tag == 128:
                message['lastManualSelectedResolution'] = reader.int32()
                continue
            elif field_number == 17 and tag == 136:
                message['detailedNetworkType'] = reader.int32()
                continue
            elif field_number == 18 and tag == 144:
                message['clientViewportWidth'] = reader.int32()
                continue
            elif field_number == 19 and tag == 152:
                message['clientViewportHeight'] = reader.int32()
                continue
            elif field_number == 20 and tag == 160:
                message['clientBitrateCapBytesPerSec'] = longtonumber(reader.int64())
                continue
            elif field_number == 21 and tag == 168:
                message['stickyResolution'] = reader.int32()
                continue
            elif field_number == 22 and tag == 176:
                message['clientViewportIsFlexible'] = reader.bool()
                continue
            elif field_number == 23 and tag == 184:
                message['bandwidthEstimate'] = longtonumber(reader.int64())
                continue
            elif field_number == 24 and tag == 192:
                message['minAudioQuality'] = reader.int32()
                continue
            elif field_number == 25 and tag == 200:
                message['maxAudioQuality'] = reader.int32()
                continue
            elif field_number == 26 and tag == 208:
                message['videoQualitySetting'] = reader.int32()
                continue
            elif field_number == 27 and tag == 216:
                message['audioRoute'] = reader.int32()
                continue
            elif field_number == 28 and tag == 224:
                message['playerTimeMs'] = longtonumber(reader.int64())
                continue
            elif field_number == 29 and tag == 232:
                message['timeSinceLastSeek'] = longtonumber(reader.int64())
                continue
            elif field_number == 30 and tag == 240:
                message['dataSaverMode'] = reader.bool()
                continue
            elif field_number == 32 and tag == 256:
                message['networkMeteredState'] = reader.int32()
                continue
            elif field_number == 34 and tag == 272:
                message['visibility'] = reader.int32()
                continue
            elif field_number == 35 and tag == 285:
                message['playbackRate'] = reader.float()
                continue
            elif field_number == 36 and tag == 288:
                message['elapsedWallTimeMs'] = longtonumber(reader.int64())
                continue
            elif field_number == 38 and tag == 306:
                message['mediaCapabilities'] = reader.bytes()
                continue
            elif field_number == 39 and tag == 312:
                message['timeSinceLastActionMs'] = longtonumber(reader.int64())
                continue
            elif field_number == 40 and tag == 320:
                message['enabledTrackTypesBitfield'] = reader.int32()
                continue
            elif field_number == 43 and tag == 344:
                message['maxPacingRate'] = reader.int32()
                continue
            elif field_number == 44 and tag == 352:
                message['playerState'] = longtonumber(reader.int64())
                continue
            elif field_number == 46 and tag == 368:
                message['drcEnabled'] = reader.bool()
                continue
            elif field_number == 48 and tag == 384:
                message['Jda'] = reader.int32()
                continue
            elif field_number == 50 and tag == 400:
                message['qw'] = reader.int32()
                continue
            elif field_number == 51 and tag == 408:
                message['Ky'] = reader.int32()
                continue
            elif field_number == 54 and tag == 432:
                message['sabrReportRequestCancellationInfo'] = reader.int32()
                continue
            elif field_number == 56 and tag == 448:
                message['l'] = reader.bool()
                continue
            elif field_number == 57 and tag == 456:
                message['G7'] = longtonumber(reader.int64())
                continue
            elif field_number == 58 and tag == 464:
                message['preferVp9'] = reader.bool()
                continue
            elif field_number == 59 and tag == 472:
                message['qj'] = reader.int32()
                continue
            elif field_number == 60 and tag == 480:
                message['Hx'] = reader.int32()
                continue
            elif field_number == 61 and tag == 488:
                message['isPrefetch'] = reader.bool()
                continue
            elif field_number == 62 and tag == 496:
                message['sabrSupportQualityConstraints'] = reader.int32()
                continue
            elif field_number == 63 and tag == 506:
                message['sabrLicenseConstraint'] = reader.bytes()
                continue
            elif field_number == 64 and tag == 512:
                message['allowProximaLiveLatency'] = reader.int32()
                continue
            elif field_number == 66 and tag == 528:
                message['sabrForceProxima'] = reader.int32()
                continue
            elif field_number == 67 and tag == 536:
                message['Tqb'] = reader.int32()
                continue
            elif field_number == 68 and tag == 544:
                message['sabrForceMaxNetworkInterruptionDurationMs'] = longtonumber(reader.int64())
                continue
            elif field_number == 69 and tag == 554:
                message['audioTrackId'] = reader.string()
                continue
            else:
                if (tag & 7) == 4 or tag == 0: break
                reader.skip(tag & 7)
        return message


'''FormatId'''
class FormatId:
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("itag", 0) != 0: writer.uint32(8).int32(message["itag"])
        if message.get("lastModified", 0) != 0: writer.uint32(16).uint64(message["lastModified"])
        if message.get("xtags", None) is not None: writer.uint32(26).string(message["xtags"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = {"itag": 0, "lastModified": 0, "xtags": None}
        while reader.pos < end:
            tag = reader.uint32()
            field_no = tag >> 3
            if field_no == 1 and tag == 8: message["itag"] = reader.int32(); continue
            elif field_no == 2 and tag == 16: message["lastModified"] = reader.uint64(); continue
            elif field_no == 3 and tag == 26: message["xtags"] = reader.string(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''InitRange'''
class InitRange:
    def __init__(self, start=0, end=0):
        self.start = start
        self.end = end
    '''encode'''
    @staticmethod
    def encode(message, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.start != 0:
            writer.uint32(8)
            writer.int32(message.start)
        if message.end != 0:
            writer.uint32(16)
            writer.int32(message.end)
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = InitRange()
        while reader.pos < end:
            tag = reader.uint32()
            field_no = tag >> 3
            if field_no == 1 and tag == 8: message.start = reader.int32(); continue
            elif field_no == 2 and tag == 16: message.end = reader.int32(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''IndexRange'''
class IndexRange:
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("start", 0) != 0: writer.uint32(8).int32(message["start"])
        if message.get("end", 0) != 0: writer.uint32(16).int32(message["end"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = {"start": 0, "end": 0}
        while reader.pos < end:
            tag = reader.uint32()
            field_no = tag >> 3
            if field_no == 1 and tag == 8: message["start"] = reader.int32(); continue
            elif field_no == 2 and tag == 16: message["end"] = reader.int32(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''Lo'''
class Lo:
    def __init__(self):
        self.format_id: Optional[FormatId] = None
        self.Lj: int = 0
        self.sequenceNumber: int = 0
        self.field4: Optional[LoField4] = None
        self.MZ: int = 0
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        for v in message.get("field1", []): writer.uint32(10).string(v)
        if "field2" in message and message["field2"] is not None: writer.uint32(18).int32(message["field2"])
        if "field3" in message and message["field3"] is not None: writer.uint32(26).int32(message["field3"])
        if "field4" in message and message["field4"] is not None: writer.uint32(32).int32(message["field4"])
        if "field5" in message and message["field5"] is not None: writer.uint32(40).int32(message["field5"])
        if "field6" in message and message["field6"] is not None: writer.uint32(50).int32(message["field6"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = Lo()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.format_id = FormatId.decode(reader, reader.uint32()); continue
            elif field_number == 2 and tag == 16: message.Lj = reader.int32(); continue
            elif field_number == 3 and tag == 24: message.sequenceNumber = reader.int32(); continue
            elif field_number == 4 and tag == 34: message.field4 = LoField4.decode(reader, reader.uint32()); continue
            elif field_number == 5 and tag == 40: message.MZ = reader.int32(); continue
        return message


'''LoField4'''
class LoField4:
    def __init__(self):
        self.field1: int = 0
        self.field2: int = 0
        self.field3: int = 0
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if "field1" in message and message["field1"] is not None: writer.uint32(8).int32(message["field1"])
        if "field2" in message and message["field2"] is not None: writer.uint32(16).int32(message["field2"])
        if "field3" in message and message["field3"] is not None: writer.uint32(24).int32(message["field3"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = LoField4()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 8: message.field1 = reader.int32(); continue
            elif field_number == 2 and tag == 16: message.field2 = reader.int32(); continue
            elif field_number == 3 and tag == 24: message.field3 = reader.int32(); continue
        return message


'''OQa'''
class OQa:
    def __init__(self):
        self.field1: List[str] = []
        self.field2: bytes = bytes()
        self.field3: str = ""
        self.field4: int = 0
        self.field5: int = 0
        self.field6: str = ""
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if "field1" in message and message["field1"] is not None: writer.uint32(8).int32(message["field1"])
        if "field2" in message and message["field2"] is not None: writer.uint32(16).int32(message["field2"])
        if "field3" in message and message["field3"] is not None: writer.uint32(24).int32(message["field3"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = OQa()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.field1.append(reader.string()); continue
            elif field_number == 2 and tag == 18: message.field2 = reader.bytes(); continue
            elif field_number == 3 and tag == 26: message.field3 = reader.string(); continue
            elif field_number == 4 and tag == 32: message.field4 = reader.int32(); continue
            elif field_number == 5 and tag == 40: message.field5 = reader.int32(); continue
            elif field_number == 6 and tag == 50: message.field6 = reader.string(); continue
        return message


'''KobPa'''
class KobPa:
    def __init__(self):
        self.videoId = ""
        self.lmt = 0
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        writer = writer or BinaryWriter()
        if message.get("videoId"): writer.uint32(10).string(message["videoId"])
        if message.get("lmt", 0) != 0: writer.uint32(16).uint64(message["lmt"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = KobPa()
        while reader.pos < end:
            tag = reader.uint32()
            field_num = tag >> 3
            if field_num == 1 and tag == 10: message.videoId = reader.string(); continue
            elif field_num == 2 and tag == 16: message.lmt = longtonumber(reader.uint64())
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''Kob'''
class Kob:
    def __init__(self):
        self.EW = []
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        writer = writer or BinaryWriter()
        for v in message.get("EW", []): KobPa.encode(v, writer.uint32(10).fork()).join()
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = Kob()
        while reader.pos < end:
            tag = reader.uint32()
            field_num = tag >> 3
            if field_num == 1 and tag == 10: message.EW.append(KobPa.decode(reader, reader.uint32())); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''YPa'''
class YPa:
    def __init__(self):
        self.field1 = 0
        self.field2 = 0
        self.field3 = 0
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        writer = writer or BinaryWriter()
        if message.get("field1", 0) != 0: writer.uint32(8).int32(message["field1"])
        if message.get("field2", 0) != 0: writer.uint32(16).int32(message["field2"])
        if message.get("field3", 0) != 0: writer.uint32(24).int32(message["field3"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = YPa()
        while reader.pos < end:
            tag = reader.uint32()
            field_num = tag >> 3
            if field_num == 1 and tag == 8: message.field1 = reader.int32(); continue
            elif field_num == 2 and tag == 16: message.field2 = reader.int32(); continue
            elif field_num == 3 and tag == 24: message.field3 = reader.int32(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''TimeRange'''
class TimeRange:
    def __init__(self):
        self.start: int = 0
        self.duration: int = 0
        self.timescale: int = 0
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = TimeRange
        while reader.pos < end:
            tag = reader.uint32()
            field = tag >> 3
            if field == 1 and tag == 8: message.start = longtonumber(reader.int64()); continue
            elif field == 2 and tag == 16: message.duration = longtonumber(reader.int64()); continue
            elif field == 3 and tag == 24: message.timescale = reader.int32(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message
    '''encode'''
    def encode(self, writer: Optional[BinaryWriter] = None):
        writer = writer or BinaryWriter()
        if self.start != 0: writer.uint32(8).int64(self.start)
        if self.duration != 0: writer.uint32(16).int64(self.duration)
        if self.timescale != 0: writer.uint32(24).int32(self.timescale)
        return writer


'''BufferedRange'''
class BufferedRange:
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        writer = writer or BinaryWriter()
        if message.get("formatId") is not None: FormatId.encode(message["formatId"], writer.uint32(10).fork()).join()
        if message.get("startTimeMs", 0) != 0: writer.uint32(16).int64(message["startTimeMs"])
        if message.get("durationMs", 0) != 0: writer.uint32(24).int64(message["durationMs"])
        if message.get("startSegmentIndex", 0) != 0: writer.uint32(32).int32(message["startSegmentIndex"])
        if message.get("endSegmentIndex", 0) != 0: writer.uint32(40).int32(message["endSegmentIndex"])
        if message.get("timeRange") is not None: TimeRange.encode(message["timeRange"], writer.uint32(50).fork()).join()
        if message.get("field9") is not None: Kob.encode(message["field9"], writer.uint32(74).fork()).join()
        if message.get("field11") is not None: YPa.encode(message["field11"], writer.uint32(90).fork()).join()
        if message.get("field12") is not None: YPa.encode(message["field12"], writer.uint32(98).fork()).join()
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = {"formatId": None, "startTimeMs": 0, "durationMs": 0, "startSegmentIndex": 0, "endSegmentIndex": 0, "timeRange": None, "field9": None, "field11": None, "field12": None}
        while reader.pos < end:
            tag = reader.uint32()
            field_num = tag >> 3
            if field_num == 1 and tag == 10: message["formatId"] = FormatId.decode(reader, reader.uint32()); continue
            elif field_num == 2 and tag == 16: message["startTimeMs"] = longtonumber(reader.int64()); continue
            elif field_num == 3 and tag == 24: message["durationMs"] = longtonumber(reader.int64()); continue
            elif field_num == 4 and tag == 32: message["startSegmentIndex"] = reader.int32(); continue
            elif field_num == 5 and tag == 40: message["endSegmentIndex"] = reader.int32(); continue
            elif field_num == 6 and tag == 50: message["timeRange"] = TimeRange.decode(reader, reader.uint32()); continue
            elif field_num == 9 and tag == 74: message["field9"] = Kob.decode(reader, reader.uint32()); continue
            elif field_num == 11 and tag == 90: message["field11"] = YPa.decode(reader, reader.uint32()); continue
            elif field_num == 12 and tag == 98: message["field12"] = YPa.decode(reader, reader.uint32()); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''Pqa'''
class Pqa:
    def __init__(self):
        self.formats: List[FormatId] = []
        self.ud: List[BufferedRange] = []
        self.clip_id: str = ""
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        for v in message.get("formats", []): FormatId.encode(v, writer.uint32(10).fork()).join()
        for v in message.get("ud", []): BufferedRange.encode(v, writer.uint32(18).fork()).join()
        if "clipId" in message and message["clipId"] is not None: writer.uint32(26).int32(message["clipId"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        message = Pqa()
        end = reader.len if length is None else reader.pos + length
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.formats.append(FormatId.decode(reader, reader.uint32())); continue
            elif field_number == 2 and tag == 18: message.ud.append(BufferedRange.decode(reader, reader.uint32())); continue
            elif field_number == 3 and tag == 26: message.clip_id = reader.string(); continue
        return message


'''PlaybackCookie'''
class PlaybackCookie:
    '''createbase'''
    @staticmethod
    def createbase():
        return {"field1": 0, "field2": 0, "videoFmt": None, "audioFmt": None}
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("field1", 0) != 0: writer.uint32(8).int32(message["field1"])
        if message.get("field2", 0) != 0: writer.uint32(16).int32(message["field2"])
        if message.get("videoFmt") is not None: FormatId.encode(message["videoFmt"], writer.uint32(58).fork()).join()
        if message.get("audioFmt") is not None: FormatId.encode(message["audioFmt"], writer.uint32(66).fork()).join()
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = PlaybackCookie.createbase()
        while reader.pos < end:
            tag = reader.uint32()
            field = tag >> 3
            if field == 1 and tag == 8: message["field1"] = reader.int32(); continue
            elif field == 2 and tag == 16: message["field2"] = reader.int32(); continue
            elif field == 7 and tag == 58: message["videoFmt"] = FormatId.decode(reader, reader.uint32()); continue
            elif field == 8 and tag == 66: message["audioFmt"] = FormatId.decode(reader, reader.uint32()); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''StreamerContextClientInfo'''
class StreamerContextClientInfo:
    def __init__(self):
        self.locale = None
        self.deviceMake = None
        self.deviceModel = None
        self.clientName = None
        self.clientVersion = None
        self.osName = None
        self.osVersion = None
        self.acceptLanguage = None
        self.acceptRegion = None
        self.screenWidthPoints = None
        self.screenHeightPoints = None
        self.screenWidthInches = None
        self.screenHeightInches = None
        self.screenPixelDensity = None
        self.clientFormFactor = None
        self.gmscoreVersionCode = None
        self.windowWidthPoints = None
        self.windowHeightPoints = None
        self.androidSdkVersion = None
        self.screenDensityFloat = None
        self.utcOffsetMinutes = None
        self.timeZone = None
        self.chipset = None
        self.glDeviceInfo = None
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("deviceMake", ""): writer.uint32(98).string(message["deviceMake"])
        if message.get("deviceModel", ""): writer.uint32(106).string(message["deviceModel"])
        if message.get("clientName", 0): writer.uint32(128).int32(message["clientName"])
        if message.get("clientVersion", ""): writer.uint32(138).string(message["clientVersion"])
        if message.get("osName", ""): writer.uint32(146).string(message["osName"])
        if message.get("osVersion", ""): writer.uint32(154).string(message["osVersion"])
        if message.get("acceptLanguage", ""): writer.uint32(170).string(message["acceptLanguage"])
        if message.get("acceptRegion", ""): writer.uint32(178).string(message["acceptRegion"])
        if message.get("screenWidthPoints", 0): writer.uint32(296).int32(message["screenWidthPoints"])
        if message.get("screenHeightPoints", 0): writer.uint32(304).int32(message["screenHeightPoints"])
        if message.get("screenWidthInches", 0): writer.uint32(317).float(message["screenWidthInches"])
        if message.get("screenHeightInches", 0): writer.uint32(325).float(message["screenHeightInches"])
        if message.get("screenPixelDensity", 0): writer.uint32(328).int32(message["screenPixelDensity"])
        if message.get("clientFormFactor", 0): writer.uint32(368).int32(message["clientFormFactor"])
        if message.get("gmscoreVersionCode", 0): writer.uint32(400).int32(message["gmscoreVersionCode"])
        if message.get("windowWidthPoints", 0): writer.uint32(440).int32(message["windowWidthPoints"])
        if message.get("windowHeightPoints", 0): writer.uint32(448).int32(message["windowHeightPoints"])
        if message.get("androidSdkVersion", 0): writer.uint32(512).int32(message["androidSdkVersion"])
        if message.get("screenDensityFloat", 0): writer.uint32(525).float(message["screenDensityFloat"])
        if message.get("utcOffsetMinutes", 0): writer.uint32(536).int64(message["utcOffsetMinutes"])
        if message.get("timeZone", ""): writer.uint32(642).string(message["timeZone"])
        if message.get("chipset", ""): writer.uint32(738).string(message["chipset"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = StreamerContextClientInfo()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.locale = reader.string(); continue
            if field_number == 12 and tag == 98: message.deviceMake = reader.string(); continue
            elif field_number == 13 and tag == 106: message.deviceModel = reader.string(); continue
            elif field_number == 16 and tag == 128: message.clientName = reader.int32(); continue
            elif field_number == 17 and tag == 138: message.clientVersion = reader.string(); continue
            elif field_number == 18 and tag == 146: message.osName = reader.string(); continue
            elif field_number == 19 and tag == 154: message.osVersion = reader.string(); continue
            elif field_number == 21 and tag == 170: message.acceptLanguage = reader.string(); continue
            elif field_number == 22 and tag == 178: message.acceptRegion = reader.string(); continue
            elif field_number == 37 and tag == 296: message.screenWidthPoints = reader.int32(); continue
            elif field_number == 38 and tag == 304: message.screenHeightPoints = reader.int32(); continue
            elif field_number == 39 and tag == 317: message.screenWidthInches = reader.float(); continue
            elif field_number == 40 and tag == 325: message.screenHeightInches = reader.float(); continue
            elif field_number == 41 and tag == 328: message.screenPixelDensity = reader.int32(); continue
            elif field_number == 46 and tag == 368: message.clientFormFactor = reader.int32(); continue
            elif field_number == 50 and tag == 400: message.gmscoreVersionCode = reader.int32(); continue
            elif field_number == 55 and tag == 440: message.windowWidthPoints = reader.int32(); continue
            elif field_number == 56 and tag == 448: message.windowHeightPoints = reader.int32(); continue
            elif field_number == 64 and tag == 512: message.androidSdkVersion = reader.int32(); continue
            elif field_number == 65 and tag == 525: message.screenDensityFloat = reader.float(); continue
            elif field_number == 67 and tag == 536: message.utcOffsetMinutes = longtonumber(reader.int64()); continue
            elif field_number == 80 and tag == 642: message.timeZone = reader.string(); continue
            elif field_number == 92 and tag == 738: message.chipset = reader.string(); continue
            elif field_number == 102 and tag == 818: message.glDeviceInfo = StreamerContextGLDeviceInfo.decode(reader, reader.uint32())
            else:
                if (tag & 7) == 4 or tag == 0: break
                reader.skip(tag & 7)
        return message


'''StreamerContextGLDeviceInfo'''
class StreamerContextGLDeviceInfo:
    def __init__(self):
        self.glRenderer = ""
        self.glEsVersionMajor = 0
        self.glEsVersionMinor = 0
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("glRenderer", ""): writer.uint32(10).string(message["glRenderer"])
        if message.get("glEsVersionMajor", ""): writer.uint32(16).int32(message["glEsVersionMajor"])
        if message.get("glEsVersionMinor", ""): writer.uint32(24).int32(message["glEsVersionMinor"])
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = StreamerContextGLDeviceInfo()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.glRenderer = reader.string(); continue
            elif field_number == 2 and tag == 16: message.glEsVersionMajor = reader.int32(); continue
            elif field_number == 3 and tag == 24: message.glEsVersionMinor = reader.int32(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''StreamerContextUpdate'''
class StreamerContextUpdate:
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("type", 0): writer.uint32(8).int32(message["type"])
        if message.get("value", 0): StreamerContextUpdateValue.encode(message["value"], writer.uint32(18).fork()).join()
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = dict()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 8: message["type"] = reader.int32(); continue
            elif field_number == 2 and tag == 16: message["scope"] = reader.int32(); continue
            elif field_number == 3 and tag == 26: message["value"] = StreamerContextUpdateValue.decode(reader, reader.uint32()); continue
            elif field_number == 4 and tag == 32: message["sendByDefault"] = reader.bool(); continue
            elif field_number == 5 and tag == 40: message["writePolicy"] = reader.int32(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message
    '''SabrContextWritePolicy'''
    class SabrContextWritePolicy(Enum):
        SABR_CONTEXT_WRITE_POLICY_UNSPECIFIED = 0
        SABR_CONTEXT_WRITE_POLICY_OVERWRITE = 1
        SABR_CONTEXT_WRITE_POLICY_KEEP_EXISTING = 2


''''StreamerContextUpdateValue'''
class StreamerContextUpdateValue:
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("field1", 0): StreamerContextUpdateField1.encode(message["field1"], writer.uint32(10).fork()).join()
        if message.get("field2", 0): writer.uint32(18).bytes(message["field2"])
        if message.get("field3", 0): writer.uint32(40).int32(message["field3"])
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = dict()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message["field1"] = StreamerContextUpdateField1.decode(reader, reader.uint32()); continue
            elif field_number == 2 and tag == 18: message["field2"] = reader.bytes(); continue
            elif field_number == 5 and tag == 40: message["field3"] = reader.int32(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''StreamerContextUpdateField1'''
class StreamerContextUpdateField1:
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("timestamp", 0): writer.uint32(8).int64(message["timestamp"])
        if message.get("skip", 0): writer.uint32(16).int32(message["skip"])
        if message.get("fiedl3", 0): writer.uint32(26).bytes(message["fiedl3"])
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = dict()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 8: message["timestamp"] = reader.int64(); continue
            elif field_number == 2 and tag == 16: message["skip"] = reader.int32(); continue
            elif field_number == 3 and tag == 26: message["fiedl3"] = reader.bytes(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''StreamerContextGqa'''
class StreamerContextGqa:
    def __init__(self):
        self.field1 = None
        self.field2 = None
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("field1", 0): writer.uint32(10).bytes(message["field1"])
        if message.get("field2", 0): StreamerContextGqaHqa.encode(message["field2"], writer.uint32(18).fork()).join()
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = StreamerContextGqa()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.field1 = reader.bytes(); continue
            elif field_number == 2 and tag == 18: message.field2 = StreamerContextGqaHqa.decode(reader, reader.uint32()); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''StreamerContextGqaHqa'''
class StreamerContextGqaHqa:
    def __init__(self):
        self.code = 0
        self.message = ""
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("code", 0): writer.uint32(8).int32(message["code"])
        if message.get("message", ""): writer.uint32(18).string(message["message"])
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = StreamerContextGqaHqa()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 8: message.code = reader.int32(); continue
            elif field_number == 2 and tag == 18: message.message = reader.string(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''StreamerContext'''
class StreamerContext:
    def __init__(self):
        self.clientInfo = None
        self.poToken = None
        self.playbackCookie = None
        self.gp = None
        self.sabrContexts = []
        self.field6 = []
        self.field6 = ""
        self.field6 = []
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("clientInfo") is not None: StreamerContextClientInfo.encode(message["clientInfo"], writer.uint32(10).fork()).join()
        if message.get("poToken"): writer.uint32(18).bytes(message["poToken"])
        if message.get("playbackCookie"): writer.uint32(26).bytes(message["playbackCookie"])
        if message.get("gp"): writer.uint32(34).bytes(message["gp"])
        for v in message.get("sabrContexts", []): StreamerContextUpdate.encode(v, writer.uint32(42).fork()).join()
        writer.uint32(50).fork()
        for v in message.get("field6", []): writer.int32(v)
        writer.join()
        if message.get("field7", "") != "": writer.uint32(58).string(message["field7"])
        if message.get("field8") is not None: StreamerContextGqa.encode(message["field8"], writer.uint32(66).fork()).join()
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = StreamerContext()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10:
                message.clientInfo = StreamerContextClientInfo.decode(reader, reader.uint32())
                continue
            if field_number == 2 and tag == 18:
                message.poToken = reader.bytes()
                continue
            if field_number == 3 and tag == 26:
                message.playbackCookie = PlaybackCookie.decode(reader, reader.uint32())
                continue
            if field_number == 4 and tag == 34:
                message.gp = reader.bytes()
                continue
            if field_number == 5 and tag == 42:
                message.sabrContexts.append(StreamerContextUpdate.decode(reader, reader.uint32()))
                continue
            if field_number == 6 and tag == 48:
                message.field6.append(reader.int32())
                continue
            if field_number == 6 and tag == 50:
                end2 = reader.uint32() + reader.pos
                while (reader.pos < end2): message.field6.append(reader.int32())
                continue
            if field_number == 7 and tag == 58: message.field7 = reader.string(); continue
            if field_number == 8 and tag == 66: message.field5.append(StreamerContextGqa.decode(reader, reader.uint32())); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''VideoPlaybackAbrRequest'''
class VideoPlaybackAbrRequest:
    def __init__(self):
        self.client_abr_state = None
        self.selected_format_ids = []
        self.buffered_ranges = []
        self.player_time_ms: int = 0
        self.video_playback_ustreamer_config: bytes = bytes()
        self.lo = None
        self.lj = None
        self.selected_audio_format_ids = []
        self.selected_video_format_ids = []
        self.streamer_context = None
        self.field1 = None
        self.field2 = None
        self.field3 = None
        self.field21 = None
        self.field22: int = 0
        self.field23: int = 0
        self.field1000 = []
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if "clientAbrState" in message and message["clientAbrState"] is not None:
            writer.uint32(10)
            ClientAbrState.encode(message["clientAbrState"], writer.fork())
            writer.join()
        for v in message.get("selectedFormatIds", []):
            writer.uint32(18)
            FormatId.encode(v, writer.fork())
            writer.join()
        for v in message.get("bufferedRanges", []):
            writer.uint32(26)
            BufferedRange.encode(v, writer.fork())
            writer.join()
        if message.get("playerTimeMs", 0):
            writer.uint32(32).int64(message["playerTimeMs"])
        if message.get("videoPlaybackUstreamerConfig", b''):
            writer.uint32(42).bytes(message["videoPlaybackUstreamerConfig"])
        if "lo" in message and message["lo"] is not None:
            writer.uint32(50)
            Lo.encode(message["lo"], writer.fork())
            writer.join()
        for v in message.get("selectedAudioFormatIds", []):
            writer.uint32(130)
            FormatId.encode(v, writer.fork())
            writer.join()
        for v in message.get("selectedVideoFormatIds", []):
            writer.uint32(138)
            FormatId.encode(v, writer.fork())
            writer.join()
        if "streamerContext" in message and message["streamerContext"] is not None:
            writer.uint32(154)
            StreamerContext.encode(message["streamerContext"], writer.fork())
            writer.join()
        if "field21" in message and message["field21"] is not None:
            writer.uint32(170)
            OQa.encode(message["field21"], writer.fork())
            writer.join()
        if message.get("field22", 0):
            writer.uint32(176).int32(message["field22"])
        if message.get("field23", 0):
            writer.uint32(184).int32(message["field23"])
        for v in message.get("field1000", []):
            writer.uint32(8002)
            Pqa.encode(v, writer.fork())
            writer.join()
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = VideoPlaybackAbrRequest()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.client_abr_state = ClientAbrState.decode(reader, reader.uint32()); continue
            elif field_number == 2 and tag == 18: message.selected_format_ids.append(FormatId.decode(reader, reader.uint32())); continue
            elif field_number == 3 and tag == 26: message.buffered_ranges.append(BufferedRange.decode(reader, reader.uint32())); continue
            elif field_number == 4 and tag == 32: message.player_time_ms = longtonumber(reader.int64()); continue
            elif field_number == 5 and tag == 42: message.video_playback_ustreamer_config = reader.bytes(); continue
            elif field_number == 6 and tag == 50: message.lo = Lo.decode(reader, reader.uint32()); continue
            elif field_number == 16 and tag == 130: message.selected_audio_format_ids.append(FormatId.decode(reader, reader.uint32())); continue
            elif field_number == 17 and tag == 138: message.selected_video_format_ids.append(FormatId.decode(reader, reader.uint32())); continue
            elif field_number == 19 and tag == 154: message.streamer_context = StreamerContext.decode(reader, reader.uint32()); continue
            elif field_number == 21 and tag == 170: message.field21 = OQa.decode(reader, reader.uint32()); continue
            elif field_number == 22 and tag == 176: message.field22 = reader.int32(); continue
            elif field_number == 23 and tag == 184: message.field23 = reader.int32(); continue
            elif field_number == 1000 and tag == 8002: message.field1000.append(Pqa.decode(reader, reader.uint32())); continue
        return message


'''SabrError'''
class SabrError:
    def __init__(self):
        self.type = ""
        self.code = 0
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("type") not in (None, ""): writer.uint32(10).string(message["type"])
        if message.get("code") not in (None, 0): writer.uint32(16).int32(message["code"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = SabrError()
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.type = reader.string(); continue
            if field_number == 2 and tag == 16: message.code = reader.int32(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''MediaHeader'''
class MediaHeader:
    def __init__(self):
        self.headerId: int = 0
        self.videoId: str = ""
        self.itag: int = 0
        self.lmt: int = 0
        self.xtags: str = ""
        self.startRange: int = 0
        self.compressionAlgorithm: int = 0
        self.isInitSeg: bool = False
        self.sequenceNumber: int = 0
        self.field10: int = 0
        self.startMs: int = 0
        self.durationMs: int = 0
        self.formatId: Optional[FormatId] = None
        self.contentLength: int = 0
        self.timeRange: Optional[TimeRange] = None
    '''decode'''
    @staticmethod
    def decode(reader, length: Optional[int] = None):
        if not isinstance(reader, BinaryReader): reader = BinaryReader(reader)
        end = reader.len if length is None else reader.pos + length
        message = MediaHeader()
        while reader.pos < end:
            tag = reader.uint32()
            field = tag >> 3
            if field == 1 and tag == 8: message.headerId = reader.uint32(); continue
            elif field == 2 and tag == 18: message.videoId = reader.string(); continue
            elif field == 3 and tag == 24: message.itag = reader.int32(); continue
            elif field == 4 and tag == 32: message.lmt = longtonumber(reader.uint64()); continue
            elif field == 5 and tag == 42: message.xtags = reader.string(); continue
            elif field == 6 and tag == 48: message.startRange = longtonumber(reader.int64()); continue
            elif field == 7 and tag == 56: message.compressionAlgorithm = reader.int32(); continue
            elif field == 8 and tag == 64: message.isInitSeg = reader.bool(); continue
            elif field == 9 and tag == 72: message.sequenceNumber = longtonumber(reader.int64()); continue
            elif field == 10 and tag == 80: message.field10 = longtonumber(reader.int64()); continue
            elif field == 11 and tag == 88: message.startMs = longtonumber(reader.int64()); continue
            elif field == 12 and tag == 96: message.durationMs = longtonumber(reader.int64()); continue
            elif field == 13 and tag == 106:
                length = reader.uint32()
                message.formatId = FormatId.decode(reader, length)
                continue
            elif field == 14 and tag == 112:
                message.contentLength = longtonumber(reader.int64())
                continue
            elif field == 15 and tag == 122:
                length = reader.uint32()
                message.timeRange = TimeRange.decode(reader, length)
                continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("headerId", 0): writer.uint32(8).uint32(message["headerId"])
        if message.get("videoId", ""): writer.uint32(18).string(message["videoId"])
        if message.get("itag", 0): writer.uint32(24).int32(message["itag"])
        if message.get("lmt", 0): writer.uint32(32).uint64(message["lmt"])
        if message.get("xtags", ""): writer.uint32(42).string(message["xtags"])
        if message.get("startRange", 0): writer.uint32(48).int64(message["startRange"])
        if message.get("compressionAlgorithm", 0): writer.uint32(56).int32(message["compressionAlgorithm"])
        if message.get("isInitSeg", False): writer.uint32(64).bool(message["isInitSeg"])
        if message.get("sequenceNumber", 0): writer.uint32(72).int64(message["sequenceNumber"])
        if message.get("field10", 0): writer.uint32(80).int64(message["field10"])
        if message.get("startMs", 0): writer.uint32(88).int64(message["startMs"])
        if message.get("durationMs", 0): writer.uint32(96).int64(message["durationMs"])
        if message.get("formatId", 0): FormatId.encode(message["formatId"], writer.uint32(106).fork()).join()
        if message.get("contentLength", 0): writer.uint32(112).int64(message["contentLength"])
        if message.get("timeRange", 0): TimeRange.encode(message["timeRange"], writer.uint32(122).fork()).join()
        return writer


'''NextRequestPolicy'''
class NextRequestPolicy:
    def __init__(self):
        self.targetAudioReadaheadMs = 0
        self.targetVideoReadaheadMs = 0
        self.backoffTimeMs = 0
        self.playbackCookie = None
        self.videoId = ""
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("targetAudioReadaheadMs", 0) != 0: writer.uint32(8).int32(message["targetAudioReadaheadMs"])
        if message.get("targetVideoReadaheadMs", 0) != 0: writer.uint32(16).int32(message["targetVideoReadaheadMs"])
        if message.get("backoffTimeMs", 0) != 0: writer.uint32(32).int32(message["backoffTimeMs"])
        if message.get("playbackCookie") is not None: PlaybackCookie.encode(message["playbackCookie"], writer.uint32(58).fork()).join()
        if message.get("videoId", "") != "": writer.uint32(66).string(message["videoId"])
        return writer
    '''decode'''
    @staticmethod
    def decode(data, length=None):
        reader = data if isinstance(data, BinaryReader) else BinaryReader(data)
        end = reader.len if length is None else reader.pos + length
        message = NextRequestPolicy
        while reader.pos < end:
            tag = reader.uint32()
            field = tag >> 3
            if field == 1 and tag == 8: message.targetAudioReadaheadMs = reader.int32(); continue
            elif field == 2 and tag == 16: message.targetVideoReadaheadMs = reader.int32(); continue
            elif field == 4 and tag == 32: message.backoffTimeMs = reader.int32(); continue
            elif field == 7 and tag == 58: message.playbackCookie = PlaybackCookie.decode(reader, reader.uint32()); continue
            elif field == 8 and tag == 66: message.videoId = reader.string(); continue
            elif (tag & 7) == 4 or tag == 0: break
            else: reader.skip(tag & 7)
        return message


'''FormatInitializationMetadata'''
class FormatInitializationMetadata:
    def __init__( self):
        self.videoId = ""
        self.formatId = None
        self.endTimeMs = 0
        self.endSegmentNumber = 0
        self.mimeType = ""
        self.initRange = None
        self.indexRange = None
        self.field8 = 0
        self.durationMs = 0
        self.field10 = 0
    '''encode'''
    @staticmethod
    def encode(message, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.videoId != "":
            writer.uint32(10)
            writer.string(message.videoId)
        if message.formatId is not None:
            writer.uint32(18)
            FormatId.encode(message.formatId, writer.fork()).join()
        if message.endTimeMs != 0:
            writer.uint32(24)
            writer.int32(message.endTimeMs)
        if message.endSegmentNumber != 0:
            writer.uint32(32)
            writer.int64(message.endSegmentNumber)
        if message.mimeType != "":
            writer.uint32(42)
            writer.string(message.mimeType)
        if message.initRange is not None:
            writer.uint32(50)
            InitRange.encode(message.initRange, writer.fork()).join()
        if message.indexRange is not None:
            writer.uint32(58)
            IndexRange.encode(message.indexRange, writer.fork()).join()
        if message.field8 != 0:
            writer.uint32(64)
            writer.int32(message.field8)
        if message.durationMs != 0:
            writer.uint32(72)
            writer.int32(message.durationMs)
        if message.field10 != 0:
            writer.uint32(80)
            writer.int32(message.field10)
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = FormatInitializationMetadata()
        while reader.pos < end:
            tag = reader.uint32()
            field_no = tag >> 3
            if field_no == 1 and tag == 10: message.videoId = reader.string(); continue
            elif field_no == 2 and tag == 18: message.formatId = FormatId.decode(reader, reader.uint32()); continue
            elif field_no == 3 and tag == 24: message.endTimeMs = reader.int32(); continue
            elif field_no == 4 and tag == 32: message.endSegmentNumber = longtonumber(reader.int64()); continue
            elif field_no == 5 and tag == 42: message.mimeType = reader.string(); continue
            elif field_no == 6 and tag == 50: message.initRange = InitRange.decode(reader, reader.uint32()); continue
            elif field_no == 7 and tag == 58: message.indexRange = IndexRange.decode(reader, reader.uint32()); continue
            elif field_no == 8 and tag == 64: message.field8 = reader.int32(); continue
            elif field_no == 9 and tag == 72: message.durationMs = reader.int32(); continue
            elif field_no == 10 and tag == 80: message.field10 = reader.int32(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''SabrRedirect'''
class SabrRedirect:
    def __init__(self):
        self.url = ""
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("url") not in (None, ""): writer.uint32(10).string(message["url"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = SabrRedirect
        while reader.pos < end:
            tag = reader.uint32()
            field_number = tag >> 3
            if field_number == 1 and tag == 10: message.url = reader.string(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message


'''StreamProtectionStatus'''
class StreamProtectionStatus:
    def __init__(self):
        self.status = None
        self.field2 = None
    '''encode'''
    @staticmethod
    def encode(message: dict, writer=None):
        if writer is None: writer = BinaryWriter()
        if message.get("status", 0) != 0:
            writer.uint32(8)
            writer.int32(message["status"])
        if message.get("field2") != 0:
            writer.uint32(16)
            writer.int32(message["field2"])
        return writer
    '''decode'''
    @staticmethod
    def decode(input_data, length=None):
        reader = input_data if isinstance(input_data, BinaryReader) else BinaryReader(input_data)
        end = reader.len if length is None else reader.pos + length
        message = StreamProtectionStatus()
        while reader.pos < end:
            tag = reader.uint32()
            field_no = tag >> 3
            if field_no == 1 and tag == 8: message.status = reader.int32(); continue
            elif field_no == 2 and tag == 16: message.field2 = reader.int32(); continue
            if (tag & 7) == 4 or tag == 0: break
            reader.skip(tag & 7)
        return message
    '''Status'''
    class Status(Enum):
        OK = 1
        ATTESTATION_PENDING = 2
        ATTESTATION_REQUIRED = 3


'''ServerAbrStream'''
class ServerAbrStream:
    def __init__(self, stream: Stream, write_chunk: Callable, monostate: Monostate):
        self.stream = stream
        self.write_chunk = write_chunk
        self.youtube = monostate.youtube
        self.po_token = self.stream.po_token
        self.server_abr_streaming_url = self.stream.url
        self.video_playback_ustreamer_config = self.stream.video_playback_ustreamer_config
        self.totalDurationMs = int(self.stream.durationMs)
        self.bytes_remaining = self.stream.filesize
        self.initialized_formats = []
        self.formats_by_key = {}
        self.playback_cookie = None
        self.header_id_to_format_key_map = {}
        self.previous_sequences = {}
        self.RELOAD = False
        self.maximum_reload_attempt = 4
        self.stream_protection_status = PoTokenStatus.UNKNOWN.name
        self.sabr_contexts_to_send = []
        self.sabr_context_updates = dict()
    '''emit'''
    def emit(self, data):
        for formatId in data['initialized_formats']:
            if formatId['formatId']['itag'] == self.stream.itag:
                media_chunks = formatId['mediaChunks']
                for chunk in media_chunks:
                    self.bytes_remaining -= len(chunk)
                    self.write_chunk(chunk, self.bytes_remaining)
    '''start'''
    def start(self):
        audio_format = [{'itag': self.stream.itag, 'lastModified': int(self.stream.last_Modified), 'xtags': self.stream.xtags}] if self.stream.type == 'audio' else []
        video_format = [{'itag': self.stream.itag, 'lastModified': int(self.stream.last_Modified), 'xtags': self.stream.xtags}] if self.stream.type == 'video' else []
        client_abr_state = {
            'lastManualDirection': 0, 'timeSinceLastManualFormatSelectionMs': 0, 'lastManualSelectedResolution': int(self.stream.resolution.replace('p', '')) if video_format else 720,
            'stickyResolution': int(self.stream.resolution.replace('p', '')) if video_format else 720, 'playerTimeMs': 0, 'visibility': 0, 'drcEnabled': self.stream.is_drc,
            'enabledTrackTypesBitfield': 0 if video_format else 1
        }
        while client_abr_state['playerTimeMs'] < self.totalDurationMs:
            data = self.fetchmedia(client_abr_state, audio_format, video_format)
            if data.get("sabr_error"): self.reload()
            self.emit(data)
            if data.get("sabr_context_update"):
                if self.maximum_reload_attempt > 0: continue
                else: raise Exception 
            if client_abr_state["enabledTrackTypesBitfield"] == 0:
                main_format = next((fmt for fmt in data.get("initialized_formats", []) if "video" in (fmt.get("mimeType") or "")), None)
            else:
                main_format = data['initialized_formats'][0] if data['initialized_formats'] else None
            for fmt in data.get("initialized_formats", []):
                format_key = fmt["formatKey"]
                sequence_numbers = [seq.get("sequenceNumber", 0) for seq in fmt.get("sequenceList", [])]
                self.previous_sequences[format_key] = sequence_numbers
            if not self.RELOAD and (main_format is None or not main_format.get("sequenceList")): self.reload()
            if self.RELOAD:
                if self.maximum_reload_attempt > 0:
                    self.RELOAD = False
                    continue
                else:
                    raise Exception 
            if (not main_format or main_format["sequenceCount"] == main_format["sequenceList"][-1].get("sequenceNumber")): break
            total_sequence_duration = sum(seq.get("durationMs", 0) for seq in main_format["sequenceList"])
            client_abr_state["playerTimeMs"] += total_sequence_duration
    '''fetchmedia'''
    def fetchmedia(self, client_abr_state, audio_format, video_format):
        body = VideoPlaybackAbrRequest.encode({
            'clientAbrState': client_abr_state, 'selectedAudioFormatIds': audio_format, 'selectedVideoFormatIds': video_format,
            'selectedFormatIds': [fmt["formatId"] for fmt in self.initialized_formats], 'videoPlaybackUstreamerConfig': self.base64tou8(self.video_playback_ustreamer_config),
            'streamerContext': {
                'sabrContexts': [ctx for ctx in self.sabr_context_updates.values() if ctx["type"] in self.sabr_contexts_to_send],
                'field6': [],
                'poToken': self.base64tou8(self.po_token) if self.po_token else None,
                'playbackCookie': PlaybackCookie.encode(self.playback_cookie).finish() if self.playback_cookie else None,
                'clientInfo': {'clientName': 1, 'clientVersion': '2.20250523.01.00', 'osName': 'Windows', 'osVersion': '10.0', 'platform': 'DESKTOP'}
            },
            'bufferedRanges': [fmt["_state"] for fmt in self.initialized_formats], 'field1000': []
        }).finish()
        base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en", "Content-Type": "application/vnd.yt-ump"}
        request = Request(self.server_abr_streaming_url, headers=base_headers, method="POST", data=bytes(body))
        return self.parseumpresponse(bytes(urlopen(request).read()))
    '''parseumpresponse'''
    def parseumpresponse(self, resp):
        self.header_id_to_format_key_map.clear()
        for k, v in enumerate(self.initialized_formats): self.initialized_formats[k]['sequenceList'], self.initialized_formats[k]['mediaChunks'] = [], []
        sabr_error, sabr_redirect, sabr_context_update = None, None, False
        ump = UMP(ChunkedDataBuffer([resp]))
        def callback(part):
            data = list(part['data'].chunks[0] if part['data'].chunks else [])
            if part['type'] == PART.MEDIA_HEADER.value:
                self.processmediaheader(data)
            elif part['type'] == PART.MEDIA.value:
                self.processmediadata(part['data'])
            elif part['type'] == PART.MEDIA_END.value:
                self.processendofmedia(part['data'])
            elif part['type'] == PART.NEXT_REQUEST_POLICY.value:
                self.processnextrequestpolicy(data)
            elif part['type'] == PART.FORMAT_INITIALIZATION_METADATA.value:
                self.processformatinitialization(data)
            elif part['type'] == PART.SABR_ERROR.value:
                nonlocal sabr_error
                sabr_error = SabrError.decode(data)
            elif part['type'] == PART.SABR_REDIRECT.value:
                nonlocal sabr_redirect
                sabr_redirect = self.processsabrredirect(data)
            elif part['type'] == PART.STREAM_PROTECTION_STATUS.value:
                self.processstreamprotectionstatus(data)
            elif part['type'] == PART.RELOAD_PLAYER_RESPONSE.value:
                self.reload()
            elif part["type"] == PART.PLAYBACK_START_POLICY.value:
                pass
            elif part["type"] == PART.REQUEST_CANCELLATION_POLICY.value:
                pass
            elif part["type"] == PART.SABR_CONTEXT_UPDATE.value:
                nonlocal sabr_context_update
                sabr_context_update = True
                self.processsabrcontextupdate(data)
            elif part["type"] == PART.SNACKBAR_MESSAGE.value:
                sabr_context_update = True
                self.processsnackbarmessage()
        ump.parse(callback)
        return {"initialized_formats": self.initialized_formats, "sabr_redirect": sabr_redirect, "sabr_error": sabr_error, "sabr_context_update": sabr_context_update}
    '''processmediaheader'''
    def processmediaheader(self, data):
        media_header = MediaHeader.decode(data)
        if not media_header.formatId: return
        format_key = self.getformatkey(media_header.formatId)
        current_format = self.formats_by_key.get(format_key) or self.registerformat(media_header)
        if not current_format: return
        sequence_number = media_header.sequenceNumber
        if sequence_number is not None:
            if format_key in self.previous_sequences:
                if sequence_number in self.previous_sequences[format_key]: return
        header_id = media_header.headerId
        if header_id is not None:
            if header_id not in self.header_id_to_format_key_map:
                self.header_id_to_format_key_map[header_id] = format_key
        if not any(seq.get("sequenceNumber") == (media_header.sequenceNumber or 0) for seq in current_format["sequenceList"]):
            current_format["sequenceList"].append({
                "itag": media_header.itag, "formatId": media_header.formatId, "isInitSegment": media_header.isInitSeg, "durationMs": media_header.durationMs, "startMs": media_header.startMs, 
                "startDataRange": media_header.startRange, "sequenceNumber": media_header.sequenceNumber, "contentLength": media_header.contentLength, "timeRange": media_header.timeRange
            })
            if isinstance(sequence_number, int):
                current_format["_state"]["durationMs"] += media_header.durationMs
                current_format["_state"]["endSegmentIndex"] += 1
    '''processmediadata'''
    def processmediadata(self, data):
        header_id = data.getuint8(0)
        stream_data = data.split(1)['remaining_buffer']
        format_key = self.header_id_to_format_key_map.get(header_id)
        if not format_key: return
        current_format = self.formats_by_key.get(format_key)
        if not current_format: return
        current_format['mediaChunks'].append(stream_data.chunks[0])
    '''processendofmedia'''
    def processendofmedia(self, data):
        header_id = data.getuint8(0)
        self.header_id_to_format_key_map.pop(header_id, None)
    '''processnextrequestpolicy'''
    def processnextrequestpolicy(self, data):
        next_request_policy = NextRequestPolicy.decode(data)
        self.playback_cookie = next_request_policy.playbackCookie
    '''processformatinitialization'''
    def processformatinitialization(self, data):
        format_metadata = FormatInitializationMetadata.decode(data)
        self.registerformat(format_metadata)
    '''processsabrredirect'''
    def processsabrredirect(self, data):
        sabr_redirect = SabrRedirect.decode(data)
        if not sabr_redirect.url:
            raise ValueError("Invalid SABR redirect")
        self.server_abr_streaming_url = sabr_redirect.url
        return sabr_redirect
    '''processsnackbarmessage'''
    def processsnackbarmessage(self):
        skip = self.sabr_context_updates[self.sabr_contexts_to_send[-1]].get("skip", 1000) / 1000
        if skip >= 60: raise Exception
        time.sleep(skip)
        self.maximum_reload_attempt -= 1
    '''processstreamprotectionstatus'''
    def processstreamprotectionstatus(self, data):
        protection_status = StreamProtectionStatus.decode(data).status
        if protection_status == StreamProtectionStatus.Status.OK.value:
            result_status = PoTokenStatus.OK.name if self.po_token else PoTokenStatus.NOT_REQUIRED.name
        elif protection_status == StreamProtectionStatus.Status.ATTESTATION_PENDING.value:
            result_status = PoTokenStatus.PENDING.name if self.po_token else PoTokenStatus.PENDING_MISSING.name
        elif protection_status == StreamProtectionStatus.Status.ATTESTATION_REQUIRED.value:
            result_status = PoTokenStatus.INVALID.name if self.po_token else PoTokenStatus.MISSING.name
        else:
            result_status = PoTokenStatus.UNKNOWN.name
        self.stream_protection_status = result_status
    '''processsabrcontextupdate'''
    def processsabrcontextupdate(self, data):
        sabr_ctx_update = StreamerContextUpdate.decode(data)
        if not (sabr_ctx_update["type"] and sabr_ctx_update["value"] and sabr_ctx_update["writePolicy"]): return
        if (sabr_ctx_update["writePolicy"] == StreamerContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_KEEP_EXISTING.value and sabr_ctx_update["type"] in self.sabr_context_updates): return
        self.sabr_context_updates[sabr_ctx_update["type"]] = sabr_ctx_update
        timestamp = sabr_ctx_update.get("value", "").get("field1", "").get("timestamp", "")
        skip = sabr_ctx_update.get("value", "").get("field1", "").get("skip", "")
        self.sabr_context_updates[sabr_ctx_update["type"]]["timestamp"] = timestamp
        self.sabr_context_updates[sabr_ctx_update["type"]]["skip"] = skip
        if sabr_ctx_update["sendByDefault"] is True: self.sabr_contexts_to_send.append(sabr_ctx_update["type"])
    '''getformatkey'''
    @staticmethod
    def getformatkey(format_id):
        return f"{format_id['itag']};{format_id['lastModified']};"
    '''registerformat'''
    def registerformat(self, data):
        if data.formatId is None: return None
        format_key = self.getformatkey(data.formatId)
        if format_key not in self.formats_by_key:
            format_ = {
                "formatId": data.formatId, "formatKey": format_key, "durationMs": data.durationMs, "mimeType": data.mimeType, "sequenceCount": data.endSegmentNumber,
                "sequenceList": [], "mediaChunks": [], "_state": {"formatId": data.formatId, "startTimeMs": 0, "durationMs": 0, "startSegmentIndex": 1, "endSegmentIndex": 0}
            }
            self.initialized_formats.append(format_)
            self.formats_by_key[format_key] = self.initialized_formats[-1]
            return format_
        return None
    '''reload'''
    def reload(self):
        self.RELOAD = True
        self.maximum_reload_attempt -= 1
        self.sabr_contexts_to_send = []
        self.sabr_context_updates = dict()
        self.youtube.vid_info = None
        refresh_url = self.youtube.server_abr_streaming_url
        if not refresh_url: raise ValueError("Invalid SABR refresh")
        self.server_abr_streaming_url = refresh_url
        self.video_playback_ustreamer_config = self.youtube.video_playback_ustreamer_config
    '''base64tou8'''
    @staticmethod
    def base64tou8(base64_str: str):
        standard_base64 = base64_str.replace('-', '+').replace('_', '/')
        padded_base64 = standard_base64 + '=' * ((4 - len(standard_base64) % 4) % 4)
        byte_data = base64.b64decode(padded_base64)
        return bytearray(byte_data)


'''StreamQuery'''
class StreamQuery(Sequence):
    def __init__(self, fmt_streams):
        self.fmt_streams = fmt_streams
        self.itag_index = {int(s.itag): s for s in fmt_streams}
    '''filter'''
    def filter(self, fps=None, res=None, resolution=None, mime_type=None, type=None, subtype=None, file_extension=None, abr=None, bitrate=None, video_codec=None, audio_codec=None, 
               only_audio=None, only_video=None, progressive=None, adaptive=None, is_dash=None, is_drc=None, audio_track_name=None, custom_filter_functions=None):
        filters = []
        if res or resolution:
            if isinstance(res, str) or isinstance(resolution, str): filters.append(lambda s: s.resolution == (res or resolution))
            elif isinstance(res, list) or isinstance(resolution, list): filters.append(lambda s: s.resolution in (res or resolution))
        if fps: filters.append(lambda s: s.fps == fps)
        if mime_type: filters.append(lambda s: s.mime_type == mime_type)
        if type: filters.append(lambda s: s.type == type)
        if subtype or file_extension: filters.append(lambda s: s.subtype == (subtype or file_extension))
        if abr or bitrate: filters.append(lambda s: s.abr == (abr or bitrate))
        if video_codec: filters.append(lambda s: s.video_codec == video_codec)
        if audio_codec: filters.append(lambda s: s.audio_codec == audio_codec)
        if only_audio: filters.append(lambda s: (s.includesaudiotrack and not s.includesvideotrack))
        if only_video: filters.append(lambda s: (s.includesvideotrack and not s.includesaudiotrack))
        if progressive: filters.append(lambda s: s.isprogressive)
        if adaptive: filters.append(lambda s: s.isadaptive)
        if audio_track_name: filters.append(lambda s: s.audio_track_name == audio_track_name)
        if custom_filter_functions: filters.extend(custom_filter_functions)
        if is_dash is not None: filters.append(lambda s: s.is_dash == is_dash)
        if is_drc is not None: filters.append(lambda s: s.is_drc == is_drc)
        return self._filter(filters)
    '''_filter'''
    def _filter(self, filters: List[Callable]):
        fmt_streams = self.fmt_streams
        for filter_lambda in filters: fmt_streams = filter(filter_lambda, fmt_streams)
        return StreamQuery(list(fmt_streams))
    '''orderby'''
    def orderby(self, attribute_name: str):
        has_attribute = [s for s in self.fmt_streams if getattr(s, attribute_name) is not None]
        if has_attribute and isinstance(getattr(has_attribute[0], attribute_name), str):
            try: return StreamQuery(sorted(has_attribute, key=lambda s: int("".join(filter(str.isdigit, getattr(s, attribute_name))))))
            except ValueError: pass
        return StreamQuery(sorted(has_attribute, key=lambda s: getattr(s, attribute_name)))
    '''desc'''
    def desc(self):
        return StreamQuery(self.fmt_streams[::-1])
    '''asc'''
    def asc(self):
        return self
    '''getbyitag'''
    def getbyitag(self, itag: Union[int, str]):
        if isinstance(itag, int): return self.itag_index.get(itag)
        elif isinstance(itag, str) and itag.isdigit(): return self.itag_index.get(int(itag))
    '''getbyresolution'''
    def getbyresolution(self, resolution: str):
        return self.filter(progressive=True, subtype="mp4", resolution=resolution).first()
    '''getdefaultaudiotrack'''
    def getdefaultaudiotrack(self):
        return self._filter([lambda s: s.is_default_audio_track])
    '''getextraaudiotrack'''
    def getextraaudiotrack(self):
        return self._filter([lambda s: not s.is_default_audio_track and s.includesaudiotrack and not s.includesvideotrack])
    '''getextraaudiotrackbyname'''
    def getextraaudiotrackbyname(self, name):
        return self._filter([lambda s: s.audio_track_name == name])
    '''getlowestresolution'''
    def getlowestresolution(self, progressive=True):
        return self.filter(progressive=progressive, subtype="mp4").orderby("resolution").first()
    '''gethighestresolution'''
    def gethighestresolution(self, progressive=True, mime_type=None):
        return self.filter(progressive=progressive, mime_type=mime_type).orderby("resolution").last()
    '''getaudioonly'''
    def getaudioonly(self, subtype: str = "mp4"):
        return self.filter(only_audio=True, subtype=subtype).orderby("abr").last()
    '''otf'''
    def otf(self, is_otf: bool = False):
        return self._filter([lambda s: s.is_otf == is_otf])
    '''first'''
    def first(self):
        try: return self.fmt_streams[0]
        except IndexError: return None
    '''last'''
    def last(self):
        try: return self.fmt_streams[-1]
        except IndexError: pass
    '''count'''
    def count(self, value: Optional[str] = None):
        return self.fmt_streams.count(value) if value else len(self)
    '''all'''
    def all(self):
        return self.fmt_streams
    '''getitem'''
    def __getitem__(self, i: Union[slice, int]):
        return self.fmt_streams[i]
    '''len'''
    def __len__(self):
        return len(self.fmt_streams)


'''InnerTube'''
class InnerTube:
    def __init__(self, client='ANDROID_VR', use_oauth=False, allow_cache=True, token_file=None, oauth_verifier=None, use_po_token=False, po_token_verifier=None):
        self.client_name = client
        self.innertube_context = DEFAULT_CLIENTS[client]['innertube_context']
        self.header = DEFAULT_CLIENTS[client]['header']
        self.api_key = DEFAULT_CLIENTS[client]['api_key']
        self.require_js_player = DEFAULT_CLIENTS[client]['require_js_player']
        self.require_po_token = DEFAULT_CLIENTS[client]['require_po_token']
        self.access_token = None
        self.refresh_token = None
        self.access_po_token = None
        self.access_visitorData = None
        self.use_oauth = use_oauth
        self.allow_cache = allow_cache
        self.oauth_verifier = oauth_verifier or defaultoauthverifier
        self.expires = None
        self.use_po_token = use_po_token
        self.po_token_verifier = po_token_verifier or defaultpotokenverifier
        if not self.allow_cache:
            cache_dir = os.path.join(os.path.dirname(__file__), '__cache__')
            if os.path.exists(cache_dir) and os.path.isdir(cache_dir):
                shutil.rmtree(cache_dir)
        self.token_file = token_file or os.path.join(pathlib.Path(__file__).parent.resolve() / '__cache__', 'tokens.json')
        if self.use_oauth and self.allow_cache and os.path.exists(self.token_file):
            with open(self.token_file) as f:
                data = json.load(f)
                if data['access_token']:
                    self.access_token = data['access_token']
                    self.refresh_token = data['refresh_token']
                    self.expires = data['expires']
                    self.refreshbearertoken()
        if self.use_po_token and self.allow_cache and os.path.exists(self.token_file):
            with open(self.token_file) as f:
                data = json.load(f)
                self.access_visitorData = data['visitorData']
                self.access_po_token = data['po_token']
    '''cachetokens'''
    def cachetokens(self):
        if not self.allow_cache: return
        data = {'access_token': self.access_token, 'refresh_token': self.refresh_token, 'expires': self.expires, 'visitorData': self.access_visitorData, 'po_token': self.access_po_token}
        cache_dir = os.path.dirname(self.token_file)
        if not os.path.exists(cache_dir): os.makedirs(cache_dir, exist_ok=True)
        with open(self.token_file, 'w') as f: json.dump(data, f)
    '''refreshbearertoken'''
    def refreshbearertoken(self, force=False):
        if not self.use_oauth: return
        if self.expires > time.time() and not force: return
        start_time = int(time.time() - 30)
        data = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'refresh_token', 'refresh_token': self.refresh_token}
        resp = RequestWrapper._executerequest('https://oauth2.googleapis.com/token', 'POST', headers={'Content-Type': 'application/json'}, data=data)
        resp_data = json.loads(resp.read())
        self.access_token = resp_data['access_token']
        self.expires = start_time + resp_data['expires_in']
        self.cachetokens()
    '''fetchbearertoken'''
    def fetchbearertoken(self):
        start_time = int(time.time() - 30)
        data = {'client_id': CLIENT_ID, 'scope': 'https://www.googleapis.com/auth/youtube'}
        resp = RequestWrapper._executerequest('https://oauth2.googleapis.com/device/code', 'POST', headers={'Content-Type': 'application/json'}, data=data)
        resp_data = json.loads(resp.read())
        verification_url = resp_data['verification_url']
        user_code = resp_data['user_code']
        self.oauth_verifier(verification_url, user_code)
        data = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'device_code': resp_data['device_code'], 'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'}
        resp = RequestWrapper._executerequest('https://oauth2.googleapis.com/token', 'POST', headers={'Content-Type': 'application/json'}, data=data)
        resp_data = json.loads(resp.read())
        self.access_token = resp_data['access_token']
        self.refresh_token = resp_data['refresh_token']
        self.expires = start_time + resp_data['expires_in']
        self.cachetokens()
    '''insertvisitordata'''
    def insertvisitordata(self, visitor_data: str):
        self.innertube_context['context']['client'].update({"visitorData": visitor_data})
    '''insertpotoken'''
    def insertpotoken(self, visitor_data: str = None, po_token : str = None):
        self.insertvisitordata(self.access_visitorData or visitor_data)
        self.innertube_context.update({"serviceIntegrityDimensions": {"poToken": self.access_po_token or po_token}})
    '''fetchpotoken'''
    def fetchpotoken(self):
        self.access_visitorData, self.access_po_token = self.po_token_verifier()
        self.cachetokens()
        self.insertpotoken()
    '''baseurl'''
    @property
    def baseurl(self):
        return 'https://www.youtube.com/youtubei/v1'
    '''basedata'''
    @property
    def basedata(self):
        return self.innertube_context
    '''baseparams'''
    @property
    def baseparams(self):
        return {'prettyPrint': "false"}
    '''callapi'''
    def callapi(self, endpoint, query, data):
        endpoint_url = f'{endpoint}?{parse.urlencode(query)}'
        headers = {'Content-Type': 'application/json'}
        if self.use_oauth:
            if self.access_token: self.refreshbearertoken()
            else: self.fetchbearertoken()
            headers['Authorization'] = f'Bearer {self.access_token}'
        if self.use_po_token:
            if self.access_po_token: self.insertpotoken()
            else: self.fetchpotoken()
        headers.update(self.header)
        resp = RequestWrapper._executerequest(endpoint_url, 'POST', headers=headers, data=data)
        return json.loads(resp.read())
    '''browse'''
    def browse(self, continuation=None, visitor_data=None):
        endpoint = f'{self.baseurl}/browse'
        query = self.baseparams
        if continuation: self.basedata.update({"continuation": continuation})
        if visitor_data: self.basedata['context']['client'].update({"visitorData": visitor_data})
        return self.callapi(endpoint, query, self.basedata)
    '''next'''
    def next(self, video_id: str = None, continuation: str = None):
        if continuation: self.basedata.update({"continuation": continuation})
        if video_id: self.basedata.update({'videoId': video_id, 'contentCheckOk': "true"})
        endpoint = f'{self.baseurl}/next'
        query = self.baseparams
        return self.callapi(endpoint, query, self.basedata)
    '''player'''
    def player(self, video_id):
        endpoint = f'{self.baseurl}/player'
        query = self.baseparams
        self.basedata.update({'videoId': video_id, 'contentCheckOk': "true"})
        return self.callapi(endpoint, query, self.basedata)
    '''search'''
    def search(self, search_query, continuation=None, data=None):
        endpoint = f'{self.baseurl}/search'
        query = self.baseparams
        data = data if data else {}
        self.basedata.update({'query': search_query})
        if continuation: data['continuation'] = continuation
        data.update(self.basedata)
        return self.callapi(endpoint, query, data)
    '''verifyage'''
    def verifyage(self, video_id):
        endpoint = f'{self.baseurl}/verify_age'
        data = {'nextEndpoint': {'watchEndpoint': {'racyCheckOk': True, 'contentCheckOk': True, 'videoId': video_id}}, 'setControvercy': True}
        data.update(self.basedata)
        result = self.callapi(endpoint, self.baseparams, data)
        return result
    '''gettranscript'''
    def gettranscript(self, video_id):
        endpoint = f'{self.baseurl}/get_transcript'
        query = {'videoId': video_id}
        query.update(self.baseparams)
        result = self.callapi(endpoint, query, self.basedata)
        return result


'''YouTubeMetadata'''
class YouTubeMetadata:
    def __init__(self, metadata):
        self._raw_metadata = metadata
        self._metadata = [{}]
        for el in metadata:
            if 'title' in el and 'simpleText' in el['title']: metadata_title = el['title']['simpleText']
            else: continue
            contents = el['contents'][0]
            if 'simpleText' in contents: self._metadata[-1][metadata_title] = contents['simpleText']
            elif 'runs' in contents: self._metadata[-1][metadata_title] = contents['runs'][0]['text']
            if el.get('hasDividerLine', False): self._metadata.append({})
        if self._metadata[-1] == {}: self._metadata = self._metadata[:-1]
    '''getitem'''
    def __getitem__(self, key):
        return self._metadata[key]
    '''iter'''
    def __iter__(self):
        for el in self._metadata:
            yield el
    '''str'''
    def __str__(self):
        return json.dumps(self._metadata)
    '''rawmetadata'''
    @property
    def rawmetadata(self):
        return self._raw_metadata
    '''metadata'''
    @property
    def metadata(self):
        return self._metadata


'''Cipher'''
class Cipher:
    def __init__(self, js: str, js_url: str):
        self.js_url = js_url
        self.js = js
        self._sig_param_val = None
        self._nsig_param_val = None
        self.sig_function_name = self.getsigfunctionname(js, js_url)
        self.nsig_function_name = self.getnsigfunctionname(js, js_url)
        self.runner_sig = NodeRunner(js)
        self.runner_sig.loadfunction(self.sig_function_name)
        self.runner_nsig = NodeRunner(js)
        self.runner_nsig.loadfunction(self.nsig_function_name)
        self.calculated_n = None
    '''getnsig'''
    def getnsig(self, n: str):
        try:
            if self._nsig_param_val:
                for param in self._nsig_param_val:
                    nsig = self.runner_nsig.call([param, n])
                    if not isinstance(nsig, str): continue
                    else: break
            else:
                nsig = self.runner_nsig.call([n])
        except Exception as err:
            raise err
        if 'error' in nsig or '_w8_' in nsig or not isinstance(nsig, str): raise Exception 
        return nsig
    '''getsig'''
    def getsig(self, ciphered_signature: str):
        try:
            if self._sig_param_val: sig = self.runner_sig.call([self._sig_param_val, ciphered_signature])
            else: sig = self.runner_sig.call([ciphered_signature])
        except Exception as err:
            raise err
        if 'error' in sig or not isinstance(sig, str): raise Exception 
        return sig
    '''getsigfunctionname'''
    def getsigfunctionname(self, js: str, js_url: str):
        function_patterns = [
            r'(?P<sig>[a-zA-Z0-9_$]+)\s*=\s*function\(\s*(?P<arg>[a-zA-Z0-9_$]+)\s*\)\s*{\s*(?P=arg)\s*=\s*(?P=arg)\.split\(\s*[a-zA-Z0-9_\$\"\[\]]+\s*\)\s*;\s*[^}]+;\s*return\s+(?P=arg)\.join\(\s*[a-zA-Z0-9_\$\"\[\]]+\s*\)',
            r'(?:\b|[^a-zA-Z0-9_$])(?P<sig>[a-zA-Z0-9_$]{2,})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)(?:;[a-zA-Z0-9_$]{2}\.[a-zA-Z0-9_$]{2}\(a,\d+\))?',
            r'\b(?P<var>[a-zA-Z0-9_$]+)&&\((?P=var)=(?P<sig>[a-zA-Z0-9_$]{2,})\((?:(?P<param>\d+),decodeURIComponent|decodeURIComponent)\((?P=var)\)\)',
            r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
            r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
            r'\bm=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(h\.s\)\)',
            r'("|\')signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
            r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(',
            r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(',
            r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
            r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\('
        ]
        for pattern in function_patterns:
            regex = re.compile(pattern)
            function_match = regex.search(js)
            if function_match:
                sig = function_match.group('sig')
                if "param" in function_match.groupdict():
                    param = function_match.group('param')
                    if param: self._sig_param_val = int(param)
                return sig
        raise Exception
    '''getnsigfunctionname'''
    def getnsigfunctionname(self, js: str, js_url: str):
        try:
            pattern = r"var\s*[a-zA-Z0-9$_]{3}\s*=\s*\[(?P<funcname>[a-zA-Z0-9$_]{3})\]"
            func_name = re.search(pattern, js)
            if func_name: return func_name.group("funcname")
            else:
                global_obj, varname, code = extractplayerjsglobalvar(js)
                if global_obj and varname and code:
                    global_obj = JSInterpreter(js).interpretexpression(code, {}, 100)
                    for k, v in enumerate(global_obj):
                        if v.endswith('_w8_'):
                            pattern = r'''(?xs)
                                    [;\n](?:
                                        (?P<f>function\s+)|
                                        (?:var\s+)?
                                    )(?P<funcname>[a-zA-Z0-9_$]+)\s*(?(f)|=\s*function\s*)
                                    \(\s*(?:[a-zA-Z0-9_$]+\s*,\s*)?(?P<argname>[a-zA-Z0-9_$]+)(?:\s*,\s*[a-zA-Z0-9_$]+)*\s*\)\s*\{
                                    (?:(?!(?<!\{)\};(?![\]\)])).)*
                                    \}\s*catch\(\s*[a-zA-Z0-9_$]+\s*\)\s*
                                    \{\s*(?:return\s+|[\w=]+)%s\[%d\]\s*\+\s*(?P=argname)\s*[\};].*?\s*return\s+[^}]+\}[;\n]
                                '''  % (re.escape(varname), k)
                            func_name = re.search(pattern, js)
                            if func_name:
                                n_func = func_name.group("funcname")
                                self._nsig_param_val = self._extractnsigparamval(js, n_func)
                                return n_func
                            raise Exception
        except Exception as err:
            raise err
    '''_extractnsigparamval'''
    @staticmethod
    def _extractnsigparamval(code: str, func_name: str):
        pattern = re.compile(
            rf'(?<![A-Za-z0-9_$\.])' 
            rf'(?P<func>{re.escape(func_name)})\s*'
            r'\[\w\[\d+\]\]'
            r'\(\s*'
            r'(?P<arg1>[A-Za-z0-9_$]+)'
            r'(?:\s*,\s*(?P<arg2>[A-Za-z0-9_$]+))?'
            r'(?:\s*,\s*[^)]*)?'
            r'\s*\)',
            re.MULTILINE
        )
        results = []
        for m in pattern.finditer(code):
            chosen = m.group('arg2') if m.group('arg1') == 'this' and m.group('arg2') else m.group('arg1')
            results.append(chosen)
        return results


'''YouTube'''
class YouTube:
    def __init__(self, video_id: str, client: str = InnerTube().client_name, on_progress_callback: Optional[Callable[[Any, bytes, int], None]] = None, on_complete_callback: Optional[Callable[[Any, Optional[str]], None]] = None,
                 use_oauth: bool = False, allow_oauth_cache: bool = True, token_file: Optional[str] = None, oauth_verifier: Optional[Callable[[str, str], None]] = None, use_po_token: Optional[bool] = False,
                 po_token_verifier: Optional[Callable[[None], Tuple[str, str]]] = None):
        self._js: Optional[str] = None
        self._js_url: Optional[str] = None
        self._vid_info: Optional[Dict] = None
        self._vid_details: Optional[Dict] = None
        self._watch_html: Optional[str] = None
        self._embed_html: Optional[str] = None
        self._player_config_args: Optional[Dict] = None
        self._age_restricted: Optional[bool] = None
        self._fmt_streams: Optional[List[Stream]] = None
        self._initial_data = None
        self._metadata = None
        self.video_id = video_id
        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"
        self.client = client
        self.client = 'TV' if use_oauth else self.client
        self.fallback_clients = ['TV', 'IOS']
        self._signature_timestamp: dict = {}
        self._visitor_data = None
        self.stream_monostate = Monostate(on_progress=on_progress_callback, on_complete=on_complete_callback, youtube=self)
        self._author = None
        self._title = None
        self.use_oauth = use_oauth
        self.allow_oauth_cache = allow_oauth_cache
        self.token_file = token_file
        self.oauth_verifier = oauth_verifier
        self.use_po_token = use_po_token
        self.po_token_verifier = po_token_verifier
        self.po_token = None
        self._pot = None
    '''watch_html'''
    @property
    def watch_html(self):
        if self._watch_html: return self._watch_html
        self._watch_html = RequestWrapper.get(url=self.watch_url)
        return self._watch_html
    '''embed_html'''
    @property
    def embed_html(self):
        if self._embed_html: return self._embed_html
        self._embed_html = RequestWrapper.get(url=self.embed_url)
        return self._embed_html
    '''age_restricted'''
    @property
    def age_restricted(self):
        if self._age_restricted: return self._age_restricted
        self._age_restricted = isagerestricted(self.watch_html)
        return self._age_restricted
    '''js_url'''
    @property
    def js_url(self):
        if self._js_url: return self._js_url
        if self.age_restricted: self._js_url = extractjsurl(self.embed_html)
        else: self._js_url = extractjsurl(self.watch_html)
        return self._js_url
    '''js'''
    @property
    def js(self):
        if self._js: return self._js
        self._js = RequestWrapper.get(self.js_url)
        return self._js
    '''visitor_data'''
    @property
    def visitor_data(self):
        if self._visitor_data: return self._visitor_data
        if InnerTube(self.client).require_po_token:
            try:
                self._visitor_data = extractvisitordata(str(self.initial_data['responseContext']))
                return self._visitor_data
            except:
                pass
        innertube_response = InnerTube('WEB').player(self.video_id)
        try:
            self._visitor_data = innertube_response['responseContext']['visitorData']
        except KeyError:
            p_dicts = innertube_response['responseContext']['serviceTrackingParams'][0]['params']
            self._visitor_data = next(p for p in p_dicts if p['key'] == 'visitor_data')['value']
        return self._visitor_data
    '''pot'''
    @property
    def pot(self):
        if self._pot: return self._pot
        try:
            self._pot = generatepotoken(video_id=self.video_id)
        except Exception as err:
            pass
        return self._pot
    '''initial_data'''
    @property
    def initial_data(self):
        if self._initial_data: return self._initial_data
        self._initial_data = extractinitialdata(self.watch_html)
        return self._initial_data
    '''streaming_data'''
    @property
    def streaming_data(self):
        invalid_id_list = ['aQvGIIdgFDM']
        if 'streamingData' not in self.vid_info or self.vid_info['videoDetails']['videoId'] in invalid_id_list:
            for client in self.fallback_clients:
                self.client = client
                self.vid_info = None
                if 'streamingData' in self.vid_info: break
        return self.vid_info['streamingData']
    '''fmt_streams'''
    @property
    def fmt_streams(self):
        if self._fmt_streams: return self._fmt_streams
        self._fmt_streams = []
        stream_manifest = applydescrambler(self.streaming_data)
        inner_tube = InnerTube(self.client)
        if self.po_token: applypotoken(stream_manifest, self.vid_info, self.po_token)
        if inner_tube.require_js_player:
            try:
                applysignature(stream_manifest, self.vid_info, self.js, self.js_url)
            except:
                self._js = None
                self._js_url = None
                applysignature(stream_manifest, self.vid_info, self.js, self.js_url)
        for stream in stream_manifest:
            video = Stream(stream=stream, monostate=self.stream_monostate, po_token=self.po_token, video_playback_ustreamer_config=self.video_playback_ustreamer_config)
            self._fmt_streams.append(video)
        self.stream_monostate.title = self.title
        self.stream_monostate.duration = self.length
        return self._fmt_streams
    '''signature_timestamp'''
    @property
    def signature_timestamp(self):
        if not self._signature_timestamp:
            self._signature_timestamp = {'playbackContext': {'contentPlaybackContext': {'signatureTimestamp': extractsignaturetimestamp(self.js)}}}
        return self._signature_timestamp
    '''video_playback_ustreamer_config'''
    @property
    def video_playback_ustreamer_config(self):
        return self.vid_info['playerConfig']['mediaCommonConfig']['mediaUstreamerRequestConfig']['videoPlaybackUstreamerConfig']
    '''server_abr_streaming_url'''
    @property
    def server_abr_streaming_url(self):
        try:
            url = self.vid_info['streamingData']['serverAbrStreamingUrl']
            stream_manifest = [{"url": url}]
            applysignature(stream_manifest, vid_info=self.vid_info, js=self.js, url_js=self.js_url)
            return stream_manifest[0]["url"]
        except Exception:
            return None
    '''vid_info'''
    @property
    def vid_info(self):
        if self._vid_info: return self._vid_info
        self._vid_info = self.vid_info_client()
        return self._vid_info
    @vid_info.setter
    def vid_info(self, value):
        self._vid_info = value
    '''vid_info_client'''
    def vid_info_client(self, optional_client=None):
        if optional_client is None:
            if self._vid_info: return self._vid_info
            optional_client = self.client
        def _callinnertube(optional_client):
            innertube = InnerTube(
                client=optional_client, use_oauth=self.use_oauth, allow_cache=self.allow_oauth_cache, token_file=self.token_file, oauth_verifier=self.oauth_verifier,
                use_po_token=self.use_po_token, po_token_verifier=self.po_token_verifier
            )
            if innertube.require_js_player: innertube.innertube_context.update(self.signature_timestamp)
            if innertube.require_po_token and not self.use_po_token: innertube.insertvisitordata(visitor_data=self.visitor_data)
            elif not self.use_po_token: innertube.insertvisitordata(visitor_data=self.visitor_data)
            response = innertube.player(self.video_id)
            if self.use_po_token or innertube.require_po_token: self.po_token = innertube.access_po_token or self.pot
            return response
        innertube_response = _callinnertube(optional_client)
        for client in self.fallback_clients:
            playability_status = innertube_response['playabilityStatus']
            if playability_status['status'] == 'UNPLAYABLE' and 'reason' in playability_status and playability_status['reason'] == 'This video is not available':
                self.client = client
                innertube_response = _callinnertube(client)
            else:
                break
        return innertube_response
    '''vid_details'''
    @property
    def vid_details(self):
        if self._vid_details: return self._vid_details
        innertube = InnerTube(
            client='TV' if self.use_oauth else 'WEB', use_oauth=self.use_oauth, allow_cache=self.allow_oauth_cache, token_file=self.token_file,
            oauth_verifier=self.oauth_verifier, use_po_token=self.use_po_token, po_token_verifier=self.po_token_verifier
        )
        innertube_response = innertube.next(self.video_id)
        self._vid_details = innertube_response
        return self._vid_details
    @vid_details.setter
    def vid_details(self, value):
        self._vid_details = value
    '''streams'''
    @property
    def streams(self):
        return StreamQuery(self.fmt_streams)
    '''vid_engagement_items'''
    def vid_engagement_items(self):
        for i in range(len(self.vid_details.get('engagementPanels', []))):
            try:
                return self.vid_details['engagementPanels'][i]['engagementPanelSectionListRenderer']['content']['structuredDescriptionContentRenderer']['items']
            except:
                continue
    '''title'''
    @property
    def title(self):
        self._author = self.vid_info.get("videoDetails", {}).get("author", "unknown")
        if self._title: return self._title
        if self.use_oauth == True: self._title = self.vid_engagement_items()[0]['videoDescriptionHeaderRenderer']['title']['runs'][0]['text']
        if 'title' in self.vid_info['videoDetails']:
            self._title = self.vid_info['videoDetails']['title']
        else:
            if 'singleColumnWatchNextResults' in self.vid_details['contents']:
                contents = self.vid_details['contents']['singleColumnWatchNextResults']['results']['results']['contents'][0]['itemSectionRenderer']['contents'][0]
                if 'videoMetadataRenderer' in contents:
                    self._title = contents['videoMetadataRenderer']['title']['runs'][0]['text']
                else:
                    self._title = contents['musicWatchMetadataRenderer']['title']['simpleText']
            elif 'twoColumnWatchNextResults' in self.vid_details['contents']:
                contents = self.vid_details['contents']['twoColumnWatchNextResults']['results']['results']['contents']
                for videoPrimaryInfoRenderer in contents:
                    if 'videoPrimaryInfoRenderer' in videoPrimaryInfoRenderer:
                        self._title = videoPrimaryInfoRenderer['videoPrimaryInfoRenderer']['title']['runs'][0]['text']
                        break
        return self._title
    @title.setter
    def title(self, value):
        self._title = value
    '''length'''
    @property
    def length(self):
        return int(self.vid_info.get('videoDetails', {}).get('lengthSeconds'))
    '''author'''
    @property
    def author(self):
        _author = self.vid_info.get("videoDetails", {}).get("author", "unknown")
        if self.use_oauth == True: _author = self.vid_engagement_items()[0]['videoDescriptionHeaderRenderer']['channel']['simpleText']
        self._author = _author
        return self._author
    @author.setter
    def author(self, value):
        self._author = value
    '''metadata'''
    @property
    def metadata(self):
        if not self._metadata:
            self._metadata = extractmetadata(self.initial_data)
        return self._metadata