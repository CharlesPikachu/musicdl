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

Some music platforms require [FFmpeg](https://www.ffmpeg.org/) and [Node.js](https://nodejs.org/en) to be directly callable in your environment 
(*i.e.*, `ffmpeg` and `node` must be available on your system `PATH`) in order to obtain higher-quality audio or improve the robustness of the download process.  

To verify that they are installed and available on your `PATH`, run the following commands in a terminal (Command Prompt / PowerShell on Windows, Terminal on macOS/Linux):

- **Check FFmpeg**
  ```bash
  ffmpeg -version
  ```
  If FFmpeg is installed correctly and on your `PATH`, this command will print the FFmpeg version information (*e.g.*, a few lines starting with `ffmpeg version ...`).
  If you see an error like `command not found` or `'ffmpeg' is not recognized as an internal or external command`, then FFmpeg is either not installed or not added to your `PATH`.

- **Check Node.js**
  ```bash
  node -v
  npm -v
  ```
  If Node.js is installed correctly, `node -v` will print the Node.js version (*e.g.*, `v22.11.0`), and `npm -v` will print the npm version.
  If you see a similar `command not found` / `not recognized` error, Node.js is not installed correctly or not available on your `PATH`.

FFmpeg is primarily used by `TIDALMusicClient`, while Node.js is primarily used by `YouTubeMusicClient`.