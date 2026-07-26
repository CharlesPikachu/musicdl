import re
import json
import time
import hashlib
import os
import requests
from urllib.parse import quote

# 将配置分离为常量，避免在代码中硬编码敏感信息
DEFAULT_COUNTRY = "hk"
DEFAULT_LANG = "zh_TW"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.joox.com",
    "Referer": "https://www.joox.com/",
}

def build_joox_cookies(email, password, country=DEFAULT_COUNTRY, lang=DEFAULT_LANG):
    """
    获取 JooxMusicClient 的 Cookies 和凭证信息
    """
    ts = int(time.time() * 1000)
    enc_email = quote(quote(email))
    md5_pw = hashlib.md5(password.encode("utf-8")).hexdigest()
    
    url = (f"https://api.joox.com/web-fcgi-bin/web_wmauth?"
           f"country={country}&lang={lang}&wxopenid={enc_email}&password={md5_pw}"
           f"&wmauth_type=0&authtype=2&time={ts}&_={ts}&callback=axiosJsonpCallback6")

    # 使用 with 管理 Session，确保连接正确释放
    with requests.Session() as session:
        session.headers.update(HEADERS)
        
        try:
            resp = session.get(url=url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"网络请求失败: {e}")

        # 使用非贪婪匹配防止跨行或超限匹配
        m = re.search(r"\{.*?\}", resp.text, re.S)
        body = json.loads(m.group(0)) if m else {}

        if body.get("code") not in (0, None):
            # 抛出 ValueError 而不是 SystemExit，避免阻塞主程序
            raise ValueError(f"登录被拒绝，返回数据: {body}")
            
        wmid = body.get("wmid")
        skey = body.get("session_key")
        
        if not (wmid and skey):
            raise ValueError(f"登录成功但未获取到 session_key，返回数据: {body}")

        # session.cookies 已经包含了本次响应的 cookies，直接提取即可
        cookies = requests.utils.dict_from_cookiejar(session.cookies)
        
        creds = {
            "cookies": cookies, 
            "body": body, 
            "wmid": str(wmid), 
            "session_key": skey, 
            "country": body.get("country") or country, 
            "user_type": body.get("user_type"), 
            "nickname": body.get("nickname")
        }
        return creds


if __name__ == '__main__':
    # 推荐通过环境变量传入账号密码，保证安全性
    TEST_EMAIL = os.getenv("JOOX_EMAIL", "YOUR_EMAIL")
    TEST_PASSWORD = os.getenv("JOOX_PASSWORD", "YOUR_PASSWORD")
    
    if TEST_EMAIL != "YOUR_EMAIL":
        try:
            result = build_joox_cookies(TEST_EMAIL, TEST_PASSWORD)
            print(result)
        except Exception as e:
            print(f"获取凭证失败: {e}")
    else:
        print("请在运行前配置 JOOX_EMAIL 和 JOOX_PASSWORD 环境变量，或直接传入真实账号。")
