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
import MusicDownloader
from setuptools import setup, find_packages


setup(
	name='MusicDownloader',
	version=MusicDownloader.__version__,
	description='MusicDownloader which supports qq, wangyiyun, xiami, kuwo, kugou and xiami.',
	classifiers=[
			'License :: OSI Approved :: MIT License',
			'Programming Language :: Python',
			'Intended Audience :: Developers',
			'Operating System :: OS Independent'],
	author='Charles',
	url='https://github.com/CharlesPikachu/Music-Downloader',
	author_email='charlesjzc@qq.com',
	license='MIT',
	include_package_data=True,
	install_requires=['requests', 'click', 'pycryptodome'],
	zip_safe=True,
	packages=find_packages()
)