@echo off
echo Installing requirements...
python -m pip install PyQt6 pyinstaller -r ..\requirements.txt

echo Building Executable...
pyinstaller --noconfirm --noconsole --onefile --windowed ^
    --name "MusicDL_GUI" ^
    --add-data "../musicdl;musicdl" ^
    --hidden-import "PyQt6" ^
    --hidden-import "requests" ^
    --hidden-import "rich" ^
    --hidden-import "click" ^
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
    --hidden-import "musicdl.modules.sources.lizhi" ^
    --hidden-import "musicdl.modules.sources.migu" ^
    --hidden-import "musicdl.modules.sources.missevan" ^
    --hidden-import "musicdl.modules.sources.mitu" ^
    --hidden-import "musicdl.modules.sources.netease" ^
    --hidden-import "musicdl.modules.sources.qianqian" ^
    --hidden-import "musicdl.modules.sources.qq" ^
    --hidden-import "musicdl.modules.sources.soda" ^
    --hidden-import "musicdl.modules.sources.tidal" ^
    --hidden-import "musicdl.modules.sources.twot58" ^
    --hidden-import "musicdl.modules.sources.ximalaya" ^
    --hidden-import "musicdl.modules.sources.yinyuedao" ^
    --hidden-import "musicdl.modules.sources.youtube" ^
    --hidden-import "musicdl.modules.common.gdstudio" ^
    --hidden-import "musicdl.modules.common.mp3juice" ^
    --hidden-import "musicdl.modules.common.myfreemp3" ^
    --hidden-import "musicdl.modules.common.tunehub" ^
    --collect-all "fake_useragent" ^
    ../musicdl/musicdl_gui.py

echo Build Complete. Executable is in dist/MusicDL_GUI.exe
pause
