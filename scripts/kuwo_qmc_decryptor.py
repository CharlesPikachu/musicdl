'''
Function:
    Implementation of KuwoQmcDecryptor
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations

import base64
import math
from pathlib import Path
from urllib.parse import unquote


class KuwoQmcDecryptor:
    KUWO_KEY = b"ylzsxkwm"
    RAW_KEY_LENGTHS = (704, 364)
    V2_PREFIX = b"QQMusic EncV2,Key:"
    V2_KEY1 = b"\x33\x38\x36\x5A\x4A\x59\x21\x40\x23\x2A\x24\x25\x5E\x26\x29\x28"
    V2_KEY2 = b"\x2A\x2A\x23\x21\x28\x23\x24\x25\x26\x5E\x61\x31\x63\x5A\x2C\x54"
    DELTA = 0x9E3779B9

    EXP = (
        31,0,1,2,3,4,-1,-1, 3,4,5,6,7,8,-1,-1,
        7,8,9,10,11,12,-1,-1, 11,12,13,14,15,16,-1,-1,
        15,16,17,18,19,20,-1,-1, 19,20,21,22,23,24,-1,-1,
        23,24,25,26,27,28,-1,-1, 27,28,29,30,31,30,-1,-1,
    )
    IPERM = (
        57,49,41,33,25,17,9,1, 59,51,43,35,27,19,11,3,
        61,53,45,37,29,21,13,5, 63,55,47,39,31,23,15,7,
        56,48,40,32,24,16,8,0, 58,50,42,34,26,18,10,2,
        60,52,44,36,28,20,12,4, 62,54,46,38,30,22,14,6,
    )
    FPERM = (
        39,7,47,15,55,23,63,31, 38,6,46,14,54,22,62,30,
        37,5,45,13,53,21,61,29, 36,4,44,12,52,20,60,28,
        35,3,43,11,51,19,59,27, 34,2,42,10,50,18,58,26,
        33,1,41,9,49,17,57,25, 32,0,40,8,48,16,56,24,
    )
    ROUND_P = (
        15,6,19,20,28,11,27,16, 0,14,22,25,4,17,30,9,
        1,7,23,13,31,26,2,8, 18,12,29,5,21,10,3,24,
    )
    KPC1 = (
        56,48,40,32,24,16,8,0, 57,49,41,33,25,17,9,1,
        58,50,42,34,26,18,10,2, 59,51,43,35,62,54,46,38,
        30,22,14,6,61,53,45,37, 29,21,13,5,60,52,44,36,
        28,20,12,4,27,19,11,3,
    )
    KPC2 = (
        13,16,10,23,0,4,-1,-1, 2,27,14,5,20,9,-1,-1,
        22,18,11,3,25,7,-1,-1, 15,6,26,19,12,1,-1,-1,
        40,51,30,36,46,54,-1,-1, 29,39,50,44,32,47,-1,-1,
        43,48,38,55,33,52,-1,-1, 45,41,49,35,28,31,-1,-1,
    )
    ROT = (1,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1)
    ROT_MASK = (0, 0x100001, 0x300003)
    SBOX = (
        (14,4,3,15,2,13,5,3,13,14,6,9,11,2,0,5,4,1,10,12,15,6,9,10,1,8,12,7,8,11,7,0,0,15,10,5,14,4,9,10,7,8,12,3,13,1,3,6,15,12,6,11,2,9,5,0,4,2,11,14,1,7,8,13),
        (15,0,9,5,6,10,12,9,8,7,2,12,3,13,5,2,1,14,7,8,11,4,0,3,14,11,13,6,4,1,10,15,3,13,12,11,15,3,6,0,4,10,1,7,8,4,11,14,13,8,0,6,2,15,9,5,7,1,10,12,14,2,5,9),
        (10,13,1,11,6,8,11,5,9,4,12,2,15,3,2,14,0,6,13,1,3,15,4,10,14,9,7,12,5,0,8,7,13,1,2,4,3,6,12,11,0,13,5,14,6,8,15,2,7,10,8,15,4,9,11,5,9,0,14,3,10,7,1,12),
        (7,10,1,15,0,12,11,5,14,9,8,3,9,7,4,8,13,6,2,1,6,11,12,2,3,0,5,14,10,13,15,4,13,3,4,9,6,10,1,12,11,0,2,5,0,13,14,2,8,15,7,4,15,1,10,7,5,6,12,11,3,8,9,14),
        (2,4,8,15,7,10,13,6,4,1,3,12,11,7,14,0,12,2,5,9,10,13,0,3,1,11,15,5,6,8,9,14,14,11,5,6,4,1,3,10,2,12,15,0,13,2,8,5,11,8,0,15,7,14,9,4,12,7,10,9,1,13,6,3),
        (12,9,0,7,9,2,14,1,10,15,3,4,6,12,5,11,1,14,13,0,2,8,7,13,15,5,4,10,8,3,11,6,10,4,6,11,7,9,0,6,4,2,13,1,9,15,3,8,15,3,1,14,12,5,11,0,2,12,14,7,5,10,8,13),
        (4,1,3,10,15,12,5,0,2,11,9,6,8,7,6,9,11,4,12,15,0,3,10,5,14,13,7,8,13,14,1,2,13,6,14,9,4,1,2,14,11,13,5,0,1,10,8,3,0,11,3,5,9,4,15,2,7,8,12,15,10,7,6,12),
        (13,7,10,0,6,9,5,15,8,4,3,10,11,14,12,5,2,11,9,6,15,12,0,3,4,1,14,13,1,2,7,8,1,2,12,15,10,4,0,3,13,14,6,9,7,8,9,6,15,1,5,12,3,10,14,5,8,7,11,0,4,13,2,11),
    )

    @staticmethod
    def _b64decode(data: bytes | str) -> bytes:
        if isinstance(data, str):
            data = unquote(data.strip()).replace(" ", "+").encode()
        data = b"".join(data.split())
        try:
            return base64.b64decode(data, validate=True)
        except Exception as e:
            raise ValueError("invalid Base64 data") from e

    @staticmethod
    def _shuffle(table, bits: int, value: int) -> int:
        out = 0
        for p in range(bits):
            s = table[p]
            if s >= 0:
                out |= ((value >> s) & 1) << p
        return out

    @classmethod
    def _des_round_keys(cls, key: bytes, decrypt=True):
        if len(key) != 8:
            raise ValueError("DES key must be 8 bytes")
        cv = cls._shuffle(cls.KPC1, 56, int.from_bytes(key, "little"))
        keys = []
        for amt in cls.ROT:
            m = cls.ROT_MASK[amt]
            cv = ((cv & m) << (28 - amt)) | ((cv & ~m) >> amt)
            keys.append(cls._shuffle(cls.KPC2, 64, cv))
        return keys[::-1] if decrypt else keys

    @classmethod
    def _des_block(cls, block: bytes, round_keys) -> bytes:
        v = cls._shuffle(cls.IPERM, 64, int.from_bytes(block, "little"))
        lo, hi = v & 0xFFFFFFFF, (v >> 32) & 0xFFFFFFFF
        for rk in round_keys:
            e = cls._shuffle(cls.EXP, 64, hi) ^ rk
            s = 0
            for b in range(8):
                s |= cls.SBOX[b][(e >> (b * 8)) & 0x3F] << (b * 4)
            lo, hi = hi, (lo ^ cls._shuffle(cls.ROUND_P, 32, s)) & 0xFFFFFFFF
        pre = ((lo & 0xFFFFFFFF) << 32) | hi
        return cls._shuffle(cls.FPERM, 64, pre).to_bytes(8, "little")

    @classmethod
    def _decrypt_ekey(cls, ekey: str) -> bytes:
        raw = cls._b64decode(ekey)
        if len(raw) % 8:
            raise ValueError("ekey ciphertext length must be a multiple of 8")
        keys = cls._des_round_keys(cls.KUWO_KEY)
        return b"".join(cls._des_block(raw[i:i + 8], keys) for i in range(0, len(raw), 8)).rstrip(b"\0")

    @classmethod
    def _tea_block(cls, block: bytes, key: bytes) -> bytes:
        if len(block) != 8 or len(key) != 16:
            raise ValueError("invalid TEA block/key length")
        v0, v1 = int.from_bytes(block[:4], "big"), int.from_bytes(block[4:], "big")
        k = [int.from_bytes(key[i:i + 4], "big") for i in range(0, 16, 4)]
        total = (cls.DELTA * 16) & 0xFFFFFFFF
        for _ in range(16):
            v1 = (v1 - ((((v0 << 4) + k[2]) & 0xFFFFFFFF) ^ ((v0 + total) & 0xFFFFFFFF) ^ (((v0 >> 5) + k[3]) & 0xFFFFFFFF))) & 0xFFFFFFFF
            v0 = (v0 - ((((v1 << 4) + k[0]) & 0xFFFFFFFF) ^ ((v1 + total) & 0xFFFFFFFF) ^ (((v1 >> 5) + k[1]) & 0xFFFFFFFF))) & 0xFFFFFFFF
            total = (total - cls.DELTA) & 0xFFFFFFFF
        return v0.to_bytes(4, "big") + v1.to_bytes(4, "big")

    @classmethod
    def _tencent_tea(cls, data: bytes, key: bytes) -> bytes:
        if len(data) < 16 or len(data) % 8:
            raise ValueError("invalid Tencent TEA ciphertext length")

        dec = cls._tea_block(data[:8], key)
        pad = dec[0] & 7
        out_len = len(data) - 1 - pad - 2 - 7
        if out_len < 0:
            raise ValueError("invalid Tencent TEA padding")

        iv_prev, iv_cur = b"\0" * 8, data[:8]
        pos, idx = 8, 1 + pad

        def next_block():
            nonlocal dec, iv_prev, iv_cur, pos, idx
            if pos + 8 > len(data):
                raise ValueError("truncated Tencent TEA ciphertext")
            iv_prev, iv_cur = iv_cur, data[pos:pos + 8]
            dec = cls._tea_block(bytes(a ^ b for a, b in zip(dec, iv_cur)), key)
            pos += 8
            idx = 0

        for _ in range(2):
            if idx >= 8:
                next_block()
            idx += 1

        out = bytearray()
        while len(out) < out_len:
            if idx >= 8:
                next_block()
            out.append(dec[idx] ^ iv_prev[idx])
            idx += 1

        for _ in range(7):
            if idx >= 8:
                next_block()
            if dec[idx] != iv_prev[idx]:
                raise ValueError("Tencent TEA zero-byte validation failed")
            idx += 1
        return bytes(out)

    @staticmethod
    def _simple_key(salt=106, length=8) -> bytes:
        return bytes(int(abs(math.tan(salt + i * 0.1) * 100.0)) & 0xFF for i in range(length))

    @classmethod
    def _extract_raw_key(cls, ekey: str) -> bytes:
        dec = cls._decrypt_ekey(ekey)
        for n in cls.RAW_KEY_LENGTHS:
            if len(dec) >= n:
                candidate = dec[-n:]
                try:
                    cls._b64decode(candidate)
                    return candidate
                except ValueError:
                    pass
        raise ValueError("failed to extract QMC raw key from ekey")

    @classmethod
    def _derive_key(cls, raw_key_b64: bytes) -> bytes:
        decoded = cls._b64decode(raw_key_b64)
        if decoded.startswith(cls.V2_PREFIX):
            buf = cls._tencent_tea(decoded[len(cls.V2_PREFIX):], cls.V2_KEY1)
            buf = cls._tencent_tea(buf, cls.V2_KEY2)
            decoded = cls._b64decode(buf)

        if len(decoded) < 16:
            raise ValueError("QMC key is too short")

        simple = cls._simple_key()
        tea_key = bytes(x for pair in zip(simple, decoded[:8]) for x in pair)
        return decoded[:8] + cls._tencent_tea(decoded[8:], tea_key)

    @staticmethod
    def _rotate(value: int, bits: int) -> int:
        r = (bits + 4) % 8
        return ((value << r) | (value >> r)) & 0xFF

    class _MapCipher:
        def __init__(self, key: bytes):
            if not key:
                raise ValueError("empty QMC key")
            self.key = key
            self.size = len(key)

        def decrypt(self, data: bytes, offset: int) -> bytes:
            out = bytearray(len(data))
            for i, b in enumerate(data):
                p = offset + i
                p = p % 0x7FFF if p > 0x7FFF else p
                idx = (p * p + 71214) % self.size
                out[i] = b ^ KuwoQmcDecryptor._rotate(self.key[idx], idx & 7)
            return bytes(out)

    class _Rc4Cipher:
        FIRST = 128
        SEGMENT = 5120

        def __init__(self, key: bytes):
            if not key:
                raise ValueError("empty QMC key")
            self.key, self.size = key, len(key)
            self.box = [i & 0xFF for i in range(self.size)]
            j = 0
            for i in range(self.size):
                j = (j + self.box[i] + key[i]) % self.size
                self.box[i], self.box[j] = self.box[j], self.box[i]
            self.hash = self._hash_base(key)
            self._skip_cache = {}

        @staticmethod
        def _hash_base(key: bytes) -> int:
            result = 1
            for value in key:
                if value == 0:
                    continue
                nxt = (result * value) & 0xFFFFFFFF
                if nxt == 0 or nxt <= result:
                    break
                result = nxt
            return result

        def _skip(self, segment_id: int) -> int:
            if segment_id not in self._skip_cache:
                seed = self.key[segment_id % self.size]
                self._skip_cache[segment_id] = 0 if seed == 0 else int(self.hash / ((segment_id + 1) * seed) * 100.0) % self.size
            return self._skip_cache[segment_id]

        def _first(self, data: bytes, file_offset: int) -> bytes:
            return bytes(b ^ self.key[self._skip(file_offset + i)] for i, b in enumerate(data))

        def _segment(self, data: bytes, file_offset: int) -> bytes:
            box, j, k = self.box.copy(), 0, 0
            segment_id = file_offset // self.SEGMENT
            skip_len = file_offset % self.SEGMENT + self._skip(segment_id)
            out = bytearray(len(data))
            for n in range(skip_len + len(data)):
                j = (j + 1) % self.size
                k = (box[j] + k) % self.size
                box[j], box[k] = box[k], box[j]
                if n >= skip_len:
                    out[n - skip_len] = box[(box[j] + box[k]) % self.size]
            return bytes(a ^ b for a, b in zip(data, out))

        def decrypt(self, data: bytes, offset: int) -> bytes:
            result = bytearray()
            pos = 0

            if offset < self.FIRST:
                n = min(len(data), self.FIRST - offset)
                result += self._first(data[:n], offset)
                offset, pos = offset + n, n

            while pos < len(data):
                n = min(len(data) - pos, self.SEGMENT - (offset % self.SEGMENT) if offset % self.SEGMENT else self.SEGMENT)
                result += self._segment(data[pos:pos + n], offset)
                offset, pos = offset + n, pos + n

            return bytes(result)

    @classmethod
    def _cipher_from_ekey(cls, ekey: str):
        key = cls._derive_key(cls._extract_raw_key(ekey))
        return cls._Rc4Cipher(key) if len(key) > 300 else cls._MapCipher(key)

    @staticmethod
    def _output_path(src: Path) -> Path:
        suffix = src.suffix.lower()
        ext = {".mflac": ".flac", ".mflac0": ".flac", ".mgg": ".ogg", ".mggl": ".ogg", ".mmp3": ".mp3"}.get(suffix, ".audio")
        return src.with_suffix(ext)

    @staticmethod
    def _check_magic(path: Path) -> None:
        with path.open("rb") as f:
            head = f.read(16)
        if not (head.startswith(b"fLaC") or head.startswith(b"OggS") or head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)):
            raise ValueError("decryption finished, but output does not look like FLAC/OGG/MP3; check encrypted file and ekey")

    def decrypt(self, encrypted_file_path: str | Path, ekey: str, output_path: str | Path | None = None, chunk_size: int = 1024 * 1024) -> Path:
        src = Path(encrypted_file_path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(src)
        if not ekey or not ekey.strip():
            raise ValueError("ekey cannot be empty")

        dst = Path(output_path).expanduser().resolve() if output_path else self._output_path(src)
        if src == dst:
            raise ValueError("output path must differ from input path")
        dst.parent.mkdir(parents=True, exist_ok=True)

        cipher = self._cipher_from_ekey(ekey)
        offset = 0
        tmp = dst.with_name(dst.name + ".part")

        try:
            with src.open("rb") as fin, tmp.open("wb") as fout:
                while chunk := fin.read(chunk_size):
                    fout.write(cipher.decrypt(chunk, offset))
                    offset += len(chunk)
            self._check_magic(tmp)
            tmp.replace(dst)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

        return dst

    __call__ = decrypt


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Decrypt Kuwo/QMC encrypted audio using encrypted_file_path + ekey")
    p.add_argument("encrypted_file_path")
    p.add_argument("ekey")
    p.add_argument("-o", "--output")
    args = p.parse_args()

    print(KuwoQmcDecryptor().decrypt(args.encrypted_file_path, args.ekey, args.output))
