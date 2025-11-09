'''
Function:
    一些工具函数
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import re
import json


'''新建文件夹'''
def touchdir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)
        return False
    return True


'''导入配置文件'''
def loadConfig(filepath='config.json'):
    f = open(filepath, 'r', encoding='utf-8')
    return json.load(f)


'''清除可能出问题的字符'''
def filterBadCharacter(string, fit_gbk=True):
    need_removed_strs = ['<em>', '</em>', '<', '>', '\\', '/', '?', ':', '"', '：', '|', '？', '*']
    for item in need_removed_strs:
        string = string.replace(item, '')
    try:
        rule = re.compile(u'[\U00010000-\U0010ffff]')
    except:
        rule = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
    string = rule.sub('', string)
    if fit_gbk:
        string_clean = ''
        for c in string:
            try: 
                c = c.encode('gbk').decode('gbk')
                string_clean += c
            except:
                continue
        string = string_clean
    return string.strip().encode('utf-8', 'ignore').decode('utf-8')


'''秒转时分秒'''
def seconds2hms(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return '%02d:%02d:%02d' % (h, m, s)