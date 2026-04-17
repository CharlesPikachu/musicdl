'''
Function:
    Implementation of CMD Related Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Union


'''CmdArg'''
@dataclass
class CmdArg:
    key: Optional[str] = None
    value: Optional[str] = None


'''CmdOp'''
@dataclass
class CmdOp:
    op: str
    key: Optional[str] = None
    value: Any = None
    occurrence: int = 0
    remove_all: bool = True
    '''set'''
    @classmethod
    def set(cls, key: str, value: Any, occurrence: int = 0) -> "CmdOp": return cls(op="set", key=key, value=value, occurrence=occurrence)
    '''add'''
    @classmethod
    def add(cls, key: str, value: Any = None) -> "CmdOp": return cls(op="add", key=key, value=value)
    '''remove'''
    @classmethod
    def remove(cls, key: str, remove_all: bool = True) -> "CmdOp": return cls(op="remove", key=key, remove_all=remove_all)
    '''beforeoutput'''
    @classmethod
    def beforeoutput(cls, key: str, value: Any = None) -> "CmdOp": return cls(op="before_output", key=key, value=value)


'''ModType'''
ModType = Union[Callable[["CommandBuilder"], None], Mapping[str, Any], Sequence[Union[CmdOp, tuple, Mapping[str, Any]]]]


'''CommandBuilder'''
class CommandBuilder:
    def __init__(self, executable: str):
        self.executable = executable
        self.args: list[CmdArg] = []
    '''flag'''
    def flag(self, key: str) -> "CommandBuilder":
        self.args.append(CmdArg(key=key, value=None))
        return self
    '''opt'''
    def opt(self, key: str, value: Any) -> "CommandBuilder":
        self.args.append(CmdArg(key=key, value=str(value)))
        return self
    '''inlineopt'''
    def inlineopt(self, key: str, value: Any, sep: str = "=") -> "CommandBuilder":
        self.args.append(CmdArg(key=f"{key}{sep}{value}", value=None))
        return self
    '''positional'''
    def positional(self, value: Any) -> "CommandBuilder":
        self.args.append(CmdArg(key=None, value=str(value)))
        return self
    '''add'''
    def add(self, key: str, value: Any = None) -> "CommandBuilder":
        if value is None: return self.flag(key)
        return self.opt(key, value)
    '''set'''
    def set(self, key: str, value: Any, occurrence: int = 0, append_if_missing: bool = True) -> "CommandBuilder":
        if (match := next((arg for i, arg in enumerate(a for a in self.args if a.key == key) if i == occurrence), None)) is not None:
            match.value = None if value is None else str(value)
            return self
        if append_if_missing: return self.insertbeforeoutput(key, value)
        return self
    '''remove'''
    def remove(self, key: str, remove_all: bool = True) -> "CommandBuilder":
        if remove_all: self.args = [arg for arg in self.args if arg.key != key]; return self
        idx = next((i for i, arg in enumerate(self.args) if arg.key == key), None)
        self.args = self.args if idx is None else self.args[:idx] + self.args[idx+1:]
        return self
    '''insertbeforeoutput'''
    def insertbeforeoutput(self, key: str, value: Any = None) -> "CommandBuilder":
        idx = next((i for i in range(len(self.args) - 1, -1, -1) if self.args[i].key is None), len(self.args))
        self.args.insert(idx, CmdArg(key=key, value=None if value is None else str(value)))
        return self
    '''insertpositionalbeforeoutput'''
    def insertpositionalbeforeoutput(self, value: Any) -> "CommandBuilder":
        idx = next((i for i in range(len(self.args) - 1, -1, -1) if self.args[i].key is None), len(self.args))
        self.args.insert(idx, CmdArg(key=None, value=str(value)))
        return self
    '''tolist'''
    def tolist(self) -> list[str]:
        cmd = [self.executable] + [x for arg in self.args for x in ((arg.value,) if arg.key is None else (arg.key,) if arg.value is None else (arg.key, arg.value))]
        return cmd
    '''repr'''
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.tolist()!r})"


'''CommandModsApplier'''
class CommandModsApplier:
    RESERVED_KEYS = {"__add__", "__remove__", "__before_output__"}
    '''apply'''
    @classmethod
    def apply(cls, builder: CommandBuilder, mods: Optional[ModType]) -> CommandBuilder:
        if mods is None or not mods: return builder
        if callable(mods): mods(builder); return builder
        if isinstance(mods, Mapping): cls.applydictmods(builder, mods); return builder
        if isinstance(mods, Sequence) and not isinstance(mods, (str, bytes)): list(map(lambda item: cls.applyoneop(builder, item), mods)); return builder
        raise TypeError(f"Unsupported mods type: {type(mods)!r}")
    '''applydictmods'''
    @classmethod
    def applydictmods(cls, builder: CommandBuilder, mods: Mapping[str, Any]) -> None:
        # 1) non-special keys
        for key, value in mods.items():
            if key in cls.RESERVED_KEYS: continue
            if value is False: builder.remove(key)
            elif value is True: builder.insertbeforeoutput(key) if not any(arg.key == key for arg in builder.args) else None
            else: builder.set(key, value)
        # 2) __remove__
        for item in mods.get("__remove__", []):
            if isinstance(item, str): builder.remove(item)
            elif isinstance(item, (tuple, list)): builder.remove(item[0]) if len(item) == 1 else builder.remove(item[0], remove_all=bool(item[1]))
            elif isinstance(item, Mapping): builder.remove(item["key"], remove_all=item.get("remove_all", True))
            else: raise TypeError(f"Unsupported __remove__ item: {item!r}")
        # 3) __add__
        for item in mods.get("__add__", []): cls.applyaddlike(builder, item, before_output=False)
        # 4) __before_output__
        for item in mods.get("__before_output__", []): cls.applyaddlike(builder, item, before_output=True)
    '''applyaddlike'''
    @classmethod
    def applyaddlike(cls, builder: CommandBuilder, item: Any, before_output: bool) -> None:
        if isinstance(item, (tuple, list)): key, value = (item[0], None) if len(item) == 1 else (item[0], item[1]) if len(item) == 2 else (_ for _ in ()).throw(ValueError(f"Tuple/list mod must have length 1 or 2: {item!r}"))
        elif isinstance(item, Mapping): key, value = item["key"], item.get("value")
        else: raise TypeError(f"Unsupported add-like item: {item!r}")
        if before_output: builder.insertbeforeoutput(key, value)
        else: builder.add(key, value)
    '''applyoneop'''
    @classmethod
    def applyoneop(cls, builder: CommandBuilder, op_item: Union[CmdOp, tuple, Mapping[str, Any]]) -> None:
        if isinstance(op_item, CmdOp): op, key, value, occurrence, remove_all = op_item.op, op_item.key, op_item.value, op_item.occurrence, op_item.remove_all
        elif isinstance(op_item, Mapping): op, key, value, occurrence, remove_all = op_item["op"], op_item.get("key"), op_item.get("value"), op_item.get("occurrence", 0), op_item.get("remove_all", True)
        elif isinstance(op_item, tuple): op, key, value, occurrence, remove_all = op_item[0], op_item[1], op_item[2] if len(op_item) >= 3 else None, op_item[3] if len(op_item) >= 4 else 0, op_item[4] if len(op_item) >= 5 else True
        else: raise TypeError(f"Unsupported op item: {op_item!r}")
        if op == "set": builder.set(key, value, occurrence=occurrence)
        elif op == "add": builder.add(key, value)
        elif op == "remove": builder.remove(key, remove_all=remove_all)
        elif op == "before_output": builder.insertbeforeoutput(key, value)
        else: raise ValueError(f"Unknown operation: {op}")


'''FFmpegCommandFactory'''
class FFmpegCommandFactory:
    def __init__(self, executable: str = "ffmpeg"):
        self.executable = executable
    '''newbuilder'''
    def newbuilder(self) -> CommandBuilder:
        return CommandBuilder(self.executable)
    '''applymods'''
    def applymods(self, builder: CommandBuilder, mods: Optional[ModType]) -> CommandBuilder:
        return CommandModsApplier.apply(builder, mods)


'''ExtractAudioFromVideoFFmpegCommand'''
class ExtractAudioFromVideoFFmpegCommand(FFmpegCommandFactory):
    '''build'''
    def build(self, video_path: str, audio_path: str, mods: Optional[ModType] = None) -> list[str]:
        builder = (self.newbuilder().opt("-v", "error").flag("-y").opt("-i", video_path).flag("-vn").opt("-map", "0:a:0").opt("-c:a", "copy").positional(audio_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''ConvertImageToJpegFFmpegCommand'''
class ConvertImageToJpegFFmpegCommand(FFmpegCommandFactory):
    '''build'''
    def build(self, src_img: str, out_jpg: str, scale: Optional[str] = None, quality: int = 3, pix_fmt: str = "yuvj420p", mods: Optional[ModType] = None) -> list[str]:
        builder = (self.newbuilder().flag("-y").opt("-v", "error").opt("-i", src_img))
        if scale: builder.opt("-vf", scale)
        builder.opt("-q:v", quality).opt("-pix_fmt", pix_fmt).positional(out_jpg)
        self.applymods(builder, mods)
        return builder.tolist()


'''FFmpegDecryptRemuxCommand'''
class FFmpegDecryptRemuxCommand(FFmpegCommandFactory):
    '''build'''
    def build(self, input_path: str, output_path: str, decryption_key: Optional[str] = None, loglevel: str = "error", codec: str = "copy", movflags: str = "+faststart", mods: Optional[ModType] = None) -> list[str]:
        builder = self.newbuilder().opt("-loglevel", loglevel).flag("-y")
        if decryption_key: builder.opt("-decryption_key", decryption_key)
        builder.opt("-i", str(input_path)).opt("-c", codec).opt("-movflags", movflags).positional(str(output_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''FFprobeCommandFactory'''
class FFprobeCommandFactory(FFmpegCommandFactory):
    def __init__(self, executable: str = "ffprobe"):
        super().__init__(executable=executable)


'''FFprobeAudioCodecCommand'''
class FFprobeAudioCodecCommand(FFprobeCommandFactory):
    '''build'''
    def build(self, file_path: str, mods: Optional[ModType] = None) -> list[str]:
        builder = (self.newbuilder().opt("-v", "error").opt("-select_streams", "a:0").opt("-show_entries", "stream=codec_name").opt("-of", "json").positional(file_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''MetaflacCommandFactory'''
class MetaflacCommandFactory(FFmpegCommandFactory):
    def __init__(self, executable: str = "metaflac"):
        super().__init__(executable=executable)


'''MetaflacBlockCommand'''
class MetaflacBlockCommand(MetaflacCommandFactory):
    '''build'''
    def build(self, flac_path: str, action_flag: str, block_type: str = "PICTURE", mods: Optional[ModType] = None) -> list[str]:
        builder = (self.newbuilder().flag(action_flag).opt("--block-type", block_type).positional(flac_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''MetaflacListPictureCommand'''
class MetaflacListPictureCommand(MetaflacBlockCommand):
    '''build'''
    def build(self, flac_path: str, mods: Optional[ModType] = None) -> list[str]:
        return super().build(flac_path=flac_path, action_flag="--list", block_type="PICTURE", mods=mods)


'''MetaflacRemovePictureCommand'''
class MetaflacRemovePictureCommand(MetaflacBlockCommand):
    '''build'''
    def build(self, flac_path: str, mods: Optional[ModType] = None) -> list[str]:
        return super().build(flac_path=flac_path, action_flag="--remove", block_type="PICTURE", mods=mods)


'''MetaflacExportPictureCommand'''
class MetaflacExportPictureCommand(MetaflacCommandFactory):
    '''build'''
    def build(self, flac_path: str, dest_file: str, mods: Optional[ModType] = None) -> list[str]:
        builder = (self.newbuilder().inlineopt("--export-picture-to", dest_file).positional(flac_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''MetaflacImportPictureCommand'''
class MetaflacImportPictureCommand(MetaflacCommandFactory):
    '''buildpicturespec'''
    @staticmethod
    def buildpicturespec(img_file: str, picture_type: int = 3, mime: str = "image/jpeg", description: str = "", extra: str = "") -> str:
        return f"{picture_type}|{mime}|{description}|{extra}|{img_file}"
    '''build'''
    def build(self, flac_path: str, img_file: str, picture_type: int = 3, mime: str = "image/jpeg", description: str = "", extra: str = "", mods: Optional[ModType] = None) -> list[str]:
        picture_spec = self.buildpicturespec(img_file=img_file, picture_type=picture_type, mime=mime, description=description, extra=extra)
        builder = (self.newbuilder().inlineopt("--import-picture-from", picture_spec).positional(flac_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''NM3U8DLRECommandFactory'''
class NM3U8DLRECommandFactory(FFmpegCommandFactory):
    def __init__(self, executable: str = "N_m3u8DL-RE"):
        super().__init__(executable=executable)


'''NM3U8DLREDownloadCommand'''
class NM3U8DLREDownloadCommand(NM3U8DLRECommandFactory):
    '''build'''
    def build(self, stream_url: str, download_path: str | Path, log_file_path: str | Path, ffmpeg_binary_path: Optional[str] = None, save_pattern: Optional[str] = None, tmp_dir: Optional[str | Path] = None, mods: Optional[ModType] = None) -> list[str]:
        download_path_obj, ffmpeg_binary_path = Path(download_path), ffmpeg_binary_path or shutil.which("ffmpeg")
        tmp_dir, save_pattern = Path(tmp_dir) if tmp_dir is not None else download_path_obj.parent, save_pattern or download_path_obj.stem
        builder = self.newbuilder().positional(stream_url).flag("--binary-merge").opt("--ffmpeg-binary-path", ffmpeg_binary_path).opt("--save-name", download_path_obj.stem).opt("--save-dir", download_path_obj.parent).opt("--tmp-dir", tmp_dir).opt("--log-file-path", log_file_path).flag("--auto-select").opt("--save-pattern", save_pattern)
        self.applymods(builder, mods)
        return builder.tolist()


'''MP4BoxCommandFactory'''
class MP4BoxCommandFactory(FFmpegCommandFactory):
    def __init__(self, executable: str = "MP4Box"):
        super().__init__(executable=executable)


'''MP4BoxAddCommand'''
class MP4BoxAddCommand(MP4BoxCommandFactory):
    '''build'''
    def build(self, input_path: str, output_path: str, itags: Optional[str] = None, quiet: bool = True, mods: Optional[ModType] = None) -> list[str]:
        builder = self.newbuilder(); quiet and builder.flag("-quiet")
        builder.opt("-add", str(input_path)).opt("-itags", itags).flag("-keep-utc").flag("-new").positional(str(output_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''Mp4DecryptCommandFactory'''
class Mp4DecryptCommandFactory(FFmpegCommandFactory):
    def __init__(self, executable: str = "mp4decrypt"):
        super().__init__(executable=executable)


'''Mp4DecryptCommand'''
class Mp4DecryptCommand(Mp4DecryptCommandFactory):
    '''build'''
    def build(self, input_path: str, output_path: str, keys: Optional[Sequence[str]] = None, mods: Optional[ModType] = None) -> list[str]:
        builder = self.newbuilder()
        for key in (keys or []): builder.opt("--key", key)
        builder.positional(str(input_path)).positional(str(output_path))
        self.applymods(builder, mods)
        return builder.tolist()


'''AmdecryptCommandFactory'''
class AmdecryptCommandFactory(FFmpegCommandFactory):
    def __init__(self, executable: str = "amdecrypt"):
        super().__init__(executable=executable)


'''AmdecryptCommand'''
class AmdecryptCommand(AmdecryptCommandFactory):
    '''build'''
    def build(self, wrapper_decrypt_ip: str, media_id: str, fairplay_key: str, input_path: str, output_path: str, mp4decrypt_binary_path: Optional[str] = None, mods: Optional[ModType] = None) -> list[str]:
        mp4decrypt_binary_path = mp4decrypt_binary_path or shutil.which("mp4decrypt") or "mp4decrypt"
        builder = (self.newbuilder().positional(str(wrapper_decrypt_ip)).positional(str(mp4decrypt_binary_path)).positional(str(media_id)).positional(str(fairplay_key)).positional(str(input_path)).positional(str(output_path)))
        self.applymods(builder, mods)
        return builder.tolist()