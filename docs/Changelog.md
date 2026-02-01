# Release Log

- 2026-01-31: Released musicdl v2.8.12 — refactored the terminal table rendering algorithm to better accommodate support for giant table; fixed kugou lossless api; added a new YouTube parsing endpoint.

- 2026-01-30: Released musicdl v2.8.11 — added or enhanced search and download support for Ximalaya, Lizhi FM, and Qingting FM; fixed several known bugs.

- 2026-01-29: Released musicdl v2.8.10 — support batch downloading audiobooks from the same album on the Ximalaya platform; update the API interfaces for Ximalaya, Kuwo, and TuneHub; and fix some minor bugs.

- 2026-01-28: Released musicdl v2.8.9 — add an automatic song tag autofill feature, introduce shared membership APIs for additional platforms, and deploy a TuneHub hotfix.

- 2026-01-26: Released musicdl v2.8.8 — added a new lossless music search and download site, implemented a Lanzou Cloud direct-download link parser, and performed partial code optimizations.

- 2026-01-22: Released musicdl v2.8.7 — refactor the code for three music platforms (*i.e.*, YouTube, Joox, and Jamendo) to retrieve higher-quality audio from each platform.

- 2026-01-21: Released musicdl v2.8.6 — refactor the currently supported unofficial download sites to return more standardized song information.

- 2026-01-19: Released musicdl v2.8.5 — refactored four cross-platform search sources to speed up song cover and metadata extraction via the musicdl API, revamped the terminal UI, and fixed several potential bugs.

- 2026-01-16: Released musicdl v2.8.4 — partial code optimizations, added support for Qishui Music, refactored the Bilibili and 5sing music APIs.

- 2026-01-14: Released musicdl v2.8.3 — refactor and optimize the code for Migu Music, QQ Music, NetEase Cloud Music, Qianqian Music, Kuwo Music, and Kugou Music, standardize the lyrics output format, extract song cover image URLs into a unified location in the returned song information, and integrate more high-quality third-party APIs for retrieving lossless music.

- 2026-01-01: Released musicdl v2.8.2 — adjusted the FreeProxy API arguments, improved the robustness of fetching high-quality music from NetEase Cloud Music, QQ Music, and Migu Music, and fixed some bugs.

- 2025-12-31: Released musicdl v2.8.1 — support more lossless-music sharing sites, add pagination support for some of the previously supported sites, and fix the Rich display conflict under two-level concurrency with multi-source searching.

- 2025-12-29: Released musicdl v2.8.0 — added support for two additional sites, improved the search speed, stability and metadata completeness when fetching lossless tracks from some sites, and optimized certain default arguments (prioritize search speed).

- 2025-12-24: Released musicdl v2.7.6 — add support for MissEvan FM, and fix bugs on the Gequhai site.

- 2025-12-24: Released musicdl v2.7.5 — add support for lossless music search and parsing for the gequhai site, and optimize parts of the code.

- 2025-12-19: Released musicdl v2.7.4 — supports music search and download using TuneHubMusicClient.

- 2025-12-17: Released musicdl v2.7.3 — supports native Bilibili music search and downloads, improves the search speed of some third-party APIs, refactors the Ximalaya music platform code, and includes several other minor code optimizations.

- 2025-12-15: Released musicdl v2.7.2 — added support for jamendo and make some improvements.

- 2025-12-11: Released musicdl v2.7.1 — added support for two new sites and fixed several potential bugs.

- 2025-12-10: Released musicdl v2.7.0 — the code has been further refactored, with a large amount of redundant code removed or merged; all supported sites can now download lossless music (for some sites, you need to set your membership cookies in the command line or in the code), the search speed has been greatly optimized, and several problematic sites have been fixed.

- 2025-12-02: Released musicdl v2.6.2 — support parsing `AppleMusicClient` encrypted audio streams, along with some minor optimizations.

- 2025-12-01: Released musicdl v2.6.1 — we have provided more comprehensive documentation and added four new music search and download sources, *i.e.*, `MituMusicClient`, `GequbaoMusicClient`, `YinyuedaoMusicClient`, and `BuguyyMusicClient`, which allow you to download a large collection of lossless tracks.

- 2025-11-30: Released musicdl v2.6.0 — by tuning and improving the search arguments, we have significantly increased the search efficiency for some music sources, added support for searching and downloading music from Apple Music and MP3 Juice, and made several other minor optimizations.

- 2025-11-25: Released musicdl v2.5.0 — supports searching and downloading from YouTube Music and make musicdl more robust. 

- 2025-11-21: Released musicdl v2.4.6 — fixed bugs caused by mismatched arguments in MusicClient.download and optimized music sources.

- 2025-11-19: Released musicdl v2.4.5 — fix potential in-place modified bugs in HTTP requests.

- 2025-11-19: Released musicdl v2.4.4 — some minor improvements and bug fixes.

- 2025-11-15: Released musicdl v2.4.3 — migu and netease have introduced an automatic audio quality enhancement feature, which significantly increases the chances of getting lossless quality, Hi-Res audio, JyEffect (HD surround sound), Sky (immersive surround sound), and JyMaster (ultra-clear master quality).

- 2025-11-15: Released musicdl v2.4.2 — save meta info to music files from TIDAL, fix user input bugs and migu search bugs.

- 2025-11-14: Released musicdl v2.4.1 — beautify print, add support for TIDAL (TIDAL is an artist-first, fan-centered music streaming platform that delivers over 110 million songs in HiFi sound quality to the global music community).

- 2025-11-12: Released musicdl v2.4.0 — complete code refactor; reintroduced support for music search and downloads on major platforms.

- 2023-02-22: Released musicdl v2.3.6 — fixed incorrect Netease Cloud Music information display and Migu lossless music download failures.

- 2022-09-03: Released musicdl v2.3.5 — fixed QQ Music song search.

- 2022-06-08: Released musicdl v2.3.4 — added support for Ximalaya audio search and download.

- 2022-05-14: Released musicdl v2.3.3 — fixed minor bugs.

- 2022-03-24: Released musicdl v2.3.0–v2.3.2 — removed Xiami Music; improved user interaction (progress bar, speech recognition, printed messages, etc.); and optimized code.

- 2022-03-15: Released musicdl v2.2.8 — fixed download issues for KuGou Music.

- 2022-03-08: Released musicdl v2.2.7 — added support for running directly via the `musicdl` command in the terminal.

- 2022-02-09: Released musicdl v2.2.6 — fixed header retrieval issues for QQ Music downloads.

- 2022-01-15: Released musicdl v2.2.5 — added support for specifying page indices in some music sources.

- 2022-01-05: Released musicdl v2.2.4 — refactored the code, removed Baidu lossless music (API deprecated and not recoverable), and fixed 5Sing song search.

- 2021-12-14: Released musicdl v2.2.3 — fixed issues with KuWo Music sources.

- 2021-08-30: Released musicdl v2.2.2 — added support for online voice-based song requests.

- 2021-08-29: Released musicdl v2.2.1 — fixed KuWo Music and Qianqian Music.

- 2020-11-27: Released musicdl v2.2.0 — added support for Lizhi FM, YiTing Music, and 5Sing Music; fixed issues with the progress bar and display; and added multi-threaded search.

- 2020-11-21: Released musicdl v2.1.11 — fixed Qianqian Music.

- 2020-11-20: Released musicdl v2.1.10 — further code optimization.

- 2020-11-04: Released musicdl v2.1.9 — added support for saving error messages to a `.log` file.

- 2020-10-17: Released musicdl v2.1.8 — optimized code.

- 2020-10-16: Released musicdl v2.1.7 — fixed Baidu lossless and Qianqian Music interfaces, and removed potential bugs and unnecessary characters.

- 2020-07-26: Released musicdl v2.1.6 — updated KuGou integration and removed the default proxy to avoid potential bugs.

- 2020-07-04: Released musicdl v2.1.5 — fixed QQ Music and JOOX Music.

- 2020-04-15: Released musicdl v2.1.4 — fixed several minor issues.

- 2020-04-03: Released musicdl v2.1.2 — added support for JOOX Music.

- 2020-04-02: Released musicdl v2.1.1 — improved robustness and re-added support for Xiami Music.

- 2020-04-01: Released musicdl v2.1.0 — major upgrade with a more user-friendly design, bug fixes, code optimization, and added project documentation.

- 2020-01-07: Released musicdl v2.0.7 — fixed bugs in Migu Music.

- 2019-08-28: Released musicdl v2.0.6 — added support for Migu Music.

- 2019-08-24: Released musicdl v2.0.5 — fixed various bugs and repaired invalid APIs.

- 2019-07-13: Released musicdl v2.0.4 — added support for Baidu lossless music.

- 2019-06-09: Released musicdl v2.0.2 — fixed bugs in KuGou Music.

- 2019-04-15: Released musicdl v2.0.2 — fixed bugs in Xiami Music.

- 2019-02-02: Released musicdl v2.0.1 — optimized code, improved user experience, and added support for installation via pip.

- 2018-08-05: Released musicdl v1.3 — added support for running in the terminal.

- 2018-07-02: Released musicdl v1.2 — optimized code and added support for Xiami Music.

- 2018-07-01: Released musicdl v1.1 — added support for KuWo Music.

- 2018-06-27: Released musicdl v1.0 — added download support for Netease Cloud Music, Qianqian Music, KuGou Music, and QQ Music.