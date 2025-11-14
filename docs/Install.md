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

Some music platforms require [FFmpeg](https://www.ffmpeg.org/) to be directly callable in your environment in order to obtain higher-quality audio. 
You can choose whether to install [FFmpeg](https://www.ffmpeg.org/) depending on your needs.