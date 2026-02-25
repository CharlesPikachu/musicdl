@echo off
setlocal enabledelayedexpansion

:: ============================================
:: MusicDL Windows Build Script
:: Automatically extracts version from source
:: ============================================

echo ========================================
echo     MusicDL Windows Build Script
echo ========================================
echo.

:: Change to project root directory
cd /d "%~dp0\.."

:: ============================================
:: Extract version from musicdl_gui.py
:: ============================================
echo Extracting version from source...

:: Use dedicated Python script to extract version (avoids batch escaping issues)
for /f "delims=" %%v in ('python "%~dp0get_version.py"') do set "VERSION=%%v"

:: Fallback if extraction failed
if "%VERSION%"=="" (
    echo Warning: Could not extract version, using default v1.0.0
    set "VERSION=1.0.0"
)

set "APP_NAME=MusicDL_v%VERSION%"
echo Building: %APP_NAME%
echo.

:: ============================================
:: Install dependencies
:: ============================================
echo Installing requirements...
:: python -m pip install PyQt6 pyinstaller mutagen tinytag requests -q
:: python -m pip install -r requirements.txt -q
echo Done.
echo.

:: ============================================
:: Clean previous build
:: ============================================
echo Cleaning previous build...
if exist "dist\%APP_NAME%.exe" del /q "dist\%APP_NAME%.exe"
if exist "build\%APP_NAME%" rmdir /s /q "build\%APP_NAME%"
echo Done.
echo.

:: ============================================
:: Build executable
:: ============================================
echo Building Executable...
echo.

pyinstaller --noconfirm --noconsole --onefile --windowed --icon="icon.ico" ^
    --name "%APP_NAME%" ^
    --add-data "musicdl;musicdl" ^
    --add-data "musicdl/gui;musicdl/gui" ^
    --add-data "icon.ico;." ^
    --hidden-import "PyQt6" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "requests" ^
    --hidden-import "rich" ^
    --hidden-import "click" ^
    --hidden-import "mutagen" ^
    --hidden-import "mutagen.mp3" ^
    --hidden-import "mutagen.flac" ^
    --hidden-import "mutagen.id3" ^
    --hidden-import "tinytag" ^
    --hidden-import "musicdl.gui" ^
    --hidden-import "musicdl.gui.main_window" ^
    --hidden-import "musicdl.gui.themes" ^
    --hidden-import "musicdl.gui.themes.manager" ^
    --hidden-import "musicdl.gui.themes.presets" ^
    --hidden-import "musicdl.gui.themes.stylesheet" ^
    --hidden-import "musicdl.gui.themes.system_theme" ^
    --hidden-import "musicdl.gui.dialogs" ^
    --hidden-import "musicdl.gui.dialogs.source_dialog" ^
    --hidden-import "musicdl.gui.dialogs.theme_dialog" ^
    --hidden-import "musicdl.gui.widgets" ^
    --hidden-import "musicdl.gui.widgets.table" ^
    --hidden-import "musicdl.gui.workers" ^
    --hidden-import "musicdl.gui.workers.tasks" ^
    --hidden-import "musicdl.modules.audiobooks.lizhi" ^
    --hidden-import "musicdl.modules.audiobooks.qingting" ^
    --hidden-import "musicdl.modules.audiobooks.ximalaya" ^
    --hidden-import "musicdl.modules.audiobooks.lrts" ^
    --hidden-import "musicdl.modules.sources.apple" ^
    --hidden-import "musicdl.modules.sources.bilibili" ^
    --hidden-import "musicdl.modules.sources.buguyy" ^
    --hidden-import "musicdl.modules.sources.fangpi" ^
    --hidden-import "musicdl.modules.sources.fivesing" ^
    --hidden-import "musicdl.modules.sources.fivesong" ^
    --hidden-import "musicdl.modules.sources.flmp3" ^
    --hidden-import "musicdl.modules.sources.gequbao" ^
    --hidden-import "musicdl.modules.sources.gequhai" ^
    --hidden-import "musicdl.modules.sources.htqyy" ^
    --hidden-import "musicdl.modules.sources.jamendo" ^
    --hidden-import "musicdl.modules.sources.jcpoo" ^
    --hidden-import "musicdl.modules.sources.joox" ^
    --hidden-import "musicdl.modules.sources.kkws" ^
    --hidden-import "musicdl.modules.sources.kugou" ^
    --hidden-import "musicdl.modules.sources.kuwo" ^
    --hidden-import "musicdl.modules.sources.livepoo" ^
    --hidden-import "musicdl.modules.sources.migu" ^
    --hidden-import "musicdl.modules.sources.mitu" ^
    --hidden-import "musicdl.modules.sources.netease" ^
    --hidden-import "musicdl.modules.sources.qianqian" ^
    --hidden-import "musicdl.modules.sources.qq" ^
    --hidden-import "musicdl.modules.sources.soda" ^
    --hidden-import "musicdl.modules.sources.tidal" ^
    --hidden-import "musicdl.modules.sources.streetvoice" ^
    --hidden-import "musicdl.modules.sources.twot58" ^
    --hidden-import "musicdl.modules.sources.yinyuedao" ^
    --hidden-import "musicdl.modules.sources.youtube" ^
    --hidden-import "musicdl.modules.sources.zhuolin" ^
    --hidden-import "musicdl.modules.common.gdstudio" ^
    --hidden-import "musicdl.modules.common.jbsou" ^
    --hidden-import "musicdl.modules.common.mp3juice" ^
    --hidden-import "musicdl.modules.common.myfreemp3" ^
    --hidden-import "musicdl.modules.common.tunehub" ^
    --hidden-import "musicdl.modules.sources.soundcloud" ^
    --hidden-import "urllib3" ^
    --hidden-import "urllib3.util" ^
    --hidden-import "urllib3.util.retry" ^
    --hidden-import "urllib3.util.timeout" ^
    --hidden-import "urllib3.util.ssl_" ^
    --hidden-import "urllib3.contrib" ^
    --hidden-import "urllib3.contrib.pyopenssl" ^
    --hidden-import "certifi" ^
    --hidden-import "charset_normalizer" ^
    --hidden-import "idna" ^
    --hidden-import "ssl" ^
    --collect-all "rich" ^
    --collect-all "certifi" ^
    --collect-all "fake_useragent" ^
    musicdl/musicdl_gui.py

:: ============================================
:: Check result
:: ============================================
echo.
if exist "dist\%APP_NAME%.exe" (
    echo ========================================
    echo     Build Successful!
    echo ========================================
    echo.
    echo Output: dist\%APP_NAME%.exe
    echo.
    
    :: Show file size
    for %%A in ("dist\%APP_NAME%.exe") do (
        set /a "size_mb=%%~zA / 1048576"
        echo Size: !size_mb! MB
    )
) else (
    echo ========================================
    echo     Build Failed!
    echo ========================================
    echo Check the error messages above.
)

echo.
echo ========================================
endlocal
pause
