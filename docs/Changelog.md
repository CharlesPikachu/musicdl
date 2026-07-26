# Release Log

- 2026-07-26: Released musicdl v2.13.4 — fix potential bugs in playlist parsing for several music clients; add and fix several third-party parsing APIs for the Deezer, Tidal, and Qobuz music clients.

- 2026-07-24: Released musicdl v2.13.3 — fixed bugs in all affected common music clients; addressed potential issues in DeezerMusicClient, QobuzMusicClient, YouTubeMusicClient, JooxMusicClient, BilibiliMusicClient, JamendoMusicClient, JioSaavnMusicClient, FiveSingMusicClient, and SpotifyMusicClient.

- 2026-07-20: Released musicdl v2.13.2 — added support for music search and downloading from multiple third-party music platforms, including liziyy.top, mgmp3.top, itingwa.com, sgogo.com, and xiageba.liumingye.cn; regularly maintained and updated third-party APIs for Kuwo Music, Kugou Music, QQ Music, Qianqian Music, Migu Music, Bodian Music, and NetEase Cloud Music, while also fixing unreasonable behavior in playlist parsing.

- 2026-07-08: Released musicdl v2.13.1 — optimized the unreasonable display of progress; removed all third-party music clients that no longer exist; optimized several third-party APIs; updated some music clients that had become unavailable; added support for configuring cookies in Soda Music to download VIP songs.

- 2026-07-04: Released musicdl v2.13.0 — perform routine maintenance on several commonly used clients.

- 2026-06-24: Released musicdl v2.12.9 — fixed and cleaned up a large number of unavailable third-party interfaces, and added many new parsing interfaces with VIP account support, including QQ Music, Kuwo, TIDAL, Qobuz, and others. Also fixed bugs on platforms such as NetEase Cloud Music.

- 2026-06-21: Released musicdl v2.12.8 — updated third-party API integrations for Deezer, YouTube, Spotify, and Qobuz; fixed the GDStudio music client and upgraded it to the latest API algorithm.

- 2026-06-16: Released musicdl v2.12.7 — fix the freezing issue that occurs when Kugou, Kuwo, QQ Music, and NetEase Cloud Music access third-party APIs (refer to issues #79).

- 2026-06-11: Released musicdl v2.12.6 — consolidate the third-party APIs for QQ, Kuwo, Kugou, and NetEase Cloud Music, and optimize the request mechanism to improve the overall pipeline efficiency.

- 2026-06-01: Released musicdl v2.12.5 — fixed invalid interfaces for QQ Music Client and NetEase Cloud Music Client, and added multiple parsing interfaces with SVIP/VIP/member accounts.

- 2026-05-27: Released musicdl v2.12.4 — optimize the third-party NetEase Cloud Music lossless audio API to avoid returning preview clips; add several lossless music APIs for netease music client.

- 2026-05-25: Released musicdl v2.12.3 — added multiple lossless music APIs; optimized the search interface for common music clients and added message prompts to make the search process feel more natural.

- 2026-05-24: Released musicdl v2.12.2 — added multiple high-quality lossless music sources; fixed all invalid third-party music platforms in the supported list; added progress bars to the search process for all third-party music platforms, making the search experience appear smoother and more natural.

- 2026-05-23: Released musicdl v2.12.1 — for users in mainland China, Kuwo Music song downloads now support higher audio quality; added several member-only interfaces; optimized the search interface for some supported platforms so that it no longer appears frozen while waiting for search results.

- 2026-05-22: Released musicdl v2.12.0 — improved third-party API support across multiple platforms, including VIP-account handling and cookie-free fallback calls; added music search, playlist parsing, and download support for MOOV Music, plus search and downloads for Alger Music.

- 2026-05-16: Released musicdl v2.11.10 — emergency fix for Migu Music becoming invalid issues, ensuring access to at least 320 kbps files and restoring lossless audio via member cookies.

- 2026-05-15: Released musicdl v2.11.9 — optimized some third-party interfaces; added multiple API endpoints with member-quality audio for supported music platforms (kuwo, netease, kugou).

- 2026-05-14: Released musicdl v2.11.8 — added support for music search and downloads from the Suno site, as well as playlist parsing and downloading; added multiple third-party parsing APIs for the Ximalaya and Qobuz platforms.

- 2026-05-13: Released musicdl v2.11.7 — fix some broken third-party APIs for TIDAL, Qobuz, Deezer, YouTube, and Spotify, and add multiple new parsing APIs that include VIP accounts.

- 2026-05-11: Released musicdl v2.11.6 — added support for Bodian Music, including search, download, and playlist parsing features; fixed multiple lossless music API endpoints; added several new lossless music API endpoints; Tidal now downloads in FLAC format by default.

- 2026-05-09: Released musicdl v2.11.5 — added support for music search and downloads from OpenGameArt ("opengameart.org"), along with multiple VIP account APIs for QQ Music, Kuwo Music, and NetEase Cloud Music.

- 2026-05-08: Released musicdl v2.11.4 — added a NetEase Cloud Music lossless parsing interface; added a Qobuz lossless music parsing interface; added a common music client that supports JOOX and Qobuz music sources.

- 2026-04-28: Released musicdl v2.11.3 — added support for searching and downloading a large collection of free audiobooks/audio programs from Apple Podcasts; added a free built-in member account for the Qobuz Music.

- 2026-04-26: Released musicdl v2.11.2 — introduced support for the JioSaavn music platform, enabling users to easily search for songs, parse entire playlists, and download tracks directly.

- 2026-04-24: Released musicdl v2.11.1 — fix Spotify playlist parsing; add multiple free lossless music sources; add support for music search, playlist parsing, and music downloads from Free Music Archive.

- 2026-04-16: Released musicdl v2.11.0 — fix all broken music clients; refactor and optimize a large amount of low-performance code, such as file sniffing logic; add more free lossless music download sources; and restructure the documentation to make it clearer and easier to understand.

- 2026-03-16: Released musicdl v2.10.2 — added multiple shared premium membership APIs for Tidal, Deezer, and Qobuz; added support for multiple lyric search platforms to supplement third-party lyric information for several music platforms supported by musicdl; and made some minor code optimizations.

- 2026-03-14: Released musicdl v2.10.1 — added music search and download support for Qobuz (https://play.qobuz.com/discover), along with playlist parsing and download features; expanded the number of shared NetEase Cloud Music premium accounts; fixed several known minor bugs.

- 2026-03-13: Released musicdl v2.10.0 — added support for the Deezer Music Client (search, download, playlist); modified arguments of some API interfaces so that users can choose whether to write song metadata and save lyrics; and attempted to fix several known bugs.

- 2026-03-11: Released musicdl v2.9.10 — meticulously refactored the core code for Qishui Music, SoundCloud, TIDAL, and Apple Music to support playlist parsing and downloading across these platforms; fixed some bugs.

- 2026-03-10: Released musicdl v2.9.9 — refactored the code for QQ Music, Migu Music, Kugou Music, Kuwo Music, Qianqian Music, NetEase Cloud Music, YouTube Music, JOOX Music, Jamendo Music, Bilibili Music, 5SING Music, and StreetVoice to better support playlist parsing and future feature expansion; also improved the downloadable audio quality for some of the above platforms, such as Jamendo Music; fix some known bugs.

- 2026-03-07: Released musicdl v2.9.8 — fixed multiple third-party music search and download platforms; resolved a bug in determining whether music download links are available; unified the code style across the e-book platform and third-party music platforms.

- 2026-02-24: Released musicdl v2.9.7 — fix some bugs in musicdl, and add support for searching and downloading books and albums from LanRenTingShu site.

- 2026-02-19: Released musicdl v2.9.6 — this release introduces official API support for parsing complete playlists across NetEase, Migu, Qianqian, Kuwo, and Kugou Music; it also includes bug fixes for incomplete playlist/lyric fetching on specific platforms, alongside minor under-the-hood code improvements.

- 2026-02-14: Released musicdl v2.9.5 — this update fixes the incomplete playlist retrieval for NetEase Cloud Music, adds support for Kugou Music playlist parsing, introduces multiple lossless music APIs, and includes several potential bug fixes.

- 2026-02-11: Released musicdl v2.9.4 — supported batch downloading for Kuwo Music playlists; optimized playlist downloading for NetEase Cloud Music and QQ Music; added support for QQ Music’s "Premium Master 4.0" (臻品母带 4.0) to provide high-fidelity audio files.

- 2026-02-10: Released musicdl v2.9.3 — refactored the TIDAL client to utilize N_m3u8DL-RE for HI_RES_LOSSLESS support, and optimized the lossless interface for shared membership accounts.

- 2026-02-07: Released musicdl v2.9.2 — support parsing and downloading QQ Music playlists; update arguments for some API endpoints; update the KuGou Music track link parsing API to enable downloading music files with Viper audio effects/quality using a KuGou VIP account; and fix several bugs.

- 2026-02-05: Released musicdl v2.9.1 — support ALAC-quality downloads for Apple Music; add song search and download for the StreetVoice platform; add two new shared VIP-account API endpoints for NetEase Cloud Music.

- 2026-02-03: Released musicdl v2.9.0 — added support for native SoundCloud search and download APIs, session cookie authentication, and batch lossless music downloads from NetEase Cloud Music playlists.

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