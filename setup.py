'''
Function:
	setup
Author:
	Charles
微信公众号:
	Charles的皮卡丘
GitHub:
	https://github.com/CharlesPikachu
'''
import musicdl
from setuptools import setup, find_packages


'''readme'''
with open('README.md', 'r', encoding='utf-8') as f:
	long_description = f.read()


'''setup'''
setup(
	name='musicdl',
	version=musicdl.__version__,
	description='Music Downloader.',
	long_description=long_description,
	long_description_content_type='text/markdown',
	classifiers=[
			'License :: OSI Approved :: MIT License',
			'Programming Language :: Python :: 3',
			'Intended Audience :: Developers',
			'Operating System :: OS Independent'],
	author='Charles',
	url='https://github.com/CharlesPikachu/Music-Downloader',
	author_email='charlesjzc@qq.com',
	license='MIT',
	include_package_data=True,
	install_requires=['requests >= 2.22.0', 'pycryptodome >= 3.8.1', 'click >= 7.0', 'prettytable >= 0.7.2'],
	zip_safe=True,
	packages=find_packages()
)