# Musicdl Installation

#### Environment Requirements

- Operating system: Linux, macOS, or Windows.
- Python version: Python 3.10+ with requirements in [musicdl requirements.txt](https://github.com/CharlesPikachu/musicdl/blob/master/requirements.txt).

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

Certain music clients supported by musicdl require extra CLI tools to function correctly, mainly to decrypt encrypted search and download requests, as well as protected audio files. These tools include:

- [FFmpeg](https://www.ffmpeg.org/) is a cross-platform command-line tool for processing audio and video. The official FFmpeg site provides source code and links to ready-to-use builds for different platforms.
  
  Required By:

  - [AppleMusicClient](https://music.apple.com/)
  - [SoundCloudMusicClient](https://soundcloud.com/discover)
  - [StreetVoiceMusicClient](https://www.streetvoice.cn/)
  - [TIDALMusicClient](https://tidal.com/)
  
  Install Guidance:
  
  - Windows: Download a build from the [official site](https://ffmpeg.org/download.html), extract it, and add the "bin" directory to your `PATH`.
  - macOS: `brew install ffmpeg`
  - Ubuntu / Debian: `sudo apt install ffmpeg`
  
  Verify that the installation was successful:
  
  ```bash
  ffmpeg -version
  ```
  
  If version information is shown, FFmpeg was installed successfully.

- [Node.js](https://nodejs.org/en) is a cross-platform JavaScript runtime used to run JavaScript outside the browser.

  Required By:
  
  - [YouTubeMusicClient](https://music.youtube.com/)
  
  Install Guidance:
  
  - Windows: Download and install it from the [official Node.js site](https://nodejs.org/en/download).
  - macOS: Download and install it from the [official Node.js site](https://nodejs.org/en/download).
  - Linux: Follow the installation guidance on the [official Node.js site](https://nodejs.org/en/download).
  
  Verify that the installation was successful:
  
  ```bash
  node -v
  npm -v
  ```
  
  If both commands print version information, Node.js was installed successfully.

- [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE) is a cross-platform stream downloader for MPD, M3U8, and ISM.

  Required By:
  
  - [AppleMusicClient](https://music.apple.com/)
  - [SoundCloudMusicClient](https://soundcloud.com/discover)
  - [TIDALMusicClient](https://tidal.com/)
  
  Install Guidance:
  
  - Windows: Download a prebuilt binary from the [official Releases page](https://github.com/nilaoda/N_m3u8DL-RE/releases).
  - macOS: Download a prebuilt binary from the [official Releases page](https://github.com/nilaoda/N_m3u8DL-RE/releases).
  - Linux: Download a prebuilt binary from the [official Releases page](https://github.com/nilaoda/N_m3u8DL-RE/releases).
  - Arch Linux: `yay -Syu n-m3u8dl-re-bin` or `yay -Syu n-m3u8dl-re-git`
  
  Verify that the installation was successful:
  
  ```bash
  N_m3u8DL-RE --version
  ```
  
  If version information is shown, N_m3u8DL-RE was installed successfully.

- [Bento4](https://www.bento4.com/downloads/) is a full-featured MP4 and MPEG-DASH toolkit. In this setup, its mp4decrypt tool is required by amdecrypt and N_m3u8DL-RE.

  Required By:
  
  - [AppleMusicClient](https://music.apple.com/)
  - [SoundCloudMusicClient](https://soundcloud.com/discover)
  - [TIDALMusicClient](https://tidal.com/)
  
  Install Guidance:

  - Windows: Download the binaries from the [official Bento4 downloads page](https://www.bento4.com/downloads/).
  - macOS: Download the binaries from the [official Bento4 downloads page](https://www.bento4.com/downloads/), or install with `brew install bento4`.
  - Linux: Download the binaries from the [official Bento4 downloads page](https://www.bento4.com/downloads/).
  
  Verify that the installation was successful:
  
  ```bash
  mp4decrypt
  ```
  
  If usage or version information is shown, Bento4 was installed successfully.

- [amdecrypt](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools) is a command-line tool for decrypting Apple Music songs in conjunction with a wrapper server.
  
  Required By:
  
  - [AppleMusicClient](https://music.apple.com/)
  
  Install Guidance:

  - Prerequisite: Make sure [Bento4](https://www.bento4.com/downloads/) is installed first, and mp4decrypt is available in your `PATH`.
  - Windows: Download the binary from the [musicdl clitools release](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools), extract it, and add it to your `PATH`.
  - macOS: Download the binary from the [musicdl clitools release](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools), extract it, and add it to your `PATH`.
  - Linux: Download the binary from the [musicdl clitools release](https://github.com/CharlesPikachu/musicdl/releases/tag/clitools), extract it, and add it to your `PATH`.

  Verify that the installation was successful:

  ```bash
  python -c "import shutil; print(shutil.which('amdecrypt'))"
  ```

  If the command prints the full path of `amdecrypt` without an error, amdecrypt was installed successfully.

