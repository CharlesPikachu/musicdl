# Musicdl Installation

#### Environment Requirements

- Operating system: Linux, macOS, or Windows.
- Python version: Python 3.9+ with requirements in [musicdl requirements.txt](https://github.com/CharlesPikachu/musicdl/blob/master/requirements.txt).

#### Installation Instructions

You have three installation methods to choose from,

```sh
# from pip
pip install musicdl
# from github repo method-1
pip install git+https://github.com/CharlesPikachu/musicdl.git@master
# from github repo method-2
git clone https://github.com/CharlesPikachu/musicdl.git
cd musicdl
python setup.py install
```

Some of the music downloaders supported by musicdl require additional CLI tools to function properly, mainly for decrypting encrypted search/download requests and audio files.
These CLI tools include,

- [FFmpeg](https://www.ffmpeg.org/): At the moment, only `TIDALMusicClient` and `AppleMusicClient` depends on FFmpeg for audio file decoding.
  If you don’t need to use `TIDALMusicClient` and `AppleMusicClient` when working with musicdl, you don’t need to install FFmpeg.
  After installing it, you should run the following command in a terminal (Command Prompt / PowerShell on Windows, Terminal on macOS/Linux) to check whether FFmpeg is on your system `PATH`:
  ```bash
  ffmpeg -version
  ```
  If FFmpeg is installed correctly and on your `PATH`, this command will print the FFmpeg version information (*e.g.*, a few lines starting with `ffmpeg version ...`).
  If you see an error like `command not found` or `'ffmpeg' is not recognized as an internal or external command`, then FFmpeg is either not installed or not added to your `PATH`.

- [Node.js](https://nodejs.org/en): Currently, only `YouTubeMusicClient` in musicdl depends on Node.js, so if you don’t need `YouTubeMusicClient`, you don’t have to install Node.js.
  Similar to FFmpeg, after installing Node.js, you should run the following command to check whether Node.js is on your system `PATH`:
  ```bash
  node -v (npm -v)
  ```
  If Node.js is installed correctly, `node -v` will print the Node.js version (*e.g.*, `v22.11.0`), and `npm -v` will print the npm version.
  If you see a similar `command not found` / `not recognized` error, Node.js is not installed correctly or not available on your `PATH`.

- [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE): N_m3u8DL-RE is a powerful open-source command-line tool for downloading, decrypting, and muxing HLS/DASH (m3u8/mpd) streaming media into local video files.
  In musicdl, this library is mainly used for handling `AppleMusicClient` audio streams, so if you don’t need `AppleMusicClient` support, you don’t need to install it.
  After installing N_m3u8DL-RE, you need to make sure all of its executables are available in your system `PATH`.
  A quick way to verify this is that you should be able to run
  ```bash
  python -c "import shutil; print(shutil.which('N_m3u8DL-RE'))"
  ```
  in Command Prompt and get the full path without an error. 

- [Bento4](https://www.bento4.com/downloads/): Bento4 is an open-source C++ toolkit for reading, writing, inspecting, and packaging MP4 files and related multimedia formats.
  In musicdl, this library is mainly used for handling `AppleMusicClient` audio streams, so if you don’t need `AppleMusicClient` support, you don’t need to install it.
  After installing Bento4, you need to make sure all of its executables are available in your system `PATH`.
  A quick way to verify this is that you should be able to run
  ```bash
  python -c "import shutil; print(shutil.which('mp4decrypt'))"
  ```
  in Command Prompt and get the full path without an error. 

- [amdecrypt](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools): amdecrypt is a command-line tool developed by AI that leverages Bento4's mp4decrypt to process Apple Music encrypted files into playable formats. 
  You can obtain it from the [GitHub Releases](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools) of this repository.
  After installing amdecrypt, you need to make sure all of its executables are available in your system `PATH`.
  A quick way to verify this is that you should be able to run
  ```bash
  python -c "import shutil; print(shutil.which('amdecrypt'))"
  ```
  in Command Prompt and get the full path without an error. 