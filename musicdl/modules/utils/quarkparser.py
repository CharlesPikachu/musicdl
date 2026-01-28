'''
Function:
    Implementation of QuarkParser
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import time
import requests
from urllib.parse import urlparse
from .misc import resp2json, cookies2dict


'''QuarkParser'''
class QuarkParser():
    '''parsefromdirurl'''
    @staticmethod
    def parsefromdirurl(url: str, passcode: str = '', cookies: str | dict = '', max_tries: int = 3):
        for _ in range(max_tries):
            try:
                download_result, download_url = QuarkParser._parsefromdirurl(url=url, passcode=passcode, cookies=cookies)
                break
            except:
                download_result, download_url = {}, ""
        return download_result, download_url
    '''_parsefromdirurl'''
    @staticmethod
    def _parsefromdirurl(url: str, passcode: str = '', cookies: str | dict = ''):
        # init
        session, download_result = requests.Session(), {}
        parsed_url = urlparse(url)
        pwd_id = parsed_url.path.strip('/').split('/')[-1]
        cookies = cookies2dict(cookies)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Core/1.94.225.400 QQBrowser/12.2.5544.400',
            'origin': 'https://pan.quark.cn', 'referer': 'https://pan.quark.cn/', 'accept-language': 'zh-CN,zh;q=0.9',
        }
        # share/sharepage/token
        json_data = {'pwd_id': pwd_id, 'passcode': passcode, 'support_visit_limit_private_share': 'true'}
        params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', '__dt': '597', '__t': f'{str(int(time.time() * 1000))}'}
        resp = session.post('https://drive-h.quark.cn/1/clouddrive/share/sharepage/token', params=params, json=json_data, cookies=cookies, headers=headers)
        resp.raise_for_status()
        token_data = resp2json(resp=resp)
        stoken = token_data['data']['stoken']
        download_result['token_data'] = token_data
        time.sleep(0.1)
        # share/sharepage/detail-1
        params = {
            'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', 'ver': '2', 'pwd_id': pwd_id, 'stoken': stoken, 'pdir_fid': '0',
            'force': '0', '_page': '1', '_size': '50', '_fetch_banner': '1', '_fetch_share': '1', 'fetch_relate_conversation': '1',
            '_fetch_total': '1', '_sort': 'file_type:asc,file_name:asc', '__dt': '951', '__t': f'{int(time.time() * 1000)}',
        }
        resp = session.get('https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail', params=params, cookies=cookies, headers=headers)
        resp.raise_for_status()
        detail_data = resp2json(resp=resp)
        pdir_fid = detail_data["data"]["list"][0]["fid"]
        download_result['detail_data-1'] = detail_data
        time.sleep(0.1)
        # clouddrive/file/info/path_list
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": "", "__dt": "1266", "__t": f"{int(time.time() * 1000)}"}
        json_data = {"file_path": ["/来自：分享"]}
        resp = session.post('https://drive-pc.quark.cn/1/clouddrive/file/info/path_list', params=params, json=json_data, cookies=cookies, headers=headers)
        resp.raise_for_status()
        path_list_data = resp2json(resp=resp)
        to_pdir_fid = path_list_data["data"][0]["fid"]
        download_result['path_list_data'] = path_list_data
        time.sleep(0.1)
        # share/sharepage/detail-2
        params = {
            'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', 'ver': '2', 'pwd_id': pwd_id, 'stoken': stoken, 'pdir_fid': pdir_fid,
            'force': '0', '_page': '1', '_size': '50', '_fetch_banner': '0', '_fetch_share': '0', 'fetch_relate_conversation': '0',
            '_fetch_total': '1', '_sort': 'file_type:asc,file_name:asc', '__dt': '1804336', '__t': f'{int(time.time() * 1000)}',
        }
        resp = session.get('https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail', params=params, cookies=cookies, headers=headers)
        resp.raise_for_status()
        detail_data = resp2json(resp=resp)
        file_list: list[dict] = detail_data["data"]["list"]
        file_list = sorted(file_list, key=lambda x: x.get("size", 0), reverse=True)
        pdir_fid = file_list[0]['pdir_fid']
        download_result['detail_data-2'] = detail_data
        time.sleep(0.1)
        # share/sharepage/save
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": "", "__dt": "1233372", "__t": f"{int(time.time() * 1000)}"}
        json_data = {
            'pwd_id': pwd_id, 'stoken': stoken, 'pdir_fid': pdir_fid, 'to_pdir_fid': to_pdir_fid, 'fid_list': [file_list[0]['fid']], 
            'fid_token_list': [file_list[0]['share_fid_token']], 'scene': 'link',
        }
        resp = session.post(url='https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save', params=params, cookies=cookies, json=json_data, headers=headers)
        resp.raise_for_status()
        save_data = resp2json(resp=resp)
        task_id = save_data['data']['task_id']
        download_result['save_data'] = save_data
        time.sleep(0.1)
        # clouddrive/task
        for retry_index in range(5):
            try:
                params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', 'task_id': task_id, 'retry_index': str(retry_index), '__dt': '1234221', '__t': f'{str(int(time.time() * 1000))}'}
                resp = session.get('https://drive-pc.quark.cn/1/clouddrive/task', params=params, cookies=cookies, headers=headers)
                resp.raise_for_status()
                task_data = resp2json(resp=resp)
                fid_encrypt = task_data['data']['save_as']['save_as_top_fids'][0]
                download_result['task_data'] = task_data
                break
            except:
                time.sleep(0.1)
                continue
        # clouddrive/file/download
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/2.5.56 Chrome/100.0.4896.160 Electron/18.3.5.12-a038f7b798 Safari/537.36 Channel/pckk_other_ch",
            "Accept": "application/json, text/plain, */*", "Content-Type": "application/json", "accept-language": "zh-CN", "origin": "https://pan.quark.cn", "referer": "https://pan.quark.cn/",
        }
        params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', '__dt': '1235217', '__t': f'{str(int(time.time() * 1000))}'}
        json_data = {'fids': [fid_encrypt]}
        resp = session.post('https://drive-pc.quark.cn/1/clouddrive/file/download', params=params, json=json_data, cookies=cookies, headers=headers)
        resp.raise_for_status()
        download_data = resp2json(resp=resp)
        download_url = download_data["data"][0]["download_url"]
        download_result['download_data'] = download_data
        # return
        return download_result, download_url
    '''parsefromurl'''
    @staticmethod
    def parsefromurl(url: str, passcode: str = '', cookies: str | dict = '', max_tries: int = 3):
        for _ in range(max_tries):
            try:
                download_result, download_url = QuarkParser._parsefromurl(url=url, passcode=passcode, cookies=cookies)
                break
            except:
                download_result, download_url = {}, ""
        return download_result, download_url
    '''_parsefromurl'''
    @staticmethod
    def _parsefromurl(url: str, passcode: str = '', cookies: str | dict = ''):
        # init
        session, download_result = requests.Session(), {}
        parsed_url = urlparse(url)
        pwd_id = parsed_url.path.strip('/').split('/')[-1]
        cookies = cookies2dict(cookies)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Core/1.94.225.400 QQBrowser/12.2.5544.400',
            'origin': 'https://pan.quark.cn', 'referer': 'https://pan.quark.cn/', 'accept-language': 'zh-CN,zh;q=0.9',
        }
        # share/sharepage/token
        json_data = {'pwd_id': pwd_id, 'passcode': passcode}
        params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', '__dt': '596', '__t': f'{str(int(time.time() * 1000))}'}
        resp = session.post('https://drive-h.quark.cn/1/clouddrive/share/sharepage/token', params=params, json=json_data, cookies=cookies, headers=headers)
        resp.raise_for_status()
        token_data = resp2json(resp=resp)
        stoken = token_data['data']['stoken']
        download_result['token_data'] = token_data
        time.sleep(0.1)
        # share/sharepage/detail
        params = {
            "pr": "ucpro", "fr": "pc", "uc_param_str": "", "ver": "2", "pwd_id": pwd_id, "stoken": stoken, "pdir_fid": "0", "force": "0",
            "_page": "1", "_size": "50", "_fetch_banner": "1", "_fetch_share": "1", "fetch_relate_conversation": "1", "_fetch_total": "1",
            "_sort": "file_type:asc,file_name:asc", "__dt": "1020", "__t": f"{int(time.time() * 1000)}"
        }
        resp = session.get('https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail', params=params, cookies=cookies, headers=headers)
        resp.raise_for_status()
        detail_data = resp2json(resp=resp)
        fid = detail_data["data"]["list"][0]["fid"]
        share_fid_token = detail_data["data"]["list"][0]["share_fid_token"]
        download_result['detail_data'] = detail_data
        time.sleep(0.1)
        # clouddrive/file/info/path_list
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": "", "__dt": "1266", "__t": f"{int(time.time() * 1000)}"}
        json_data = {"file_path": ["/来自：分享"]}
        resp = session.post('https://drive-pc.quark.cn/1/clouddrive/file/info/path_list', params=params, json=json_data, cookies=cookies, headers=headers)
        resp.raise_for_status()
        path_list_data = resp2json(resp=resp)
        to_pdir_fid = path_list_data["data"][0]["fid"]
        download_result['path_list_data'] = path_list_data
        time.sleep(0.1)
        # share/sharepage/save
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": "", "__dt": "5660", "__t": f"{int(time.time() * 1000)}"}
        json_data = {"pwd_id": pwd_id, "stoken": stoken, "pdir_fid": "0", "to_pdir_fid": to_pdir_fid, "fid_list": [fid], "fid_token_list": [share_fid_token], "scene": "link"}
        resp = session.post(url='https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save', params=params, cookies=cookies, json=json_data, headers=headers)
        resp.raise_for_status()
        save_data = resp2json(resp=resp)
        task_id = save_data['data']['task_id']
        download_result['save_data'] = save_data
        time.sleep(0.1)
        # clouddrive/task
        for retry_index in range(5):
            try:
                params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', 'task_id': task_id, 'retry_index': str(retry_index), '__dt': '6355', '__t': f'{str(int(time.time() * 1000))}'}
                resp = session.get('https://drive-pc.quark.cn/1/clouddrive/task', params=params, cookies=cookies, headers=headers)
                resp.raise_for_status()
                task_data = resp2json(resp=resp)
                fid_encrypt = task_data['data']['save_as']['save_as_top_fids'][0]
                download_result['task_data'] = task_data
                break
            except:
                time.sleep(0.1)
                continue
        # clouddrive/file/download
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/2.5.56 Chrome/100.0.4896.160 Electron/18.3.5.12-a038f7b798 Safari/537.36 Channel/pckk_other_ch",
            "Accept": "application/json, text/plain, */*", "Content-Type": "application/json", "accept-language": "zh-CN", "origin": "https://pan.quark.cn", "referer": "https://pan.quark.cn/",
        }
        params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': '', '__dt': '6743', '__t': f'{str(int(time.time() * 1000))}'}
        json_data = {'fids': [fid_encrypt]}
        resp = session.post('https://drive-pc.quark.cn/1/clouddrive/file/download', params=params, json=json_data, cookies=cookies, headers=headers)
        resp.raise_for_status()
        download_data = resp2json(resp=resp)
        download_url = download_data["data"][0]["download_url"]
        download_result['download_data'] = download_data
        # return
        return download_result, download_url