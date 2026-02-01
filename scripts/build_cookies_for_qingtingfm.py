'''
Function:
    Implementation of QingtingMusicClient Cookies Builder
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import warnings
import requests
warnings.filterwarnings('ignore')


'''settings'''
USERNAME = 'Your Phone Number Here'
PASSWORD = 'Your Password Here'


'''buildqingtingfmcookies'''
def buildqingtingfmcookies():
    data = {'account_type': '5', 'device_id': 'web', 'user_id': USERNAME, 'password': PASSWORD}
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    }
    resp = requests.post('https://u2.qingting.fm/u2/api/v4/user/login', headers=headers, data=data, verify=False)
    resp.raise_for_status()
    raw_data = resp.json()['data']
    return {'qingting_id': raw_data['qingting_id'], 'access_token': raw_data['access_token'], 'refresh_token': raw_data['refresh_token']}


'''tests'''
if __name__ == '__main__':
    print(buildqingtingfmcookies())