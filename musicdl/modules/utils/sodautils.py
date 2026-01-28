'''
Function:
    Implementation of SodaMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import struct
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


'''SpadeDecryptor'''
class SpadeDecryptor:
    '''bitcount'''
    @staticmethod
    def bitcount(n):
        n = n & 0xFFFFFFFF
        n = n - ((n >> 1) & 0x55555555)
        n = (n & 0x33333333) + ((n >> 2) & 0x33333333)
        return ((n + (n >> 4) & 0xF0F0F0F) * 0x1010101) >> 24
    '''decodebase36'''
    @staticmethod
    def decodebase36(c):
        if 48 <= c <= 57: return c - 48
        if 97 <= c <= 122: return c - 97 + 10
        return 0xFF
    '''decryptspadeinner'''
    @staticmethod
    def decryptspadeinner(spade_key_bytes):
        result = bytearray(len(spade_key_bytes))
        buff = bytearray([0xFA, 0x55]) + spade_key_bytes
        for i in range(len(result)):
            v = (spade_key_bytes[i] ^ buff[i]) - SpadeDecryptor.bitcount(i) - 21
            while v < 0: v += 255 
            result[i] = v
        return result
    '''extractkey'''
    @classmethod
    def extractkey(cls, play_auth_str):
        binary_string = base64.b64decode(play_auth_str)
        bytes_data = bytearray(binary_string)
        if len(bytes_data) < 3: return None
        padding_len = (bytes_data[0] ^ bytes_data[1] ^ bytes_data[2]) - 48
        if len(bytes_data) < padding_len + 2: return None
        inner_input = bytes_data[1: len(bytes_data)-padding_len]
        tmp_buff = cls.decryptspadeinner(inner_input)
        if len(tmp_buff) == 0: return None
        skip_bytes = cls.decodebase36(tmp_buff[0])
        decoded_message_len = len(bytes_data) - padding_len - 2
        end_index = 1 + decoded_message_len - skip_bytes
        final_bytes = tmp_buff[1:end_index]
        return final_bytes.decode('utf-8')


'''AudioDecryptor'''
class AudioDecryptor:
    '''readuint32be'''
    @staticmethod
    def readuint32be(data, offset):
        return struct.unpack(">I", data[offset: offset+4])[0]
    '''findbox'''
    @staticmethod
    def findbox(data: bytes, box_type: str, start: int = 0, end: int = None):
        if end is None: end = len(data)
        pos = start
        while pos + 8 <= end:
            size = AudioDecryptor.readuint32be(data, pos)
            if size < 8: break
            current_type_bytes = data[pos+4: pos+8]
            try: current_type = current_type_bytes.decode('ascii', errors='ignore')
            except: current_type = "????"
            if current_type == box_type: return {'offset': pos, 'size': size, 'data': data[pos+8: pos+size]}
            pos += size
        return None
    '''decrypt'''
    @staticmethod
    def decrypt(file_data: bytes, play_auth: str, output_filepath: str = "./decrypted.m4a"):
        hex_key = SpadeDecryptor.extractkey(play_auth)
        if not hex_key: return
        moov = AudioDecryptor.findbox(file_data, 'moov')
        if not moov: return
        senc = AudioDecryptor.findbox(file_data, 'senc', start=moov['offset'] + 8, end=moov['offset'] + moov['size'])
        trak = AudioDecryptor.findbox(file_data, 'trak', start=moov['offset'] + 8, end=moov['offset'] + moov['size'])
        if not trak: return
        mdia = AudioDecryptor.findbox(file_data, 'mdia', start=trak['offset'] + 8, end=trak['offset'] + trak['size'])
        if not mdia: return
        minf = AudioDecryptor.findbox(file_data, 'minf', start=mdia['offset'] + 8, end=mdia['offset'] + mdia['size'])
        if not minf: return
        stbl = AudioDecryptor.findbox(file_data, 'stbl', start=minf['offset'] + 8, end=minf['offset'] + minf['size'])
        if not stbl: return
        stsz = AudioDecryptor.findbox(file_data, 'stsz', start=stbl['offset'] + 8, end=stbl['offset'] + stbl['size'])
        if not stsz: return
        stsz_data = stsz['data']
        sample_size_fixed, sample_count, sample_sizes = struct.unpack(">I", stsz_data[4: 8])[0], struct.unpack(">I", stsz_data[8: 12])[0], []
        if sample_size_fixed != 0: sample_sizes = [sample_size_fixed] * sample_count
        else:
            for i in range(sample_count): sample_sizes.append(struct.unpack(">I", stsz_data[12 + i*4 : 16 + i*4])[0])
        if not senc: senc = AudioDecryptor.findbox(file_data, 'senc', start=stbl['offset'] + 8, end=stbl['offset'] + stbl['size'])
        if not senc: return
        senc_body = senc['data']
        senc_flags, senc_sample_count, ivs, ptr = struct.unpack(">I", senc_body[0:4])[0] & 0x00FFFFFF, struct.unpack(">I", senc_body[4:8])[0], [], 8
        has_subsamples = (senc_flags & 0x02) != 0
        for _ in range(senc_sample_count):
            ivs.append(senc_body[ptr : ptr+8] + b'\x00'*8); ptr += 8
            if has_subsamples: sub_count = struct.unpack(">H", senc_body[ptr: ptr+2])[0]; ptr += 2 + (sub_count * 6)
        mdat = AudioDecryptor.findbox(file_data, 'mdat')
        if not mdat: return
        key_bytes, backend, decrypted_mdat, read_ptr = bytes.fromhex(hex_key), default_backend(), bytearray(), mdat['offset'] + 8
        for i in range(len(sample_sizes)):
            size = sample_sizes[i]
            if i < len(ivs):
                cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(ivs[i]), backend=backend)
                decryptor = cipher.decryptor()
                plain_chunk = decryptor.update(file_data[read_ptr: read_ptr + size]) + decryptor.finalize()
                decrypted_mdat.extend(plain_chunk)
            else:
                decrypted_mdat.extend(file_data[read_ptr: read_ptr + size])
            read_ptr += size
        stsd = AudioDecryptor.findbox(file_data, 'stsd', start=stbl['offset'] + 8, end=stbl['offset'] + stbl['size'])
        if stsd:
            offset, length = stsd['offset'], stsd['size']
            original_stsd = file_data[offset: offset+length]
            new_stsd = original_stsd.replace(b'enca', b'mp4a', 1)
            file_data[offset: offset+length] = new_stsd
        if len(decrypted_mdat) == mdat['size'] - 8: file_data[mdat['offset']+8: mdat['offset']+mdat['size']] = decrypted_mdat
        else: pass 
        with open(output_filepath, "wb") as fp: fp.write(file_data)