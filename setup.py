'''
Function:
    Implementation of Setup
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
GitHub:
    https://github.com/CharlesPikachu/musicdl
'''
import musicdl
from setuptools import setup, find_packages


'''readme'''
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()


'''setup'''
setup(
    name=musicdl.__title__,
    version=musicdl.__version__,
    description=musicdl.__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        "License :: Free for non-commercial use",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ],
    author=musicdl.__author__,
    url=musicdl.__url__,
    author_email=musicdl.__email__,
    license=musicdl.__license__,
    license_files=("LICENSE",),
    include_package_data=True,
    packages=find_packages(),
    package_data={"musicdl": ["modules/js/youtube/*.js"]},
    entry_points={'console_scripts': ['musicdl = musicdl.musicdl:MusicClientCMD']},
    install_requires=[lab.strip('\n') for lab in list(open('requirements.txt', 'r').readlines())],
    zip_safe=True,
)