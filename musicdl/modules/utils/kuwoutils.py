'''
Function:
    Implementation of KuwoMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import math
import zlib
import base64
from operator import or_
from functools import reduce
from itertools import accumulate


'''settings'''
MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1


'''HelperFunctions'''
class HelperFunctions():
    @staticmethod
    def u64(x: int) -> int: return x & MASK64
    @staticmethod
    def u32(x: int) -> int: return x & MASK32
    @staticmethod
    def rangen(n: int): return range(n)
    @staticmethod
    def power2(n: int) -> int: return 1 << n
    @staticmethod
    def longarray(*arr): return list(arr)


'''settings'''
SECRET_KEY_SONG, SECRET_KEY_LYRIC = b"ylzsxkwm", b'yeelion'
ARRAYLS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
ARRAYLSMASK = HelperFunctions.longarray(0, 0x100001, 0x300003)
ARRAYE = HelperFunctions.longarray(31, 0, 1, 2, 3, 4, -1, -1, 3, 4, 5, 6, 7, 8, -1, -1, 7, 8, 9, 10, 11, 12, -1, -1, 11, 12, 13, 14, 15, 16, -1, -1, 15, 16, 17, 18, 19, 20, -1, -1, 19, 20, 21, 22, 23, 24, -1, -1, 23, 24, 25, 26, 27, 28, -1, -1, 27, 28, 29, 30, 31, 30, -1, -1)
ARRAYIP1 = HelperFunctions.longarray(39, 7, 47, 15, 55, 23, 63, 31, 38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53, 21, 61, 29, 36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27, 34, 2, 42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25, 32, 0, 40, 8, 48, 16, 56, 24)
ARRAYIP2 = HelperFunctions.longarray(57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3, 61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7, 56, 48, 40, 32, 24, 16, 8, 0, 58, 50, 42, 34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4, 62, 54, 46, 38, 30, 22, 14, 6)
ARRAYMASK = [HelperFunctions.power2(n) for n in HelperFunctions.rangen(64)]
ARRAYMASK[-1] = -ARRAYMASK[-1]
ARRAYP = HelperFunctions.longarray(15, 6, 19, 20, 28, 11, 27, 16, 0, 14, 22, 25, 4, 17, 30, 9, 1, 7, 23, 13, 31, 26, 2, 8, 18, 12, 29, 5, 21, 10, 3, 24)
ARRAYPC1 = HelperFunctions.longarray(56, 48, 40, 32, 24, 16, 8, 0, 57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18, 10, 2, 59, 51, 43, 35, 62, 54, 46, 38, 30, 22, 14, 6, 61, 53, 45, 37, 29, 21, 13, 5, 60, 52, 44, 36, 28, 20, 12, 4, 27, 19, 11, 3)
ARRAYPC2 = HelperFunctions.longarray(13, 16, 10, 23, 0, 4, -1, -1, 2, 27, 14, 5, 20, 9, -1, -1, 22, 18, 11, 3, 25, 7, -1, -1, 15, 6, 26, 19, 12, 1, -1, -1, 40, 51, 30, 36, 46, 54, -1, -1, 29, 39, 50, 44, 32, 47, -1, -1, 43, 48, 38, 55, 33, 52, -1, -1, 45, 41, 49, 35, 28, 31, -1, -1)
MATRIXNSBOX = [
    [14,4,3,15,2,13,5,3,13,14,6,9,11,2,0,5,4,1,10,12,15,6,9,10,1,8,12,7,8,11,7,0,0,15,10,5,14,4,9,10,7,8,12,3,13,1,3,6,15,12,6,11,2,9,5,0,4,2,11,14,1,7,8,13],
    [15,0,9,5,6,10,12,9,8,7,2,12,3,13,5,2,1,14,7,8,11,4,0,3,14,11,13,6,4,1,10,15,3,13,12,11,15,3,6,0,4,10,1,7,8,4,11,14,13,8,0,6,2,15,9,5,7,1,10,12,14,2,5,9],
    [10,13,1,11,6,8,11,5,9,4,12,2,15,3,2,14,0,6,13,1,3,15,4,10,14,9,7,12,5,0,8,7,13,1,2,4,3,6,12,11,0,13,5,14,6,8,15,2,7,10,8,15,4,9,11,5,9,0,14,3,10,7,1,12],
    [7,10,1,15,0,12,11,5,14,9,8,3,9,7,4,8,13,6,2,1,6,11,12,2,3,0,5,14,10,13,15,4,13,3,4,9,6,10,1,12,11,0,2,5,0,13,14,2,8,15,7,4,15,1,10,7,5,6,12,11,3,8,9,14],
    [2,4,8,15,7,10,13,6,4,1,3,12,11,7,14,0,12,2,5,9,10,13,0,3,1,11,15,5,6,8,9,14,14,11,5,6,4,1,3,10,2,12,15,0,13,2,8,5,11,8,0,15,7,14,9,4,12,7,10,9,1,13,6,3],
    [12,9,0,7,9,2,14,1,10,15,3,4,6,12,5,11,1,14,13,0,2,8,7,13,15,5,4,10,8,3,11,6,10,4,6,11,7,9,0,6,4,2,13,1,9,15,3,8,15,3,1,14,12,5,11,0,2,12,14,7,5,10,8,13],
    [4,1,3,10,15,12,5,0,2,11,9,6,8,7,6,9,11,4,12,15,0,3,10,5,14,13,7,8,13,14,1,2,13,6,14,9,4,1,2,14,11,13,5,0,1,10,8,3,0,11,3,5,9,4,15,2,7,8,12,15,10,7,6,12],
    [13,7,10,0,6,9,5,15,8,4,3,10,11,14,12,5,2,11,9,6,15,12,0,3,4,1,14,13,1,2,7,8,1,2,12,15,10,4,0,3,13,14,6,9,7,8,9,6,15,1,5,12,3,10,14,5,8,7,11,0,4,13,2,11],
]


'''KuwoMusicClientUtils'''
class KuwoMusicClientUtils:
    '''bittransform'''
    @staticmethod
    def bittransform(arr_int, n, l):
        return HelperFunctions.u64(reduce(or_, (ARRAYMASK[i] for i in HelperFunctions.rangen(n) if (idx := arr_int[i]) >= 0 and (l & ARRAYMASK[idx]) != 0), 0))
    '''des64'''
    @staticmethod
    def des64(longs, l):
        p_r, p_source = [0] * 8, [HelperFunctions.u32(out := KuwoMusicClientUtils.bittransform(ARRAYIP2, 64, l)), HelperFunctions.u32((out & 0xFFFFFFFF00000000) >> 32)]
        for i in HelperFunctions.rangen(16):
            s_out, R = 0, (KuwoMusicClientUtils.bittransform(ARRAYE, 64, p_source[1]) ^ longs[i])
            p_r[:] = [((R >> (j * 8)) & 0xFF) for j in HelperFunctions.rangen(8)]
            s_out = reduce(lambda acc, sbi: (acc << 4) | (MATRIXNSBOX[sbi][p_r[sbi]] & 0xF), reversed(HelperFunctions.rangen(8)), s_out)
            p_source[0], p_source[1] = p_source[1], HelperFunctions.u32(p_source[0] ^ KuwoMusicClientUtils.bittransform(ARRAYP, 32, s_out))
        p_source.reverse(); out = ((p_source[1] << 32) & 0xFFFFFFFF00000000) | (p_source[0] & 0xFFFFFFFF)
        return HelperFunctions.u64(KuwoMusicClientUtils.bittransform(ARRAYIP1, 64, out))
    '''subkeys'''
    @staticmethod
    def subkeys(l, longs, mode):
        l2 = KuwoMusicClientUtils.bittransform(ARRAYPC1, 56, l)
        states = list(accumulate((ARRAYLS[i] for i in HelperFunctions.rangen(16)), lambda x, r: HelperFunctions.u64(HelperFunctions.u64((x & (mask := ARRAYLSMASK[r])) << (28 - r)) | ((x & HelperFunctions.u64(~mask)) >> r)), initial=l2))
        longs[:16], l2 = [KuwoMusicClientUtils.bittransform(ARRAYPC2, 64, x) for x in states[1:]], states[-1]
        longs[:] = longs[::-1] if mode == 1 else longs
    '''crypt'''
    @staticmethod
    def crypt(msg: bytes, key: bytes, mode: int) -> bytes:
        l, j = sum((key[i] & 0xFF) << (i * 8) for i in HelperFunctions.rangen(8)), len(msg) // 8
        KuwoMusicClientUtils.subkeys((l := HelperFunctions.u64(l)), (arr_long1 := [0] * 16), mode)
        arr_long2 = [HelperFunctions.u64(int.from_bytes(bytes(msg[n + m * 8] & 0xFF for n in HelperFunctions.rangen(8)), 'little')) for m in HelperFunctions.rangen(j)]
        arr_long3 = [KuwoMusicClientUtils.des64(arr_long1, arr_long2[i1]) for i1 in HelperFunctions.rangen(j)] + [0]
        arr_byte1, l2 = msg[j * 8:], int.from_bytes(bytes(x & 0xFF for x in msg[j * 8: j * 8 + (len(msg) % 8)]), 'little')
        l2 = HelperFunctions.u64(l2); arr_long3[j] = KuwoMusicClientUtils.des64(arr_long1, l2) if len(arr_byte1) != 0 or mode == 0 else arr_long3[j]
        out_bytes = bytearray((l3 >> (i6 * 8)) & 0xFF for l3 in arr_long3 for i6 in HelperFunctions.rangen(8))
        return bytes(out_bytes)
    '''encrypt'''
    @staticmethod
    def encrypt(msg: bytes) -> bytes:
        return KuwoMusicClientUtils.crypt(msg, SECRET_KEY_SONG, 0)
    '''decrypt'''
    @staticmethod
    def decrypt(msg: bytes) -> bytes:
        return KuwoMusicClientUtils.crypt(msg, SECRET_KEY_SONG, 1)
    '''encryptquery'''
    @staticmethod
    def encryptquery(query: str) -> str:
        return base64.b64encode(KuwoMusicClientUtils.encrypt(query.encode("utf-8"))).decode("ascii")
    '''xorencrypt'''
    @staticmethod
    def xorencrypt(data: bytes, key: bytes) -> bytes:
        output = bytearray(data[i] ^ key[i % len(key)] for i in range(len(data)))
        return bytes(output)
    '''buildlyricsparams'''
    @staticmethod
    def buildlyricsparams(music_id, is_get_lyricx: bool = True):
        params_str = f"user=12345,web,web,web&requester=localhost&req=1&rid=MUSIC_{music_id}"
        buf_str = (params_str + '&lrcx=1' if is_get_lyricx else params_str).encode('utf-8')
        encrypted_bytes = KuwoMusicClientUtils.xorencrypt(buf_str, SECRET_KEY_LYRIC)
        final_params = base64.b64encode(encrypted_bytes).decode('utf-8')
        return final_params
    '''decodelyrics'''
    @staticmethod
    def decodelyrics(buf: bytes, is_get_lyricx: bool):
        if buf[:10] != b'tp=content': return ''
        try: split_index = buf.index(b'\r\n\r\n') + 4; lrc_data = zlib.decompress(buf[split_index:])
        except (ValueError, zlib.error): return ''
        if not is_get_lyricx: return lrc_data.decode('gb18030', errors='ignore')
        buf_str = base64.b64decode(lrc_data.decode('utf-8'))
        decrypted_buffer = KuwoMusicClientUtils.xorencrypt(buf_str, SECRET_KEY_LYRIC)
        return decrypted_buffer.decode('gb18030', errors='ignore')
    '''formatlyricstime'''
    @staticmethod
    def formatlyricstime(ms):
        ms = 0 if math.isnan(ms) or ms < 0 else ms
        return f"[{math.floor(ms / 60000):02}:{math.floor(ms / 1000 % 60):02}.{round(ms % 1000):03}]"
    '''convertrawlrc'''
    @staticmethod
    def convertrawlrc(raw_lrc: str) -> str:
        out, i, lines, rx_line, rx_word, rx_zh = [], 0, re.split(r"\r\n|\r|\n", raw_lrc), re.compile(r"^\[(\d{2}:\d{2}\.\d{3})\](.*)$"), re.compile(r"<(-?\d+),(-?\d+)>([^<]*)"), re.compile(r"[\u4e00-\u9fa5]")
        while i < len(lines):
            if not (m := rx_line.match(lines[i])): out.append(lines[i]); i += 1; continue
            if not (payload := m.group(2)).replace("<0,0>", "").strip(): i += 1; continue
            if payload.startswith("<0,0>") and rx_zh.search(payload): i += 1; continue
            lyric = "".join(w.group(3) for w in words) if (words := list(rx_word.finditer(payload))) else payload.replace("<0,0>", "").strip(); trans = ""
            if i + 1 < len(lines) and (nm := rx_line.match(lines[i + 1])) and (next_payload := nm.group(2)).startswith("<0,0>") and rx_zh.search(next_payload): trans, i = next_payload.replace("<0,0>", "").strip(), i + 1
            out.extend([f"[{(ts := m.group(1))}]{lyric}"] + ([f"[{ts}]{trans}"] if trans else [])); i += 1
        return "\n".join(out)