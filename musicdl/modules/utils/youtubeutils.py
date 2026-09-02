'''
Function:
    Implementation of YouTubeMusicClient Utils (Refer To https://github.com/yt-dlp/yt-dlp/)
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import os
import re
import ssl
import time
import zlib
import html
import json
import gzip
import copy
import base64
import shutil
import hashlib
import subprocess
import http.client
import urllib.error
import urllib.parse
import http.cookiejar
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any
from collections.abc import Callable, Iterable, Mapping, Sequence


'''REPAIDAPI_KEYS'''
REPAIDAPI_KEYS = [
    "MTU1NmY2Y2NiMm1zaDY0YjgwNzQ4NTE1NmIzM3AxMmE2NmRqc243ZTE5N2JjMjNmMTk=", "NWE4MTBhODA2ZG1zaDE2NDJmNjEyZTIxNjViN3AxOTYwODRqc244Y2ViNDIxNjlhNTc=", "YmViZDlkMWE1Zm1zaDdkNTJmZGZhNzFkODVlYnAxYTZiMzVqc25lZWYzYjg4MTJiZmI=",
    "NmM5ZGQzNjBiY21zaGJkMjk2MGM2NzY5MzM4MHAxYjY3MjBqc25mMmNhNzdkN2UzZTA=", "MDdmZTg1ZWY0MW1zaGE3MDdkMTgxYzZkZmE5ZXAxZTMyYTNqc25lMDIxNmYxNGI2MWU=", "M2Y3OTQ3MzVlYW1zaDg3NzNlOTY5M2RjYTczMHAxNDNmNWZqc242ZGRiYjY3MGZkNzE=",
    "NWI1YjE2NTBmZG1zaGUxYTlmYjk2NjlkMWQ0MnAxZmZiYmVqc24xN2RiMjgxZGEyMjg=", "NmUzYjhhYjQ5Mm1zaGRmNzJhMzkxMjA4MjczYXAxYzBhODJqc24wNmIxM2EyZWFiMmQ=", "ODMyYzM4ZGRjZm1zaGVlNTNjZTk5ODNiNjJiZnAxODdmZDlqc24xODk3M2ExNDI0NDI=",
    "YTUyODE1MjZjNG1zaGZjOTlmNzJiMzE4MjJmMXAxNThjMTdqc24zZjM0ODJhNDE4NjI=", "NzMyNGRkMDBjNW1zaDc1MDQ3ZTNjNWRjY2ViN3AxMjEwZTJqc25hYzQzMGQ0ZjIxMzM=", "OWUwOTQxOTExYW1zaDU1MzdiZDhiZmYwYTRmNnAxZmFjYzJqc242MWZiNTRmOGI0NzQ=",
]


'''YouTubeAudioURLExtractor'''
class YouTubeAudioURLExtractor:
    EJS_VERSION = "0.8.0"
    EJS_REPOSITORY = "https://github.com/yt-dlp/ejs"
    UPSTREAM_REPOSITORY = "https://github.com/yt-dlp/yt-dlp"
    UPSTREAM_COMMIT = "bbc809a1161d3bfca51fa36f59dda35556ee85a0"
    class Error(RuntimeError):
        """Base error for this extractor."""
    class InvalidURLError(Error):
        """The supplied value is not a supported YouTube video URL or ID."""
    class NetworkError(Error):
        """A network request failed."""
    class NoAudioFormatError(Error):
        """No usable anonymous audio format was found."""
    class AnonymousAccessError(Error):
        """The video cannot be accessed by an anonymous client."""
    class JavaScriptRuntimeError(Error):
        """A player challenge could not be solved."""
    DEFAULT_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
    WEB_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    AUDIO_QUALITY = {"AUDIO_QUALITY_ULTRALOW": 0, "AUDIO_QUALITY_LOW": 1, "AUDIO_QUALITY_MEDIUM": 2, "AUDIO_QUALITY_HIGH": 3}
    CLIENTS = {
        "visionos": {"number": 101, "host": "www.youtube.com", "requires_js_player": False, "gvs_pot_required": False, "context": {"client": {"clientName": "VISIONOS", "clientVersion": "1.02", "deviceMake": "Apple", "deviceModel": "RealityDevice17,1", "userAgent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7_3) " "AppleWebKit/605.1.15 (KHTML, like Gecko) " "Version/26.0 Safari/605.1.15"), "osName": "visionOS", "osVersion": "26.5.23O471", "hl": "en"}}},
        "web": {"number": 1, "host": "www.youtube.com", "requires_js_player": True, "gvs_pot_required": True, "context": {"client": {"clientName": "WEB", "clientVersion": "2.20260708.00.00", "hl": "en"}}},
        "web_embedded": {"number": 56, "host": "www.youtube.com", "requires_js_player": True, "gvs_pot_required": False, "context": {"client": {"clientName": "WEB_EMBEDDED_PLAYER", "clientVersion": "2.20260708.00.00", "hl": "en"}, "thirdParty": {"embedUrl": "https://www.reddit.com/"}}},
        "tv_downgraded": {"number": 7, "host": "www.youtube.com", "requires_js_player": True, "gvs_pot_required": False, "context": {"client": {"clientName": "TVHTML5", "clientVersion": "5.20260707", "userAgent": "Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version", "hl": "en"}}},
    }
    VIDEO_ID_RE = re.compile(r"^[0-9A-Za-z_-]{11}$")
    PLAYER_ID_RE = re.compile(r"/s/player/(?P<id>[0-9a-fA-F]{8,})/")
    PLAYER_PATH_RE = re.compile(r"(?P<path>/s/player/(?P<id>[0-9a-fA-F]{8,})/[^\"'<>\\]+?\.js)")
    EJS_LIB_SHA3_512 = (
        "8420c259ad16e99ce004e4651ac1bcabb53b4457bf5668a97a9359be9a998a789"
        "fee8ab124ee17f91a2ea8fd84e0f2b2fc8eabcaf0b16a186ba734cf422ad053"
    )
    EJS_CORE_SHA3_512 = (
        "c163a6f376db6ce3da47d516a28a8f2a0554ae95c58dc766f0a6e2b3894f2cef"
        "1ee07fa84beb442fa471aac4f300985added1657c7c94c4d1cfefe68920ab599"
    )
    EJS_LIB_B85 = (
        "c-qvxd6!$&wJ-Yr{S-pyq+E(sMtiGQS@;xofgOzPxNHb<e8MhiSCz0zTi%jv9NQTNjB!JN0HzCI8uun4379T4V{qW!H%2mU?)eJ-"
        "0{4A{H-"
        "B@^wf5Soa+Bt~ci+juHP_m!oon{1(cM41>%V1wn3>zL=_gZLJFT!c2&cBR!``s7&<W#4W_PbExhS=3sWZqdbh=^YU@*u8qhYih3_"
        "Go$+dY(740~Z548wM2{!nIVIP4D^ci+9(87__H*R`VMyAKVg+TH%$;bQ}8360%5>b1L6d{fvDd(>mA6Al{sZE9)?f3^k7VI#8~#+"
        "^gK5;7hN<3T6tH8PcT-ntTUbj*#+mbr~c?+p9Vpfil(LyZjezIK(7XnW@GI{Ji~Go#^BL^FOM?DY<1?pv3cT&3;<_jQB8Qcj0SeV"
        "PGi&c>*JDDEsS4KtIiT*fbW^-"
        "R!fXS#%#IG>T)oD&U~XfErt+Kw<@?hG)s%rMG~24OzaqL%WR<*40Rpube*?kLW*JA+}|nI8?q%n)lah!%zigE-7A(8qv=-"
        "5<p?e_9_Ja)$EoHyRBy3t^a{^3-QY%d;2<JzA-JrXNQKI&E5n;ZiW9f5J>K9~}s}bD2gjq6H3l$lPN;8L9cy?}tI0>GU#02dGKwX"
        "y&zR^K52r`+d6}p4mA|*vjnKx&5Inn`Sp<vNLm(&Sqw|ZQ?>RyLWBgzB99lFuHYS%Y$>7nXOwhRBPwVwq09h=Q0m(*|j;dbN2q3o"
        "m751RiVa`hPQ3px_i@>ZTEAnEf4P4x`n!MYHz<U^Wf~xjhiVsbMKa|TXsFd9pATQ*S6WYxpmY)X5046>_fBLc4g)^qY-CJ_s(XvZ"
        "kf4v>ulyeO3iG0gqUS^<CdANc^dA{*^RsMRNp{UV&nF0bF)9*O>I$`%%+(KXYR)kq^e0iym@BV+;-"
        "}5C(UYZ_tsq){e3&PKbYCNeU1mbdv2CGnAtUhs)RQh>|CDe&C<|zV#G7_{~LF0*}e^>sncCMXE1_ov-fY^a{uhMjkBn@olEc9zLN"
        "^>p3@5X%*@U$bLesV?p>(8og1V!w#`b5jBen7M#25h?xe{-IK!>pmq!1(6wj{U-T)NaTTF4Ux30dfkmBA4x9l3{-c`7-"
        "9T2t7N4;J+yj$BH=iW^ylDU`5WY%+qf0G*PTCIC-#--)_omF)BbQNw|h>6Rhg-mNHh!=^4iItfrY1&jFnjZ$89t}AYFn^&vDxBtH"
        "@L4bzM6C{s(stAuEt4=NDN8Lt@(wbSVAJfJ*2w0#pLQ5@(I9alKAW$W|KkwoYN44t6>4=yZH&Zx?sk?t+6k&NZXl;`B8^CLVt)P6"
        "e77@L$~$5ypBW&NSJg_bLD=QNiENNbCu7WuaEU~;3>94i<Q!azmecd;@Te9>agRC<xmr6S^l`tBg{>iSP-"
        "7wLcB6xsV=L;lJD8f)F1!9NIX75>e47syebjlUht?9Q2Z2k&7z~LXIzcznk7Dk3e8zVw9rMhG;8B%jkAV3gMjjxElh4flWCsZk$Q"
        "D*cBKPu+IJ}ptZri?#<QMVRtV+(=TT8|~+EU3V5-+o3hQ!Cl-CJi!5bWN$V>`(Nh|g`?w{6*W-%jdi_Cb<%HxZ-EoGeM_L^|$xWa"
        "pOqH}A@9-"
        "oACyEM=~gudD*{uIOYj#sXuD8Ri{`LWn(E`{6ARs7CNX)bdPkD*^2SQ4vQXieTL|JF}IVqt)6rzM$(8NqF~vJ3tDu+nH}JjC#z2l"
        "VR>~mKZA|T$!CFA{`LzHYX>;{4m$N=dfhN&0csgv%Aw97X6tx4h~IL>Xo9Oo9>d3>NN}bs9BgM-9I_qTkn^v-gHhYcADXy-rBW$r"
        "#lOio%MxWG}Y`(huuMV7&Qa))t~50OiTvN;htb`F7HirHpJ^l%5*1#e3XyYYO!1+-"
        "V@Q^W^nXq91e;3GV#&e<en)n@8|sr{;ASG<ve8+^3`g&UapjC`C`6QqU<8&c>pR!{8Qo#{?Dt_s`W~xidrSVUZQICIyII@y9N5M<"
        "Z;20`Ch4%{i0@3DfC<^b6F`+D^{w-GMe^%&-crvq-nCmN@%)L!ElNtuk3qu8Juss_v%#JWcig^u~;bAYeh+vise$Fgo%1Jr_XxD^"
        "U9vqqHlHmRw>lHYN=4I>s%`M2em6)u~wmaUcH`Fw0P0+Rz0Ah#QhX%G>p1e;KJ0SU#Jt7WhQ>9ST9z~TCrRzQWjdG*^_1~_>BK@l"
        "@cXspafKu%=jy{TD2@gDCBE}T2W9|@k-TNvFzDq3A+_7MI)$|Y9%S^)hlHlO0iro6{|(BP~Ziq(dT-#QbVgHT30Sp!Jw2TN`-"
        "o{QlfQ1E0s#2;?=627OGXviuyHZXD;oR>t2Nu^ruqy3k4oPz2?{J9ycnO_dQ~fQmO38;QeadC*0LJQLOl-YQe`Cls0OmQmHPVYeW"
        "DAP!>}c8mm+b)k>kxlub2|<rS*MYKfNC&Y@5xk{8-97m7sHB}Ru&#9FBkiDPJHUD2D&$FJ6?Hz6n=`1gucG-Bw%FDl`91p|Q8ePt"
        "-7rjmZC;!73FQ>~h;nyKY6`2r`XUQP(E$TQ{EP?#w-"
        "`CJoJmc2@~N}Pc_6u{K#G;7bZj8Y>~A?DyRJaxhv;j!r3wo1NX0{vUWKQ(1C;u4;k$CD}>=C65%Q;ReVT><kgVM!rA>atW4as}^u"
        "l|rGytC+%RSx{G^m8mJaVMfwsIT14jj|G}%hU^(OC|0XNz@9Ec#UPSL<-"
        "5yOLv{^=s4>m@#1iPHEMusZd99eKNIdfNyb@2DzVZt2chsqwF&3#{O(bB|Or>0R=|fhnRHb!;V5N32{kmcBDIPJiT-hhy@Jkh630"
        "?$3rA`c2;+my|7HcAIE$LLXF%gDS=2M}PpAy7WSdLeVwhSW%UjWvNj5fotv|<Gxa?G=f!eX?JVbv3otQ+#FqyJLH47zA(rf!K61W"
        "_#VM2kePg}PVt4fXgXU3S0VmItRZ%1tp(^2_zA5`ajLV$w^!SSK`!SS5BQd0yw4@}vvC@GJAO5$<TOTB&G8Ns9A~S@ICM`l=#X{Q"
        "Jow5I?bu0S!_`lKNbWIj2xbD<Be5iI|Xo%&bZV3q=`ZO{4;7xkx$&%v7!xS#x`Zx?K<!QLe66swgPJNSWzcdprte3Qq{zE~*dmP~"
        "_J0Q^+qDNkY=<(5I5=hDXPG+K7#+VZ;=Nc_J39Jy0-"
        "W(_<>H+F}VLLuC}%u4IyRS#gz3f*fD|)nR+mHd9ZrV2anw$Fi;KOp_LAO6-"
        "ejl>~g5^^8wkMnfr8iZXm22_uhLq9}MRYA2*vWm%_+2`#9=D45SFpp>#t%7qeJUQjPpBOwaKDl3gLE7}6-sv-"
        "@jU{;`1lqFEQDO#(?6B0;7YO$86iCWDn9pABIL=cyZvMRF_tf&Mc3otRlXdI%qg_4-SimXgc4zFCXU~DX6@^X<UqV^1F+-"
        "l9Q3ZIa<NRqx<mkG1QgxbDXmLfh$q@y7_1{f}WwNNWnWeHqyg4LT!?9G~ABn?y(J|ok$QX&D8s2d}LO66p&N>;O%RW}n|dxFNPa)"
        "P|6q-"
        "O|oG8;sglR6XwjtskcrOqp8sIw?$MTu6M%x?_euR07`GFqxqONj%jZp3Pd+XIq#u{g<6mRqY8Yitl|Z&<)$fsjzEmRM6U)p<-"
        "0#Uj~iWo9#ya8q?7Ow~sB*(NQL$v`^WtJfWiye`dG>PC?W4Oom6Mf<QM6)aBGRKr+`l*MFLGEB*9<d+=9T~nm{R(qq9vWniSS*x0"
        "BiP?nJH!K0lf{?oOH)R_nYh%g~)>J9&Y7{Hws_VJbi!irER**$qQ9s0E!&XPda)D{TTvi$2vzh0W3RZ-"
        "9B{3v?VKS>o!2EuK!jf1o)hbwot=FOoc(D+ynk<TX2how+Q2|Rar!tF?X+~}h3+{52XKpPmD+!p2JSL-xZ!=k-"
        "2*s4@j;a#25OWj5<#vjcBVL2rIwIFfqHPP#kn6rRfePiKnCN5+R;hHY#I8jdXe*YC)*{qSRn#Xc7K$~;VI&FZxxO15n<-"
        "<mzzZPzv&6!M{X8La5t3Dhq}cWK3>8-"
        "rK}w$(HRZCBGg!<o!WwW)R+0`=EPfezUYQ#xGy2Lh1MU{fAhrOOP)%>Lu&ja<(WxIQi8<!gcy1N#k-"
        "5gJI7~w2rm9uP+Qouvy3B69_Ek{&C!?}lP!m;hDju_7Ij<HBd^Zw}g_}kQrfhhC{ET8H2@ljnm)tZw;8)A5h6fUj$#beyj7WxNC|"
        "PH-M#{ud1w^}5zbfui6&;jJSJi5vQmYvOQ>ofI9tMoOI^-aEnq}f;&<JUNa#t%NmaR|3LewvNc1Cp>7!x-8&hQica=GGFT=`jb-"
        "0~`~Xn_=M&EqhDPc~_d+#hzt$x9;7uTZHv@d3ZaMqZgp)XN$jD3oi(0=pk1<O_wG6CGeXpjr^IY~?o7E}Kc!f_7RZf7Yw03&TUvm"
        ";mW2bqlG@ipqB{aq&Z$0;%Y_UnxomfDlQ_%n6Ag6i{IDDfsnbp~5i&BHRMWrK+f-"
        "I(dq9H*z4|l95}JRUku!bSe9W5*nzL;Y2#dJ=?=oqmso9BFRdaEfk$h4h0akkj+z+`eH-Xiy8^=9D|Nms7f+FksqSf%N4;tY4a*b"
        "OtJ3QYorhgYLi$0G523B%fH$2CmJX6uY<)jrUehyhO-"
        "!()k@7T0hv=Pe0?iL{dzg=^e1fSy7~$2`<~+>NWW@hvn{}Z8j*KAy{ZZF5XIGOR|XH|g82+0uZ%hM60a<k5QQ?5QKwS7L&u(1)H?"
        "CSJ968JPrX`k+-"
        "olu3v65@4*L`<6637X1nR6FORlmr3ID&yPlu6L_0xfck|?f15+5kviMMW~blGFAS+$hJ)c^?R5G#<;TxPLTuO*H|&9~kWJ1HzAMG"
        "lFmE7S_Kl)mK{R`VVQeTs-#`iS6I1zsXo0pTOZjrT<UkuWUZ#*MH3{r)?77ljJ=z5Gw|-=~TzeRbCQWoa-"
        "W+`rRLuZ=n8Q!D)PV&Qgvxq9CJC;H_iILMchQmgsn;`9C^4mq=JLdrzl60mkWa>UAca%@Pa{c!cZb#YQ|xJW>D5rnuPa>c{*tA;b"
        "h`YhSZqQg{mR{A9pNHQiZQFau4A#ulz;;Ksc+gs_D8~L7C2IQZUye0u#Ff%BMR4>>3ItSKZl^cPsG-owrxnd?>uz@O)<B7A(78MD"
        "lGE|Y%hJ>^dJCEbour8D=bb(#Jn^xOdQjr1daI@Si)xDZJbH?8`VX9;=h{TA5qbtRtC%Y#w4C>Wl)r2cK;>Cu-"
        "s&2SMy~L`oYKpxlUzLr=f>DAqLK?iD9Dwmb*IvP_ps^R3)$3CIpXgc_m=15}Tf<>cA1Ccsd#U(g&G=abL$=}zuJo&`tNYa?&1*)F"
        "!5#BO2LD&P(GuF4@@m!pSDar_XjA2?>%mrCY#NVTv>X|w6%X#I7?UN(O|{r&!cY8EPF9S};js1!UsXhq6YC<IqIl<?YO(hJrGr{4"
        ")+&4RdxT@FFi<V%@kV2*QXmJ!x)CJHY=IJQxq8(qO<yhC8e!LNMycE?A_6D7JY}<G2>Yd2tCNdgf)+OIpd9v)YY>JI4h8l?xp6W<"
        "bQ}nz5(0~4b61ndD*QViMNAmo<1ihW7dGx;i~9&LNvkzffz&N)j1r>2C$qFb5~XA(3un7fuYw{qK0^2_TZhV&!-"
        "fc4SPAEf^XI{rhb}4lgdY-twQ91D%wU10j(uAb2DDZlna<cAFIQ`*q~oiL+g&Jw8LS7cpTYOM(G4OccOG#ejlC9m!^J}^5(2V{ok"
        "Y7rHG>)QKYdQn_!EpHlw6c;5pJ$ZKBC199H9zXoUj%!c|{P7lO(&rIjK}quj1Gu-"
        "p+~+{woa;_8%=ZS**TowhYT03<sOiqt$~+BuggN0ntpgg7Bb05%tEAXun*<mMoVgn}(_ti|XIY9LYDLnG;HDWwt(uI%<R$pbi_=v"
        "`mDKGFc{Go#~lygd+ex%Me7H$xAX@_VBAc(P$)|3qpZDsQ{w6I`KBb5YlTMJI8i4YY7|qX2u}uGB%GrMxF`d__k=Rz(ijoC#**FQ"
        "ZptLwyF#tnEoof89-C>38z4?X{0P=iO$%;uh8n(VUX~WlP6F}hE_x*yHX@}tr<?>7<I8gv>|3Y2mi>HsAAduTG_{P<CFo-"
        ")6AR?6@mvzFd)JNiYK|k1u9gaUNhrIpDYauwTi7z5Oh|lROW_>O^5=~q$7(IpF-bq<fVX+q!|IWL2Qsn5lUq+E};t|2|v}PUo{{L"
        "h?3<4&{Gw5U$I<=ULaEn;}!7(g;g$>VM((1Vm@L1t6{5@)N-"
        "NDOhjH*y+kcTgI1|RT|8cDhop{?PPJm$k;w3^tRyR2^BDszz|R9IGCvDyv4`cCAe)Kie4L>nHAISsd}|UoH4)P+Z4~lKi7-"
        "tBZN=N0%g4>IdCy&UO?nf<J(J-"
        "*_uNy?ttBS$DtieIbJON5SB6h>>A9$IT`TI2mV0a0<_R3dao8JfTnebIb%SUWw<wcR8>4nOGn`zzHeA=~wZq4AM{Q#f8Z)QCQcd6"
        "}7cE%5a#wS*LVW5^40Ac{wlHnZi>=m=_OjN?O>6lwVuH4vIJcqDVA-^GauR}+T3)~2E9BNnDt5-#;R9-"
        "i|CY%SCKkHE;^0V==y76r<jADKQnNtcx}9FQcCFJz02DZN{>HvmG@Z0Oa8`<ls@ZIYM~?6op@3wM2vDw?ui-sS63G6<M7X|L^9#i"
        "zM_^>jH|%|BMI7!hnFY@@Ou`gkGJuv#D(frd4dGO&)(EF6<+Wa6!Yd~wyC^w0*crB#m?DBfn1RJmD-z2#q>1dd5$-"
        "UwwswYL9CWkOsZv!_YK{*|rwfsZ;Cl@V`ljr?QPd5C-pazoq|a_Q{h8)jDwxkZ!^KfIh-"
        "V+~#~~k|HHE6A&xmImZmQnU5qqZku5h`J%M!MScDN9Xy2FN9HB#!8!o)Ab4OF{=zu6r?*(exBaki0tAUt$1irWMwmsqk#j|z8;nt"
        "KZQmH#6dW3~c#bL-Cj2ddCukWFwS+y;VqB}v1FC`pWEwf{&Y@_z+up_?8m)$#u?-"
        "r@h?HOjfcy6ioy`2RcnUur;m^ZnHk`1kzJ`v+?N?f-"
        "Lo{YUB(4%+|qIJo5q{tv)GqWTt7@~lY)|AzjaaPK`N4(LlF%@$UcYfHJwl}ffC3N}Y|Se%xuU@fyW6=q&)?#a%PT<emo=!MyQ_CX"
        "R89fddVdT{IZe%MoRV>cRbb}(3)4|<Cmqh;Kx$T~CG2fdb$^SykO@7S^W6Frjr>*5ec`6mmx{IV89p=5e)t|;%rtd1Ikqs@@dXNT"
        "*C(Y~;^1-VUCR(Z|Dn46-"
        "kOx8xxVMduvYmN2cy0F)t&K)LGpf)kulhTZPbN0}<$7(EPJV2@DV@$?rX=1`FjF+64m`p3&;p&<;H$5MR!M>w3lu1&F{=cVc<!F&"
        "}hta7PgOQZ~$FP8|!gW!f?^LXddb*0qv=0x4K|E|6MjMTeG$mCjrETPC+FHWt*c3~3eDvt_D&0*k?ICM-BHEiDt{dQ{%j6(6uUx*"
        "9o*3um$%Zm2>`0tY&b&}gnrb3LHRJ2f2yn2xzEsTdf&M}BE>CKd{1r=&Y6G&m;)&)|IZs82j!Q6HuqI4Px;S@=+S?*7h2(CkSnJl"
        "P^%As3d7b@~pUX#6zDYW${Kx1iAA_O>Ihy0J(;J1;D_Ls8N>17^86Rnu^C0b9V-"
        "n_Y3}0cYJP{x9at)yJC@xyugej=HmNiYtvhZ3=TT$cHaz}A#<Y4|#BBOSteFL5@-vo)92iMIm_lJk3!v<5q^euddo=5_!F=z$-"
        "Fh~9W(j@qbNJh=hp_-kgYJ;l9Ic8*G=S(P8U7ZZaBTZXdO2`*azHICUgF)&8S&|dB3Rb`?-"
        "qmalA&cZM5N9F&MrOD{OtF+Rgm6#d3v|QY;&3Tv$s#GN+9ERen(`Q9o#r9ISUwoT(5m8ldSNoiO<RLJFa~*{*yv0gT6cdpnh&~;r"
        "YKhO*~Ki0f+J1y)y08VD096ni@higH&WJE-Hxf7lt|aFbA48MpzyKk%ci<5kgDxfx%Tc}r$thItnLVPldp5(a4=Tlz{oVOWzvn;Z"
        "q@jK+qXW}IEth?Aio7I%nduOeTT*>A2OBYYkFXU^G(rkraQh?15;1Frg2@6wd%D=Dvgh}Z5K*DYfa;|BxTFFqX7$CCCFAnyonZ3A"
        "GSOGZJ3X&>#nkl{4DaZnuq(rkUXVcqnl@cxzRf62=X{M$m(2b1P904O=&2r*p0Y+DCmwt=gOKWs$qP{SVy><CgYgIr=zWanBx`&@"
        ";&k$wN#2nj~=DgyZKfw&%R`$9v{D{dK4zkX7hqoQfo#aGQZx%_EE4mC&p4hQam=|p|kcDxF1u6x5Hp`GqiQ`)(@X%Ywef8kt21;w"
        "IHVgF0cYFaAP7<UJ?|MD|@)ZcdIcg3WD`yS95#<HbB4-"
        ")K`$G@j1pPiL&^fW?=(0DzSle3vsjz3vWl%AvGN58V8`)@&!?4nVS`)hAiIKdPg0(%*JJ+%_?S)N8P++o#%`J-"
        "7Huk8>^75*NpRDGaTvLaDZ=^yJWM9CaYkx3MR`$PBQgGTA4zg37<6B%yJAbSDD^2y2jS@kO`*a+9YeogIGf_3r|I3FtlbCGNG2tY"
        "9x`L(s7nFlv2_lN?DsKdyT_#J2aju)$$!@41qO$)_QU=G&Q}|V{4rpiWYrhC%72U*NEXo%1u-"
        "L^te^pBrmGjTfe?|L`Fb^4(PwmogkBX<F1B#SNb8Q)uGcW2ucHmm68(c!Xyld-jO4SZQgX$sd~Cx9Y(YwJ(%*0o!OJsD(f1Ri~6^"
        "uf6EQ@5FI%}og_UZt1xXZ<=*L9+yQo6Y>Z>dPRN;#V>R2E=XGYDUuf8#!KWC~U6Yj(cV@!OQzaW_Zjp6J+&We?a*LXq!t2+Uj<hB"
        "tL-AyMtmw(}SD4x2*9^_|W^NwE_p&=PY!0Q_be;V09?#?5RWpooqBdQ>$wSDteAl>XKUHcBj~>3w)NdmLlG^dg+Pz!W_TAdOm9?W"
        "=)-GBTLDyn~{nRX4I#BpF0d=cdu+HmAuMn!qeOX_lzrCDU(OhGybW~ZRqO8Ea0&&7!i4Hv&&bOjvGE`FhQA{`xq1^F6Z+tY-"
        "4hM`CkakR_Ow^bK;*_6QTk!_JK}*5eMK`<H@JgCrO7g3kRZg<J0?ZOSf{n84;aVZFu|lGziDu^=gG9&{n>EcqY>;B5$vWQ<`>m)b"
        "cbGN0ZMv2OTk5Rbb8OUz+P}y1E4f>!Xtp6zL(j8o-ZNe~+?;%ijRWrpnFo0x;}+QnH*L3-*d|jRO|msHL1f1}Ln3-"
        "&RawnmB7+8mA=rR~qgm=KfXz}MQI^cpgp07`EgHvBk?CVmt4Vgt0~@}&IRR7In`7p0+F8owCnsygi6FPWsQtofV<$i0XqPCgl{Q@"
        "d<^#x0-`r%XT9e5rAt!=nY|NV*rZL+b;_^-"
        "!0;NGm8@z^3lZg`Io)zLw2zEF<&T5%rrQui!N~R!^*hUg>O4e~Mam*9iu=}J_LtXP*SwyR0_UJ8<H%uXKm`r!SOgBBGm2DJkoMCF"
        "p4wpa?1xN34pYjOzgc40?7WOu?3}y42$w7{$hg=3Fn}Z@vpK=+>9-TZ$v~;j}_$aN+9W|W91-S7fDW4_ez&!{k*)|-"
        "|EYTO6l8@?dH@ymd(}a8xXS!LVd;uj}eC1{ly$Gyh6IYnb3ye$>sV?BsH$A_W^n)D2!Xd)KA;yAgylu_Hg$5N0AMb~)A;0&t4^jQ"
        "%D!Gl!njaL_Wb<AlyS+6Gx|xtMo*9JuM`4e~kii2&y=aIRd!mE<eviJtf`^T0uKwRrbErF&8F`0_W>{=wfA+H)KOyw9pVjZIPN|X"
        "I5qAzCuVXhXGyn2~0^XNGZBmQ0LhWq6+{kX}cEd#)o+530nAv=V%JdEd-"
        "A+5h1^SRPnI9Cg`D*fIDSSL=hpo=?%86$4b%TPgY{1?gX|+anleR{kg^OXF)a6&`f=o9I__e8DgmIM7*XrgwZJO_j)`<PHvu0U)q"
        "viRKUzUrhfya3w9{D$RD&25lIJE?X4+wjBIIFYRLnN7>-"
        "Xh#l+aqG8`L4ccl@z9ysG)69Z%TVvh(>sOYk`KIA;OA!Xr=?|<*nts=O_K%+gaSw8=5_8^7PS?vw#DOt#&7-xpWU{!#&xsHyEO-"
        "L;xZg1{n}f6sKrsaHuy7TIPvG>0H)q094$v?#&jAoM7UeA>Oy@@grkGjLw*<V+AbPCPiq~t@t2X<M2H{3W=Uu*lug%alw8VcS%}!"
        "L{@lo%OP<D-"
        "2+f|rhTXvEE7&fX{zQI3DYeShZYhpfQBL5P+P+HKCS12c(RM;;?j7#v)Cc&lJ}hj?9hZdtqvJ)Aa?pzbchO5k|?*L&P9$-"
        "3%0#Si;*6#@QDnJYB>|7$zielvP0N9;L1%Y8ILJiVy2SSTbDf4Yf=AkbdZYH8f!Mv()0UigApx2W_d)Cl;17mSIDv~TEQ1Y)|usS"
        "xD>VVLRmmqrcOcpdUOL6C3%F)E@4|Ah@*vB!uy}nK9^XN_i2qE44IXJ7Rk&(1_y4&2M}n7BrR#VW)23l22O`#bW3sqE7+&5sai-"
        "}NJc^Skxtlc|4p^(<yF;%EL}UZPY#XHl8~iA1%vpI(>zUdz=#9pGazYxzmpKwvx1@{sBy+*=G^WKg5~+n;)pqk1tJZMsw{;AW@3="
        "u46mS3{DVx3nvOtZXn;{qb@hSHVbrIQ90<EuolZ{#UuM1=wf52YOJl4X%W)iMWK<}Pjg>_*@XM$i(dVWS7zMn4lVVECMWRqrTFDf"
        "6{!76DVvxrJmViI-h(;IrIl~|LRD(naseSNoa`H>ROKmLcJSK<73sXc;=gwTBOu7r0<Am5rheFPTj}s4-NOat1kL;nya&Sn5i-"
        ";nAtC6}2;{#YJA_#uak46v@=K(as8?2D2B~Jt#kCaJdh}9u9s6Yym$x&${;+f2%OrF--PE_B}g}Nz$EJ!imvP=nO;9HM|R^AQ|>F"
        "ksM<sn3QmKP6Cc7?B*2%)+l&*bGqm2qH)fp9rwnwl!8Bbstxn+~k>hz;(!eHs~&&V8&<AN`@qr^hFAhmSs*nI8@H$;+i^L~KmWJS"
        "qi#s70tY5$OFq^8s5^1BJmBiU*4Y*ib}!pu$zZTX|Eev66PBd!nXAJFjWpL!?|%Wi=*f^$kZBvttY@(v)A(jib@xQc8B03)0*?Yz"
        "d+Smujtzm)I#(!7~CO=}Twjt|j(XT&^w?QL#5cy2wzrF3JE;d$!W_K}v|y!)SP@AJU}DMXjB2w1aJj*BaJWx#Wt3R8gS>Vhq*?RJ"
        "81<+g>XUfsVUr_5v9}N(CJ?h$j&V(T~#P9yMYadL-zr+D2;rL<NsF?|GD$6~(1R*CxcPtXL7Egq>j2uq(}sp=%fiuxl3Ct_i4oJu"
        "xggy$+uC?EFIP(zFyJ1DqCn4e6gLkYhI@QN2XAuUjUeV(G2tHc1V5x6<^|GB@1FJm`qL0Uv}iG)B!hwhl2`Jmh990i?Su!Uu6h$I"
        "pMxr1A5g>)XymP~=@gB!KE$Jd`LUGpH4!jIG#{8?eeVd^KS6|8X^7=UF7652{dJvFyyms?x^EyHZIkzctCrnQPR-"
        "?i>&V83E6Vwnx_e0H$7;Xb&3kfM}pnZLCR7h-R`~B8;(tkD=eudui#vCSR#JR;eB)VWta31XSwDcM(0#$10J`Mv?Eln2*v>_N-gC"
        "ZttUlJ)8nD8ZD)Bst&0b2{K}1brqVg`bzT&BF3m*<F9Gjs1_Z)me$S?h9nn=*;Bf?T1rNhszsle(cMX~mzuv5!{=5;PnE4>S?zzM"
        "?fh8FdDi)2`^`t~Lu&JN7E;ScYyYsmqI@u%&q$=ZGfxtP*eUD<^LXPvJqi`6|HMJmjr4Z43w5<-"
        "=seFZLSo9+OKhWB;r3F8N;w4QkeFM7sEl8tXS;rqs2IbgKRL(+M!r!9Y851ik(aNL=j!&F65v872F<~6S7pt%uyITs=1lC0z%Zkr"
        "LlwBGLv51;0=GSy!kX($;DK)*m=tr(Fk=qils#)DX+86^US^MICHo4u7;Ej3TD`(de8Nr~F=uIO6^MsnYYBQ4axV_|k4WSVtX)kG"
        "NWy@59zTogNesLfjj6L7HCY{NGLZ@GC=`=~95+NktyDOGfHT&kmgqu0$N}<PAZMd%V;sYnJpLMVrlT}M+miMPba9B;oowB4?@0l$"
        "t!7r6z1upG;M^FGTS2Dpaufbo`n&D=NxK^Nb-xx9gD<nf-"
        "~(+#iPIqN*o3Ro+SB;giS!l1H#CK@Ihsly4HpBA8J>__r!`;mFKf7A*W^p03J8=rDqbxm<a(@4xGK=RhA422C=&7HMfu`TQ+CaaQ"
        "O&D}4T(EaHEF?G7WI0%1K|wnfEb|zVYfOr)Qyeqn3SV|S_r9l$qL7<UNeD$+sP2jOV^UDBx63ha-"
        "X|o>cG;{&_*=i#fU>%1@@gKsDpnbc<Oqhi=?}S7^%s^<6hxD`ajexvp*_3AJ#h(#|fV+8ZrvpdGfNy!bd$jwqayqj)ePeC*V0%wf"
        ">qPu0gdmhe@IyU1REzfkT{Xofzda)FZ_0GR#ja9H~PT92)l}jE{tKg^1=#$$^qW3U7gH^&^N{7^4T4{Y(+*MO9?8HZ!Y+`rhAEA2"
        "o>Zaj4&f9VPU(g2z_T#*;I>Uif(C-W*yft_VpArMnB>NriOyrzuw2e`u^^Z8%YkSjR^ZHh5Ijhm9OOx=Q8p&HT-"
        "Pg%1JjNf^!%J;77t5u*vBuzMjq#6)1fF=c9W2vcqRq(m3S{{d2?ZTs5~0nv3d>Z6(J-_VQ%`BrbImI^SrMp-"
        "Jpf}-_Q(c4E_a8ku3QFpo0p^ibg+|h6Z&WvUe6%|e(tbt%|5keg6k|=J6oU<JB-"
        "pIc0Kz8`0go^dcqlXZtd^8nK?Im%<WR1~m0G;U}Mm*C~w?DZvm~NM-aJbNUJTvOIAtX$&3Dq4(I$9CZapL77D3TBfC<^tf$!6372"
        "0v!40&Q3`zkbt516Rwy*$dlag2J!ev{qj`HU7B7C(_li<2R!^OnPx$@i85`GPGyt2`zbuE*TT^?~k>5h($}FM&zdmqMKTIy|ytRO"
        "`K9KoaCoUIuP3ugSIR&zHDPFn+ocnb~$Ahm<>}8!Q8FEJWYkwFvst^q|e%zI2qMu>L^Ndu+ojSdaXy(OY9gZZ;V9l*Cs}lS7afe+"
        "n3}fny&Gw?kFa<O2@(mifYkplk7jZD_C;e6=RdpP<}MGeVf)nAzEf_Ah){FoOq@lBC;yLp@a~8U;*ol0HtVU;M1th=g14w5ek*uj"
        "UJ9DdI)GHVKXyi#YQO=X78`M8;oLAJ4Ea{#1Ob`TaAq_Z4eR1q(MaGNsCwm&O;z{_Hnft+_BKK!#3|5#o+?X9PFVI3rq<MSmrR69"
        "@<Ka@4hQNFcNHx>Xzpqgqy)EH@-uu+!o5V%Ge$$Z*=-"
        "<0b$ujL{#yh74feDWt@ObZ@eeeq}BM*+)u=RaeTwDgWq4%EgWaNE6D60MVJaIiT&x7-K{(7mx}izK^sb8ZxZk@Smd8!lU-_B)S32"
        "UK?|INQYzb$;Q7HAp1GK@G>V?n4C+^9+@y8nhn2LVkyK)4VBQ?}2yrqbvnH7f(?Lyb?prZCf}31uuoScflj_*1qm~d3f}5LY*{sO"
        "1`vASPYl0x=Y_AoKuoJ~oG!}awb^?pBK_BC}dn`ocRea-"
        "{8nc4kNe@BF`_#=G`%=2;>Wr@p5V{Zti>5DH*NtTRhl7@E(U6#m7TF&%T6JKoa&qIAjB`SC1aA9#Hv1}$il$L5x|{1DKt3@kd)pm"
        "I?TWMUoBo)=Su)*UH4B0YwOdyh5372WI`)gL<WrHkjx<`3%@CGV=ZW>bChs9!xmC||w8zXakiu{nwDgC$f|Z-"
        "cI9%Ydk)tw<<(8_&#DDLC&j%y2gBAn)rkI?~V8*KQ-dTEA-U-Y&K4myA;|$$A3QRnTwu-"
        "A6JmT?K^VaNQqkKs$b;k(>o)U%tkqH7Jn$|eD1V2`Z-cosq@oMZ8vm<SlK8U7TX{>2EOT-"
        ">hc7=x|D>d#EW67$k*6;MvafdZWr)9mi66%H|j0c%H96xz{mewJb3!u}uh8hRG#c-PHOt)#gafiul+A-"
        "JkG6$*3o;lARHMi}F_u_0_mt^AP-9MQ8S$l2n?!~<R-c=80t*05$li5AlwR*-"
        "c+W@FX1+!DxwZkNTX!G|rGTF6JE|0juIv%IJ49ZzF=;qMP;2AXc*h2DmuY9D5jbC?N^$M$V$#s}2F|?Olr9lTv&B!@aJY$YE%PHd"
        "2Vbpx5S;z;?dLGB<CgKf+hL`VBR=-)msY~SLI?e35?Ak5VN`#}r>G~cYQH|U~k$!Syw}i(^A{-"
        ")?GyHI?n$5|ge<aGuNl;uOub315c!7tHluzgCI5i(_nCv$_8lzYFVP`Flg6F$y*J|lpW3umD*d*nh!?4ZQX<W|ePE5FEFx2h_a?;"
        "3R$k|&Qp69I`lb?*qudO<!8VzYOnkv=)DT6Ac$5gMa98$p!$@fdE4$1$o91`CMiT36&9B*Rit~f3xd(&P;2ZfcFJ26!JaNHzh4v3"
        "!gXt|5HsA=ypXH1O^D_eJOlAyU<qh21Px&j|1FV%=%5A$tnIcFT)(=1F(lss*lFLemca=-"
        "ymR$+WJ`KhVE60l}TcSnvC@rV(}h*`sJP40zkjasaE@_P0?xq)*_-"
        "o|Q7)8gU8egB`_a*<IY7`SVZn1>Ki;i;#ucqWIu|H1p5_T8YPowd!I$cs`%7H*PJ3go8GLdRHRs%}Ki*u|T%=5prAop$P;`hrL=E"
        "1ST=ac+TlL^;T^e!*dVU2DHAbj<e!ghkv-"
        "4MW_=P*Qi<%Hsq038L`(oG>0H+oX7IB0crg_~iIw8K!kCnu{N=n9DD0_*)kyeVAX)lsau_RXmrOGm3Mj+nvn*Je$vE?XnhYHIgK$"
        "ro1v~j7|egv4QN*L3m#`3efZl9IQ?-"
        "jkW(wqI0f!Zjqz+@?=3FZ!hKZ#Tk9SLPWw)#T8TI*v*>&D{a0_$~phsKcD+!i0)M>C&JAYJNRi6D>;fe>9qrXFyWsrHtYrFRR?7s"
        "lM~k4)ZCL*ms$!F*|=_6R*rKKV0J39tDP3iE|3q7x@6piTnp#?v({~K_gLM0iHv5O_s~C+^xt9nZyo+yhkuXKe>wVZn*PK8_RxQO"
        ">Awd3w}Jj6dwETEO+LGJEhVO=&=CE%em(xZ=N|c&|NQWW_;)S-"
        "nc_75xf}od0RQ|u{yBnwCKwWs;SC$`FU~(j3j|1flYj$JhaBVVUG(2C(KK2H>U#VSe%!YuHGYUr&>Ihf+vP4W*e2S(i~m&+!{>1`"
        "1b`>RGm+__1vG$RV;l&|^1+n69NDG6tg4abn;uzq)bUr2T-m4{PiKBa{$<Rd?g(Yu5&aX&a*BJz02}*QX>qUtA$XECe2a-"
        "=!X~zcy-lVTezJ||NBpC#Z0G{1WcKnO-"
        "n7lKqn<su)IrQB3pY#}(~t<`m3*CrfN8WJwDtvy42f^XP&8x@A29#GG?Oj77Xl7RxG9U>vMjql_{&~SK6TnTpXI|a*#ZA6E}qPkJ"
        "VN@z%Ni12;Lic<3TB<SV|MJku#>YeB2+lL8%YV9#V0oS$A0tKf1&@z?hp_;;vewF!%LJo*B5N)wlzU`&}NsO?BzkL>w2HgewRJik"
        "o`9xT~GdG*_D^-_l1l>xikRiM{_^fg&^17{6o#dShYqCKTB)xAR$>Gy}!`F+j#Z7EIATYKTiZo-wU-"
        "`9wfyjig}_OhN^iY60Tm&chF9?SR_kX*sbC5uhLY@c_s>Oua*Z<11wkaOy>-j^F%#dpqgiL=iF*u*wr*t$uq6-"
        "=*g&MI^;wlZ+L?1)$`_>DaJ_h-STszhHJw$YB=I=G(D07ru}MOd4s=I@=Rm|*9(Pmo+(Wdl{~W|&{8kune-Sg<Q+0>cs?GlH5|%K"
        "7V^T6oG9g$CplHlvjlGNlZ|;$D)&XJMC&Wv*76BAHH!Epy1eizFF+-4*^57x^IcRd;R#=Ul7pKr<_QU<s)rX-"
        "l?AyprG(BnRn1#g<a8}B?8pi7R?UbAWbQ<MwUB2C!Go#ip+~q!KMzsBYg^AV5A&d^ULGun(#2vPY}hCltA%R4?gQ}+yglpZEnnJ?"
        ")x3~A55TYILH7(3*%?+R)RzkW(d0>`9b%E-0XlVNa=6`zcf0Yr<T`3^7p$8}*W9B9H}NB2?)Sa9{BCyWiQ-GudVyw=gB_Z@a<!#L"
        "qJR)LXEr7`tb<L4NW+$~S73LV*XZm$#o<)E-"
        "Yb%Zaeg%%hB}#McTKK3;2f@7n@Mf(8qTvS_nOFqbvTl0q_hxjm<&Tk4esFDdb@8?4==31PSk356`Xq8O}+7s9HjbXMQTi#)K-"
        "!f9+Y)5w^G+Zj>y&2EdMUL^WJFVuzYUH7u~qkpIAR^;_$e?J!F$p-x<jFnz6nkH9cJ4n_j!tK7U4EV2~27F^rzMRLU1t_3-"
        "?v{mZAZ0cfzW6W-"
        "Yn&|}QOF}Kqhd;HGr*pP~uzAa>i04oajd)JxxwuApFIZC=Uo_uE^D9B%jZELwGZ;uPxE}de$)1u|(ILJRMD9<*`z;F=NWag!oVQ2"
        "T!{bR|KjJd-cdzdWZ7vLs-*-"
        "JTih!7k(B4VIcsEvQFlQZHIgB0k)#Ke@o{$BQL@<@nt<=>}*r3pexwMdQyXt9^_@(KmCR4!mBBJPC)ozAEPwNvI2EX&49)T_o^af"
        "tgq!yc(g#^aN8W*CpnFrQ4T+D!9Rz3hIit^8`S6R$wV_*~=L&NaT>T<;$fA#U4~ro(h6;X3zp-"
        "4Waz#zG}M(kM!)YEIAjyC%)_CMFDKT{5WN)pXyt{!t=%*&iK>A3EHV{nzYT5>4hZe#-"
        "l=5+)!Xh)JTT&u_C7a07j~?qAIXbVvIB!hPD=m1Ja%Ij<HcuK;0_WZIP2hWmst4%>jnO7RDcnx|^X&Ae5F#V_!rCd;YZTEupcHv1"
        "VaGj2}Zn&)*7HxO<oLWe$vIaNor9-"
        "%`O$fs;Pl0EUuVJ_E55_VBsY5x;LBx#Z#4?u$OZ3wdL5yfuicgEa^snhDerlugmdEHVl*nW^7H_L4ZNzOJ{lsT*Quo(-"
        "JL)$z;Grd}@?vA29{0P|CldI|1X^6rr8~%0jp;Uk<w_$@%wsyVRc!Wn($h&0wbLWAQOx%0`!89G=;$#XV<*~TaO<n-"
        "YOD}k_onNv^x_U%8q$7cxApP*#$`?!P{>ry~+!3sJ*(^wKh48g`EQsesoH#a_PO~#HA&>Rs)6K3rvtcf8M|?DS8HL)9^f990J%!v"
        "@H+~_1lg4s4dwNNJ06^ckuyM`1#-"
        "7T`>7$zZG@78!JVh~ihgdRkP_Z2NH5aEMKQ1*fF}SDc)4xPpUSig)ps{IJpCd@yQ=&UE8E=?MemJF3$Ti{(i4NQ#l6!-"
        "rXc|uOBfSQ(?gsV+xVR&J8%C#ZFiKj!`qfgUSZMI?+pu)UlYYdc>1J2!5RH;#(u#OP8c%=O))T$F!IVk$DB9!}QxUf>nTOW1^Kfg"
        "jm^;!t;^HpdTJNaUgsUSu;k=(hafq#GUe03XGH)tnykhc05RoGSpj(He=JJbax~^9cr*(wg1MUwbc-6aZ_fC-"
        "`jmx<^e^+X4)6Y3CQu(PjPt3bt$#XMf57^2}GjVSGL7FN5?|duFjnk%|NV@6P?}}(H9*mN~t$0@KpVEHSE+%h=43Fv)W6o+;b9eM"
        "kn3tQ@2f|jX+qvBfWn8zjYTe*=?~`%eV63k3TAK327{4_Z>04tReQPZEn~1CA5?6_El{~xp<K`axj^XY9tMU*0@n8P0p1-"
        "qtci48NhF=V-C69#4?~}0z$k&Q>{QNHd7VsN-Ng;X22|pfI(NdMXU-pYdL}Ku3Xad*uH@eV9sf?erO15ME3nAZgf*<I)f*-"
        "@6Ed2H{emf2ms^V8G<wqcOy8l1>Q>pt^uUz%yhZymr?X`LxzilU<@ynNZ(C#+>XlWN-CF_>(>W$qb!>izTXL+#If}gBY+0Y^rxbu"
        "Su8iFxD#MAWtebPH(!by2IZsokZ&Y9!StZR1qLH2=(0}VqlXLF9C)4Y}u@!h7p^CsOK7S?Z!%nN+|<_dYasxf-_R`12H9QF7!^4w"
        "Q@r9Nu2!Jeq2AMa`JogRC{)-"
        "bOA;ElePsH>uxc1iR%a+J=rXu(t&D_zxe%``2mX?|HpA5p{cdslzN)7mO~6#C_1T?u_)mgpw^MW0k$@jFC%l8H>I-"
        "0D9;r0+Pl?Pv3Hqdu%?vTcJuPi5POd|?2YSHP?M)PDM9aGJGwn?LoTSZ?5<{#GvE!sGj`BcA(N1y%CEoiVP)9s$O=tAhKG^w{x$i"
        "l-"
        "+hHpm<M{F8t<6a%qWuh#hBmghFW#aJkM{I$5cVWThYt@TV#C0L)M^c#DUo6h8yByaxm=V(>!Sp=5wb10*Hix$l{oG=F_#t|hq?QD"
        "MQ8_j~uqvL5qw5kdk{J`b(>OWFoo-yUn!G>|P0$-"
        "(aP0(7Z6dDz_f%U6Lo=MWpQI{ty2UPH2CAVn5Bw5m`*Kj+lE7hrDUfGWM;4FNpkg8N^I6t)EJ~?P;L5tlHN?iIPM3ngF5;mBQ(!;"
        "6}@w?^A`Vg<Gt<~ltAKbYZ&NsHkoh)Ce=!~^U%Tce_i@C-"
        "sQ>f$`rs1P*H}zCEt9Sy;2XXQfCX*iV_K_~}LS@yU!zwS*I?*IwUw?P0znJgemgIGArK9d5#i<!q?F{Qjjm&{r))=FSl@D@{&$uc"
        "x)`2eTKnr)sq-eoUwJ<L&+_Fm1x6k(SZ;;$Xkd^#$y;dzdoR2BmpMPU}bfu7u?`f856BF_JX1SV6>64nC9jv%QahMj0Ln{(1<05h"
        "BJUg0rns*`ri4eSGHFe|(*O2{mC-m?6C5O@(Ut>Qc<1ko>#95uxW~ICuhm=@}aL;BKY)Id77-"
        "o@%t7w}#e`T@Z$R9L0eM^d5t&da$Vs#x@QXN<;++<Wzta#KJOTAi8=1N}BouIr}yK{_}1>;q}uqwujGGyvlMUvkb3%yi|E2eRqE+"
        "OZtm6~5FmCBZ~hq>E4tUEazSM~Y3CWpc`L*|-"
        "XdJrJkdc9!dO8!xKMftG(sjjyCJeM(s#9*=<Zvp`(AlkVHZ#1`?9Womy+qqRwsb;fz6P6aP9iXILGHLj>@l>i}4F}!R*3raa^YF}"
        "Ux3k#D{>O=Ie&)d)4IGx530k9JNO?~XOeWm{g1>u`;8rJYQ8t5z8rlE#0s#wgBl~~9_40877vlg$|Kk|J-TqS0$o|h?6Sy3-"
        "sLXfB?X?@(8&_T;C|Znql!<Cle}S9$jNpF1d&s;eM@64_m+~+rYV~OX2QBXH#Ww+CAC}6TdYKZ#PPdJ&pCWj)+$D%wzBg#?8+3!g"
        "5|ujn3excb0<T?S@L-6+JWKPwmnTC*y*F&(b{2|XM=I_`qi(k|pp4@mAY+I*y-"
        "1MGn#Odm8UE)43$FhB8i71isWw{fhx;+o=d$^Yo4GR@!p7}89%*F1y+V-"
        "U`@0i>`&9DGiwt#!L3dMUVIhq9HN@^F`t<bE_;jcn9^zsBmQt-CW@J7KIBa(?{bvC4a(#CaVALa0z{Gw}sdhx*cc%$L=`Ky`+s}}"
        "|ftF49_U)&XT!>8vOC6dvhD;51LoRXS^y?=5Adw-"
        ")a{3jMv!g2+XHCYg&T_~(uTl=~#T@Jm!i_}1<a2Jp`?hh=#o+$PpXt*m?jG6{jpn=Ik8yL5z8!nZ{bqA93Y_{t?N1fPhbtc=(OZm"
        "1A<z5NyPQ@ee8`FM-hYQ&tmcj5PckU?jPdCOr1|FEt%m;*m5QSQW_lT27;=4^;1RFuOAN^(pZZlczsW4=Cc<hQEP*7?6D4l?5t9i"
        "GW78Z%DDqQ=o+l{aBTh8^caewzo?vjW#1wv>U_%wp0Y*jQlT9Iy^BIPin31W(jNA_KYKLFOoe`S+_TyA8ul=82AIrl!Y570DmHKw"
        "Sh=fN|nY)Bp|NJKBE=MdC&KyT-jMj-EHW~i<6JXHhWd?)_pL&xMv-"
        "?N90;gU;62n<#bv`uToMt3>us4I(0jSV3FPYq};lj}7zToEW#GA+V)64FsU14a@FL^|PZbRoj8~>7O?A#ab=k%w~&8KwtFQ&4k|I"
        ">DAyZg4_uamsggwLA%hj4y|R)<6*uyq0XNx2g*IcX_!-pz7)x-"
        "Qu&4FB?LN!rOi6!LMs?2QXABwuLYN&eeOzRf)G)p({1;=(JEZ>FELa?bf+bDw!)MXt8<s(erkp0_EBfJ>4UxRhcT9DNOjakP*4jb"
        "=5w?fypgdy=oSyEc<7MvhUbrwBHj`37K7sVK`#O5%1_#4}B7RymU-_^eT`faR1ARtYK9uP*}Z4-"
        "d^P2i@)*F+_}+y!t22rsW;`^vX5*q<Z)@fXZlJ65JnjSg8I_A`in{SFS6p{Cnfnlbq4%cIM;GXc<T$6*Q}w@Am*Z$h|^xah9bGA$"
        "eBR^BIC3?+k{Jl_#G<!o2z0odxHUFuIQsLMw5fqJeOCUk8t1j7{-NlfTLwuhKU&v9AEfGhLPj$B-"
        "Ds9isY}MgAWsLx)b_{UU&AWcTlC;8gkj!SXVu@REWgv;IoL=YC@!5z*eS%J;kX0E_ZP5pD_fWMSVSNM}ULe*YqbA4$~v%`m?vSl&"
        "dkV(mgYYir0l=FD$w_I+fh*wUA5w*H~atMA!Nt$pfKn={u9dRB&BN&2@7O$&Ixp>;IG8kNXr^UO}sErjOHK`SKs|MN2dsldO}Uqu"
        "3~;byTWh(0!Vy7Po|K8lSjqJ+(=b$<mg?)(DxcDslXQ|8OGP@8pKP}H#5MS{t&0!!krnpXfV9!OJe5w0RC-tr^1bH5`KW6O5VBvG"
        ")%uqE}pMOpDVfcQ>4u|-ylNO_BlpM=>K!-"
        "+JPEz2fTneZxuiygc@vjuc~5*ht&hs_^I>n*~#A24Kf(=|!PgV311XP!jXfzF`A+Kh?s#uM*5nZ~Gkf>vaU^6~Eg3LTw22AJ87sB"
        "4R&kYv#oHI~04HL+#1kLP*<ATuT*?MJ$79|Oc!s{bRUSVGi~Ob3L(9~r8+062`fIL-M-+Ab;e2gKr~0uM-"
        "QgtrHRejfuP3HX3vnoj`ZJ2JI5T8jrvZ-kErOmDRKTct6Q30sLl*V7+kMSl)>dA^Mfeghcp!;N!S0rGt>W%w77A+{4S?^Yv~zXGg"
        "d`V(MugLa_D@z&$LG5HlCR`J|r%{DsX1t%?f<(czNR$6tRkS`lUezFC=$Vtf&ee85|(d4s6N>tptNq(Z?o*K_o1^2q--"
        "`9<}+_R@8of^}Lmz~U{pXVf3b>sUsWviXHSxKcgG%xN1z#3})F`Xp?yYzfI*Rb#Dk0oF1m89KYo9t9?@0i@gV)!PVrD%9fa+6|Tx"
        "*1yNMac^s`wwaUwTr;9{2)qsyosPa^M+)nB=SYcOG=&kL~>LXUwv1SX+ivzWLhZ<^eJNiXDD+9)9JcHMfb}ckz2sPxCMGW$x9oUp"
        "UQ`H<|mTr_5d5!<fRY->lGi;nczml!XVA)AT*G}Gp}oAnh-HB6<Jse_Tf+b9+1fY?@9P<Wi>>6{UG~O=gCKUkhztV?t{d^qh+IHo"
        ";Zgbyi}&VPYUfpMJ25*d$8)Xo+L&6pcycUuLpG$s4*gmLTzso(L)ThO=ZsaG_!3gK)!zlun3Uvp9YM=<Q8oU7Xv)0oF3Y-Gs%}-"
        "OP$ufn|$c4mJfqx<u|+}wZZ^^x|UB4-"
        "2r*q!h@n}f7YXfB88Z2TXZkq7b5JvgH(@`B&oEsZ#h>K_gR2gjcXq;l=8galPv4@{+83LIvp4JlVjhWk_^K~?<C2@2>r`vl55S$<"
        "D7P;{-K*;8~cNsn>L`d$yJb;{$kMhxtlp=O{HttVPEIm6()?9PTMh>IVMieTwRfCB<d;^OlxO8&`&b*-"
        "`SMy?)Ns!nfPZm(~{0#lDsjw<$SU8{g|_ELY!CM(<&<{^y<6%Wk(zmQ%Mx*SSrW#d-"
        "cPyqN!1x5!%^F);d{P4v9T0`RqSB$i22QTe16sc9Z&MyAkRZ2V`zEKVS`h+N_A1Z>zkQ`qanxxY7$_mE?=9_P%_yeLQ*NsTZ9rt4"
        "B|2W~+sl$dL0yD#zmQ_ohGnkjCG;sc&{&zp<5)fj^auBt7QS!q2wy6G_sN-|-|b#gxw^`L@0^Hzq{L7};hF#VZ7x*f3-"
        "oBshuU?Gp6<o<_OdxBw*gx2p^AGC)XevJ1Dj=gDTIvZN=rt8_#);{^Z~<Ny0-"
        "0g_~<KCS@lv{)hhPf|YHjYc7(Z+k!Ntrp;X)A?jGNe^zvtgc{8W>!}LOJMsyP{7RaEW_dzTqb?KT}=8{2qLN%^c?$IQ?aOw=ig4!"
        "Vs1Y7vE=M9k8E)O{COH4<(SaiNixTGFpg+;I}|U3!W|qdCON(Xe~IUyRy9KWElFH#Nsyw%!wc-*!6V$ET7)ct9V`w01i-"
        "TUsV|ab!s|(1icC*^nS8Kh@-"
        "^}ZFPQ#EfNfm&c}`*bq+?^qNrw1lL@zrG=C1+9%*gWp@$T)r8n{pYW1T)N(T{a1WQG0M)FFYp^ImZ@&Jz*soV}k=L2`GeF&<t9EK"
        "bTbfZ~(9Bj6BYI8RHs)7TfU0ap8h^RWsj&G>v1z_^S%lVqmjHOYtF{q&~`gyEgy^rFe7h$c-UK&-"
        "SeH|UDVH`d#WZiYHS7u>v5boID?aXg_@nzh0ex@13$`9g0w9};Ki$rZV3;h)tH)*U*d8S3P`mn7}1E+%<NzrQh=j-"
        "T_<Se{WFW7$?JUe^!fuFmr|Kh@=%HaqcRz8=fdX}+x42}X{ka<te>ni)7@<(*2(KrCL0OTriz$U@ke_Jx22HIx}-"
        "bDh|I=cpTQ3cJA}-fX)>l4WkQZh>6^%n<R?-1hr+F-*)dXZV7cXs!ij{}O;w|2u${`rii3BK!L{0ipq-"
        "(K+QuVvafdOv`v2n={A#cFtTu#hjbOwoi}_nd>ZaAdu8A#~Nja3tUEwIcMZNIR|t5V`e@~!^R`uHHoos&*_)U2ghhgXIXOjb&~HG"
        "3*(u#_>1Pt?w<BVR553y6A2=mO@W3d-"
        "9$YBdVwKnIZ4<Sxu7*CPW>rKCbmS9mzK|8B_9$Sg7cPkEd@qe&9MwRiJ8jAnLvq!ktFS?p5Z(lG?m}AdHc?7r2dFXcI}+mgs}2)V"
        "(VQ>b!PxFM0~v~pn3mn2mmGmnGm}S!7;1^hw5AffKu731mY(x79w8ZlOJ=M<8H43bX>Y8&fPe6n)4EmjU=7H!^tldw#a%)Gg5}o)"
        "0%0~M+V+5LwA@}-"
        "07QL+NX#ccbTRB5U{$>H0RyM@_7TWD4lZxM#NQMbQ;|5c?s%0#~{bLzb7W$t)|j%0OC8b!){|L(c<q`><|ie8&iq&`))Or$b!K$#"
        "v*@yZW6{MIp<`kO>$kc#*C7;kgWmJrxZ53&ls_UMZf<eK*bOl9BGEulx}LhXfsmVWKSbIB}mR9XG~}Q4tc6UE+}j(a7N(l$L;R7-"
        "3=vfus;?Zc||kRlId0C!VdZCivr1J4SJB%65nGaX5FzIY9fA5vUayvg(NW_+9Zb~PLtX3&^*uo8bDr9YWbnIe!rqH=<gbl&O<!KG"
        "fx1DrQ)$yI5BiU$0mP2$&p~gktAczyev!w-+C>{xAc9C^U{G1VxxzY#E7gOGK>2wg3Yu^{XBHQ%zy~)VO15xpbv-bMV<jQ{jfGeT"
        "=1}IhDhgO(+tthPqYXT`%hr}kwp24DM~{6C#ERr{YT_v46)iHvWq}c=@H=&T9QW$%Msl^qQm(FAifjkAJL9zZ5}ZlkobMXbU;IYg"
        "jer-a=Lyha*UAuQ=>6IC)miXuK=R}5z9|G9{4>8>Ys*j^l+y=TyjH3KNWF>mc-&CD*36Ze-eK`HQf^v24)7N$O5zXMVtq|zj5+w0"
        "J9AJ<s-"
        "n*`X|2uB;w*dfc9WPz~dwG3_>}CM5Glg=((RjaY4uqj07R&A9TZo!6Dvvxz4Hnl7;2W5v_Zm+c8ft*o8@X8KXduWrF_liG!1u7?Q"
        "-5vz%b?O$G<usLv-!UgIRrRa|)kAX+>54nz2U@jQcK0!a4qfZKo9Bm(T+T)b?P(6JY<*d$PQ@v2Rt?!{|1$$flalR(eK-"
        "`XSwbMbdJ30z$KkdtD3oKyG!`aJ!$O>rl0adN;IJo%m^hH})3z+Z??_!ViTK)09h!O$hi2Z`sM1b{`qf|cwCqC2i&6pX-ArvY`)<"
        "Eb+MBNESR0QBSNaoYkCa!d;4_0Shdw7^i`CxB^qKg8cd%eHU8QjxenFupKJoInH}*5_by019+@P~giXgy%JINhqBsZA0aN(o@e$G"
        "BmRFub)Up-"
        "}sT&B`rJLC%>{O9?6+sAsrtOO~4<`d9$ZYf{BNd^YK1aaR7&!M2GHZm{*9l=iB>75k^3aG0z9q^t{@9>h#(?zg`Ziz4&{iL|vd!K"
        "GvpZ)8>Wq|Hu$C5|<br3`0I!ha$>{L`n0V#g?2;dr}h2)Hh!JP*P&4J;jNLCC-"
        "h@$0XGkoqYKTN!lQVv@_T*buXWgq}ZdcJ<X}1dP~riu%N$6<#N4OKH|KQ>E$>l4_GBdiGz;BpWhdV9zBm`B9mobH~K{=+<fVpW)0"
        "jU1e`NWJiJ#v9?LU>`+6)Nn<T){lVkbpJ)y#9{Go>xf8l+=`|wLVH(q&B;1b|pGhAf&CBRV&<zFG<pNB4O-"
        "gxQ)gJg^x;InR;!AtNgDUf-"
        "?w5Tq}_bxCrjFxTU;IP9OLbK81o3;{s_Emv*0)AOw*Z^l=5g5xPZ9cvk;0ppGKy>z^z`Fro5f}_`_PoHLz_XVa-pyUTB`|mOhQQp"
        "_n*wuJuQU7*z+Vf<-F_f2H}k&0+{`-ygRakB6PTNPPhf8H9K-W0h%TMtM4KBrD=;_oqQI#9vdpoK$}d05@RA-"
        "=0LW9nATUq;vcQ=7%QDU-"
        "O#S7L8D2JLCuJB)z^C8ll;M)oGLI1t>o)@PuwE0GhovwNOI8Y`@bZ%aGMcUm%+0(jFgGK;9pGtvDKIxFD|LXI#44m@UvkuSK0d%E"
        ";I~+DBdk9K94>dD%%2CG$jO1U!ZLCYQBObnnLtocm!1}QX~3T7IS}KBPwX6fPeAquBw>$z0E7m*`a6L`J^nFokKR(EWex~D0~l3L"
        "USUWrfa9DXcZX%ll~bIQf>+K+LcU0S5pY+Iae`&=mH+)2r(z!B6HhP<<$*IXEiHBBR}9Np1BUg)?j^u-"
        "@B&>^UtIiIg$I0+iioczd%GBs)Wq4{RwC{Hh!oV@x9<rQ#%*(^x23Y22&%ONh4P;m*;2^z<jt29UJl|U4XuGftkhpU!w^t?=_v+j"
        "xPLw&kRbY1NpwT@YgGQ7_#%~Sq~D1@nQX8bVxpRwqmM70v`JR`H%|Y?W~kyh{f5mkcK%zO6DA{BP`!Wo1x_xr9dhkMP7GvLmxxJP"
        "-O)Vo{rdX~k2*t>l=H<6g+e`ZE{Xj%#V2&~3Q^sEW01-"
        "02>};+8YMy^3C=!YG9G7c$Jt|}_n#I}N$t0sQZoj~GE$xU$7y9fs!WMPa<m-"
        "KfK7T}BUUf}I$$}c{3h}Z(}IwM@2)*BARlM_HN%+6wHE~BY!ZsCp$zQ|@HuKz^Bk@I%%s?(MsK6A&mpF_86IHq&YT0>)ggUi61<c"
        "D6;h14s|*oS3Ll>2q$W;CLYVS2CuBIMf5i#*D6c%tFf-^?VbGDm!>1+z-"
        "a7v!r@Dv2{rxy>+0k;&VAM*+OgU;>Jf}%(T|CbjF^s2g&og`=%?O{knU)WDAa0vtEOK*>=?d0X)Ab}-"
        "f~`Z{*6<KiJW)n_hUbK1sqM`Y)g?95wkO5kL87Zh-e*V%4p3fr=hzDZ9?(NR?Zi%c9x0CP;Cy%6h%aQbSxU-`T_+saZnxdj>22-"
        "jnbUxy;ea{j3Qf2j5{ZBNdjN729gQSnjON!~=nNP?7rsG4L>Jmz3YgAt)CsVO^tU^~vYsSwr_PmY%JB3>$r)HUl;hy-"
        "&Y~Rh{3|Be8FV<T^hdxnr2qJofew2Y7RD_c(b8w0;k>B#xJf+55|-Gc-EBoN8hiF_PQ(#N_F1CRcGT@+vHlgHa`Rchdd!{x5iu_)"
        "EChb)*PJxg!^zJ$sn)~EmpNq(*wa86@1wYm2Ug07J~16o+U5<+qEQCnxF1D5rC~;Ul52>VS0GMk1|yEmyw7n$=S?cDZA8xJ3<FP?"
        "Hk$)CE`0(}&v{~|M#_LD$byFL`;CALYIL_pN(R>fFA4pVP--7ECi_LK^e?z44CWV|MU?{QsHt$1giAq}8aV}uLlf+{0(c;26|Ruv"
        "4GjnU1~4m;Q?Ce!D92TRdMoABStQUcEq5ron`AEYI!-x<3)<g{fQ80Maf3N-"
        "Tzvz8#y&0s<|7fWFeEs+O6r6!bzFTN0KZAgk<m*?;=}Qm0CB~$3~5CSLc=5|0mcLIJgu<A(QWd8O$_?@mCqZ;j%xyL$ua!`kf<Z%"
        "5abyEl1HQwY6t<tG?b2s^kwhitbhYv|M!s)V!rYRz`W&pT_6c{YJ!IKSAhG~BH&fnpThlqF+FiuonY)mkn?EJC>dQnYr@4x0g%;X"
        "Fl58y)HzP5Z>2Eb+_~}@QU~n7N#g1asvD<(R3)(sn1pVReF#vw_yxep=vWGZ0wJXTgCt`p0gP*aV)*<|k_Qn!-"
        "lELA0CaeGI6f~w78mGd63*U-$$@%9Y76pPomL8i<QAATX)PCs7`Wu?q#_p<IvkMu-yb}Mgu?uxs|i$5a;4?6<;j>?c#PqN#|Z55j"
        "?U}91*j#S1U&2k;ja*07J3m8!+*z63|YJiI1cPNeM-"
        "O{J@c}Fe8Y*zXrYhe2x8n3Z!N?@3%>KWUnvYKeflL$5S4!WrNU)=IID>Y60d8bhQx0q;dA|$HNkaWkpw*PZ@*TUKfJ05uK%VaO8n"
        "(DNtC&pH#EV;-jYO>6K`{ZiRcMnHkNq8vm^-"
        "?jHo1Id2v?H_b<*e&yyrwR2lU@t^<}k3Lh!h7FD*$=F(M?_=_fDOBAiqo9|G7l{jjNd?FfWC4qYfi!5Dm)nHMGhV%CCHv>@?(u)I"
        "&tO^xklj-UehE?bsGYL@h)hBI=XLFpB(j8lBNO6N#X&Dxk+Q_V0T+{=Ni;L#=#3E^7mUhHHi=udG=@+|t(P5Eqm0W!h5Q4E+F^le"
        "FfY4r#@rsf51Xrg8)BvR<fsv~x8QSlF`)yTW<ukyFA!S<rMSBHqQAGe+Q?~y|KyLauff*Gf85W0p?__Z(XuQOrgjT-"
        "*tUB>kz}+1zMK7L3!icRaUm_JJvp6AX5lNqM!fhlD_ji+vC7d=HOlZTno7^0slrx0`VLY^`kfl4IIOWum8mF|3O9A;^eci%Y3c3r"
        "zu}i^nr#sY39;Cn7uKZ6fB6jM_0_w)(NlCHgLc(Q9_MncFLAs=5O$)q4RyLmqecdM10^~FaBp$~_B*;?Xt#PtPmXy#?Xx|_-"
        "_KYMCnj~sPYIJ-9czMWX(8)g`5$$u2OrN+Sd8soKC$1t>>Ew05W+#nSamg?}P-"
        "E^e^Yn~eMD(z9NJAq}JcUGmiDR}f<2%N1A>4FYdU2$q*2(Vxg5ik-I&7N!uj_zVuY60q-"
        "&t7D#p)<3XtEt+hmZ>Dbo6RVhyG6l@Uxr{*94t*dJAkmUwRV>zJ_w+IH92<%HcbrnvPl@*BE4hgR3-"
        "vyK?sjw^fjYpijO+JAU^EfY2N_PJarp4~OZ$V;()d7boY;Q0-|XWH=|^R#;-4m)=5BV%6NFOyC+rEjd>31t-"
        "Eqv8%8j#zt1^E7|Z%P*Im(<)pgemx%#85fd^-"
        "t_IMD0Cm~l0L*Hi=&s{dQzrhFNULLL;cLLj{0Ib#o%vi~W##LVVmAI*VQ9=VA4%eXsXo-JLmhJ+2&*I4cK-"
        "7ffNXovXdhFKx(*Q3LLEM)gh5pJn5@YEMa%G*nHR~A$IPg|0W3Fz{*%PvW7-"
        "8#*FL=k^o4>j=E!o{XKvqo3K$)tfObe$@V>>EcPG9h`rRi{EL!1xBJ_#e_L)%t)=|7fLZ~~V?D_^^0bc-"
        "!AJqX%)2O@VpdJZhRvEau(Vb;uoCH%>J!?W+*F+P)0G#-(A0tV;($lL8U2_%bPk`l=-(>-"
        "L5AN3jv*{%tSOGl^h&Ot^y#`Q(;0prI>%}657qHal&q+!WZ%Kkl60!%0E}A`|ZS{G+pG!jI_=S%o#pexA@B~?7a}9%`*Ezx3>bC;"
        "2cK9s|`R=^p?peUHi}ltY0n53L!wORV9tQWZUv@^|L6_0-yh$NQev!<&u5q=#2CS6vCBr->T$<{(5VS)3OfJB5y9J4J{u6+@U-"
        "qWLv2LDq+i_bx#Y>zT4K#@%wdD*O#?Ph@(Cv!!7o4=Bhp|R^>KN;u5N<9zxg4#+r6c6o7TDW<Ml#b{;^pzof!-anx!UkR&vV-"
        "R0l6uQww>R~m*EmIj}2LH@kPD0)D`=VCn~D^B7@ex<B1FsNDPz93~Pw;8<SxB?g^V>hwCX$N_RprloAShi4%jwR(V=7RH(fosc^r"
        "zZZcY=HG_GRG9-"
        "n|RY<9Uf+e((Bp`mlxdPW!xdJX(G<Dg`z6#ESC1Tc);E`E7z*zDNSCN?S@_roIuU(Ns;FGT2ujwlD^73*Zh{Fg71$9mP7r<p*32n"
        "Rzfuc9Kz6X+)qY>M4&;8yc@MFLxL(D8Jf|{<U1T=``By;RD4DENo{kE!_u2}F$h13TO%g{0XNI3c&ml?Yfc0I{U-"
        "~RekJ}d|Q0h7eJFC`;g3OJ9VekxFU&B?QIQXZ2;3@$#+ut@s17}niiP<pb%40#+KlpTbVuX18u51n<RUjW~y8Pfe<O)cnFaF;uq6"
        "oBp1iy&1sqL~fjWJw`}W04`uiLqH;42grx$DmhYS?JSXmO-G>3BuSYEAWlI@z!<7*tiP65}4HzB<5iMya?5Sw)UFBEbG86=G-5-"
        "T$sjs{1N`W$e=hD7{t)wIhGbiP*|w}k{T*iU%=WWE(b*KFjjAbTM(LlO2AO>b#^s$hkfzxC~h0UdzzCbeut5{p2cMm8tPd{YFQ(9"
        "Cy8ssp8WPhKoZJ$l0kfb^Bn<0J|H2fz8>nf)R`oV?7n0&3|XEx86w9oAW4c0<9&q;>t)>sx^ejm63|9O@yjN{PQrXS3<je(Y}+G4"
        "WN<I55F%-@jDz+!j-y{(AED`72iVp_bOf0*Fa*k~UHd&J>?WU$3cslEylyaaqOI{_NkE`oMz`G-"
        "@9+EuAn$F%En4pNlS`4yQCq@@r!hFgc_hVTj|(LX{Q~WSA)oW%Ghxd(QwuzdKtzo9(-"
        "^`ifqVK6!e1Dc_XYSC5hV`Tn|Hm`t=wN}M*1lFbI6suu~J2DiArNzr7^y{)=M9GCqC-"
        "g1CbvhVfGYhU3<Yi#|`jwPS2dSI}TWngGuvpAnFuDaw3X5vZtRk1;l(WrOXj1P7Qhc{`KD}%pQi58t7Ha-aH&=+`sJ2yY~ir$<{X"
        "~b(`!d2IWxTNx*uT`2=9yXnaOtv(qT`WoPY4fS_d30zE^?wA`{2icy4WO}`3QU7_>mB@yd+)m|7lr&oKS34wA?HoE#A67adv!evf"
        "qd{oMrkmqreFc&_1%0eWwdm1I<8WP9)14H{AaKBr`31Ml@z)9!`t^*$Gb<&<%8URgj1B7Ry6<D+-"
        "QB>DRaQ8ZTuD!>{md||25N}U?0q}tNEan3V?4I#ZK;-I)@NkSPz-5F}F8~bn>SixxrM{sVX`AwQoV!1%q2``+;97i|Ge{-"
        "O#nGNoO&<du+FX(OxSrZGLLawIdn(327)E@Y0}Q$K0R!UPo>Ex6TkaJ}<KWti1A$wbPdJ|W)TDU3_7hGC_McT)YS|Rm`r4$p7U;Z"
        "hFC+sDx?OoWOVb>ry!I6zv+8Md;-"
        "rvhKk8~o<YlB{y{}48YZU4|R7!;Q!fH=<o3&IZ=P2}BtW*HuWOl88qcAF+|453NSlC;VOszJT*EPAOaHv;Rd%P8o3!wz*0N>?AXm"
        "5n}j97;t8Q?;Uvyhw~$B>f669R^MtFvcLM@qtN#KHDpzaBflwOCHENW*Q{o}5iMeOy40$F-+rgi-"
        "}pT>+;q#A*ij>=Y21xAj{I9&kHlzcYK5f~TJrkUKqLK7@Lw6>#eAt7b^2r=0Zur2bH%)1L#>L#q%@L-"
        "9knMEVpVbCjDWXH7qFa*d_T3!Tc8vRHB`V~{wmEc^@q4S93v_$!={;4Bov0iz93>%eC9?t%RS`hcCx)gH3PNDk=EfqvpBw!$_h_%"
        ">21;LbnE3GuPDAX}&wHfEz{C`+7wiWBDRb^WU6%)XT5L1iDz?4VIh?@J=q>lF;!%ND(ZJ=H#B<wWKjQe@((9|5+fk@T7jjv+-"
        "FT>TgzlqHFj$T^f0nY%H+2FwEg@@D|;V~P=Wzc~g%+98qy@!yl0jTWSri{AhiEk}r!XyTtS3KN<ABVaUliRd`enE1u(fS2V?a+Dk"
        "%ii{%p0<d=RHN$!|=;EJ{l1S_^{=#jOn2Pik&#wUTh3CJX0%$Hgf5Qo$%O?yb4@5>r@{<@ep4_JZLq7R)@pHh*^O5YpoV*M`hl@e"
        "6Q+4GnhS>Bz{;|Rw5!MuT7OpZxv;P*;Bu0>sF-"
        "8^3@gR&TwrBlcMT(F51F^bagXYY2Ypj`^QaDXMR%96WI>X5$my!tB14U;NOa&xoC2u@S9N4!n?LmOj7(Wrnh*J3=6n*U@Nr>WMc&"
        "OK~`%G_ybHZT@>-z%+I|wGPV{n<nQ^$VKiM}5A#gEa2eDL@fiJiVu7O{Gt&-|TW03q44faFXYKZDX=l0$H>k-"
        "^hP(PQ{KY%Mwaw0*8gxWzqhK3#~-3rX-"
        "+#&eS5&0P6}HD4=$ULm;rz9i@MNGxFe@}8vHk)C(q1UoYqB*ClsM}e1na`zmtVDs`tNevI8fy>0|{bel!7EuL`i5qf#7w`xtioV6"
        "DV!fB%=d+Mkft6UoFP{PwO^UndM$<FYvbDli5~2B2GW4WbQqLFyl5j#gpKFe2ldIP?sWF_(l2jf1HBx$P_m2t>^s;?FW)n*q(C87"
        "jooY%>6+X}4LeLfJ{hcILIz0QLB+0P_dp-LSC;NJN9w58dl5ht`jxe(lDAQOOPXh*7k=*T%dM(jMl-RE%N`3E7cAfT{6(W+@Z>IV"
        "LvEY8wAW`!E5gr=B<-mcyGlv{)<Q1eiez8FzS%q^*k$A=x|JdvukXSG_*^2;8Wc*D^n7sqSRjeBYWZmec#*<(D<qw<?-"
        "|;NqHt)^hf^h8YAbf<R#Ne(7$ddF$fjMS=L15W5;6k!h@F##GCtnnhSM|bmNzCg#{5aV+ct=uVOA0I>-"
        "j;;yAzYP&>>+$03Eo4v@U$d!58-1;$sWS{k`TKTu)!72ci3T)_(b8Jy0`dd_7Q#sSoaYyHr+=!svza>Wl;7Jo)uX45uP(C-"
        "bZ+WQpN>-"
        "9k9B<uQDwA2&VwUz(o7(hLK#0bsynVfL*g)0F0Ymg|`%rZ9*b<7;wlQJl;<LsC$~fk(Alf)Q<zbYEPWY_d<RPa8V9L$2NNX6%x*i"
        "1+lUO$p{l`#0#gfhN^MdKenN2tQ(?Bf8`Pp1T-iz<tx1CW|(b__cb%UufZKT*=#0rkH}2#Y#euT-R+8JHGgb(<CJEncQD@4-"
        "1HU(Hvw+>Ge`$JoX!C!5=5~Hzhewt4bGxcm*cVERU2UcgGrbGJ2KR5y@rJ_vGLzBEbV>`SYzXt0IOAVf?<(O?=!6NX>Q2Ir@@+BB"
        "PReGa2H=jB5@_LEGFg*<k+b37f7g_dj_z1cp>JH@LmR_=<5o{CSilSz=p-=X(Z%~<>vy1`b0%+&Rc#au=@Fzz-pte3EGm*h@qv9l"
        "K>eQX-70anAdU8GO^Q%X9EU&S@i11fJFa%#-MQOyMR@deg!zxmjwoff6oDyYqW0x6n*vygVNp?468o7f<%JVmylF-"
        "^bKGzJyEsUb$VLBc|Ai5n9T|@9tI}l^%`K~SzM4rtPj`?l8_gtz}eqk0)%@p(*SUu1T`_TFgefriX?j$ew<_2n3!_>?-"
        "@)^i6MfH3BUd!V7=UNieW$}0VSUM`<fiHHU~?%HbBHZkT)*=`jmpS?0<by;R6O<)+Y-H(y-"
        "xGPK5e$fpzx<=FN(?1>|LVhhaYM^p=2}eU4!XE}mf6FwS{SnFCB@%?zA<@d4iA7{}o<8SQ+r@FOIW1Ey%nK?T{zY{oFmyWUqBVtV"
        "^PK;EYOfcG2*(ZZ0i`Yd2-@NWLg*O!h9C{_}P%7_4T*$?DJqu1Xt2|bS_Y2ytH_6sxMO%R6Jt9VKJ)~k|u!-"
        "HY|_OgD{0Lk+Thx%FwCz3}+Oj4o~`n|7@h}eh=-"
        "VNbI^1z5mN=5!Y(nn1O?h7ZJSkSwZl(3*<oD7WE0%@j*J+&OT3%a0>lbCy<3NGj!(ZMhdIKpA?>RwMW#hE$F8PGY{9a1bk$&f^m7"
        "}PV0UvVPThfV;>higx93Y!>6J;5oKIM>by%ymvPtTcP|8%`OT{hU)KJY^Ds&J#&;e=;UY%bu;aE9w17r|KR)BMG^@b5;|)r2`_8@"
        "D@wlQOj{XK9dZ`_4rD1Gyo<E$MyI^bJX?tM3aturKBTL?K3We5o^xZK?S3}M+?EY=;Ofd9~mkV^bte)z>AHxF{q34wIp<+uW>5W*"
        "IxkYQXS{il6dOpPH9Riy~?Tor@MD;lHAG?!~RNDE}fB>LKhSHE+oMe$tGvWA=zBM=22T5qBBudAhUrafb6dB%A8P0mSuToL*WRA6"
        ";iC_4-Uz*u?|}smi*9$q!0Q5vVMvGg3mekeQ|-x>TYVRjTv?!@wkt3&pq#Zj__X+Og3UsX-zh4QGds-sda+&hA--0{%!iDQqkzU;"
        "_s`UKd8~GW&Bg^_YbNYzKs7h`@shK-|-"
        ")`jJPv|IqM(ewO~5`oc$<xF4a<*v*=gGISc~+1<SGk6c)D66%GG)|2_VIUHl&aWa8*K@Z(A_;eUqLoZbFUc#VV)z{K6em|&(#)=a"
        "nk9UxxC85GDM6{f`*@tio7l_RI(Idc9len~kU{=<LEe?1k~>GFFcPXOIfya#^rBL@Efe|#@962P_o79B(R_kcW=sy)F)o`3(3_~m"
        "1M)Rz4qsQv!0_)m(<`xp2_hB#Jv5_2zAMY=8)4S*|lzWR6n2mRn4+P|V7j1l}ZcFk-hfB8@FR~d5|ppv>eLI@PZgeNW1&z}D)^-"
        "~->|99$^IC1`W&07rl{-wG}yZz7AZ+Rm9|F-V2FIlH-&HvH=LO&AKf?&G8|JU?WFl^Qo0rr3XGrF$W^nU->_-m8AV0m-"
        "?A<j_ngMUERh-Lp3UNQLvu}p+8fCN=NOGzTa`~=mr{5pwOhTH3(%G;)T1FO5`dkC;=%awFM>#Z>G{%gEun+e}w$&dcyKc!2S{0Nq"
        "Q%Z<H%jhFZwfV~w5-"
        "Toe4b7Svc;WZbGLG0g3Meg6?54KT&`fY^;7XY^9hubiH^;WnO@pTbp1jJ`6&y)SR_`w2D*iU}U>L20{9)AJ5Y|D+de~FiCcH(Wz^"
        "CSK5c**e-=*d>5DIy>kX^JrK5ztcOL>P^AW1R=1L2pzprY*DT{5^Jc&2krQCC{e&ykk-VVH0oV`LX{&{9yBBKlwbdZJzb$f5S^YW"
        "rU@`Dd3%35!doB@S0~s`U|{f%Fe%HmzO-"
        "d!&V$9!(lM%EfA8eI!*>y_>`j(K;$XQbM%+LXP0zD1sazg6ud8Tvi$Qu#~+0uuE1{|4T}-"
        "5@GHxav|aI2S8ziLGI*Ub<0@Y2#<iy$UD#Vp+5aoL76Sd>VZRKyf@DYiE|V_QZJm47?lK-GZgZ-Rv>Sh!Gzs&+Yj*{rV7kPoWW&b"
        "i!e;^`fgOlN>pxsEg8bk7HT_`J>!08?kK+H+{}q3*2>KmeR_ucBGVFtI1{#L&B{Co3Q{m-f-"
        "n*w_FW@3;mdvLjatm7%xb>%aEd@aa2qg@P-$JHPzY`6fFVd?QER_$;=^58(0WF>-"
        "D>m=H_#f#9S^qF^5nU4y{xSYYnOXn81bOHgpD^I?GcgT-;4}HW;3>79VfN)~@k7i8q>&qy<K;%n@N%Q_yWEIVm>@0Q@cv-"
        "5H#`yo6T#nb(uEO#H+XsvsKE_)`C$h68!mrg=-"
        ">?t1H#zA8y+A5%Y37ykhu{v`3t&M$z*PF!BKFu+%k(f=WoR6PT<2gVsd|m*IKTb8$Dypji3auxHl?y%#EHo=DA=K|AwxS^aGWB&K"
        "K<e#7n#fDDj+*fCI08&fx>&cuvPI{v*g6&&7N|Dtj(Q2XyQ?V<&V)GzSRl3t>b7sJ;+V*}uhW+%nMT3l=I0(0h@H+7`dZA0%Hvzc"
        "2U@@Lgi3{}0}j2Vnm`VD<|!Am9!!#DHLGFP`BUslWYac$LxR?>c)wOQPF;I2n(JL#%He&W4kbj}@h7gJ6cW+QU(wiqXRjs!BhEi("
        "wy&+T$I3cZ?Tfto9yG1AH=t8za1!g~Ks^bA~t0{9x1%heK#}Gzf>Y0RG~q!2~WQcrk?w{B{7}j%Ij)@8HJ+cxOywf;-"
        "~?FQDD=Ae;{IFN|q4!;2Ag2=f?YyJKi&Jb@0O<1vhcUN{Sf)5%^HanF-p;@!%Ejg-uIne^W5_7>rJ{NTkq4}N`dviqa+n_pg>|H&"
        "$TaQV)I5AepHtWLc7n^%4ky^U2PJAc$+g)L#Lyi@hCs<c*zlieJ6q6(+z9lORV+HXhW@!)LI?Iu{QayT09cFEg85RBkIUQDv{|Ng"
        "sw(-Gf0OGCcV!?N+-"
        "Vv%_JUgwuMo@%%2+|b1W%_W$pw3nQg>l9`<^!#Arg|+(wsu1moB9m|Q3MxiV&jSAe%nW+iYo+K@Dn+ls(5QRwEGJKI$a3-"
        "x#pUTGUR>TTG>?yy>Px)an+0cs?)Ka$DtfWdLF}%GinU64kzMveE=D*9fxb5{u=eZRGiy=963KGN6VK=0)2rsAxl#NRhMR+sBjA{"
        "e+OfQzvZ}jW#Lv3j9{=|9_?i8s4p7;M#4A}<eh;mNRl=*)V+U6PT-wUTi9o>rL~G`%>islNS4Y}%@~Wn+fNZ~3qgt=yYJbWrsne&"
        "yV0f=@feH<#{k}J6C2ac)2aFQGb5(~H(T%T5y*#paK?CRyM%`l3t9H?t%Ex-"
        ")0H%hwQra+ng~es7UEqbRF8gFS8`TimdyJJj_Qs+_Vp%kl>+40p??#z<3(6IqZy+y_NV=t#XgJlds1#Uq+zYT&dB6Kx9o+;ayrqu"
        "AY9A$h>zUh;;5{5nr+t7yaWVJ!-"
        "qMG1V$ZEo8%bZw{%m$O^^g0KiW&I7T*qa3v`lV^_7(H$`6iifC>QO#T;`kPeb8HqIY_r@j0wx31E98LlqJuOK8ZIB&czl}ZsS5m1"
        "HbTYLBcOjS%XpH(=Ti{s(kSTnvaV8lImo<cMVF*7uc7^eXxC;lWNIlEqVKRwfZ_P9u@Cmx;Wa^g`au1h+y<Od;V$sgl+i(Hb1{jU"
        "#JK0l|LDEvu;=G=5&<+OfaYPV+@P<noqn}iH@~~`C_sU!)za6JG7uVyQFo@yIsJB!K|AT6g;tYZf&53=|0N+I7)GWpu>6G?G9j<z"
        "@Of6<|;=Ybd%kVHC}YP6L=Nw4d@H_QFvarn@Ku68skRGkpsfmy7*GS{(*0Ecn#E0whpxB;sfj*2njYl4hHyvYb>swPVEUIR`w8ZF"
        "p8X`!G3=omlDbf0cc5T4Zyqb&fd9}=4#|@HT*Pkx5PnwobGmmF8tFA1pYJtBFyWvrj_j`F!=$Z(F9Alr~GfR+vO%i2;1atP*?|0S"
        "e)umKxiKK2Koz46Y$v5>2SwY(t1f*TdBuax^0gB(D-"
        "x;NOZs$^dXGTh?+Y=E>?eE>pk&LPfsgOI2755ZgCu8LcwEC%CI8$NEPbal?WmxdI$2Ct&B&UqJEq&DG&o|h2tQ#eg)2`F2jWHVw4"
        "2D>bl6E5iR;y$OS&JKV%9pG#qwv%0}ny6&qNa6yk{F0wQ*d&UvRb(g&+1MVHJZR*2pKh%SD{$@Nx}Yfh<)<g$z&J^n6PR=nk2wq3"
        "8i`KCyp!mkfkm@wrMwCP65?WEeAQdhX)KC_!*U-3;>>nAKUa+pQ4e!pAI5uq~JYuPS>OC@U-"
        "gh@aesaMzvj?MthdOg6;+&hl&Z|1=UgI$LWnG{@ZhY6?venEK0C)CjNBHv|U<~gVNd4ia5%eT#Cd7fM>7SZ{IuirV{Y|HDO8!x?m"
        "TJQ8>atUJK$|iUX<J;}t&GU5<XFY>vw6^Q*pT_HS1y5a5DgpPAJFyi=j#54VoR5d{3;k;Ez?5ZtiUTTqCjSa<C;)WcznJU0sqrgc"
        "JUIbLImxc7Yx@=XVDFD$fr){*fMx);j-"
        "Y~<@IAFjZkaSS=Tv?Ux2s1P2}%*}ra3KX#AWjN<vIpAs6VIS!e1O^6wKKu;kTwm^yfe_;9pH_<<H*}Z|gb)|Mf9zP^l5YToXh)ow"
        "*cJ<#lrP{>>&LalSv-1WFvi4Q`5Lg%pJmfiIFu-ZkVpd;lOxukdgfcDqU#rNH8>IMXD?mmeY($Mp7Pbi0z*;rYeBCKcZ91#Kq~3-"
        "ZDtE#yK3l3aAUqff!mE<l=9LaedS1c<#9f3f%DfcMT8Fk!>H&Dq)tLM29nl)vyuX`zJ%bv99S{FZT`Tf#}zD6Wq{P<5BB=bjjo_Q"
        "l$MnO*Pq^W%zBG7a~--"
        "J*xw(Yno<td6ATYgC<7_e{%S8<{S%i+!>#lcRbUy+iw8Y(;1ixClpz(#fR|d)OMveSk(yTO8ckerh${2wk9CX?guAAdq0ru*mw#p"
        "HdiV>D_WxA6480A{M_`6sKCxYKPBBD2Pz&r#7PVN`YL*PSF$acG5H9uZ2?P_{HD}g^C4xr!d|r#5+2QNupsuLL)i*y|D%P#uQ@``"
        "_%CY8c<07W)$Pg{Cy%JrR0$|NkLf#>1=~uCHB^>L7-"
        "4ICh4K#WLnCtoV8DpwO68Tep`u=iqR;<VnU)$R|H=9{KLH_qkVY!adLyzI+&Paqsp2+^z_BmB|Q9SZ{Khzx4!lwXJU5ucXp1=ZAE"
        "js7|JjmsILzkK+v!}a+w2fQIg$@ja{AQ8J6Y-"
        "7y(LXzoK`FB7P2X0sYmVc$$?_o2tAC8k(Q`sUM3zOD^3P{!?UV!1`ga*$#w0IkJL2%=kj;mtt!{D;K!-"
        "Y!A_1iej{RkPL=$xIQk_-"
        "1K4k_(M=VdF_}NqkxCaO3W#SIdPt%PbTJ*$^4im14_P_41BIlCZ@@xax$@)3=Kw1MbPFwDzN$KlYF&Z<JK*9(Gb<{t9AZ3UVlzQW"
        "w%HDvk5*)snppDP3FsrJqm;ro)YgTOwB<rt|18*kC@SFIJOOn-"
        "R=;LjFrO%coLxOPIf)|=Ls{#qV%SV$=<$~iou`}#JL%nO|nG!dl_}gWsz>G4zlb)ml1Th%K*~x%Sc~5B=`x=ZaCOgo}}sL7tBf{&"
        "BZh^C0s~rjT$LR3;-nawT!LUbH-e<ikUTY=+)b^4wN`yG|xZ05?o1XfdCJGwku%E!2fk&J-"
        "<9kYjoC&Pfbh8ZkH;0IYY`o%)bFDgUKM6PF@N!j3pMnl1{_i*T9wfN(KmHgk5Pg1S`qmg$wyPT)~_H2^rx76h*s9a!LZXrIPE~e~"
        "qf2QG1B{FY|RU_V(tYF8va=`eDm?DeO{A7zbPj8Q8V7;#PX9$tR35c0Mcc2;>tCw#BXYCEi^6kMq^@u#}2YpUFOf;Pm~ypW2hrEY"
        "uRuZb>npm(TEoTQ3+6tmW-?xj})c0w@^Ra=*_-7Xy--D)1$(DhGkLH(f7)Ju#r;pg*3B!mNgr%5YNa_EdGjwS|T2t@_yJwf&zXmL"
        "niil5G8${XzPIxbqc%-N#X)ACp7NF^|~<Fd|H&ys{TQK;w-`>gMFgnA3;oP3A51&#;B(Rttgg`k;T-"
        "?~lVeQOb}mr%}Oo5_?WqkG9Zc9(42Fu1CYPR(jDi>cG#ua54?1qfrppANA7cnZCZj+u2NWw5zAl2Z{Nx5C5YFpBoS8Hg2nsJ4{R*"
        ">=pQ5#0_e?|HH$!_-x_o+M2<6dO_p&IP^gNyo@mzHjN${1E?*I|CvA%A-"
        "WgnTWXMBJG|WvVt0KDGwJvtd*>lFK|2yt!pk3Fx`&bOTaasb1|shyWTd+CxQ~IX5?|3|rqi?GfWxbCtOodif&GTH=J}7P4MeRV@O"
        "(+|k8O&eoVxw7&*ugck0t#UqJ%N~ch+lT=3J17eZj(jUBng0B#*av9O0K-"
        "dKQ#XE{6%=6hX$e1ans^=qL^bh`~4bQn)c4Xtvwkhx^Amqbre}tpy~hr|rD+aatusyvAsQHMgaMU;?0}WvcBYK5qYBL)-"
        "1N)j;<<%2<r~nCqMh!PxV+a>>KqUGH0aZ5ypog5-"
        "~y5dDiyvLy2wCL6;{qHDFt+dZ&545*lnrf2<8Fs`8&L&IR^?fI2_)$_m7QFPIJc^n1e&M^!@mYo7pydT51tD?7)X6GM5Y^gUs9SD"
        "#g*Z{!Qc+;grV?P@G;gstzHZd^RL>oIAw6UYXD3}hX@Z}el1TzCE%<2Lb!|`G;alAR3!JAL5H?7z1U~QLjpODjyOLX0?i=~0+*f4"
        "eE2^_AHCCF7B_Wg(FgYnqdf)_w$h@dP@vWA9=RWnKVOR*P#0V|rP5xP>6IAcRCk+5+w$X?P(tE6O0Iwqs2fi)H32Qe3Snn;b8O9G"
        "E71d8PjQl&=ngOD+?QE1#nFFt&tF~%C%$UunoF8HPgg5cfF8)HVBK2>^@j#`{Wd@L|97LRK<07M70Zl)^T-"
        "Dz|#JG?loLwYQPs*oeVhlWT37%JX^jWeB!x8C8(r8hqqbMweFV7wfsXN%QQ`U}H`JvVc4dyXKha-WDb)_K3$6tUP8xqDMI@O{Vj5"
        "YT|V;ZnO);7d(OSk!e1gUFN9Rq9T%b<5~u?7X{F1U?u^ov^Kd#NgO-Y6Sd)=jwyLr&C}N2dM@J6j;2%$$2f-"
        "Qgm&|H%z2Sb=}>eu5)p!P%8UiFzRE}fr}dC(R*rOGaOg@@^aJ>oYO#_?^DcE0^J*=7WEr|-99<homPI()uRw+V>VJ-jS)7~$NJLV"
        "0`(znpVow2K{ftDVOv_{7`Msl+Db~nhRjbG3})Y8oX$@0E!ZX3YDLeN7t|S}J4>NFWiSec8Swh&;vU`cm)<;>)pT|cGrv~v;ad{m"
        "PlOdC7W;<~V6Lg*+O8k^orKFyI{OjW&9}M(%Ns~rCegcrs>Pm*7Q--"
        "7PJH&dkifrvX6#5*l|>u;g=_l-%{*>Bi`&(E6k$Y|W>VXV0Ke(Lz0JH^GC@_Ez<xGRO3GaZ3MuM<D!^<`#y(phZx25cBSL-Fl<f}"
        "MZp>H=UsP1R59<_PZK;l5zL)ei({SbNPLcvzpi3elU6X7o0#R^8hPzpi)z1_n+mn)wV05wIKVK#~S~Ds|k`E4eSl=oN*s!~dk3FY"
        "gCb-(A2B!-1>%>^Tu*9-T0I<@>Y`jH=>ExFv#;DDfY5<(REC3~VdOeDvt-QDUyB$W0!3E5U-"
        "GTWjjS1AlxdZG)R4nR&NC7vo`wV!X+|r+I)b}^+auv~TsOh7O*VJwkm$LQhnlO5WjONmO2`KN%ldWDZdK+o*aj~35Z#J0@heNxwg"
        "~<vgQ!m^^ugr9atp!667ZIwAyA224-oLUD+6!R-"
        "3#0$uDmo6V*8sed>~Dz3LrbG+5R4~Lvv>x&G3usbcUcn?3w61;dx}rv;?60KXo}(8jnVqv*&GNe4Im>$<A_)<w*e3ec(KmY2kJFI"
        "^Jy?1bbov4ZKCgtjxrLjc$2p(FkIVOn~2Nn1gfoJ*37tcHo&2Vaq~0SBB=kXP#JVvY<0vN+S8nLw~Ik2S6&-"
        "3Lx95DQ!F_;XGWu1EIE2NT=?PL;>J)N=`aJKV9|-"
        "6#c9<EJNaeD^FM)}H!w0q4NGAn%^cQI2kBi#HwNi#A)X)P#Uq`5(h159%YOu<lYAQ>q2TyH_C)I0HkD4AIVWIY2~4P&m%RFfKGYc"
        "}pMg0qnuv|MD>TO=g219r&xVs=JZ@IQaI#o7po3fda|>CBRsaax65&Rd2-"
        "$0D%5ryUhPk>n2vTJ;0Gpbd)SFo!*o<6=>w7JPwhZtX;ZN*&i6_009k1EyTsL#&!OL-FU1E!^Aq$OrJe|3OA1S@GNIQH?I(+=ETr"
        "hXR<zfB{VD5>HqA`O_*$9j2>@|vbFD=s@y!`egxnL%orLIYWMicb^0Fz`3$nioPwGtE7+!b#5Z02!4Mw1=g<+IRCeaaSiv=%;o-"
        "Oo9mc#F0vguO?mSJc<-;<GaprUMN;0{{#)TO$W8o&ajOHm|kjTOV-|V&LDt0ZIyxkFwc0@dfF1@4=$GB=+^5-"
        "1@a$rg<Nl8`V&5g$2zpWe6sjhaRB2vI+Opu5}@x=N3~0`X{Zr-"
        "20etQw?j6QUuo=bju`f?0de!9GK?ecrE;u8>dm(y+g0{r9P`+%~@aRyRWLseu*I-"
        "hikIq@k>rbH?6Y+f0|FC**vaW+Q_ewGo6M_=pzb#L9>GH-"
        "W$$v<Rt0_ctS^eHaR;GEbpSFR2RJB$H`iUiAMUzXH77{!(~SIvo=G<j|`;10i=Uq@g5d8&$h{d;FwNdhg9IywI?W>@+}xcdyJO(I"
        "_X|A53@m{r)FHDvPdfu5A7B_Hb62cGETb2F+%_756T=VwJAf527NmmjM292*W^s4-"
        "p(eV?@EcbS#zCDP0<?&xN~g7fs)EOq)G{?Hi_W97-{}G-XhhfGg?9(u*@>Kzw|;vQF7l)Y(*wiSFLJGn>K)Sz7^w5<#_k&-"
        "EOO4?QGUMg)fWey4;2*!azy7j<eM|DL|ZsFXDCj0<O2sa@@<C>P)-"
        "IS>UoFy|iSfSziaR1pRjDF0FJ<n^R=k9pW7>U;mZ3YdaNrm^|KIT_r^et8KGYYnJ2jR5N)`2HN;1`h%gT`}Wm?Znc==i?!pa3!q%"
        "nndU6gzM7uZY~?PJBIC7nl3e<A`c(4}ZD|V$<K5cZO50t{GviOr20(A7K?}7Qaa+$e`bZ$!z-"
        "Q50Ho7VI^cp0|gFHSd(3GveW^R?Ovcqjjw_c)c$8f)ZO6eeiKwr1IvW;)q?w2jJwznXx`6RwKMr9x<kmwE_3RMWFV(GacuSwlpuV"
        "_&dN-I=V7pCti3>!O9PDVeReGp@Q|7KGpWeMMEn>~>?!-"
        "Dv;Y~NbK7#48}i@5b}zvCh1OAr!#TZmyNQY)rLWpgh(@4V4DDK2!g>TrU`)Uzl%ePdqn=TU$QhYRM{n7}4FUgLRu5RQ%$*HL}iwA"
        "K<VEDzM$3x!*_K^)J07BT6Ri(L@?808v___rh-Zfe`?0a^;6&yv@)_YLpxy>?)LJ5az>N{b{sZph;44ENzJ#=1Z_z{3!>mz|o2R("
        "?k5GIVPyZ(<uguB7dAdFUqh_1(=|Y6_g)inv)MFDztsgAz#H%M4xplHOc<{%|szjJm%CB<l%(V1)TyfHGZSbLa~qW1t?lNAxQo3R"
        "bhQ`-"
        "hS_+pm6qfJpp$p15TX?IfLHh0N$cn%4cmFRZ}gf(Dwmn=cDT&@mp(a89NWlaVjeDGp5>P(shabc^p%Ju<Z5k)fTEGFZVa{GDGO6{"
        "mC}ip~SAQY@U1KCP!s5@&1t6!TD-"
        "<P=X&D5!s#G{k#owjq%;>E#JnpYaZmYwjXqef~e4RTy@@Titoj?A+h<guUCt3@4&TG>M0S&pTGleQ`*nj_FV>^*|N;=v4z%X5D;2"
        "enYo6tfZh7IpU|uy&b^Xct@Ib^rZu9>JGrz<mVQExV9N6+vWS_3;Y0)jN+Sn@yUtL#SZITIsEwTpxYe|FmDNWdo_rJlfW7B=9g-"
        "~@4L|8_Mq@4!%X@^Wnu>NOS)BDmPAYsEogD3VIqqZQ}_styTptxZm%A0L6>_Q^Ye(Wv8hov_ec~0nx&t2iXDfXCVjVud4aCMklbr"
        "zcLME$j*qBeQiy@eFR882_{_)e799V>j_{6BTH8*m;9}!x4!D`FK<6dT&eGgGGT>BDjv9N{1p~lDe>|M_r)RVN%pAP&+L?zW%u2;"
        "#uvd&{^SP*_M)RqaAF3si`H^;b1H+n!qd_p84raEiS6|1>v5pPlpRHjmPec%NxrvuaEd*D>)RehD)?|9z-"
        "GV6H_gDq&vfIW3gL{#rfk?J?Qm`~mS}cvjFN-Gdb-TgLW?bKKKa7DT$h*u#6?tT=w~Tu90Ddx+2r_e)GHKD1?Z${2%c#^^9E@R+g"
        "8uBng;zO4rmWeC!4|BxPD`H!$R#VLejRwiLR0We?M{n#eaAd27`+guupEO^(D1VuGuQI4J+z5nq^^h@w#2uL$2owiRTt4HLz_!P%"
        "W5JTzAA;z46#<u;zJE%nK}Ar%Ege$k>z4!1=q3~`p!k)^f?BLiEeXaqdasn%a6p}0s9(wf|4|1HH4T3k$V2;`k+#S>V4fH<eaA(<"
        "7L`A@m_{na$JE@7K8`Bg<O0=&a!2qL|t9NB~d|_IX`O{+e0;-"
        "Oq+S#o~%s{XASMkwm)}ksYhikdJLFha5ftDfkl;VQ85G9>b>J!55>Se4YE1q1JLFSw`1DsyIqH!k99o+Ji(w8m!V)8H7|gIzoGIN"
        "%aMynu6O7aR5d<}D-"
        "1Z~!89=sI$6pvE%m0pc>HB7P>S3&Wc;JNke{RI#|JbU&M=Y;pa?QR96i$4W(0~mp6gN$3Oa`vM_(yiMyjMO;Jb${;7h?Sj{b1q@~"
        "wr_ru>ytynpCaa9FyxCL8*oIbc?UPXGRxrJQ4{loc-2=TC0)Om~~7TA-`7`ybT|b7IcRhzqgZ2R%Mx7OzSSeeG|Fa+$-N3-"
        "qf+6B*2V8x3cpes}Hn#sd&LW@P=H%tpiUh^Mb)w`2YG+6bncj8O{Pp7eTnz-LNXF4o>#Z_PXy?UMfp2Hsl{DlDE6GUtG$7{_j>b-"
        "3t!oL}Kl0S&rg=iM}mi{~|jD>-"
        "^;05wd)XfgXvXGdrXuyAyJvDdW2LtJx64mB<6lQyd$li2VW?7VJ#7HiIrmo>>HOp?53q6scg>$xRz{bX+HNHnpoCz>GLQzn`~|F$"
        "bvgiGe0@Vv~UgTJ^VAw}lSLNSjQr}fO0`=ybaVvSBw&)bu4r3bomPt$NxTdm>7ME(8<Q)9D;YCAfEKEV{Qu17PT5JMbv8J*!t7yM"
        "Tpbuq(Y(QNq*rj*^8_gj4x%bKsk%&395Hvr9dfe0AZ{1r6p=mFr@nSbaGa7Iy>{uk*^E;Zu!-66IoK5QxP)#O5QGvw@0kZk&c+D-"
        "&~0=+9ZJDb!rSrux*5>m5sH<Nl8F+cTEMRiW(KHtNR?=Vj|EH+vJ#$*>obsz9AaM&n1Sj4Pgg#pwqH4fVi8yH(2{S<qeP{@}z&z!"
        "OQpCnHnCxuQxxsw=q)|1T^^`ql}YBncD^&DsgvvGn3bsX&F@l1BeNcbbeTb3K-"
        "IGEE}i{HwlI6b)8m#4e%;Wu;~Ln3`$^t0)uzf`eKs0WlPR<vexe}y^s)ts01oc)vx?82P@<2S(|j&kvg=9tC(w{n6?SzssJ;ORH?"
        "j@tOy{N>>%t%{W}zU7zz-"
        "H>10V0kZI8=}h+OMxZ;6cGwm0$;s1B>J<nvwrBndE+a;HbPg_1wqA+5iSDNYO1;b{&DS?jRnd0PDmn`a(me8;Vcg8s1cDDH)834{"
        "M9dwrD{Pmj4es76o)(-JZg%>N>u6BP$hj?REhPG$>GQ@e=5(qzdm3DZeTDWJFX+DNFk--3TnsOEu_&z-"
        "ihZQw5z_1udb5Sm&udO8rYwq8pKyH{2#V)neuEw{hB)ebB%(BzvdZUkhf*g2f7a_pl}FU@cPzi(cs5py>f{rIp|S6Rc)%SiGD?g1"
        "@sBZ5Yobyt@8_5p5!vUAu=MvOSQaSeb~Qgebct=*CwiV9jBSw`hw{aPzBdacR#f);!gYQgF!Hwj%LI0pnjT9J*yw-"
        "t21~5r7%FSehTkBwK>C@&HN)rC`WrCjpnnu?8swVRFij`(=O7*&mEr81`(L)Y(@o}=~Ox0R+X090?kADvk!O=ZZi=GUgPo5JhaO+"
        "4t{)7R{>Iy)lK(_vjlHRJ*lfvh-"
        "U8xyi&~IwKf{`sZpvdRAFTPYaVo<BLCvO?CAA%Fbo(_Xxv!r0VaVnz!k_|UpHC=yQYxSxkG706DEZQrDHfeh(5i8hvS^&DJPrV>&"
        "AeynYKVuUZqGmnPOrZv~M?rwPVLo01Jtgl`e_+0@)O32A~XSGzRsv!Jy?>>|o^a$^$&FABb8q#(`7X1<&HrvLbG`T8P$7VeH_Icz"
        "$m>oef47g^iiJqS-"
        "R%9kk}ZN|W`<x#pR_O4i90H^M2CtrfdF^*hh8jgIF_3bt4FS+$r($f`RcRJZ0?<`og*$rBH5xw{kN{<q$p;ah2?S$E6!I4vC;`qH"
        "9d0^f?1dMuhxQD0XfV-1q_q85*};Ne(H^MvU*ko_-fonDDf4M*adfZm63;Mr|c*IRqxGx5=yvMTodEsj_&R|$79XnkLc&Re6zzBN"
        "~cADTzuOS1yjrdFB&Wi#E%nQfbAw)QtHq8Y=?LR{<#?C0HXIG_SDyB*ukyIn_0)tzJ04qzPQfZnIWDC*(H+v5H)aXAQpP7bJUljf"
        "}L*CO1yRGvpOgKa%_*qR@zZgjSrNsd|)`Y_AO*)Y_9joK-pK5B%biN{W_cij<EHu0D?`S=xO-_n+SV<r3c^$7f&WH)}y4Uh-"
        "XAQZnw16T~>*BSdY7!QWSv&qc(br$NajE!HdhjKCpRPC5I|6Wke5z0^F;%Ip<eoj~@pny^#ptC!4K;vBjCL4@O?^LLM-EOB=;RHW"
        "j$~Sl{q1MRsFwXLo?RTiJvW5cA1utc4A0xw+q~?8HSTIi?wjD_^(=Ze~`gwqo7TMf&QNql!FrT$N9@O>abkPq3m7ho${|*>q{D&H"
        "&m1L>u=tg7usk!pF+7X6!Ch(<Myh_W(zGx_8h29j0G5ITT_E}Ka%Zg{DD*W>cmat0t0kLF_37_b}a5kpL8_evwiu(Q){C5d&iev%"
        "iWK3H!b1_X0I4qqxh=V#)5_`+`pfD=crLmoO!C5GX8of(Q2Xlp7UWJ0>WcOg{mH|9<ZM$YovB`XI3)<@hz!6Xwd4qpr0nbDB=2}@"
        "@)+AtL&V&uMxGD0wey$6%8OST1$_pt^4l>_FfTA8;uA`+|Yv`Ye3k0cP(!3F-"
        "BM&F#AFluk2Mlkw+b}=T+Vf$eGj76#frx2qf;fTuWm<Mc1z|Fe73J_bUta*_U2&hL8G^H^h2YeZU|1x39lcC2&Svjl+aX?)njdbf"
        ")!M~xlj3Re8I~3+7p_j}QFWb^>5F95V2E0yD-8Z!YYBB?mQaVqitZQ+^m(T6lxNgwc!-"
        "N=<<voRuwZl`;?9g@Ji%b#ncINJd@)S9|7PgR%|PPiOW@V9jx4O!Ev3LRP^(TLyju;`_pADmiC4fOJz)iAD?-"
        "zW0mU)1u53vsur~4nZiURFZrsMo>afQB1}$)8b}>TdbAQ|?L26(=8wO-P7?WXYJTafa`d;a_ax(8-"
        "8rE|Zz%?ecT5LjqvEW4Y^i6YX_M?#&S#yw&d-o%5I%#3&O5;+U{2T-_qv${-"
        "7aa@_KOXC6k;4??=MlAIa~euY*nw#$D5hrjvBDe0m__uKI5xv;1?4_G3o{wAWk0qL;$p&zpk=OhahI3y8hm-"
        "3mfHH*BbbcGqyC*E_#9@%!&_J_KM~*36eR5)pnW{44!z_mxxtD{cI9iVON2$QospoikojBl)HeD%^$Hs*XQMQygT#nMzrVqQ&a*K"
        "EAMnZXfEhbKOg*}}_fsC9tPvF}Smn^be_2{WoCm4qMlq1Fx9G)@5qgF3-"
        "n$3|;Bbk5zCmGlCr>l3qc5<<rLHavj0ogIg7dIerA`LY6=oX8&<c7a4&ts^Wm>VgS#nb?^dgPro)R9ALs6QQmYNoKcAwpHP*Pa#K"
        "UZF&sjbUU;bPs$JF6kKo<duwX=YRkvH_!!vszS1L*nmY-{(OpTE=Jx-=tS+`<wYaCD?wQ)E~-"
        "(T0fUQV+rp@YlZ{nSk6TtD6^N_PJ2<ihVnEJT$u5dd7{XRbJic6H85Zc4;w~wl*>cDEztTTsp8MLjiTc}fnPx2R1l7qZ-s?-"
        "2z&L&%IAzy9-"
        "52nq$GMSnz8!~j36~yh!s;@NS$^mssdYE{0l1a%`$pYNkfS4`8{Aef0{gVL?0}*=!2$1#4^$$^RVKozK<n!#%Ri+%3A!Z#Gu`h8)"
        "<%7J=1fm6_Xui&<=SEJZnIy7b3+?>dg(i?P#DyZvRYa#Pwk6+R+G?FKRX#Pf+T_BUY07eOKOyaeS<7Qf7R#tPa%Ta!{_{JJaqf$M"
        "%avk6x$@Klz#DajmfnxLJo7N04{B9o#~;^<1+Zg2o&Q&;0}>>D=&RA7%t@-?PGXZya{{nGxRZ$Tb{{S~k;YsB-DFMEGm@>(I0?a~"
        "-^t2b}5}oOc_y1>9S`?d7S}y;-l4pTpAkEw5vc@~|B|3^R8q-"
        "x{P#BV3*rPM~myuVlK&Gl6*L7jtK_zyi%+nJn3SSXRKJ+!X86=ocIXMIXuu@kSyl=IH0vQ)aJD*(vofJ;n20^Nb3$mgc&S{cqp6E"
        "%)Ezxi&1-"
        "T4Fi&I}W(LBWgi({O^<J094iu1wXy&*|tK#{0#;3#<C}tBk0auFB|`bS?{%}g9UHdRr+kf_gP57;^AHY=D@CdZk4a%RWJyfm;=2("
        "&)zEL*~y8*Afw7B2(aVv;A|2_y~zk=xSWp3y*-``gR|Z4<Rp7LDt0^gIRGNY-"
        "?3US<@9ObfAqzpPfuB5g!B>%vf}Ib>VpSpVL{q&R;|j!!OYhPOU^MHG&G)`&bK79cAYG3(8)6Yae9?zRrm$X89<^H2QqcEl<R1AI"
        "W(Q3aPjljH3r>ZER;>urfU;<q-"
        "BrmpD7Z3{>KT=z?b{Seea?*gBgz(l+)EsOhCRUYOurtc>3_AfPCu^&+4<t)GX>MGS1?`WDKl#I1rPWDH_Kn!yG2Zfp>wmA1UCKzH"
        "z0YWQQwT2$4!!1$<3_kKU4H>3`sbtooJ%;-%-~^V6N?Y&?-"
        "{p*g8$D@oO7vcG*L>@fx?ai>+&YQ>#WppKQJ;*T5hXf!wf{+b`=U^@}Mftjqrifl~9-"
        "ml`6XNL6SC|?BOz_l}Zsppi%PMt)7pR&8>{R{Rh$yN`dSl$jU9<Z|2W=;5%)nCU(cwu+;HQt35_&xeGRkKd2)~uymAai-"
        ";P&8BG=RHpl2JXbTuuAbtg4IgED#xs;Ft_f)tjL=uO-iZ=DE9ok!MBHzBehzmqJ*IUm>1@Eo{O$~e5~>zby;(6oJ=CKEDC|Snm*@"
        "Ajk`+oMdlID*pFF*FsMbB@Xc-w!{x4r=b^&B=N)!t-%78R-7!M<zBdGqVXaKaf-"
        "}{y_qvS1MY}P$Ai+`1%18+&BaLeaxQ^1ryY!|A@C*Aax0xz~QY;M5c#jJh{dvn-"
        "g`le^DI1>o9T7g<F)CDKk;vpi!N?#nEdYyp<pRScVM%wrwYUsN^AGBVPpVEi>Sl`qMencU!sV;Zys&6>W+N4anXX*PYtcT3hiSX<"
        "p*3ecJ2uTFtjQuTcUQOLumZH1je^O%ih9*9@xDoRWavU@Vc4$;Exhc9%;D(m-"
        "BUxy5XXb7=zAQ^1Bwej1Fnm~Z2pQJR`C4G2p+%_|2m>$vgGOqLc6>4zPa>WZBIrX)r#5rtM+;Z94(AQP3bD!uw1rfc*Uz3_;L9>T"
        "ZV{frGJ%VJbVX#ulGj!wbV>wbnD1cY@$2}L%mGFFcvUmHgQ!Ns3|~1Ch`LXVcH+f-6ft8c>!V@@0-"
        "o8w2*ikZJSW9Dfra$2@j|_h6g1MU9NdUo7$SMoNK;i=kzclL0jqvz)1%Kc*);3EOx<j;@!h8=r~cpk{|J<U$LdX(w086mfjMJVkg"
        "zBnU>d5fzi=oE2<J~coAinRF2A>WpU6esH01J%Q!6}4X1UKkEI@-"
        "x7IbR6|%sqrf{4q>?K!8VM`Km(E+;l{FWqLt+_xn*3L5Z06BY95Rn7|x#9ti95z~dFFRX)ZVI09UCAhNe%yb1M=}Z-"
        "qt}UQU*fzs_jbqg?DCGHUiC;}6LgCW226yFaC(WsfN+3~c1x6A2JojJV$6`rSINSMC=|z0I>L_Q?zI%yp^hlglT3VxyJL+qLwLt`"
        "790Qw!vPP4IudbER|`N+6$@h~0@W&d$~_szuDb|CD-"
        "g!6BxS=lbfoHZEoUv3j6o!<EscuG!YDJ>YHS=J=^wU64*0(u_|X6aQzW=A^^EqE9GIn0azOKtLEe2Zgy8a>p6)L=6h|EZ@Q0YtPd"
        "lA(wcGL4@j~Y&)P&9}zLM7J4%w!neES%;!zgmz7<^R27xri`&j3r7>B<VdVEK~-kqc|-"
        "l>CHgi6tXkoJC?LCXu+wfKpk>`gjaTD>^=5MBZ%Rrs8{LRX@9ONWCqK3&8%$tf%R2hdG`~M|3$)i>zsscv_<&QV6*yaL^3ot44ab"
        ">ori&zHJ4(i^GV7GV4Rq9hD}d5nmc9DVCKh2e(7C*jl0mlP9<))vp`%u5``vQq(WHZjuA8y;?QJkJN^u#Lw{GrRQJUr(?9Di%1|Y"
        "ojX?l#XNC6n{XbIR|H6>zoG!cjoR;+v-"
        "}e4via7grZ>ZDXfEebz}E{0pS@xk(%|jkfLd=rBUvnwTJ%(eU7+H3RVLDF5RzDv8=a(KM)kQf41`X+*S(hpSkgtWRq(Q)Qea)b72"
        "`+D;g@otq<j$^AFwY>NHUUV2f(iU`m#FLUV3Z;rzK^*=zI?C3X4~>1&pOz-y9$i1T-C%`ObCMMq`7fU3a_J+H9^Dy_UlUh?1^Nu-"
        "ZAfxlE{MRbCYt;;a*R8<8vy2Y>00{A*evD_Pt|B#XoTFTIA&vHoVOEXOd#xwU9}C`)(5pkn|HyD*`&r!WE&Lr~oaFgY>yR`OvP)%"
        "bXmuzi4QtSkg)wJN0p_o2SAOx?k%<hs6#vWsGq#UYe^<D%@vp4J^;$g}|hX9L$-"
        "y@q`tdC0nQXG{u$0UA>#XvIPmV0JdafSt41c+%hXK*x{0Z(=N>nJMEAa%yF<pie2T5UrrBuyK>MLNfp?qoxBjkIafndf7fgmZoa&"
        "jdpBunCg<{)bD(e;KFwNPM#(3Z%2hfmU9#Y?Du~v-p_LQr|fuh-fCOa#c<{feiGFOL4N6TyZY?dmAzLKN~-"
        "aK4G%zb+4g#rV7_<AY2C&^P4yneTB14UQ+aN9hlPZIN;DDJ$RM#XsqCO`He|<v_haY#4!HKVy1D@jKBW@@F=gaigFG^7p~2(6*J`"
        "ZLB+<1@i&eBF7N2jOF0Urqu~ig+osM0qJndVq8(4}#9if?GATSSbW_cG{&kI*(JAZ9Q?bm~8%6;8FSMpWLv65KnHpWTgzHY%oBjI"
        "$|t*C{*h|Yx;HWYk+kd;=au-r(u6rs4xNJo^(d%LgM>5y{aopi;cadnH`_P!Q7r@4+~>n4-"
        "kfh9y8!RPBHn;dGM!p^7f2icRRhHEy!OOR*!{`V@l>-A-;L5AJ@R9S$&SM{mt%^Q+K?NP(FMM--Xjr{sa^ec}m?BDTvc2|^0zAoC"
        "cv(ydZ#RiZ4IB0=wg}lE3&cD1D`A}ZEZI=G9O@5v{|1jgPELfIgF3R<8_x|@@_`RYxYo6W<2H9hYd&qht^j>q#uSf><Xn6PSQffb"
        "6X_<7JHWcRe`OR-OMPB8<`AvsOiz}ds%_S?X*iCYZsNFNabX%x3>xs6LE|oZbsVtp`Bjv)t$(8lyitCcA1)+Wu3OEf+A{P_rqYiA"
        "{61IBb#;t#a4Y~t0?Kf!<m%0YA1`T3G8iJ)kTq+IXk`Cd8ZZowZ@~`kF46Si0fM}Lg4!YhO23~6}m%6T;qWP}@824MyCL?Xng(?S"
        "|VGa6^2Ezjk<t~VLG>|4C%4yIJw{A1{T~_W*lVSV*u)D*+eK=(AsS?)^`sxsb_M0r;;bru0eMK0OHZ2L?axB>oHx^&B^@Tr!9izm"
        "I;v%1*pJ((Fi@*lREjPjzn{s=)8W|wTT0FhB*^xU!laI(E_j(4Sv8Ro9(Q}oN4p0@xc}%@fo53~lKYbF{q&tLqz8l5<+XvrtAcIc"
        ";d%vRvch)ImP1v}Vfo|aGqgVHb{662mrh8&MxKN5CjO&aq>sVu?uBDKW2pclwEE>@YA>ED|cL#NZ--"
        "{&OccD?k=rnW~A{%Hx@^%dO*=ig(7Aada<rHekzzUCQ5Nopb)4=_~{j#_kS<xK{q8j9F@75`^<cG>Exz|7#e+)^cRan_Ng_SkqLr"
        "t;@-;Nf$%aOQ-ZttTx)I}eNvv1Mn{C@I7{|_KP<jCc$4*RUXcKN}Myu7z4k^ko`N^BN-_MRrV){thmc}4jlKS+Ma+vJDCmg-"
        "%{QgI=pi6h?03lY;M8b=t76eU$$k|KN_)zU3O>$5g}tf&z=#o}pX4Qc<3#F@rXsd{w=$y<uWXre@p0^=+=KQTZu8i%7P=X%8jY34"
        "*@nnA?la_-BBr7$wI*l{~c)v}{ZJV62#54>BrVar!%@mCjWWmS6)My8j!nZE|zyjAZu%v%n|_<Hs5t@Y-"
        "XbFb~<(15DEon<vAe(E(4E~hrv!1~tz|L0xnKN#=&&sq)st?ifio1y!@8e7^mXe~gB8QpHOo7KXRw#_GA)hTN{>iRuDv2e-"
        "i@nZ7SYt%;I-%d$&gs<pdtbp24<pO#btMPUp4{BfM@H1dP%WD|!bqo#lMsx>lt>oM}Ao`8_dARntub-"
        "q{VU=ENNjX)n8bZLBHCDxd)yn3Hv*l^>vSDCXt}w7G&6%=kKWlXOv2fEBg*7m=BR#9CweYKN^BZ0rrSHd4f8OBlT)2IuF{b)Uwc5"
        "*CE(W_`d%vMx#!|DQubC5kvF4>L<xv)qhq9JQE3ReIy4KP;mKT)TMjY?cs)=1W{aX5=nDLa#u^9Q4RSl<La3%)DJ8YaqCT4*n$}g"
        "xVHIPe3Xkcm%L!N@JV1cT)a&b8N<fQU2k|RH_RFU0ly}j5d33XlBaRe^&)o8{F0&`D~3N9EA$K&yU9d9YUZ^~US6(J5XV1awQZAT"
        "tu(?q0jyIPlCTivd8n}?ZvcSTgRI$Cq`I?hHSMG$wq!aQ>Cn|z0vorJ%fuN3>^P9h{S{z%{%S(_%Fkse4S1Txd}uq3pa=`RRsd5D"
        "^tSCxJ++GO9r<6K`in7aI?(p{PyKGu%N-d!4?p&W&9N#~|Z8hK-?XOdfL&S_Q`N#XGKR*;Sr3FF_DYBuIEGPNwQabp-"
        "tc~=O^(ybyi8@RSs1j@E8>||SyHCgJhCaE23vRy3A0F&GiV1h5j&X>r0j*ne|BzW@3VLRPo!TZ-2T~fNEOLA-PFYo0ZUK-wBSPXs"
        "?e0jgf62VGpoCs6bW4Zfo*G=S9*oan;^-"
        "0xKrO!khSv8L(wAJz)#T;@XcWHa|x=Jg8{Y2FSc<qJkK*#U%Dj*ut#rG@pm9yMfHCe}!EM9#cda1AGd8nFFvRVV#R^o<?Wv%0S-"
        "F2+!47wVx$Qh$B?Qx}NB+zm?_1h|s=$TEaz)H)z15vKQJUe+vl--qi(2+{mS+y#J(X7v-tJKV%9eR}dB@&1eVQ}PT(-"
        "?=Nh(*w~1u8D(tyzw7MC>IQx?ZXl9JZh%>5}oOEr{^iQ3gvBp`@1ZPp#akP@B##?vb24ua~ve_*?0%+mn;0R&w%E=oh7p8llem)M"
        "<)>pQZ>17hWk{`Ra~z<tv%4e53L-Z&-"
        "5ZgVU97%yi{B1%pdlq_AX_o*tB6ib(vm%toz8;+uCJIjS*R^UEitHYVF=lijw4$ZS+ac8nv(itKGc_So)HPud=gU|=Q7SiUiHfaE"
        "NaN%QSrG3LGTtlZ{TwKN*|wPYe&D@33%D|s-X9Laa5LcM#tUfH{KzY((4n&qKSDW;e5(8B=hq6e7|y<L5MkuOO|xDL<Nv#-"
        "C79NCMWl^uHkx^hobIe-9q76rU-"
        "((F||X*Q*3#~OtUa95I!_UbvZeY3a8!27XQQ{zO>D@S=%AjIn=UZvU9Lz(&ZR3*XX%KQSuMp{dNb^cbzqr*-"
        "0)+kSp52_8N+imOZ!ary<5gvX{%@lpH$da6is=~Eg$wFTu9<;0l<}2U-{J><&i`SS-"
        "855DzvW%=@zu>mZF@Z?ll0XFQztX$~N>Vqs@~2SZ<Bs6Ojy%mv<(EKm%Jw?tY2K<l&0CeMg7P$P#lc~J=J#7ez^Q*bOGl|EW#*CK"
        "n>&&+$9qQ@_?NZJPU5JE-"
        "j2rvh#Df#y^Im58=3EDUYAgB+OtPlhc@%bC{|9c9xaP?uGm*j@HTDhE(ppEVWhRU(nWnyHB_N<oV*qCCNG*~iJiGO*W8RoO3iIV8"
        "AJNa*0%M&*-ES!4g{5*3sc7sa0gnk3>_;a(A_r~r`+jlZys}s@OHo3?a<rE9P-"
        "u@>X>J((F0_>IFsdg#OqUUp?9gtBtVi@42zx$!~2@#z!)po`Rc1h9-8i8oe9pm@d7~}nvMjJSD(h~bfs2HrKS2jxh#9ivh-"
        "j$l#FiEoF4sM*lQiO<5p(=o2LzDl^NxrgYiO;cLzD4tTde<LtWX&5mp{Iamw^XSObO?hMSyC`<PkyxNI!zjSk7tY&@Nqq|`d2=sG"
        "}Fn-"
        "m=qHEf~0sH2vZs@D6l5+XcNceg(sPDjCPFls1}_r7w&Y|#zl%}Gq%^~@wf3$#=3?cvN?hVx1T0FkEF+1ZcP8E_80vtTgl5B?Lt*("
        "Cm4q3RDtqI9-"
        "t{8@Pj7C>zBg5`KD))}$5@{G6}`fMgMRI3ka{v>=4Phf2#$|VjcfTNvaj&%7|(<BiFuq~AGwengDN$^K*w}a<@&xE7#*#HgDu$w?"
        "c!he}FFY|BrF#Qe?rz%~NFw&tc;xyobs`t#zqe6H_Lhk3rMZG&M$eo$Y2u@p)w;9YfB1(qkx@N_9Ugx<eEzjD$!;5r$BC(3Xar>_"
        "Kbi}|{w?>%JaO{P0rkMW#ZSHN{ZqbNIK)vznhDCyA&jx7!S61<%--"
        "(w?5H_F}PZXc%DK@XYI?}8mm}Eu|lsY4Eassa$v)a{IvJ}SxY@33VkTtb1?eW0lHISP}k8}gW0k$nPL0FU4+7{f_PL;QpYPil<4-"
        "<UC<X8$rI7X1*oKV$U7;8htHsBtGB_IH|B2a<FB6R$cwpz%Vc)M=|Ezk{&d)V-}hpR*7<F&@q-"
        ">dGZlwlr@)b*iMrK_}2E;R(8nOFBQqfVnKA|o^a^IVHHIi{D&M2jvNr<ZyvP~ROUV%Pp;`8utv$?w;^%t|Sw67I&q@&186p}8}bf"
        "rl%cISy1B%AZUct<Li2>MTDm%7HRN1(NslY(U5QQ}3G;kM-xqvHsjR)}O0m{hp<X_$@qDMU>b^w36v9oEMa$99+rlhx|4x@>VLz_"
        "Or%Sqb;2;I`42ABV&D3*pIQ-U?XIFBb55S$?bhZH`;efDt3zQ!2O}B)ns?F6BJR<nbvZomQP;#Lb1KMGb-"
        "?I<|y662L#Ts6{fO*Ti0Egb7s=&4fTo0w>;PUgr8RKeA1d$K<9h)<Gracs;34NfvBg3ZDgi164)#r8QJ>qo&H*XfaR{a3n-"
        "=VM8K@dvf2%-"
        "8rhh3KvvOC(aKY=nC(k16gG=}n~h+YwcReJ(Wp_<SU($HItr*cf>~phTlS#D#PQw;r}@}e6Tstaw_|ozUjM~I<)c4!#21SNG^-"
        "zoNCX(Idqf|7@ykb>Bulfa4~qDTvYG5LFb?Hu&p!uE@*--"
        "klO*f`bJhQcifvIqGj#CYIxqDOWT_2N1_UttV$QQwr>q77Z=r>&L&LH~O!}hFAx!-xiqA!o!4fXb{$U-"
        "Fy8uL|{nk7p4cpqN`34XW!Avf(UYyi1yC73#6E*28*77x%&tt1?!(>Jaz$a6at~j<d>Ey=^Mzzl!Mm2s1_=X#D^HNkQ;m^H!Q}4>"
        "ikCm+^V*n~3`f<4+JPn0h)4uo|ZDkG~COG)9sIr13<H}@x$+3^Gy0$oTGF+T$?|8R>@aa7f{+&jI7el)TzKecd^jP&7Z~mfJvMZM"
        "NN-I!0#`(0vNCHRO4Y>g~V985kw6^S}O^=n7Y2uj=l~(6YQX^jcs#1<LdY#iYH%Yr~NW(4&up1c{^(C}$Q$YG_v(($+C<~<DK-VV"
        "nY9Rx|Q>{K6qGI^5f=P}A;v_9l3-RIKl!Y+-"
        "hhjba9}VytU%M~JA6Cs}W3ALQS)@At5~Nm<q+i#K8w=lLRQQI!`g#1!no@=(8Rek9u39TrB4p;QzR@Ec5gKsdU7>ClEGBqvRacyQ"
        ")S{n7pJ{K_JuRPAbz=FbI)silhEvtbDay`1Zx2Vm8}pmkscV6SL;qgIMC#`X8fMQD$!Vp*tfC?!z)r1e&P0#2b$PMgO2pSTCHHEJ"
        "O3dy1DVs01?aTUFVJ;1Jnn769Bg~`5%7ePCnym)B{grw<@R|yi24gh%wxf*(GEw|jm=1JQdAG7TfT{y`D2AeAx7@_bWQA9Zg41t6"
        "QH`3*KEJAKR=3Xj#w|gMGU?Ra=&Ppoqv9ypqaA)s5j>@P>a`T94TrXRrYti>xzee+G)Xp3Hq~>ZEOlj_FNIca(`=R80A5iv!-"
        "x38U#D3j?tBc_KC3$<ZoNmp_MR7(CJ5uh>PZoo3Xn@>hjA%2hxhWVieW^iv$!<9=8xJ~lGEyOn3=+;(&a1^?i_thq0Oj%Fl$m)xe"
        "Gt3_7N7oBaxdGf;*KaWE@`-"
        "SK9Gp7T?@yc=0GLkG8OuFrZ}RAC*aRbX`@OGJNyRtF*e_K0aOMPu^U`Pt(=oJj;^m&6thkk5U*_yk5t=D2;P4Nwz9~0nHpR9P#RF"
        "8xUL6@2cpwv)gsTf!|pyI^odobi18!<aglS*zbJP2`6x?6Ha|lEjr=M?;Nu~k^IU2zSRlO{Lb6-"
        "?^_Z3L4VSW{(;W3Ws+agb9g!E!wYYVzx?6^{seyK0sHe4_ygnmFW8?q*`J@_-"
        "QnK<po)U2|5F&hl@2`|^!=vrWO`=Qn8!N`vG7;TPK-BsIixU{`Bp(Sd`i`<=_2`Io4_>9_HC&n49@)bu3`IGw~Xj5ykk^0#v2VsQ"
        "^F4_-"
        "zsX3x7;t<CkOG~SDTdyr(oiLmBob))?n<vgY~n_Tkod!Ya{>T{0fcx`puya6layP$TRK1$am$}1vLCsnygnk7=0}%ZW!$6l1hDK$"
        "f)Y*O~E-^a{8=*rRsHh9UzpzFpi_D+pT201yKL<>b!qJTJuE@FMSbLe9K-"
        "!Dpkp2Y<U#S^S82ju8MhPQFWeQ%w<>p5%g7@XS~e}8r<*YQ?H{D*%uCB7Ph-"
        "8()U@BfHZ(ubzZUd=2WaDiaw|~lRoaxl}*+CX~91g@kMAxT^wiKu1w=RViru?V3>X3ROB|^?ee$M5OhGEL48Dd&q3(pZ&vb6$H&k"
        "`$i9RghTKMql*afF2oSraK163iw)n0(S8rXs6~S-y%0*~BHlON|jX$gTw-la`eyOd(!o-"
        "+dKplg?kvFMD^g{EYR*TrNsMTq?S*KO6^CuZaLW*;c4+0%abHc<TeS&8XQp8U2B-"
        "0O42J`BzbY1}lipRwXo}=WSo@Cx!e~`*HwW8W@)PTaVJ=d{4jr#NSt$dyurE8%@)q&@CKBg2B1PhqJLPF`yH;+0eIV*B3#)beurC"
        "7oF&7S~72xk0M8kB<dPu}dnjP$YpqGi+jw<{G#ShBq<nyOCG9edI_>R3A*=A6;KB7$%#0w+a8A^;=fguz^d+*ky@@!g+S7eof|+u"
        "v0FuPXo7mH+d~|6@R%g74p|h;BbC@~a|#VpkMK@iMEpSke=}KTe(|YtO$$N%Q?|6=psS<h}d}3-"
        "_g^guTb;UV_2_J?M5}^(h$(zoDB1k&0mCmoI<=N<u2<o#5e&x8ixC5F(D!bD%A<pV;mvHv91_g*p|m<MWvBq8P=$N+SGT8+ld4Da"
        "`WfJ$nZB1L|S#lZOO@R2audim0hpa|>i)itVt4eO#P~Pv&Ceo!gG`$T3(VZgJpryRpW6)NK8O)+v?iBvz-"
        "~N3pd!rM@~v6dS8k*sT|4>v927zB-"
        "(D^a^Wr)GD&b8|V0Y+5}y5(Qv_=ztnmgt#tMs{GqMkg9m$GhBN{m_*&!=Lk0OQa~R_m#(AHbD8!OD_@oS)H&p}k4!$87u=SckIX9"
        "2idADHK#O8OqAuC$idBkF1wD<6EsHD3R*u=VM@#>BC^jrFpGM;wtuV~UAUN*rby*$zeQ-"
        "KsG8^j;x0FKm~2rUw))%)reekCv^UgI%Y=v+g#&JkgxYE8Z*8<Tg?4z>3`jvpuMWM$8SeZ9tq@=N+<j62kN!rd-kB{GU=^DbJSnm"
        "|ORsg9Zvbzsa!HSZpZy&S0Dr`a}X>T$`Rzt&DsKW*yp8S1VY9x%JBY?A$K#057@zaU#;<0g9*x<0pFmz+^idmp%-"
        "gY+{4r#{tHS}sBI0YyneW&Nf#?OPOfIEhD#W=X*Sk{K`eQE8F;rAh9~`;q&C_MxI3=}CtSsU1cB)ut`#n>HljEYv<1Mpk_ya_iy*"
        "3OSqgK3ZC{S(~$29z2^^X9V#b%xiBliD;l0(Frn<Jt&;0Dm5WA4|$_=S=@}?uzAE|MS1uQ#}@h$4M9y^GAq$x4cqM&HqQciL^WJI"
        "*EbuoJ+<5L7qiM?9;9_5Jt6!jQ?zk)P=BKw84Cr5WsJL_1Jb^Iucz>fK9UGVziOmFzO2!LLec^<8OH1MMN$~6KzG;r?BsiLhVl+$"
        "1i!dW*Nt@Z89sbDe&(iO5A)XkR{0$*sJ@QwJ2pa$5Avb~F<@gJ^)w!Vfp%i~@tUoD=WC|B3n}Cmv@f|Nq3^%FLdqlBIXI|p_n_hO"
        "FScZ<lHahO@+<c9o=X5A_)u;0@HdsEDTt=NMQFSM`Z$%5U$AQOM?n5M``))oCcnHdRMc2M<PpyJ#qeU$IZ88Z|0uuICP8UH<Sgjd"
        "{U`kBQlGH@FnPSax=M;hH000c9aLd`M^)|cS507}Oj^&gB>)Wn5Wu_>DhbB5_C-"
        "g0`4fC9m3;PEx?12r6qpiH87I&Gh^YcBA&<TX?woqvBnpbSt**;C(3&MSF?DG7y08di75%0wT~NgxV^F6^8!tXo-"
        "@y+?jqG!g^*y@8H;y_SRNo?ka%k<3z7+sVPSr_DZC#U_3LOi|8ls)IWTq7IzGTR;^G3ZTyO?+0L)1kR2`DLRb{*jL`|Nsrfg!Ou*"
        "Jkp!8k#z_tk~Y7wp&7{j-"
        "$ry+*n@6GqGe(3Z7I8brkvV33{+<AXoYfJ=Z|CNtWa%0FdbsVVN$pflOJ<r8$k8nJ5MVZELWgcv`U1tw>zrOrqjEz3?+Z7A9o<?K"
        "~u~dg2R^$@68rrd7w~PC;T7c?mk7qK_uysexo4KRJpKYaCzh@mM|#iw)4QX~<ACKCD~rhePBhuq3OwhMQ>j_A_!|s$R5t)`x&$=O"
        "-uFxjkN=R!!6L_ZpWk@+bHhyT*0pt{DJJnQx0FF@y{xNQc=4*d}Tww+L}l3>9yaG)m1f%#gtVy$mE%l8ofL4+47?RX@g%na*srCy"
        "B_ZcIqKH{XTi_RyMVHGOMXVU$upt*sJdxf{>&<3Sj!?A)^NE3KHy_H%CIR9dQLfBX62XR_Q?Mo+6XY#*tbRKwduR5O&#*hz`}PGB"
        "7d>s#vv>Q$B+ZOQ|7W^bVc}+jw<Tpg|~f+JMxR%!7cJItps%n+wFWTOM<Qo&(%4`c6wRf||;?p0WufEB9uzp0oW12<+Z(I$-"
        "t$5{4h9jLmkR-"
        "?a5eMUr$8;}_Jg19xNr;3(d5d^j(fHmCmbc|rTs*}}cHtU#l8)@v6M2}UnKys)uK5?x~vP9zM&`UiJG_iqkxef#VjgDVBgROwP{N"
        "!n@WDl`TCI<W2Mohu{>Xe%x0Vz*OFQu=;;PBEEes<q5TRP}-"
        "sQni<ULeIr%BF*S}uIL>QZAl+&0)C;HSsm|j;g<E^CgQR;3_(}jB4%KTQyPbH%9Z=300WcCI|O>=G3QA#rBUD**P<7YD#VZimWC9"
        "aLO9(~JCep1yh*|cUU{J@>FaQa-bPRei@1b>+YEkcM?JVSXx;qnRv*mRk(zlXEt!5q@gTNu0q?QLdL+ZIo7ASx>FMcVrXJ`|uMiA"
        "P+R+pC@~x6}as`^+qVpVI{0XceUA(e2Yj1~$SaaekGm3>jV+$+4M!;C1HM)zJ5(=V(tw{$gcuY3_t<$G#3U#?|Tg)Sp;8J3*vYnJ"
        "~q9T5V$5CbTZ`=wX<b3YAfjvmiq?P!*kQDIlmcQ+2bLXpQFPZw10M!uR#J=L7t>P=vUD>)30Og|5FR|l|=&3)p5mJ`{&Iv;jHbkA"
        "jFu02c4*8}<uu-njoZEE_080Vomf09{o29T!VW!}+*NH8kB+sV`GxY1!;Ky<a>(IL;=&3yIuf+>|6h|GubCUVDS_1fXhr!%(6`(%"
        ")dYr>-"
        "t(LYh87oe2PVgn2yxc<1oX!gyT8lef&ab6=FKlYYHGsof)QO4lV_tJ<i{sBiNMgwXcDqi>R3a`9kpbn@DOq6vj;wD$i7S6Jk;c$n"
        "E&0U|T^JLoAML(d6x1X#?Q#3?ou6E2_U@-FTZY?W=N`UcEA&F4p^DxenyFFRp-yvKs0Np~)V^=0yKKM0ju%^&+b@W|&b<~>izBd="
        "4U~&#8dHXst;kV1C7cDU=#3b-2-"
        "QQonK+4}autTm_L%Q=CSRx+r5D&WTA1c3+7<=FeLJAo#IF$S7)%E{B4gKNkKBlB_$K4y+3hkJHV9uZt)X)w^oR#^;VDIe#GzE7h3"
        "b0IIYNJ^G_T|s`{@=j`6EWe?&Hu)RE*@l7Pu?+37eQ2qV~~2f?U{p$sr-Lbwu=<(G((Ng@Os-hv~;c{aCbj(z(;~p?7F(qQiQN4("
        "Om3<oxrhA)2g{W=tOu6PW9YBjN=Y&S)Tse;l;WoWIS60<ZTe5u|CFtA|_vymE(I8;AKo31RdiYqYtEpy7<$?X$O{M#H_UKUX|b(P"
        "*G=^NbxW?h_fLJ_`>H0ot3<_Lky;M>8~YL$i^RrChb5w~A(ehY|C?+bOJKd1or1edH$K#!;2b8fjyKkt%57C+`d6EuENM2Nx<h9A"
        "Ei__z)wA3A;uj*m=UP2lDk`USVi9F(o`M&Zp$LgUj^!%6A*J>c+P}GPObEA|_}Kji7ra`2VO=6bErJ>yi9&fjYix^5*dngP`3NnY"
        "XVUI5`w}dQjE@z_Yt?gYSSyFAaQ+Z|l-"
        "&GbmkxpE%ho8x=R|60Fwp!f03t<EMu;%*>gwDWxlZ3DSDZZNH~T^<`7s54ZPq7m)d_e5IZu%Zyj}BlHE6Bluf--"
        "!Q8P5x0n+EmYggz#ui7BDqR#m<sWEas?}`HzD78oL;3_rM1FtoPgkkjfwl8R6<PlxEaiDk<&Knm01wwT;6=+79)d*z3=G<Ws+kv+"
        "xtZk-"
        "R|ei6`mEhS|T!}q&&DjVg`g{Q50c9((q}%tpKN@PDgs5*qudBe=P1YQzDHhQkP%mUsRy(K4CblHAz3E0XY&qsJI91I;;xzzH_TZt"
        "-i5E!~O85e8fz3l#Q^T3vm&4j*j?Xxm`oP$$u~8RY-"
        "?7v_?rEmG9HBR?u=kRL>U9yJ260rO=6^<Ks#*Kd5WDILzzuNxVVhq*@EMu5#_vlXtQeyd2ioialUskd5jcD0oBxyJly1qrL&DFVY"
        "tr75EMPkdHJ0vQM7Gn+-"
        "rAy3GsRAMu(tkSG?FtZ10*WGgS@#YPiq!#cf8*9mGO>dtTQ*52Fm&ByKg3=}6(vNz^!Jr_Hcf6btxc?o1Iat6##;DBZAE7`X7t+-"
        "GQv&s-^3L(^dESv-&)MV^hN-"
        "0O?k`TP)GMt<!lVXLwQqewN0g{{GWy}D}mx8^=Gto1m3Ac#SnmB?PxISUcAlPu6UuxrgpIy&TveL(&vTIU7*?C;Jfz!<|k19?S%|"
        "lofFKu|s&x{xBG<n8{t_~yi=lNR|9Y#c?BiS#%So8`2O9nT?0>I$_T0ubTDKy8JSYrg-"
        "m>^7@yyF5RReJUwpquFA5s?rJ&>kKH7kDRBr<Z$~=PlI7Cz0Kbxz#vDWj{|q2j5pYI~m=RXZAIW<KsU9T8nO|G6|ih{8zjl=iX1@"
        "MX~)tw?c=4e^&HVCWAuJ>~ksRVXmq|j$*DARHD&FDOLk|k`(Fl_&Unr$G&&F_vZf}0+|2F"
    )
    EJS_CORE_B85 = (
        "c-rk->u(!3694YMf)Rphx2J64^a<&FMv*3H4`~v_&7puI*z_(XZM@>D`-q}*^}pW?-"
        "{h`jId=#2Lyf?)mNP#N=f&Z0^Z3gLC*(_V@#e?h9=*&{#%uQI=Zx_tpXaO^lXtw3Pm$`^WnPncUNEwuHKA=&u4t2|v?#V@!8ogE!"
        "!mNcCCjE+*W<^J7kRU6uamS~J>E8tvSR(1eW(HH@ySP8kq>oB&PX(GdD`S9C((*k`Iat6gw{=!^F>T<PY4;dH6!>SZH5#0Zs=k1b"
        "jj+ArfSostyolEe;6U9{3^K#$>${cp{nRM$!qZ$SrSbnsUG-b0Ot@8QZeA+WKN5kP1Mufi8mG*VlzilFurJ(<m~K>0HXf-"
        "#TPxK>?5nTQS^}(EgO-XXY5l<&i>K6(y17pjfkL*V+9vW$#!Px&34Voxt&A^G6Vny`V7{OEAB4%f#D5TjZDL`8iJ@@y*mhYg=Ll0"
        "<%&fSFEh4xZ6hLv<KFow-`=pTKPRY@?6Gko={-"
        "xPC9fN@q}#fo=?yqx*YM;VtwqM<wa`=|v|Nj!$^PZZxjZ}KA`JsElPWc^qF)KDFoqo&?v6g@Wkn*nm?_MwSY`z5t;B{%u5ysO&*h"
        "cTdz}l=tZO+O{ZU{g3gQ7Und^|D!gN$1&CZSOynfBu>$whvBuUD-mP3J*^CahK(PpqbDQE{pCnYdzxp|?UMj35rfTc1|vZhtdBtd"
        "drX4~nLS;9W8D^}OQ*}=ao*Z4_`XG@y%ho@1wt~GMO8d5+a`yow%`{hp;;ASm^>^$czn-~%yISc_OOlF_w@a$B6-"
        "7GQXMmhOAQmF)DjUw$|t`$f=n|K3rt_R59$f+5GZ)fD`#0jhjAw+Iai;|KL$sd1^aOfH2d`KP;bxQs-"
        "!rP+g3H@Nnek^NPx_>4mgo_+%Rfu3+QEPP09k&oO69zu(O^kcjp#|Rdp+?}1v|7|6a>ermaUxGH;j@Cu$rpF{gI10gD`s{0RGKt5"
        "8#G`@5lh&srwYUhjk$kJhR=-$Uo;R6E8rg5tYZCp>;<}F{sD#-9C<8^!wplfF~(4U;h8s3uz3TJQnp)-"
        "XRC`L*^P*K{tH`Ov&xx+>}EjVW}bYp6o86D2ec~}lnz^-"
        "j%9js+0CEkj}Fd{EG;N3r3(amapp|yEx`c{_5Lqf<@CB>9<U+G?9<xUyxc{sK|}b1lfZU73Mg})f41H{mEq59zfQ%_ZeskD)*1XW"
        "K6<A&_IaXW!g%cQKa4xZ#$DBSyva%}OP_t_v~=qVJ-"
        "Y!r+&WKng3z83dKH9xi%Y6q^O>n$<_!c(F;rVCJfVd@>jBa&s~u8fhhB+x#uR3=VxO9drj4q+Y;D{v0FYwjWErOdP)P}sy}PgLJx"
        "Dk+7<{Vs8N^4l1Q#VUY+tnbWvJ1G;LJ0(R_^S$Zj1=Io$q>Iai2w(B5hxa?cE~|b{wDSspNVZu+2=_?YN*)L$Yq`W#mRJrz^0dT9"
        "u1m>p%dnIk>{^8v9p?B7Y@C{;IRm!)ry>uO;i(9oCssjqZYS)Y)DGllMiuZ*sw4!(Z|~K;GW%r>D-"
        "a9%)Mq>6NH;aLI5A+@1VN2^R~52MiEmh#kplWWQRY%WtGgzX?=&h~-"
        "<!@~y`*i`|+{tPQF#q}cC*+VSA`$n!O^;^Xbux1ZTrox_N;wc%Mrz_{C8_bjH2<PbrKOah|24Mcnd*!PYP@$aO%zq@B<_+GMo-"
        "^mOU@0hjEQlD$9@W>^9J2u#lWd8<RgL#wyenfUQ1<Qp+n<-J`9uJjTU#ldo7%*Lw1)PV42I2#Su8v^ugykXF$P12d{pUP2)zy0*-"
        "9i!>5xx_)x_!^JN3~UfEvSdLs^gSsBzLY|91V0wYg@KWd(A{kYlA8}|9B=_TaPw5uLmPCz+W&OIVX&#;Q8;~{`{<5txFENi(nuoV"
        "_W#g6BGu-NNUzZ0}i}gK9d4M5z>?(qB_nmSn~#-U`)d482DUbut;rb@mnPLV-"
        "T08w23Ur>kWUS>YG<!7fmS994`V8bP>dgrQ%f4FdYa2^p3I;%VrIJEaXR8z<LKWdqP(&7>OWOEP4!)oDqMn!PGbE+YUc=c4fFMRM"
        "G;KR1YMRGQPqD&4O!#)*%CQw2nGQ{~AeJs4oo~AH?MR+>Y)58)m+ep&a`sFIZ%|eg*I-"
        "kl!>oQNHH%+!jT7O$+RrCcpji@+WYix9s<p0S>0qfpLO?QOp4j2)ea4J(i?eP-nh(Z(kmRT$HIy&1cpg*qEx9V=@?woJVC1b@E`d"
        "*(8qNhZHi+9Hgq)94K@Q1(f}9WVuV&Wplot-"
        "=$sCy55vk7A#~<o23#{&gKo4RTI*qqSLZ4le&X7qg9Hk+Anfjvr5gU9}8>Ao%NtaINP8dqkCy9?zn;jo|UOMksRY1mR4sGnSdkF-"
        "8nQ1ryuhLo<5J6#v#7%JT)uk$4nvVoF|7sL5W$pIR;i!c7R2`kWItM{ube14Z^<~g#XtDq47JYULcDh(wl;Ap?Gq;-"
        "ln!#RCLwZ$pq!ZB`m;oFKpEa3}u$jw+dO|cr0~Uw7MAp+w6t@8U<L2$-"
        "T&s1*<Abd+#zdm{W2Fu;JPJPtgcH>FM4b=u=5$uGVeCvY^{^cOz@0s{i370JlXm410P`ck2MVIJE?vdpcm9Mxkogu3+~3*J>N-"
        "V@6;9(7Ux%{v>i~Qm^p>I(jl9PejDn3QX~+DCiXMu2*`I(d)ZjV5oDZD~Idb*RWmVrC}7w<Ahp7y~$x`CXo<3%)!{Igw%5CyMao;"
        "AQ`}^`=*IA?sdbu?XPHxtfTG$)pohiw6hpfSI`sgjRm*UCc+ZnJ8c<}27`X=U5v6%>+pBG{l_6lpYLfWI#3Qy97LVIygUeQ?d@+!"
        "_K<SY9TMh!dY5@m|5xTU{m4J7f$wJ*Kd|<Ihjt;7A<Pq}@ubh@g7%(f)t}9>f}(HOau5nUgk|;yd#Ey39I0uoOlWi~;5;uHNI3Sz"
        "hfe?V*oNtWmg(71Ez_Rsd0!#ABeQo3eK|3?^V;9f(pDcmclAz{V4F>TW}cT&5s9-"
        "f?9tQNNS^wqGkMkF)e#1Qh__!tJdG%~M}XAVBZky#v`R8pi9(cw%SvNKZ*-"
        "GNQjQMq%6Pl!)_oET7V~*<z~}+?REc7S?q1lPNL>2_{k7mS&TF&v)Gkm)(iL8S2`qC_g=YWEtGaGAw&z07y%ba{axYf<F6R#1t;)"
        "i4Z*^v>D5y$9#6DC9SvTK0i1;Hqt3r2uqv|?v@AwTIQDFvbe)pmutSRNsiZ#pf5J9~xt7b`YB8>Ge$u4{}JMK#PKzZq~>|KJbY6J"
        "D$d2Q?7_Mddm1MVtSiHU{2d*j-"
        "d(Oy*L>J6O4XvMN9buM1r<O5!&Q<~^P%A|&W>a=EB+NPWz5rGyN1V7K3$K8n6<+xczecxvKWzIqSVJlrpR;wP?1#2R=H_ZU8Qdh%"
        "4kNMJwf~mTv7k}#{9=i2jTVRF0)v)V<Ot>?>o2J^@E~l0;p;;E$Y4wV9FM0<lM3nN(=~&AJ$o$OWPM=yd#SMO)|J(A)>f!wrFYU2"
        "-Ox{1dRgfP_sP(XE9`D{?O*}*oP+W+fc3^W386nRC>?xd;H1{l7(RK6*4ffBA*RK+(UpNFspW=Am^vWBI1nLFIIDsMvOe??l_sX5"
        "^1)!C;_?-vcoM4$eh!I`B3Tmg)Sc_p>JDztt8<Is5#)fdLpxn7GB~j3*fZb2EDZFs)3h8w?Krd_fL)-"
        "+&nJU?;uZ6ZFCrI2^Z1szccAX<E2S#!e@4G}Z-Y?t*eI7r@<mw&2;pGN{U0xALvWK@8dUvHWNO&nOmkpw;^-"
        "nF+%&mJK$nie0x_hz`&>7I8zMy#lRdZA7GRqg!c+8cP?nA*vBp)G#&XDe<Fm0%LlXnhAey&<cC;n?vC{Vh@@_{dyvZMJfY&kVwM@"
        "n@Lf%|p@ghSt2OlCpF{C8UQWEYQM1yH^66uaBc@j<W$pOY(<bdnXgHC-?WUj0P8mAtzOSjL8Bx8F89FEGls0X>QxEwG4<nXwZ-"
        "JNv58p5VtevK*4wmu_fUCCb6RfEUf2Fq(VbOO^;ajp=uTA&E^+;DFcp?+KHW{{XxUi68"
    )
    def __init__(self, *, timeout: float = 20.0, retries: int = 2, proxy: str | Mapping[str, str] | None = None, node_path: str | None = None, js_timeout: float = 30.0, verify_ssl: bool = True, preferred_language: str | None = None, preferred_codecs: Sequence[str] = ("opus", "mp4a", "vorbis", "aac"), allow_muxed_fallback: bool = False, validate_url: bool = False, logger_handle: Callable[[str], None] | None = None,) -> None:
        if retries < 0: raise ValueError("retries cannot be negative")
        if timeout <= 0 or js_timeout <= 0: raise ValueError("timeout and js_timeout must be positive")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.js_timeout = float(js_timeout)
        self.preferred_language = preferred_language
        self.preferred_codecs = tuple(x.lower() for x in preferred_codecs)
        self.allow_muxed_fallback = bool(allow_muxed_fallback)
        self.validate_url = bool(validate_url)
        self.logger_handle = logger_handle
        self._explicit_node_path = node_path
        self._resolved_node: tuple[str, tuple[int, ...]] | None = None
        self._player_code_cache: dict[str, str] = {}
        self._challenge_cache: dict[tuple[str, str, str], str] = {}
        self._ejs_cache: tuple[str, str] | None = None
        context = ssl.create_default_context()
        if not verify_ssl: context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
        proxy_map: Mapping[str, str] | None = {"http": proxy, "https": proxy} if isinstance(proxy, str) else proxy
        self._cookie_jar = http.cookiejar.CookieJar()
        handlers: list[Any] = [urllib.request.ProxyHandler(dict(proxy_map) if proxy_map is not None else None), urllib.request.HTTPCookieProcessor(self._cookie_jar), urllib.request.HTTPSHandler(context=context),]
        self._opener = urllib.request.build_opener(*handlers)
        self.installanonymouscookie("SOCS", "CAI")
        self.installanonymouscookie("PREF", "hl=en&tz=UTC")
    '''call'''
    def __call__(self, youtube_url: str) -> dict[str, Any]:
        return self.extract(youtube_url)
    '''extractvideoid'''
    @classmethod
    def extractvideoid(cls, youtube_url: str) -> str:
        if not isinstance(youtube_url, str): raise cls.InvalidURLError("YouTube URL must be a string")
        if cls.VIDEO_ID_RE.fullmatch((value := youtube_url.strip())): return value
        candidate = value if "://" in value else f"https://{value}"
        try: parsed = urllib.parse.urlsplit(candidate)
        except ValueError as exc: raise cls.InvalidURLError(f"Invalid YouTube URL: {youtube_url!r}") from exc
        if (host := (parsed.hostname or "").lower().rstrip(".")).startswith("www."): host = host[4:]
        video_id: str | None = None
        if host == "youtu.be": video_id = parsed.path.strip("/").split("/", 1)[0]
        elif (host == "youtube.com" or host.endswith(".youtube.com") or host == "youtube-nocookie.com" or host.endswith(".youtube-nocookie.com")):
            parts = [urllib.parse.unquote(x) for x in parsed.path.split("/") if x]
            if parts and parts[0] in {"embed", "e", "v", "shorts", "live"} and len(parts) > 1: video_id = parts[1]
            else: video_id = urllib.parse.parse_qs(parsed.query).get("v", [None])[0]
        if not video_id or not cls.VIDEO_ID_RE.fullmatch(video_id): raise cls.InvalidURLError(f"Unsupported or invalid YouTube URL: {youtube_url!r}")
        return video_id
    '''getaudiourl'''
    def getaudiourl(self, youtube_url: str) -> str:
        return self.extract(youtube_url)["audio_url"]
    '''getmetadata'''
    def getmetadata(self, youtube_url: str) -> dict[str, Any]:
        video_id = self.extractvideoid(youtube_url); _, ytcfg, initial_response = self.loadwatchcontext(video_id)
        responses: list[tuple[str, dict[str, Any]]] = []; errors: list[str] = []
        if self.validplayerresponse(initial_response, video_id): responses.append(("web", initial_response))
        video_details, microformat = self.mergeresponsemetadata(responses)
        if not (video_details or microformat):
            visitor_data = YouTubeAudioURLExtractor.firststring(YouTubeAudioURLExtractor.dig(ytcfg, "VISITOR_DATA"), YouTubeAudioURLExtractor.dig(ytcfg, "INNERTUBE_CONTEXT", "client", "visitorData"), YouTubeAudioURLExtractor.dig(initial_response, "responseContext", "visitorData"),)
            for client in ("visionos", "web"):
                try: response = self.callplayerapi(client, video_id, ytcfg, visitor_data, player_url=None,)
                except self.Error as exc: errors.append(str(exc)); self.printlog(f"metadata {client} client failed: {exc}"); continue
                if self.validplayerresponse(response, video_id):
                    responses.append((client, response)); video_details, microformat = self.mergeresponsemetadata(responses)
                    if video_details or microformat: break
        if not (video_details or microformat):
            if responses: raise self.playabilityerror(video_id, responses)
            detail = "; ".join(dict.fromkeys(errors)) or "no metadata response was returned"
            raise self.NetworkError(f"Unable to obtain YouTube metadata for {video_id}: {detail}")
        metadata = self.buildmetadata(video_id, video_details, microformat)
        status_data = next((response.get("playabilityStatus") for _, response in responses if isinstance(response.get("playabilityStatus"), Mapping)), {},)
        metadata.update({"playability_status": status_data.get("status"), "playability_reason": self.playabilityreason(status_data),})
        return metadata
    '''extract'''
    def extract(self, youtube_url: str) -> dict[str, Any]:
        return self.getaudioinfo(youtube_url)
    '''getaudioinfo'''
    def getaudioinfo(self, youtube_url: str) -> dict[str, Any]:
        video_id = self.extractvideoid(youtube_url); webpage, ytcfg, initial_response = self.loadwatchcontext(video_id); player_url = self.extractplayerurl(ytcfg, webpage)
        responses: list[tuple[str, dict[str, Any]]] = []; errors: list[str] = []
        if self.validplayerresponse(initial_response, video_id): responses.append(("web", initial_response))
        visitor_data = YouTubeAudioURLExtractor.firststring(YouTubeAudioURLExtractor.dig(ytcfg, "VISITOR_DATA"), YouTubeAudioURLExtractor.dig(ytcfg, "INNERTUBE_CONTEXT", "client", "visitorData"), YouTubeAudioURLExtractor.dig(initial_response, "responseContext", "visitorData"),)
        try:
            vision_response = self.callplayerapi("visionos", video_id, ytcfg, visitor_data, player_url=None)
            if self.validplayerresponse(vision_response, video_id): responses.append(("visionos", vision_response))
            else: errors.append("visionos client returned an invalid player response")
        except self.Error as exc: errors.append(str(exc)); self.printlog(f"visionos client failed: {exc}")
        vision_playable = next((response for client, response in responses if client == "visionos" and YouTubeAudioURLExtractor.playabilitystatus(response) == "OK" and self.hasstreamingdata(response)), None,)
        if vision_playable is None:
            if not player_url:
                try: player_url = self.discoverplayerurl(video_id, webpage)
                except self.Error as exc: errors.append(str(exc))
            for fallback_client in ("web_embedded", "tv_downgraded"):
                try:
                    fallback_response = self.callplayerapi(fallback_client, video_id, ytcfg, visitor_data, player_url=player_url,)
                    if self.validplayerresponse(fallback_response, video_id): responses.append((fallback_client, fallback_response))
                except self.Error as exc: errors.append(str(exc)); self.printlog(f"{fallback_client} client failed: {exc}")
        if not any(response.get("streamingData") for _, response in responses):
            try:
                if not player_url: player_url = self.discoverplayerurl(video_id, webpage)
                web_response = self.callplayerapi("web", video_id, ytcfg, visitor_data, player_url=player_url)
                if self.validplayerresponse(web_response, video_id): responses.append(("web", web_response))
            except self.Error as exc: errors.append(str(exc)); self.printlog(f"web client failed: {exc}")
        if not responses: detail = "; ".join(dict.fromkeys(errors)) or "no player response was returned"; raise self.NetworkError(f"Unable to obtain YouTube player data for {video_id}: {detail}")
        playable = [(client, response) for client, response in responses if YouTubeAudioURLExtractor.playabilitystatus(response) in {"OK", "LIVE_STREAM_OFFLINE"}]
        if not playable: raise self.playabilityerror(video_id, responses)
        video_details, microformat = self.mergeresponsemetadata(playable)
        duration = YouTubeAudioURLExtractor.intornone(video_details.get("lengthSeconds")); saw_pot_restricted_audio = False
        candidates: list[dict[str, Any]] = []; hls_manifests: list[tuple[str, str]] = []; dash_manifests: list[tuple[str, str]] = []
        for client, response in playable:
            if not isinstance((streaming_data := response.get("streamingData")), dict): continue
            for raw_format in self.iterstreamformats(streaming_data):
                if not (candidate := self.candidatefromformat(raw_format, client, duration)): continue
                if candidate.pop("_pot_restricted", False): saw_pot_restricted_audio = True; continue
                candidates.append(candidate)
            if YouTubeAudioURLExtractor.ishttpurl((hls_url := streaming_data.get("hlsManifestUrl"))): hls_manifests.append((client, hls_url))
            if YouTubeAudioURLExtractor.ishttpurl((dash_url := streaming_data.get("dashManifestUrl"))): dash_manifests.append((client, dash_url))
        js_error: Exception | None = None
        if candidates:
            try:
                if not player_url and YouTubeAudioURLExtractor.candidatesneedplayer(candidates): player_url = self.discoverplayerurl(video_id, webpage)
                candidates = self.resolvecandidateurls(candidates, video_id, player_url)
            except self.JavaScriptRuntimeError as exc: js_error = exc; self.printlog(str(exc)); candidates = [c for c in candidates if not c.get("_needs_js")]
        if (selected := self.selectcandidate(candidates)): return self.finalizeinfo(selected, video_id, video_details, microformat)
        for client, manifest_url in hls_manifests:
            try:
                candidate = self.extracthlsaudio(manifest_url, client, video_id, player_url, video_details)
                if candidate and (not self.validate_url or self.probeurl(candidate["url"], manifest=True)): return self.finalizeinfo(candidate, video_id, video_details, microformat)
            except self.Error as exc: errors.append(str(exc))
        for client, manifest_url in dash_manifests:
            try:
                manifest_candidates = self.extractdashaudio(manifest_url, client, video_id, player_url, duration)
                if (selected := self.selectcandidate(manifest_candidates)): return self.finalizeinfo(selected, video_id, video_details, microformat)
            except self.Error as exc: errors.append(str(exc))
        if js_error: raise js_error
        if saw_pot_restricted_audio: raise self.NoAudioFormatError(f"YouTube exposed audio formats for {video_id}, but all anonymous URLs require " "a GVS PO token and were discarded exactly as in the pinned upstream policy")
        detail = "; ".join(dict.fromkeys(errors)); suffix = f" ({detail})" if detail else ""
        raise self.NoAudioFormatError(f"No non-DRM anonymous audio download URL was found for {video_id}{suffix}")
    '''installanonymouscookie'''
    def installanonymouscookie(self, name: str, value: str) -> None:
        cookie = http.cookiejar.Cookie(version=0, name=name, value=value, port=None, port_specified=False, domain=".youtube.com", domain_specified=True, domain_initial_dot=True, path="/", path_specified=True, secure=True, expires=None, discard=True, comment=None, comment_url=None, rest={},)
        self._cookie_jar.set_cookie(cookie)
    '''loadwatchcontext'''
    def loadwatchcontext(self, video_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        urls = (f"https://www.youtube.com/watch?v={video_id}&bpctr=9999999999&has_verified=1", f"https://www.youtube.com/embed/{video_id}?html5=1",); last_error: Exception | None = None
        for url in urls:
            try: webpage = self.requesttext(url, headers={"Accept-Language": "en-US,en;q=0.9"})
            except self.Error as exc: last_error = exc; continue
            ytcfg = self.extractytcfg(webpage); initial_response = self.extractinitialplayerresponse(webpage)
            if ytcfg or initial_response: return webpage, ytcfg, initial_response
        if last_error: self.printlog(f"watch page unavailable; attempting the player API directly: {last_error}")
        return "", {}, {}
    '''callplayerapi'''
    def callplayerapi(self, client_name: str, video_id: str, webpage_ytcfg: Mapping[str, Any], visitor_data: str | None, *, player_url: str | None,) -> dict[str, Any]:
        definition = copy.deepcopy(YouTubeAudioURLExtractor.CLIENTS[client_name])
        if client_name == "web":
            if isinstance((page_context := webpage_ytcfg.get("INNERTUBE_CONTEXT")), dict): definition["context"] = copy.deepcopy(page_context)
            if (page_number := YouTubeAudioURLExtractor.intornone(webpage_ytcfg.get("INNERTUBE_CONTEXT_CLIENT_NAME"))) is not None: definition["number"] = page_number
        context = definition["context"]; client: dict = context.setdefault("client", {}); client.update({"hl": "en", "timeZone": "UTC", "utcOffsetMinutes": 0})
        if visitor_data: client["visitorData"] = visitor_data
        content_playback_context: dict[str, Any] = {"html5Preference": "HTML5_PREF_WANTS"}
        if definition["requires_js_player"] and player_url:
            if (sts := self.signaturetimestamp(webpage_ytcfg, video_id, player_url)) is not None: content_playback_context["signatureTimestamp"] = sts
        body = {"context": context, "videoId": video_id, "playbackContext": {"contentPlaybackContext": content_playback_context}, "contentCheckOk": True, "racyCheckOk": True,}
        api_key = YouTubeAudioURLExtractor.firststring(webpage_ytcfg.get("INNERTUBE_API_KEY"), YouTubeAudioURLExtractor.DEFAULT_API_KEY)
        host = YouTubeAudioURLExtractor.firststring(webpage_ytcfg.get("INNERTUBE_HOST"), definition["host"])
        query = urllib.parse.urlencode({"key": api_key, "prettyPrint": "false"})
        headers = {"Content-Type": "application/json", "Origin": f"https://{host}", "X-YouTube-Client-Name": str(definition["number"]), "X-YouTube-Client-Version": str(client.get("clientVersion", "")), "User-Agent": str(client.get("userAgent") or YouTubeAudioURLExtractor.WEB_USER_AGENT)}
        if visitor_data: headers["X-Goog-Visitor-Id"] = visitor_data
        return self.requestjson(f"https://{host}/youtubei/v1/player?{query}", data=body, headers=headers)
    '''signaturetimestamp'''
    def signaturetimestamp(self, ytcfg: Mapping[str, Any], video_id: str, player_url: str) -> int | None:
        if (sts := YouTubeAudioURLExtractor.intornone(ytcfg.get("STS"))): return sts
        try: code = self.loadplayercode(video_id, player_url)
        except self.Error: return None
        match = re.search(r"(?:signatureTimestamp|sts)\s*:\s*(?P<sts>[0-9]{5,})", code)
        return int(match.group("sts")) if match else None
    '''candidatefromformat'''
    def candidatefromformat(self, raw: Mapping[str, Any], client: str, video_duration: int | None) -> dict[str, Any] | None:
        if raw.get("drmFamilies") or raw.get("drmTrackType"): return None
        if raw.get("type") == "FORMAT_STREAM_TYPE_OTF": return None
        if raw.get("targetDurationSec"): return None
        mime_type = str(raw.get("mimeType") or ""); media_type, codecs = YouTubeAudioURLExtractor.parsemimetype(mime_type)
        audio_only = media_type.startswith("audio/") or (bool(raw.get("audioQuality")) and not raw.get("width") and not raw.get("height"))
        if not audio_only and not self.allow_muxed_fallback: return None
        if not audio_only and not raw.get("audioQuality") and not codecs: return None
        if not (audio_codec := YouTubeAudioURLExtractor.audiocodec(codecs)) and audio_only and codecs: audio_codec = codecs[0]
        itag = str(raw.get("itag") or ""); raw_url = raw.get("url"); cipher = raw.get("signatureCipher") or raw.get("cipher")
        if not YouTubeAudioURLExtractor.ishttpurl(raw_url) and not isinstance(cipher, str): return None
        audio_track = raw.get("audioTrack") if isinstance(raw.get("audioTrack"), dict) else {}
        display_name = str(audio_track.get("displayName") or "")
        language = str(audio_track.get("id") or "").split(".", 1)[0] or None
        bitrate = YouTubeAudioURLExtractor.intornone(raw.get("averageBitrate") or raw.get("bitrate"))
        approx_ms = YouTubeAudioURLExtractor.intornone(raw.get("approxDurationMs"))
        damaged = bool(video_duration and approx_ms and approx_ms / 1000 < video_duration / 2)
        if not YouTubeAudioURLExtractor.ishttpurl((url_for_policy := raw_url)) and isinstance(cipher, str): url_for_policy = urllib.parse.parse_qs(cipher).get("url", [None])[0]
        has_pot = bool(YouTubeAudioURLExtractor.ishttpurl(url_for_policy) and urllib.parse.parse_qs(urllib.parse.urlsplit(url_for_policy).query).get("pot"))
        pot_restricted = bool(YouTubeAudioURLExtractor.CLIENTS.get(client, {}).get("gvs_pot_required") and itag != "18" and not has_pot)
        candidate: dict[str, Any] = {"url": raw_url if YouTubeAudioURLExtractor.ishttpurl(raw_url) else None, "_cipher": cipher if isinstance(cipher, str) else None, "_needs_js": bool(cipher), "_pot_restricted": pot_restricted, "format_id": itag or None, "itag": YouTubeAudioURLExtractor.intornone(itag), "mime_type": media_type or None, "ext": YouTubeAudioURLExtractor.extensionformime(media_type), "audio_codec": audio_codec, "audio_bitrate": bitrate, "audio_sample_rate": YouTubeAudioURLExtractor.intornone(raw.get("audioSampleRate")), "audio_channels": YouTubeAudioURLExtractor.intornone(raw.get("audioChannels")), "content_length": YouTubeAudioURLExtractor.intornone(raw.get("contentLength")), "approx_duration_ms": approx_ms, "audio_quality": raw.get("audioQuality"), "language": language, "language_name": display_name or None, "is_default_audio": bool(audio_track.get("audioIsDefault")), "is_original_audio": "original" in display_name.lower(), "is_drc": bool(raw.get("isDrc")), "is_audio_only": audio_only, "is_manifest": False, "client": client, "_damaged": damaged,}
        return candidate
    '''resolvecandidateurls'''
    def resolvecandidateurls(self, candidates: list[dict[str, Any]], video_id: str, player_url: str | None,) -> list[dict[str, Any]]:
        signatures: set[str] = set(); nsigs: set[str] = set()
        for candidate in candidates:
            if (cipher := candidate.get("_cipher")):
                parsed_cipher = urllib.parse.parse_qs(cipher); candidate["_parsed_cipher"] = parsed_cipher
                candidate["url"] = parsed_cipher.get("url", [None])[0]; signature = parsed_cipher.get("s", [None])[0]
                if signature: candidate["_signature"] = signature; signatures.add(signature)
            if YouTubeAudioURLExtractor.ishttpurl((url := candidate.get("url"))):
                n_value = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query, keep_blank_values=True).get("n", [None])[0]
                if n_value: candidate["_n"] = n_value; nsigs.add(n_value)
            candidate["_needs_js"] = bool(candidate.get("_signature") or candidate.get("_n"))
        solved: dict[str, dict[str, str]] = {"sig": {}, "n": {}}
        if signatures or nsigs:
            if not player_url: raise self.JavaScriptRuntimeError("The selected formats require player challenges, but no player JavaScript URL was found")
            player_code = self.loadplayercode(video_id, player_url); solved = self.solvechallenges(player_url, player_code, signatures=signatures, nsigs=nsigs)
        resolved: list[dict[str, Any]] = []
        for candidate in candidates:
            if not YouTubeAudioURLExtractor.ishttpurl((url := candidate.get("url"))): continue
            if (signature := candidate.get("_signature")):
                if not (result := solved["sig"].get(signature)): continue
                cipher = candidate.get("_parsed_cipher") or {}
                parameter = cipher.get("sp", ["signature"])[-1] or "signature"
                url = self.updatequery(url, {parameter: result})
            if (n_value := candidate.get("_n")):
                if not (result := solved["n"].get(n_value)) or result.endswith(n_value): continue
                url = self.updatequery(url, {"n": result})
            candidate["url"] = url; resolved.append(candidate)
        return resolved
    '''solvechallenges'''
    def solvechallenges(self, player_url: str, player_code: str, *, signatures: Iterable[str] = (), nsigs: Iterable[str] = (),) -> dict[str, dict[str, str]]:
        player_id_match = YouTubeAudioURLExtractor.PLAYER_ID_RE.search(player_url)
        player_id = player_id_match.group("id") if player_id_match else player_url
        wanted = {"n": sorted(set(nsigs)), "sig": sorted(set(signatures)),}
        results: dict[str, dict[str, str]] = {"n": {}, "sig": {}}; requests: list[dict[str, Any]] = []; request_types: list[str] = []
        for challenge_type in ("n", "sig"):
            missing: list[str] = []
            for challenge in wanted[challenge_type]:
                cached = self._challenge_cache.get((player_id, challenge_type, challenge))
                if cached is not None: results[challenge_type][challenge] = cached
                else: missing.append(challenge)
            if missing: requests.append({"type": challenge_type, "challenges": missing}); request_types.append(challenge_type)
        if not requests: return results
        payload = {"type": "player", "player": player_code, "requests": requests, "output_preprocessed": False,}; output = self.runejs(payload); responses = output.get("responses")
        if output.get("type") == "error" or not isinstance(responses, list): raise self.JavaScriptRuntimeError(f"EJS {self.EJS_VERSION} failed to preprocess the YouTube player: " f"{output.get('error') or 'invalid solver response'}")
        if len(responses) != len(requests): raise self.JavaScriptRuntimeError("EJS returned an incomplete challenge response")
        for challenge_type, request, response in zip(request_types, requests, responses, strict=True):
            data = response.get("data") if isinstance(response, dict) else None
            if not isinstance(data, dict) or response.get("type") == "error": raise self.JavaScriptRuntimeError(f"EJS could not solve the {challenge_type} challenge: " f"{response.get('error') if isinstance(response, dict) else 'invalid response'}")
            for challenge in request["challenges"]:
                if not isinstance((result := data.get(challenge)), str): raise self.JavaScriptRuntimeError(f"EJS omitted a {challenge_type} challenge result")
                self._challenge_cache[(player_id, challenge_type, challenge)] = result; results[challenge_type][challenge] = result
        return results
    '''runejs'''
    def runejs(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        node_path, node_version = self.findnode(); lib_script, core_script = self.embeddedejs()
        script = (f"{lib_script}\n" "Object.assign(globalThis, lib);\n" f"{core_script}\n" f"console.log(JSON.stringify(jsc({json.dumps(payload, ensure_ascii=False)})));\n"); command = [node_path]
        if node_version >= (23, 5, 0): command.extend(["--permission", "--no-warnings"])
        else: command.extend(["--experimental-permission", "--no-warnings=ExperimentalWarning"])
        command.append("-"); creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try: process = subprocess.run(command, input=script, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.js_timeout, check=False, creationflags=creationflags,)
        except (OSError, subprocess.SubprocessError) as exc: raise self.JavaScriptRuntimeError(f"Unable to run Node.js EJS solver: {exc}") from exc
        if process.returncode: stderr = YouTubeAudioURLExtractor.cleannodestderr(process.stderr); raise self.JavaScriptRuntimeError(f"Node.js EJS solver exited with {process.returncode}: {stderr or 'no error text'}")
        lines = [line for line in process.stdout.splitlines() if line.strip()]
        if not lines: raise self.JavaScriptRuntimeError("Node.js EJS solver produced no JSON output")
        try: output: dict = json.loads(lines[-1])
        except json.JSONDecodeError as exc: raise self.JavaScriptRuntimeError("Node.js EJS solver produced invalid JSON") from exc
        if not isinstance(output, dict): raise self.JavaScriptRuntimeError("Node.js EJS solver produced an invalid result")
        return output
    '''embeddedejs'''
    def embeddedejs(self) -> tuple[str, str]:
        if self._ejs_cache is not None: return self._ejs_cache
        try:
            lib_script = zlib.decompress(base64.b85decode("".join(YouTubeAudioURLExtractor.EJS_LIB_B85.split()).encode("ascii"))).decode("utf-8")
            core_script = zlib.decompress(base64.b85decode("".join(YouTubeAudioURLExtractor.EJS_CORE_B85.split()).encode("ascii"))).decode("utf-8")
        except Exception as exc: raise self.JavaScriptRuntimeError("The embedded EJS payload is corrupt") from exc
        if hashlib.sha3_512(lib_script.encode()).hexdigest() != YouTubeAudioURLExtractor.EJS_LIB_SHA3_512: raise self.JavaScriptRuntimeError("Embedded EJS library integrity check failed")
        if hashlib.sha3_512(core_script.encode()).hexdigest() != YouTubeAudioURLExtractor.EJS_CORE_SHA3_512: raise self.JavaScriptRuntimeError("Embedded EJS core integrity check failed")
        self._ejs_cache = lib_script, core_script
        return self._ejs_cache
    '''findnode'''
    def findnode(self) -> tuple[str, tuple[int, ...]]:
        if self._resolved_node is not None: return self._resolved_node
        path = self._explicit_node_path or shutil.which("node") or shutil.which("nodejs")
        if not path: raise self.JavaScriptRuntimeError("This audio URL requires a YouTube player challenge. Install Node.js 20+ or pass node_path=...")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try: process = subprocess.run([path, "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False, creationflags=creationflags,)
        except (OSError, subprocess.SubprocessError) as exc: raise self.JavaScriptRuntimeError(f"Cannot execute Node.js at {path!r}: {exc}") from exc
        match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", process.stdout)
        if process.returncode or not match: raise self.JavaScriptRuntimeError(f"Cannot determine Node.js version at {path!r}")
        if (version := tuple(map(int, match.groups()))) < (20, 0, 0): raise self.JavaScriptRuntimeError(f"Node.js 20+ is required for the EJS solver; found {process.stdout.strip()}")
        self._resolved_node = os.path.abspath(path), version
        return self._resolved_node
    '''extracthlsaudio'''
    def extracthlsaudio(self, manifest_url: str, client: str, video_id: str, player_url: str | None, video_details: Mapping[str, Any],) -> dict[str, Any] | None:
        manifest_url = self.solvemanifesturl(manifest_url, video_id, player_url)
        if "#EXTM3U" not in (manifest := self.requesttext(manifest_url, max_size=5 * 1024 * 1024)): return None
        choices: list[dict[str, Any]] = []
        for line in manifest.splitlines():
            if not line.startswith("#EXT-X-MEDIA:"): continue
            attrs = self.parsem3u8attributes(line.partition(":")[2])
            if attrs.get("TYPE") != "AUDIO" or not attrs.get("URI"): continue
            uri = urllib.parse.urljoin(manifest_url, attrs["URI"]); uri = self.solveurln(uri, video_id, player_url); language = attrs.get("LANGUAGE") or None
            channels = YouTubeAudioURLExtractor.intornone((attrs.get("CHANNELS") or "").split("/", 1)[0])
            choices.append({"url": uri, "format_id": f"hls-audio-{attrs.get('GROUP-ID') or 'default'}", "itag": None, "mime_type": "application/vnd.apple.mpegurl", "ext": "m3u8", "audio_codec": None, "audio_bitrate": None, "audio_sample_rate": None, "audio_channels": channels, "content_length": None, "approx_duration_ms": YouTubeAudioURLExtractor.intornone(video_details.get("lengthSeconds")) * 1000 if YouTubeAudioURLExtractor.intornone(video_details.get("lengthSeconds")) else None, "audio_quality": None, "language": language, "language_name": attrs.get("NAME") or None, "is_default_audio": attrs.get("DEFAULT") == "YES", "is_original_audio": "original" in (attrs.get("NAME") or "").lower(), "is_drc": False, "is_audio_only": True, "is_manifest": True, "client": client, "_damaged": False,})
        return max(choices, key=self.candidaterank) if choices else None
    '''extractdashaudio'''
    def extractdashaudio(self, manifest_url: str, client: str, video_id: str, player_url: str | None, video_duration: int | None,) -> list[dict[str, Any]]:
        manifest_url = self.solvemanifesturl(manifest_url, video_id, player_url)
        xml_text = self.requesttext(manifest_url, max_size=8 * 1024 * 1024)
        try: root = ET.fromstring(xml_text)
        except ET.ParseError as exc: raise self.NetworkError("YouTube returned an invalid DASH manifest") from exc
        results: list[dict[str, Any]] = []
        for adaptation in root.iter():
            if YouTubeAudioURLExtractor.xmlname(adaptation.tag) != "AdaptationSet": continue
            adaptation_mime = adaptation.attrib.get("mimeType", "")
            content_type = adaptation.attrib.get("contentType", "")
            if content_type != "audio" and not adaptation_mime.startswith("audio/"): continue
            language = adaptation.attrib.get("lang")
            inherited_base = next(((node.text or "").strip() for node in adaptation if YouTubeAudioURLExtractor.xmlname(node.tag) == "BaseURL" and (node.text or "").strip()), None,)
            for representation in adaptation:
                if YouTubeAudioURLExtractor.xmlname(representation.tag) != "Representation": continue
                if not (base_url := next(((node.text or "").strip() for node in representation if YouTubeAudioURLExtractor.xmlname(node.tag) == "BaseURL" and (node.text or "").strip()), inherited_base,)): continue
                url = urllib.parse.urljoin(manifest_url, base_url); url = self.solveurln(url, video_id, player_url)
                mime = representation.attrib.get("mimeType") or adaptation_mime
                codecs = representation.attrib.get("codecs") or adaptation.attrib.get("codecs") or ""
                results.append({"url": url, "format_id": representation.attrib.get("id") or "dash-audio", "itag": YouTubeAudioURLExtractor.intornone(representation.attrib.get("id")), "mime_type": mime or None, "ext": YouTubeAudioURLExtractor.extensionformime(mime), "audio_codec": YouTubeAudioURLExtractor.audiocodec([codecs]) or codecs or None, "audio_bitrate": YouTubeAudioURLExtractor.intornone(representation.attrib.get("bandwidth")), "audio_sample_rate": YouTubeAudioURLExtractor.intornone(representation.attrib.get("audioSamplingRate")), "audio_channels": None, "content_length": None, "approx_duration_ms": video_duration * 1000 if video_duration else None, "audio_quality": None, "language": language, "language_name": None, "is_default_audio": False, "is_original_audio": False, "is_drc": False, "is_audio_only": True, "is_manifest": False, "client": client, "_damaged": False,})
        return results
    '''solvemanifesturl'''
    def solvemanifesturl(self, manifest_url: str, video_id: str, player_url: str | None) -> str:
        if not (match := re.search(r"/n/([^/]+)/", urllib.parse.urlsplit(manifest_url).path)): return self.solveurln(manifest_url, video_id, player_url)
        if not player_url: raise self.JavaScriptRuntimeError("Manifest n challenge has no player URL")
        challenge, player_code = match.group(1), self.loadplayercode(video_id, player_url)
        result = self.solvechallenges(player_url, player_code, nsigs=[challenge])["n"].get(challenge)
        if not result: raise self.JavaScriptRuntimeError("Unable to solve manifest n challenge")
        path = (parts := urllib.parse.urlsplit(manifest_url)).path.replace(f"/n/{challenge}/", f"/n/{result}/", 1)
        manifest_url = urllib.parse.urlunsplit(parts._replace(path=path))
        return self.solveurln(manifest_url, video_id, player_url)
    '''solveurln'''
    def solveurln(self, url: str, video_id: str, player_url: str | None) -> str:
        if not (n_value := urllib.parse.parse_qs(urllib.parse.urlsplit(url).query, keep_blank_values=True).get("n", [None])[0]): return url
        if not player_url: raise self.JavaScriptRuntimeError("URL n challenge has no player URL")
        player_code = self.loadplayercode(video_id, player_url)
        result = self.solvechallenges(player_url, player_code, nsigs=[n_value])["n"].get(n_value)
        if not result or result.endswith(n_value): raise self.JavaScriptRuntimeError("Unable to solve URL n challenge")
        return self.updatequery(url, {"n": result})
    '''selectcandidate'''
    def selectcandidate(self, candidates: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
        unique: dict[tuple[Any, ...], dict[str, Any]] = {}
        for candidate in candidates:
            if not YouTubeAudioURLExtractor.ishttpurl(candidate.get("url")): continue
            key = (candidate.get("format_id"), candidate.get("language"), candidate.get("is_drc"), candidate.get("url"),)
            if not (existing := unique.get(key)) or self.candidaterank(candidate) > self.candidaterank(existing): unique[key] = candidate
        ordered = sorted(unique.values(), key=self.candidaterank, reverse=True)
        if not self.validate_url: return ordered[0] if ordered else None
        for candidate in ordered:
            if self.probeurl(candidate["url"], manifest=candidate.get("is_manifest", False)): return candidate
        return None
    '''candidaterank'''
    def candidaterank(self, candidate: Mapping[str, Any]) -> tuple[Any, ...]:
        language = (candidate.get("language") or "").lower()
        preferred_language = (self.preferred_language or "").lower()
        language_preference = bool(preferred_language and (language == preferred_language or language.startswith(preferred_language + "-")))
        quality = YouTubeAudioURLExtractor.AUDIO_QUALITY.get(str(candidate.get("audio_quality") or ""), -1)
        codec, codec_preference = str(candidate.get("audio_codec") or "").lower(), 0
        for index, preferred in enumerate(self.preferred_codecs):
            if codec.startswith(preferred): codec_preference = len(self.preferred_codecs) - index; break
        client_preference = {"visionos": 4, "web_embedded": 3, "tv_downgraded": 2, "web": 1,}.get(str(candidate.get("client")), 0)
        return (bool(candidate.get("is_audio_only")), not bool(candidate.get("_damaged")), language_preference, bool(candidate.get("is_original_audio")), bool(candidate.get("is_default_audio")), not bool(candidate.get("is_drc")), quality, YouTubeAudioURLExtractor.intornone(candidate.get("audio_bitrate")) or -1, codec_preference, YouTubeAudioURLExtractor.intornone(candidate.get("audio_sample_rate")) or -1, client_preference,)
    '''mergeresponsemetadata'''
    def mergeresponsemetadata(self, responses: Iterable[tuple[str, Mapping[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any]]:
        video_details: dict[str, Any] = {}; microformat: dict[str, Any] = {}
        for _, response in responses:
            if isinstance((details := response.get("videoDetails")), Mapping):
                for key, value in details.items():
                    if key not in video_details or video_details[key] in (None, "", [], {}): video_details[key] = value
            if isinstance((renderer := YouTubeAudioURLExtractor.dig(response, "microformat", "playerMicroformatRenderer")), Mapping):
                for key, value in renderer.items():
                    if key not in microformat or microformat[key] in (None, "", [], {}): microformat[key] = value
        return video_details, microformat
    '''buildmetadata'''
    def buildmetadata(self, video_id: str, video_details: Mapping[str, Any], microformat: Mapping[str, Any],) -> dict[str, Any]:
        title = YouTubeAudioURLExtractor.firststring(video_details.get("title"), YouTubeAudioURLExtractor.textvalue(microformat.get("title")))
        duration = YouTubeAudioURLExtractor.intornone(video_details.get("lengthSeconds"))
        author = YouTubeAudioURLExtractor.firststring(video_details.get("author"), microformat.get("ownerChannelName"))
        channel_id = YouTubeAudioURLExtractor.firststring(video_details.get("channelId"), microformat.get("externalChannelId"))
        description = YouTubeAudioURLExtractor.firststring(video_details.get("shortDescription"), YouTubeAudioURLExtractor.textvalue(microformat.get("description")),)
        thumbnail = thumbnails[-1]["url"] if (thumbnails := self.collectthumbnails(video_details.get("thumbnail"), microformat.get("thumbnail"))) else None
        if not isinstance((keywords := video_details.get("keywords")), list): keywords = []
        keywords = [keyword for keyword in keywords if isinstance(keyword, str)]
        if not isinstance((available_countries := microformat.get("availableCountries")), list): available_countries = []
        available_countries = [country for country in available_countries if isinstance(country, str)]
        is_live = bool(video_details.get("isLive") or YouTubeAudioURLExtractor.dig(microformat, "liveBroadcastDetails", "isLiveNow"))
        return {"video_id": video_id, "webpage_url": YouTubeAudioURLExtractor.firststring(microformat.get("urlCanonical"), f"https://www.youtube.com/watch?v={video_id}",), "title": title, "duration": duration, "duration_seconds": duration, "duration_text": self.formatduration(duration), "author": author, "channel_id": channel_id, "channel_url": YouTubeAudioURLExtractor.firststring(microformat.get("ownerProfileUrl")), "description": description, "view_count": YouTubeAudioURLExtractor.intornone(video_details.get("viewCount") or microformat.get("viewCount")), "average_rating": video_details.get("averageRating"), "keywords": keywords, "thumbnail": thumbnail, "thumbnails": thumbnails, "publish_date": YouTubeAudioURLExtractor.firststring(microformat.get("publishDate")), "upload_date": YouTubeAudioURLExtractor.firststring(microformat.get("uploadDate")), "category": YouTubeAudioURLExtractor.firststring(microformat.get("category")), "available_countries": available_countries, "is_family_safe": microformat.get("isFamilySafe"), "is_live": is_live, "is_live_content": bool(video_details.get("isLiveContent")), "source_commit": self.UPSTREAM_COMMIT,}
    '''finalizeinfo'''
    def finalizeinfo(self, candidate: dict[str, Any], video_id: str, video_details: Mapping[str, Any], microformat: Mapping[str, Any],) -> dict[str, Any]:
        result = {key: value for key, value in candidate.items() if not key.startswith("_")}
        audio_url, metadata = result["url"], self.buildmetadata(video_id, video_details, microformat)
        audio_format = {"format_id": result.get("format_id"), "itag": result.get("itag"), "extension": result.get("ext"), "mime_type": result.get("mime_type"), "codec": result.get("audio_codec"), "bitrate": result.get("audio_bitrate"), "sample_rate": result.get("audio_sample_rate"), "channels": result.get("audio_channels"), "content_length": result.get("content_length"), "quality": result.get("audio_quality"), "language": result.get("language"), "language_name": result.get("language_name"), "is_default": result.get("is_default_audio"), "is_original": result.get("is_original_audio"), "is_drc": result.get("is_drc"), "is_manifest": result.get("is_manifest"), "client": result.get("client")}
        result.update(metadata); result.update({"audio_url": audio_url, "audio_title": metadata["title"], "audio_extension": result.get("ext"), "audio_format": audio_format, "expires": self.urlexpiry(audio_url), "http_headers": {"User-Agent": YouTubeAudioURLExtractor.WEB_USER_AGENT},})
        return result
    '''collectthumbnails'''
    @classmethod
    def collectthumbnails(cls, *containers: Any) -> list[dict[str, Any]]:
        thumbnails: list[dict[str, Any]] = []; seen: set[str] = set()
        for container in containers:
            if not isinstance((values := container.get("thumbnails") if isinstance(container, Mapping) else None), list): continue
            for value in values:
                if not isinstance(value, Mapping) or not cls.ishttpurl(value.get("url")): continue
                if (url := value["url"]) in seen: continue
                seen.add(url); thumbnails.append({"url": url, "width": cls.intornone(value.get("width")), "height": cls.intornone(value.get("height")),})
        thumbnails.sort(key=lambda item: (item.get("width") or 0) * (item.get("height") or 0))
        return thumbnails
    '''textvalue'''
    @staticmethod
    def textvalue(value: Any) -> str | None:
        if isinstance(value, str): return value or None
        if not isinstance(value, Mapping): return None
        if isinstance((simple := value.get("simpleText")), str) and simple: return simple
        if isinstance((runs := value.get("runs")), list): text = "".join(str(run.get("text") or "") for run in runs if isinstance(run, Mapping)); return text or None
        return None
    '''formatduration'''
    @staticmethod
    def formatduration(duration: int | None) -> str | None:
        if duration is None or duration < 0: return None
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return (f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}")
    '''playabilityerror'''
    def playabilityerror(self, video_id: str, responses: Sequence[tuple[str, Mapping[str, Any]]]) -> Exception:
        statuses: list[str] = []; anonymous_only = False
        for client, response in responses:
            if not isinstance((status := response.get("playabilityStatus")), dict): continue
            code = str(status.get("status") or "UNKNOWN"); reason = self.playabilityreason(status)
            statuses.append(f"{client}: {code}{': ' + reason if reason else ''}")
            anonymous_only = anonymous_only or code in {"LOGIN_REQUIRED", "AGE_CHECK_REQUIRED", "AGE_VERIFICATION_REQUIRED",}
        detail = "; ".join(dict.fromkeys(statuses)) or "unknown playability status"
        message = f"YouTube video {video_id} is not available anonymously: {detail}"
        return self.AnonymousAccessError(message) if anonymous_only else self.NoAudioFormatError(message)
    '''playabilitystatus'''
    @staticmethod
    def playabilitystatus(response: Mapping[str, Any]) -> str | None:
        status = response.get("playabilityStatus")
        return status.get("status") if isinstance(status, dict) else None
    '''playabilityreason'''
    @classmethod
    def playabilityreason(cls, status: Mapping[str, Any]) -> str | None:
        if isinstance((reason := status.get("reason")), str): return reason
        messages: list[str] = []
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                if isinstance((simple := value.get("simpleText")), str): messages.append(simple)
                if isinstance((runs := value.get("runs")), list):
                    if (text := "".join(run.get("text", "") for run in runs if isinstance(run, dict))): messages.append(text)
                for child in value.values(): walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(status.get("errorScreen"))
        return next(iter(dict.fromkeys(messages)), None)
    '''discoverplayerurl'''
    def discoverplayerurl(self, video_id: str, webpage: str = "") -> str | None:
        if (extracted := self.extractplayerurl({}, webpage)): return extracted
        try: iframe_api = self.requesttext("https://www.youtube.com/iframe_api")
        except self.Error as exc: raise self.JavaScriptRuntimeError(f"Unable to discover the YouTube player JavaScript: {exc}") from exc
        if not (match := re.search(r"player\\?/([0-9a-fA-F]{8,})\\?/", iframe_api)): raise self.JavaScriptRuntimeError("Unable to identify the YouTube player version")
        return (f"https://www.youtube.com/s/player/{match.group(1)}/" "player_ias.vflset/en_US/base.js")
    '''loadplayercode'''
    def loadplayercode(self, video_id: str, player_url: str) -> str:
        if player_url not in self._player_code_cache: self._player_code_cache[player_url] = self.requesttext(player_url, max_size=10 * 1024 * 1024)
        return self._player_code_cache[player_url]
    '''extractplayerurl'''
    @classmethod
    def extractplayerurl(cls, ytcfg: Mapping[str, Any], webpage: str = "") -> str | None:
        candidates: list[str] = []
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"PLAYER_JS_URL", "jsUrl"} and isinstance(child, str): candidates.append(child)
                    else: walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(ytcfg)
        if not candidates and webpage:
            normalized = html.unescape(webpage).replace("\\/", "/")
            if (match := cls.PLAYER_PATH_RE.search(normalized)): candidates.append(match.group("path"))
        for candidate in candidates:
            candidate = html.unescape(candidate).replace("\\/", "/")
            absolute = urllib.parse.urljoin("https://www.youtube.com", candidate)
            if cls.ishttpurl(absolute) and cls.PLAYER_ID_RE.search(absolute): return absolute
        return None
    '''extractytcfg'''
    @classmethod
    def extractytcfg(cls, webpage: str) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for value in cls.jsonvaluesafter(webpage, re.compile(r"ytcfg\.set\s*\(")):
            if isinstance(value, dict): merged.update(value)
        return merged
    '''extractinitialplayerresponse'''
    @classmethod
    def extractinitialplayerresponse(cls, webpage: str) -> dict[str, Any]:
        markers = (re.compile(r"ytInitialPlayerResponse\s*="), re.compile(r"window\s*\[\s*[\"']ytInitialPlayerResponse[\"']\s*\]\s*="),)
        for marker in markers:
            for value in cls.jsonvaluesafter(webpage, marker):
                if isinstance(value, dict): return value
        return {}
    '''jsonvaluesafter'''
    @staticmethod
    def jsonvaluesafter(source: str, marker: re.Pattern[str]) -> Iterable[Any]:
        decoder = json.JSONDecoder()
        for match in marker.finditer(source):
            start = match.end()
            while start < len(source) and source[start].isspace(): start += 1
            if start >= len(source) or source[start] not in "{[":
                if not (brace_positions := [p for p in (source.find("{", start), source.find("[", start)) if p >= 0]): continue
                start = min(brace_positions)
            try: value, _ = decoder.raw_decode(source[start:])
            except json.JSONDecodeError: continue
            yield value
    '''validplayerresponse'''
    @staticmethod
    def validplayerresponse(response: Any, video_id: str) -> bool:
        return bool(isinstance(response, dict) and response and (not isinstance(response.get("videoDetails"), dict) or response["videoDetails"].get("videoId") in {None, video_id}))
    '''iterstreamformats'''
    @staticmethod
    def iterstreamformats(streaming_data: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        for key in ("formats", "adaptiveFormats"):
            values = streaming_data.get(key)
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, dict): yield value
    '''hasstreamingdata'''
    @classmethod
    def hasstreamingdata(cls, response: Mapping[str, Any]) -> bool:
        streaming_data = response.get("streamingData")
        if not isinstance(streaming_data, Mapping): return False
        if any(True for _ in cls.iterstreamformats(streaming_data)): return True
        return any(cls.ishttpurl(streaming_data.get(key)) for key in ("hlsManifestUrl", "dashManifestUrl"))
    '''parsemimetype'''
    @staticmethod
    def parsemimetype(value: str) -> tuple[str, list[str]]:
        if not (match := re.match(r"\s*([^;\s]+)(?:\s*;\s*codecs=\"([^\"]+)\")?", value)): return "", []
        codecs = [x.strip() for x in (match.group(2) or "").split(",") if x.strip()]
        return match.group(1).lower(), codecs
    '''audiocodec'''
    @staticmethod
    def audiocodec(codecs: Sequence[str]) -> str | None:
        prefixes = ("mp4a", "opus", "vorbis", "aac", "ac-3", "ec-3", "flac")
        return next((codec for codec in codecs if codec.lower().startswith(prefixes)), None)
    '''extensionformime'''
    @staticmethod
    def extensionformime(mime_type: str) -> str | None:
        return {"audio/webm": "webm", "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/3gpp": "3gp", "application/vnd.apple.mpegurl": "m3u8",}.get((mime_type or "").lower())
    '''parsem3u8attributes'''
    @staticmethod
    def parsem3u8attributes(value: str) -> dict[str, str]:
        result: dict[str, str] = {}; pattern = re.compile(r"([A-Z0-9-]+)=(\"(?:[^\"\\]|\\.)*\"|[^,]*)")
        for match in pattern.finditer(value):
            if (raw := match.group(2).strip()).startswith('"') and raw.endswith('"'):
                try: raw = json.loads(raw)
                except json.JSONDecodeError: raw = raw[1:-1]
            result[match.group(1)] = raw
        return result
    '''xmlname'''
    @staticmethod
    def xmlname(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
    '''candidatesneedplayer'''
    @staticmethod
    def candidatesneedplayer(candidates: Iterable[Mapping[str, Any]]) -> bool:
        return any(candidate.get("_needs_js") for candidate in candidates)
    '''updatequery'''
    @staticmethod
    def updatequery(url: str, changes: Mapping[str, str]) -> str:
        parts = urllib.parse.urlsplit(url); pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        changed = set(); updated: list[tuple[str, str]] = []
        for key, value in pairs:
            if key in changes:
                if key not in changed: updated.append((key, changes[key])); changed.add(key)
            else: updated.append((key, value))
        for key, value in changes.items():
            if key not in changed: updated.append((key, value))
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(updated)))
    '''urlexpiry'''
    @staticmethod
    def urlexpiry(url: str) -> int | None:
        value = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("expire", [None])[0]
        try: return int(value) if value is not None else None
        except (TypeError, ValueError): return None
    '''ishttpurl'''
    @staticmethod
    def ishttpurl(value: Any) -> bool:
        if not isinstance(value, str): return False
        try: parsed = urllib.parse.urlsplit(value)
        except ValueError: return False
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    '''dig'''
    @staticmethod
    def dig(value: Any, *path: str) -> Any:
        for key in path:
            if not isinstance(value, Mapping): return None
            value = value.get(key)
        return value
    '''firststring'''
    @staticmethod
    def firststring(*values: Any) -> str | None:
        return next((value for value in values if isinstance(value, str) and value), None)
    '''intornone'''
    @staticmethod
    def intornone(value: Any) -> int | None:
        try: return int(value) if value is not None else None
        except (TypeError, ValueError, OverflowError): return None
    '''cleannodestderr'''
    @staticmethod
    def cleannodestderr(stderr: str) -> str:
        lines = [line for line in stderr.splitlines() if not (re.match(r"^\[stdin\]:", line) or re.match(r"^var jsc", line) or re.match(r"^Node\.js v\d+\.\d+\.\d+$", line) or "Use `node --trace-uncaught" in line)]
        return "\n".join(lines).strip()
    '''probeurl'''
    def probeurl(self, url: str, *, manifest: bool = False) -> bool:
        headers = {"User-Agent": YouTubeAudioURLExtractor.WEB_USER_AGENT, "Accept-Encoding": "identity",}
        if not manifest: headers["Range"] = "bytes=0-0"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                response: http.client.HTTPResponse = response
                sample = response.read(512 if manifest else 1)
                return bool(sample) and (not manifest or b"#EXTM3U" in sample)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError): return False
    '''requestjson'''
    def requestjson(self, url: str, *, data: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None,) -> dict[str, Any]:
        text = self.requesttext(url, data=json.dumps(data, separators=(",", ":")).encode("utf-8") if data is not None else None, headers=headers, max_size=15 * 1024 * 1024,)
        try: value: dict = json.loads(text)
        except json.JSONDecodeError as exc: raise self.NetworkError(f"YouTube returned invalid JSON from {url}") from exc
        if not isinstance(value, dict): raise self.NetworkError(f"YouTube returned an unexpected JSON value from {url}")
        return value
    '''requesttext'''
    def requesttext(self, url: str, *, data: bytes | None = None, headers: Mapping[str, str] | None = None, max_size: int = 20 * 1024 * 1024,) -> str:
        real_headers = {"User-Agent": YouTubeAudioURLExtractor.WEB_USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity",}
        if headers: real_headers.update({k: v for k, v in headers.items() if v is not None})
        request = urllib.request.Request(url, data=data, headers=real_headers); last_error: BaseException | None = None
        for attempt in range(self.retries + 1):
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    response: http.client.HTTPResponse = response
                    length = YouTubeAudioURLExtractor.intornone(response.headers.get("Content-Length"))
                    if length is not None and length > max_size: raise self.NetworkError(f"Response from {url} exceeds the {max_size}-byte safety limit")
                    if len((raw := response.read(max_size + 1))) > max_size: raise self.NetworkError(f"Response from {url} exceeds the {max_size}-byte safety limit")
                    encoding = (response.headers.get("Content-Encoding") or "").lower()
                    if encoding == "gzip": raw = gzip.decompress(raw)
                    elif encoding == "deflate": raw = zlib.decompress(raw)
                    if len(raw) > max_size: raise self.NetworkError(f"Decoded response from {url} exceeds the {max_size}-byte safety limit")
                    charset = response.headers.get_content_charset() or "utf-8"
                    return raw.decode(charset, errors="replace")
            except self.NetworkError: raise
            except urllib.error.HTTPError as exc:
                last_error = exc; retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt >= self.retries: detail = YouTubeAudioURLExtractor.httperrordetail(exc); raise self.NetworkError(f"HTTP {exc.code} from {url}{': ' + detail if detail else ''}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt >= self.retries: raise self.NetworkError(f"Network request failed for {url}: {exc}") from exc
            time.sleep(min(2**attempt, 4))
        raise self.NetworkError(f"Network request failed for {url}: {last_error}")
    '''httperrordetail'''
    @staticmethod
    def httperrordetail(error: urllib.error.HTTPError) -> str | None:
        try:
            value: dict = json.loads(error.read(2048).decode("utf-8", errors="replace"))
            message = (value.get("error", {}) or {}).get("message")
            return message if isinstance(message, str) else None
        except Exception: return None
    '''printlog'''
    def printlog(self, message: str) -> None:
        if self.logger_handle: self.logger_handle(message)