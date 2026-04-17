'''
Function:
    Implementation of SodaMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import struct
import base64
from typing import Dict, Any, List
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''SpadeDecryptor'''
class SpadeDecryptor:
    '''bitcount'''
    @staticmethod
    def bitcount(n):
        n = ((m := ((n & 0xFFFFFFFF) - (((n & 0xFFFFFFFF) >> 1) & 0x55555555))) & 0x33333333) + ((m >> 2) & 0x33333333)
        return ((n + (n >> 4) & 0xF0F0F0F) * 0x1010101) >> 24
    '''decodebase36'''
    @staticmethod
    def decodebase36(c):
        return c - 48 if 48 <= c <= 57 else (c - 97 + 10 if 97 <= c <= 122 else 0xFF)
    '''decryptspadeinner'''
    @staticmethod
    def decryptspadeinner(spade_key_bytes):
        result, buff = bytearray(len(spade_key_bytes)), bytearray([0xFA, 0x55]) + spade_key_bytes
        result[:] = [v if (v := (spade_key_bytes[i] ^ buff[i]) - SpadeDecryptor.bitcount(i) - 21) >= 0 else v % 255 for i in range(len(result))]
        return result
    '''extractkey'''
    @classmethod
    def extractkey(cls, play_auth_str):
        if len((bytes_data := bytearray(base64.b64decode(play_auth_str)))) < 3: return None
        if len(bytes_data) < (padding_len := (bytes_data[0] ^ bytes_data[1] ^ bytes_data[2]) - 48) + 2: return None
        if len((tmp_buff := cls.decryptspadeinner(bytes_data[1: len(bytes_data)-padding_len]))) == 0: return None
        end_index = 1 + (len(bytes_data) - padding_len - 2) - cls.decodebase36(tmp_buff[0])
        return tmp_buff[1: end_index].decode('utf-8')


'''AudioDecryptor'''
class AudioDecryptor:
    '''readuint32be'''
    @staticmethod
    def readuint32be(data, offset):
        return struct.unpack(">I", data[offset: offset+4])[0]
    '''findbox'''
    @staticmethod
    def findbox(data: bytes, box_type: str, start: int = 0, end: int = None):
        pos, end = start, len(data) if end is None else end
        while pos + 8 <= end:
            if (size := AudioDecryptor.readuint32be(data, pos)) < 8: break
            try: current_type = data[pos+4: pos+8].decode('ascii', errors='ignore')
            except Exception: current_type = "????"
            if current_type == box_type: return {'offset': pos, 'size': size, 'data': data[pos+8: pos+size]}
            pos += size
        return None
    '''decrypt'''
    @staticmethod
    def decrypt(file_data: bytes, play_auth: str, output_filepath: str = "./decrypted.m4a"):
        if not (hex_key := SpadeDecryptor.extractkey(play_auth)): return
        if not (moov := AudioDecryptor.findbox(file_data, 'moov')): return
        senc = AudioDecryptor.findbox(file_data, 'senc', start=moov['offset'] + 8, end=moov['offset'] + moov['size'])
        if not (trak := AudioDecryptor.findbox(file_data, 'trak', start=moov['offset'] + 8, end=moov['offset'] + moov['size'])): return
        if not (mdia := AudioDecryptor.findbox(file_data, 'mdia', start=trak['offset'] + 8, end=trak['offset'] + trak['size'])): return
        if not (minf := AudioDecryptor.findbox(file_data, 'minf', start=mdia['offset'] + 8, end=mdia['offset'] + mdia['size'])): return
        if not (stbl := AudioDecryptor.findbox(file_data, 'stbl', start=minf['offset'] + 8, end=minf['offset'] + minf['size'])): return
        if not (stsz := AudioDecryptor.findbox(file_data, 'stsz', start=stbl['offset'] + 8, end=stbl['offset'] + stbl['size'])): return
        sample_size_fixed, sample_count, sample_sizes = struct.unpack(">I", (stsz_data := stsz['data'])[4: 8])[0], struct.unpack(">I", stsz_data[8: 12])[0], []
        sample_sizes = [sample_size_fixed] * sample_count if sample_size_fixed != 0 else [struct.unpack(">I", stsz_data[12 + i*4 : 16 + i*4])[0] for i in range(sample_count)]
        if not senc and not (senc := AudioDecryptor.findbox(file_data, 'senc', start=stbl['offset'] + 8, end=stbl['offset'] + stbl['size'])): return
        senc_flags, senc_sample_count, ivs, ptr = struct.unpack(">I", (senc_body := senc['data'])[0:4])[0] & 0x00FFFFFF, struct.unpack(">I", senc_body[4:8])[0], [], 8
        for _ in range(senc_sample_count):
            ivs.append(senc_body[ptr : ptr+8] + b'\x00'*8); ptr += 8
            if (senc_flags & 0x02) != 0: sub_count = struct.unpack(">H", senc_body[ptr: ptr+2])[0]; ptr += 2 + (sub_count * 6)
        if not (mdat := AudioDecryptor.findbox(file_data, 'mdat')): return
        key_bytes, backend, decrypted_mdat, read_ptr = bytes.fromhex(hex_key), default_backend(), bytearray(), mdat['offset'] + 8
        for i in range(len(sample_sizes)):
            if i < len(ivs):
                decryptor = Cipher(algorithms.AES(key_bytes), modes.CTR(ivs[i]), backend=backend).decryptor()
                decrypted_mdat.extend(decryptor.update(file_data[read_ptr: read_ptr + sample_sizes[i]]) + decryptor.finalize())
            else:
                decrypted_mdat.extend(file_data[read_ptr: read_ptr + sample_sizes[i]])
            read_ptr += sample_sizes[i]
        if (stsd := AudioDecryptor.findbox(file_data, 'stsd', start=stbl['offset'] + 8, end=stbl['offset'] + stbl['size'])):
            original_stsd = file_data[stsd['offset']: stsd['offset']+stsd['size']]
            file_data[stsd['offset']: stsd['offset']+stsd['size']] = original_stsd.replace(b'enca', b'mp4a', 1)
        if len(decrypted_mdat) == mdat['size'] - 8: file_data[mdat['offset']+8: mdat['offset']+mdat['size']] = decrypted_mdat
        with open(output_filepath, "wb") as fp: fp.write(file_data)


'''SodaTimedLyricsParser'''
class SodaTimedLyricsParser:
    LINE_PATTERN_RE = re.compile(r"^\[(\d+),(\d+)\]")
    TOKEN_PATTERN_RE = re.compile(r"<(\d+),(\d+),(\d+)>")
    '''parsetimedlyrics'''
    @staticmethod
    def parsetimedlyrics(text: str) -> List[Dict[str, Any]]:
        if not text or text in {'NULL', 'null', 'None', 'none'}: return []
        text = text.replace(r"\u003C", "<").replace(r"\u003E", ">"); lines_out: List[Dict[str, Any]] = []
        for raw_line in text.splitlines():
            if (not (raw_line := raw_line.rstrip("\n")).strip()) or (not (m := SodaTimedLyricsParser.LINE_PATTERN_RE.match(raw_line.strip()))): continue
            line_start, line_dur = int(m.group(1)), int(m.group(2)); line_end, rest, tokens, pieces = line_start + line_dur, raw_line[m.end():], [], []
            for i, tm in enumerate((matches := list(SodaTimedLyricsParser.TOKEN_PATTERN_RE.finditer(rest)))):
                offset, dur, flag, seg_start = int(tm.group(1)), int(tm.group(2)), int(tm.group(3)), tm.end()
                seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(rest)
                if (token_text := rest[seg_start: seg_end].replace("\r", "")) == "": continue
                tokens.append({"text": token_text, "offset_ms": offset, "duration_ms": dur, "flag": flag, "start_ms": line_start + offset, "end_ms": line_start + offset + dur}); pieces.append(token_text)
            lines_out.append({"line_start_ms": line_start, "line_duration_ms": line_dur, "line_end_ms": line_end, "text": "".join(pieces), "tokens": tokens, "raw": rest})
        return lines_out
    '''toplaintext'''
    @staticmethod
    def toplaintext(parsed: List[Dict[str, Any]]) -> str:
        if not parsed: return
        return "\n".join(line["text"] for line in parsed)
    '''tolrclinelevel'''
    @staticmethod
    def tolrclinelevel(parsed: List[Dict[str, Any]], use_centiseconds: bool = True) -> str:
        if not parsed: return
        fmt_func = lambda ms: ((lambda mm, ss: f"{mm:02d}:{ss:02d}.{((ms % 1000) // 10):02d}" if use_centiseconds else f"{mm:02d}:{ss:02d}")(ms // 60000, (ms % 60000) // 1000))
        return "\n".join(f"[{fmt_func(line['line_start_ms'])}]{line['text']}" for line in parsed)