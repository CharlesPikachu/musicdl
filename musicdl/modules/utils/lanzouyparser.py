'''
Function:
    Implementation of LanZouYParser
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import random
import warnings
import requests
import json_repair
from urllib.parse import urljoin, urlparse
warnings.filterwarnings('ignore')


'''LanZouYParser'''
class LanZouYParser():
    '''parsefromurl'''
    @staticmethod
    def parsefromurl(url: str, passcode: str = '', max_tries: int = 3):
        for _ in range(max_tries):
            # official api
            try: download_result, download_url = LanZouYParser.parsefromurlwithofficialapi(url=url, passcode=passcode)
            except Exception: download_result, download_url = {}, ""
            if download_url and str(download_url).startswith('http'): break
            # fall back to parsefromurlwithzxkiapi
            try: download_result, download_url = LanZouYParser.parsefromurlwithzxkiapi(url=url, passcode=passcode)
            except Exception: download_result, download_url = {}, ""
            if download_url and str(download_url).startswith('http'): break
            # fall back to parsefromurlwithkohlapi
            try: download_result, download_url = LanZouYParser.parsefromurlwithkohlapi(url=url, passcode=passcode)
            except Exception: download_result, download_url = {}, ""
            if download_url and str(download_url).startswith('http'): break
            # fall back to parsefromurlwithcggapi
            try: download_result, download_url = LanZouYParser.parsefromurlwithcggapi(url=url, passcode=passcode)
            except Exception: download_result, download_url = {}, ""
            if download_url and str(download_url).startswith('http'): break
        return download_result, download_url
    '''parsefromurlwithzxkiapi'''
    @staticmethod
    def parsefromurlwithzxkiapi(url: str, passcode: str = ''):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}
        (resp := requests.get(f'https://api.zxki.cn/api/lzy?url={url}&pwd={passcode}&type=json', headers=headers)).raise_for_status()
        download_url = (download_result := resp.json())['downUrl']
        return download_result, download_url
    '''parsefromurlwithkohlapi'''
    @staticmethod
    def parsefromurlwithkohlapi(url: str, passcode: str = ''):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}
        (resp := requests.get(f'https://vercel-chi-kohl.vercel.app/lanzouyunapi.php?url={url}&pw={passcode}', headers=headers)).raise_for_status()
        download_url = (download_result := resp.json())['data']['url']
        return download_result, download_url
    '''parsefromurlwithcggapi'''
    @staticmethod
    def parsefromurlwithcggapi(url: str, passcode: str = ''):
        headers, file_id = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}, urlparse(url).path.strip('/').split('/')[-1]
        (resp := requests.get(f'https://api-v2.cenguigui.cn/api/lanzou/api.php?url=https://cenguigui.lanzouw.com/{file_id}&pwd={passcode}', headers=headers)).raise_for_status()
        download_url = (download_result := resp.json())['data']['downurl']
        return download_result, download_url
    '''randip'''
    @staticmethod
    def randip() -> str:
        ip1 = random.choice(["218", "218", "66", "66", "218", "218", "60", "60", "202", "204", "66", "66", "66", "59", "61", "60", "222", "221", "66", "59", "60", "60", "66", "218", "218", "62", "63", "64", "66", "66", "122", "211"])
        return f"{ip1}.{round(random.randint(600000, 2550000) / 10000)}.{round(random.randint(600000, 2550000) / 10000)}.{round(random.randint(600000, 2550000) / 10000)}"
    '''httpget'''
    @staticmethod
    def httpget(url: str, user_agent: str = "", referer: str = "", cookies: dict = None, timeout: int = 10) -> str:
        headers = {"X-FORWARDED-FOR": (random_ip := LanZouYParser.randip()), "CLIENT-IP": random_ip, **({"User-Agent": user_agent} if user_agent else {}), **({"Referer": referer} if referer else {})}
        (resp := requests.get(url, headers=headers, cookies=cookies, timeout=timeout, verify=False, allow_redirects=True)).raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    '''httppost'''
    @staticmethod
    def httppost(data: dict, url: str, referer: str = "", user_agent: str = "", timeout: int = 10) -> str:
        headers = {"X-FORWARDED-FOR": (random_ip := LanZouYParser.randip()), "CLIENT-IP": random_ip, **({"User-Agent": user_agent} if user_agent else {}), **({"Referer": referer} if referer else {})}
        (resp := requests.post(url, data=data, headers=headers, timeout=timeout, verify=False, allow_redirects=True)).raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    '''httpredirecturl'''
    @staticmethod
    def httpredirecturl(url: str, referer: str, user_agent: str, cookie_str: str, timeout: int = 10) -> str:
        headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.9", "Cache-Control": "no-cache", "Connection": "keep-alive", "Pragma": "no-cache", "Upgrade-Insecure-Requests": "1", "User-Agent": user_agent, "Referer": referer, "Cookie": cookie_str}
        (resp := requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=False)).raise_for_status()
        return urljoin(url, loc) if (loc := resp.headers.get("Location", "") or resp.headers.get("location", "")) else resp.url
    '''acwscv2simple'''
    @staticmethod
    def acwscv2simple(arg1: str):
        if not arg1 or not isinstance(arg1, str): return ""
        pos_list = (15, 35, 29, 24, 33, 16, 1, 38, 10, 9, 19, 31, 40, 27, 22, 23, 25, 13, 6, 11, 39, 18, 20, 8, 14, 21, 32, 26, 2, 30, 7, 4, 17, 5, 3, 28, 34, 37, 12, 36)
        arg2 = "".join(arg1[p - 1] for p in pos_list if p <= len(arg1))
        length = min(len(arg2), len((mask := "3000176000856006061501533003690027800375")))
        return "".join(f"{(int(arg2[i: i+2], 16) ^ int(mask[i: i+2], 16)):02x}" for i in range(0, length, 2))
    '''parsefromurlwithofficialapi'''
    @staticmethod
    def parsefromurlwithofficialapi(url: str, passcode: str = ''):
        # init
        download_result, user_agent = {}, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        extract_first_func = lambda regex_list, text: next((m.group(1) for rgx in regex_list if (m := re.search(rgx, text, flags=re.S))), "")
        normalize_lanzou_url_func = lambda u: ("https://www.lanzouf.com/" + t.lstrip("/") if (t := (u.split(".com/", 1)[1] if ".com/" in u else None)) is not None else ("https://www.lanzouf.com" + u) if u.startswith("/") else u if u.startswith("http") else "https://www.lanzouf.com/" + u.lstrip("/"))
        # vist home page
        homepage_url_html = LanZouYParser.httpget((url := normalize_lanzou_url_func(url)), user_agent=user_agent)
        if "文件取消分享了" in homepage_url_html: raise RuntimeError(f'Invalid link {url} as the file sharing has been canceled')
        soft_name = extract_first_func([r'style="font-size: 30px;text-align: center;padding: 56px 0px 20px 0px;">(.*?)</div>', r'<div class="n_box_3fn".*?>(.*?)</div>', r"var filename = '(.*?)';", r'div class="b"><span>(.*?)</span></div>'], homepage_url_html)
        soft_size = extract_first_func([r'<div class="n_filesize".*?>大小：(.*?)</div>', r'<span class="p7">文件大小：</span>(.*?)<br>'], homepage_url_html)
        # with passcode
        if "function down_p(){" in homepage_url_html:
            payload = {"action": "downprocess", "sign": re.findall(r"'sign':'(.*?)',", homepage_url_html, flags=re.S)[1], "p": passcode, "kd": 1}
            parse_result = LanZouYParser.httppost(data=payload, url=("https://www.lanzouf.com/" + re.findall(r"ajaxm\.php\?file=\d+", homepage_url_html, flags=re.S)[0]), referer=url, user_agent=user_agent)
            soft_name = (parse_result := json_repair.loads(parse_result)).get("inf") or soft_name
        # without passcode    
        else:
            link = extract_first_func([r'\n<iframe.*?name="[\s\S]*?"\ssrc="\/(.*?)"', r'<iframe.*?name="[\s\S]*?"\ssrc="\/(.*?)"'], homepage_url_html)
            iframe_html = LanZouYParser.httpget(url=(ifurl := "https://www.lanzouf.com/" + link.lstrip("/")), user_agent=user_agent)
            payload = {"action": "downprocess", "websignkey": (ajaxdata := re.findall(r"ajaxdata = '(.*?)'", iframe_html, flags=re.S))[0], "signs": ajaxdata[0], "sign": re.findall(r"wp_sign = '(.*?)'", iframe_html, flags=re.S)[0], "websign": "", "kd": 1, "ves": 1}
            parse_result = json_repair.loads(LanZouYParser.httppost(data=payload, url=("https://www.lanzouf.com/" + re.findall(r"ajaxm\.php\?file=\d+", iframe_html, flags=re.S)[1]), referer=ifurl, user_agent=user_agent))
        # final process
        download_html = LanZouYParser.httpget((download_url := f"{parse_result['dom']}/file/{parse_result['url']}"), user_agent=user_agent)
        if (arg1_list := re.findall(r"arg1='(.*?)'", download_html, flags=re.S)):
            cookie_str = f"down_ip=1; expires=Sat, 16-Nov-2019 11:42:54 GMT; path=/; domain=.baidupan.com; acw_sc__v2={LanZouYParser.acwscv2simple(arg1_list[0])}"
            redirected_download_url = LanZouYParser.httpredirecturl(download_url, referer="https://developer.lanzoug.com", user_agent=user_agent, cookie_str=cookie_str)
            if "http" in (redirected_download_url or ""): download_url = redirected_download_url
        download_result = {"name": soft_name or "", "filesize": soft_size or "", "downUrl": (download_url := re.sub(r"pid=[^&]*&", "", download_url)), "parse_result": parse_result}
        # return
        return download_result, download_url