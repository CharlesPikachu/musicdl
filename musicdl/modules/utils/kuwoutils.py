'''
Function:
    Implementation of KuwoMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import base64


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
SECRET_KEY = b"ylzsxkwm"
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
        l2 = 0
        for i in HelperFunctions.rangen(n):
            idx = arr_int[i]
            if idx < 0: continue
            if (l & ARRAYMASK[idx]) == 0: continue
            l2 |= ARRAYMASK[i]
        return HelperFunctions.u64(l2)
    '''des64'''
    @staticmethod
    def des64(longs, l):
        p_r, p_source, out = [0] * 8, [0, 0], KuwoMusicClientUtils.bittransform(ARRAYIP2, 64, l)
        p_source[0], p_source[1] = HelperFunctions.u32(out), HelperFunctions.u32((out & 0xFFFFFFFF00000000) >> 32)
        for i in HelperFunctions.rangen(16):
            s_out, R = 0, KuwoMusicClientUtils.bittransform(ARRAYE, 64, p_source[1])
            R ^= longs[i]
            for j in HelperFunctions.rangen(8): p_r[j] = (R >> (j * 8)) & 0xFF
            for sbi in reversed(HelperFunctions.rangen(8)): s_out = (s_out << 4) | (MATRIXNSBOX[sbi][p_r[sbi]] & 0xF)
            R, L = KuwoMusicClientUtils.bittransform(ARRAYP, 32, s_out), p_source[0]
            p_source[0] = p_source[1]
            p_source[1] = HelperFunctions.u32(L ^ R)
        p_source.reverse()
        out = ((p_source[1] << 32) & 0xFFFFFFFF00000000) | (p_source[0] & 0xFFFFFFFF)
        out = KuwoMusicClientUtils.bittransform(ARRAYIP1, 64, out)
        return HelperFunctions.u64(out)
    '''subkeys'''
    @staticmethod
    def subkeys(l, longs, mode):
        l2 = KuwoMusicClientUtils.bittransform(ARRAYPC1, 56, l)
        for i in HelperFunctions.rangen(16):
            r = ARRAYLS[i]
            mask = ARRAYLSMASK[r]
            not_mask = HelperFunctions.u64(~mask)
            part1, part2 = HelperFunctions.u64((l2 & mask) << (28 - r)), (l2 & not_mask) >> r
            l2 = HelperFunctions.u64(part1 | part2)
            longs[i] = KuwoMusicClientUtils.bittransform(ARRAYPC2, 64, l2)
        if mode == 1:
            for j in HelperFunctions.rangen(8): longs[j], longs[15 - j] = longs[15 - j], longs[j]
    '''crypt'''
    @staticmethod
    def crypt(msg: bytes, key: bytes, mode: int) -> bytes:
        l = 0
        for i in HelperFunctions.rangen(8): l |= (key[i] & 0xFF) << (i * 8)
        l, j, arr_long1 = HelperFunctions.u64(l), len(msg) // 8, [0] * 16
        KuwoMusicClientUtils.subkeys(l, arr_long1, mode)
        arr_long2 = [0] * j
        for m in HelperFunctions.rangen(j):
            v = 0
            for n in HelperFunctions.rangen(8): v |= (msg[n + m * 8] & 0xFF) << (n * 8)
            arr_long2[m] = HelperFunctions.u64(v)
        arr_long3 = [0] * ((1 + 8 * (j + 1)) // 8)
        for i1 in HelperFunctions.rangen(j): arr_long3[i1] = KuwoMusicClientUtils.des64(arr_long1, arr_long2[i1])
        arr_byte1, l2 = msg[j * 8:], 0
        for i1 in HelperFunctions.rangen(len(msg) % 8): l2 |= (arr_byte1[i1] & 0xFF) << (i1 * 8)
        l2 = HelperFunctions.u64(l2)
        if len(arr_byte1) != 0 or mode == 0: arr_long3[j] = KuwoMusicClientUtils.des64(arr_long1, l2)
        out_bytes, i4 = bytearray(8 * len(arr_long3)), 0
        for l3 in arr_long3:
            for i6 in HelperFunctions.rangen(8): out_bytes[i4] = (l3 >> (i6 * 8)) & 0xFF; i4 += 1
        return bytes(out_bytes)
    '''encrypt'''
    @staticmethod
    def encrypt(msg: bytes) -> bytes:
        return KuwoMusicClientUtils.crypt(msg, SECRET_KEY, 0)
    '''decrypt'''
    @staticmethod
    def decrypt(msg: bytes) -> bytes:
        return KuwoMusicClientUtils.crypt(msg, SECRET_KEY, 1)
    '''encryptquery'''
    @staticmethod
    def encryptquery(query: str) -> str:
        return base64.b64encode(KuwoMusicClientUtils.encrypt(query.encode("utf-8"))).decode("ascii")