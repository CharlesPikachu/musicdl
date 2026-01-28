'''
Function:
    Implementation of LanZouYParser
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import json
import random
import requests
from urllib.parse import urljoin, urlparse


'''LanZouYParser'''
class LanZouYParser():
    '''parsefromurl'''
    @staticmethod
    def parsefromurl(url: str, passcode: str = '', max_tries: int = 3):
        for _ in range(max_tries):
            try:
                download_result, download_url = LanZouYParser._parsefromurl(url=url, passcode=passcode)
                assert download_url and str(download_url).startswith('http')
                break
            except:
                download_result, download_url = {}, ""
            if not download_url or not str(download_url).startswith('http'):
                file_id = urlparse(url).path.strip('/').split('/')[-1]
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}
                try:
                    resp = requests.get(f'https://api-v2.cenguigui.cn/api/lanzou/api.php?url=https://cenguigui.lanzouw.com/{file_id}', headers=headers)
                    download_result = resp.json()
                    download_url = download_result['data']['downurl']
                    assert download_url and str(download_url).startswith('http')
                    break
                except:
                    download_result, download_url = {}, ""
        return download_result, download_url
    '''_randip'''
    @staticmethod
    def _randip() -> str:
        ip2 = round(random.randint(600000, 2550000) / 10000)
        ip3 = round(random.randint(600000, 2550000) / 10000)
        ip4 = round(random.randint(600000, 2550000) / 10000)
        arr1 = ["218", "218", "66", "66", "218", "218", "60", "60", "202", "204", "66", "66", "66", "59", "61", "60", "222", "221", "66", "59", "60", "60", "66", "218", "218", "62", "63", "64", "66", "66", "122", "211"]
        ip1 = random.choice(arr1)
        return f"{ip1}.{ip2}.{ip3}.{ip4}"
    '''_httpget'''
    @staticmethod
    def _httpget(url: str, user_agent: str = "", referer: str = "", cookies: dict = None, timeout: int = 10) -> str:
        headers = {"X-FORWARDED-FOR": LanZouYParser._randip(), "CLIENT-IP": LanZouYParser._randip()}
        if user_agent: headers["User-Agent"] = user_agent
        if referer: headers["Referer"] = referer
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=timeout, verify=False, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    '''_httppost'''
    @staticmethod
    def _httppost(data: dict, url: str, referer: str = "", user_agent: str = "", timeout: int = 10) -> str:
        headers = {"X-FORWARDED-FOR": LanZouYParser._randip(), "CLIENT-IP": LanZouYParser._randip()}
        if user_agent: headers["User-Agent"] = user_agent
        if referer: headers["Referer"] = referer
        resp = requests.post(url, data=data, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    '''_httpredirecturl'''
    @staticmethod
    def _httpredirecturl(url: str, referer: str, user_agent: str, cookie_str: str, timeout: int = 10) -> str:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8", "Accept-Encoding": "gzip, deflate", 
            "Accept-Language": "zh-CN,zh;q=0.9", "Cache-Control": "no-cache", "Connection": "keep-alive", "Pragma": "no-cache", "Upgrade-Insecure-Requests": "1", 
            "User-Agent": user_agent, "Referer": referer, "Cookie": cookie_str,
        }
        resp = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=False)
        resp.raise_for_status()
        loc = resp.headers.get("Location", "") or resp.headers.get("location", "")
        if not loc: return ""
        return urljoin(url, loc)
    '''_acwscv2simple'''
    @staticmethod
    def _acwscv2simple(arg1: str):
        if not arg1: return ""
        mask = "3000176000856006061501533003690027800375"
        pos_list = (15, 35, 29, 24, 33, 16, 1, 38, 10, 9, 19, 31, 40, 27, 22, 23, 25, 13, 6, 11, 39, 18, 20, 8, 14, 21, 32, 26, 2, 30, 7, 4, 17, 5, 3, 28, 34, 37, 12, 36)
        arg2 = "".join(arg1[p - 1] for p in pos_list if p <= len(arg1))
        length = min(len(arg2), len(mask))
        return "".join(f"{(int(arg2[i:i+2], 16) ^ int(mask[i:i+2], 16)):02x}" for i in range(0, length, 2))
    '''_parsefromurl'''
    @staticmethod
    def _parsefromurl(url: str, passcode: str = ''):
        # init
        download_result, user_agent = {}, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        normalize_lanzou_url_func = lambda u: ("https://www.lanzouf.com/" + t.lstrip("/") if (t := (u.split(".com/", 1)[1] if ".com/" in u else None)) is not None else ("https://www.lanzouf.com" + u) if u.startswith("/") else u if u.startswith("http") else "https://www.lanzouf.com/" + u.lstrip("/"))
        extract_first_func = lambda regex_list, text: next((m.group(1) for rgx in regex_list if (m := re.search(rgx, text, flags=re.S))), "")
        # vist home page
        url = normalize_lanzou_url_func(url)
        homepage_url_html = LanZouYParser._httpget(url, user_agent=user_agent)
        if "文件取消分享了" in homepage_url_html: raise
        soft_name = extract_first_func([r'style="font-size: 30px;text-align: center;padding: 56px 0px 20px 0px;">(.*?)</div>', r'<div class="n_box_3fn".*?>(.*?)</div>', r"var filename = '(.*?)';", r'div class="b"><span>(.*?)</span></div>'], homepage_url_html)
        soft_size = extract_first_func([r'<div class="n_filesize".*?>大小：(.*?)</div>', r'<span class="p7">文件大小：</span>(.*?)<br>'], homepage_url_html)
        # with passcode
        if "function down_p(){" in homepage_url_html:
            segment = re.findall(r"'sign':'(.*?)',", homepage_url_html, flags=re.S)
            ajaxm = re.findall(r"ajaxm\.php\?file=\d+", homepage_url_html, flags=re.S)
            assert not (len(segment) < 2 or len(ajaxm) < 1)
            post_data = {"action": "downprocess", "sign": segment[1], "p": passcode, "kd": 1}
            post_url = "https://www.lanzouf.com/" + ajaxm[0]
            parse_result = LanZouYParser._httppost(post_data, post_url, referer=url, user_agent=user_agent)
            parse_result: dict = json.loads(parse_result)
            soft_name = parse_result.get("inf") or soft_name
        # without passcode    
        else:
            link = extract_first_func([r'\n<iframe.*?name="[\s\S]*?"\ssrc="\/(.*?)"', r'<iframe.*?name="[\s\S]*?"\ssrc="\/(.*?)"'], homepage_url_html)
            assert link
            ifurl = "https://www.lanzouf.com/" + link.lstrip("/")
            iframe_html = LanZouYParser._httpget(ifurl, user_agent=user_agent)
            wp_sign = re.findall(r"wp_sign = '(.*?)'", iframe_html, flags=re.S)
            ajaxdata = re.findall(r"ajaxdata = '(.*?)'", iframe_html, flags=re.S)
            ajaxm = re.findall(r"ajaxm\.php\?file=\d+", iframe_html, flags=re.S)
            assert not (len(wp_sign) < 1 or len(ajaxdata) < 1 or len(ajaxm) < 2)
            post_data = {"action": "downprocess", "websignkey": ajaxdata[0], "signs": ajaxdata[0], "sign": wp_sign[0], "websign": "", "kd": 1, "ves": 1}
            post_url = "https://www.lanzouf.com/" + ajaxm[1]
            parse_result = LanZouYParser._httppost(post_data, post_url, referer=ifurl, user_agent=user_agent)
            parse_result: dict = json.loads(parse_result)
        # final parse
        assert not (not isinstance(parse_result, dict) or parse_result.get("zt") != 1)
        download_url = f"{parse_result['dom']}/file/{parse_result['url']}"
        download_html = LanZouYParser._httpget(download_url, user_agent=user_agent)
        arg1_list = re.findall(r"arg1='(.*?)'", download_html, flags=re.S)
        if arg1_list:
            decrypted = LanZouYParser._acwscv2simple(arg1_list[0])
            cookie_str = f"down_ip=1; expires=Sat, 16-Nov-2019 11:42:54 GMT; path=/; domain=.baidupan.com; acw_sc__v2={decrypted}"
            redirected_download_url = LanZouYParser._httpredirecturl(download_url, referer="https://developer.lanzoug.com", user_agent=user_agent, cookie_str=cookie_str)
            if "http" in (redirected_download_url or ""): download_url = redirected_download_url
        download_url = re.sub(r"pid=[^&]*&", "", download_url)
        download_result = {"name": soft_name or "", "filesize": soft_size or "", "downUrl": download_url, "parse_result": parse_result}
        # return
        return download_result, download_url