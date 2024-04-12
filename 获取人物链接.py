# !/user/bin/env python3
# -*- coding: utf-8 -*-
import json
import pandas as pd
import numpy as np
from IPython.display import clear_output
import time
from datetime import datetime
import string
import json
import re
import copy
import os
import selenium
import requests
import urllib
from selenium import webdriver
import random
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import traceback
from tools import spillt

######################
pth = 'F:/0/0304/'
######################

driver_path = r'D:\chromedriver-win64\chromedriver.exe'
# prefs = {'profile.managed_default_content_settings.images': 2}  # 会显示不出搜狗验证码
chrome_options = webdriver.ChromeOptions()
# chrome_options.add_experimental_option('prefs', prefs)
# chrome_options.add_argument("headless")
# chrome_options.add_argument('--no-sandbox')
# chrome_options.add_argument('--disable-gpu')
# chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(driver_path, options=chrome_options)

def cdrv_refresh():
    global driver
    try:
        driver.close()
        # windows = driver.window_handles
        # for window in windows:
        #     driver.switch_to.window(window)
        #     driver.close()
    except:
        pass
    driver = webdriver.Chrome(driver_path, options=chrome_options)
    driver.set_page_load_timeout(10)

sd = round(10E5*random.random())
print(f'log at ./log{sd}.txt')

yz_failed = 0

def search_sg(etprs, subject='', typ='人', pg=1, n=False):
    if pg<2:
        url = f"https://www.sogou.com/web?query={urllib.parse.quote(' '.join([etprs, subject, typ]))}"
    else:
        url = f"https://www.sogou.com/web?query={urllib.parse.quote(' '.join([etprs, subject, typ]))}&page={pg}"
    if n:
        driver.execute_script(f"window.open('{url}', '_blank');")
    else:
        driver.get(url)


alikes = ['海事', '航务', '水运', '交通运输局', '交通局', '水利局', '交通运输厅', '教授', '讲师', '院士', '医生', '导师', '硕导', '导', '博导', '研究', '法院']
if 'unsure' not in vars().keys():
    unsure = []


def 搜索百科(名字, keyw, watch=True, ylk='https://www.sogou.com/', flg=1, rigid=True):
    global yz_failed
    shortkeyw = [x for x in alikes if x in keyw or x[:2] in keyw] + ['']
    shortkeyw = shortkeyw[0]
    if len(spillt(keyw, [None, '，', '、', ','])) > 1:
        shortkeyw = spillt(keyw, [None, '，', '、', ','])[0]
    elif len(spillt(keyw, ['：'])) > 1:
        shortkeyw = spillt(keyw, ['：'])[1]
    url = None
    best = False
    if keyw == '':
        print('未定义关键词')
        keyw = input(名字 + '关键词：') if watch and not rigid else ''
    if shortkeyw == '':
        shortkeyw = re.search('[市区县省][\w]+', keyw)
        shortkeyw = shortkeyw.group()[1:] if shortkeyw else ''
    if shortkeyw == '':
        shortkeyw = keyw
    try:
        search_sg(名字, f'{keyw} site:baike.baidu.com', n=False)
        time.sleep(0.3)
        # windows = driver.window_handles  # 获取句柄
        # driver.switch_to.window(windows[-1])
        if driver.find_elements_by_xpath('//p[contains(text(),"验证码")]'):
            yz_failed += 1
            raise Exception('搜狗验证码')
        h3s = driver.find_elements_by_xpath('//h3/a')
        h3s = list(filter(lambda x: 名字 in x.text, h3s))
        if not h3s or len(set(名字) & set(h3s[0].text.strip().replace('_百度百科', ''))) < 2:
            driver.get('https://baike.baidu.com/item/' + 名字)
            if '访问的页面不存在' in driver.find_element_by_tag_name('body').text:
                print(f'无相关百科({名字})')
                if rigid or (input(f"搜不到此人({名字})信息 1/0") not in ['0', '']):
                    # close
                    # windows = driver.window_handles
                    # for window in windows[1:]:
                    #     driver.switch_to.window(window)
                    #     driver.close()
                    # driver.switch_to.window(windows[0])
                    return '', flg
        else:
            best = 1
            h3 = h3s[0]
            driver.get(h3.get_attribute('href'))
            # driver.execute_script("arguments[0].click();", h3)

        # windows = driver.window_handles  # 获取句柄
        # driver.switch_to.window(windows[-1])
        tries = 0
        while 'baike' not in driver.current_url:
            time.sleep(0.1)
            tries += 1
            if tries > 9:
                print('未采集到百科链接')
                break
            # driver.switch_to.window(driver.window_handles[-1])

        ft = driver.find_element_by_tag_name('body').text
        if '无法访问此网站' in ft:
            cdrv_refresh()
            return 搜索百科(名字, keyw, watch, ylk, flg, rigid)
        if best and shortkeyw[:2] in ft:
            url = driver.current_url
        elif best and keyw[:2] in ft:
            url = driver.current_url
            print(keyw[:2], keyw, 名字)
            unsure.append([名字, keyw])
            return url, flg
        if best and (shortkeyw if shortkeyw and len(keyw) > 8 else keyw) in ft:  # rootkeyw
            pass
        elif not driver.find_elements_by_xpath("//svg[text()='编辑']") and ('请在下列义项' in ft or '个同名词条' in ft):
            if driver.find_elements_by_xpath('//span[contains(text(), "展开")]'):
                driver.execute_script("arguments[0].click();",
                                      driver.find_element_by_xpath('//span[contains(text(), "展开")]'))
                time.sleep(0.2)
            choices = driver.find_elements_by_tag_name('li')
            choices = [x for x in choices if x.text and x.text[0] == '▪']
            if not choices or '个同名词条' in ft:
                choices = driver.find_elements_by_xpath('//a/span[2]')
            time.sleep(0.5 if watch else 0.2)
            if [x for x in choices if keyw in x.text]:
                choice = [x for x in choices if keyw in x.text][0]
            elif shortkeyw and [x for x in choices if shortkeyw in x.text]:
                choice = [x for x in choices if shortkeyw in x.text][0]
                print(keyw, [x for x in choices if shortkeyw in x.text][0].text, 名字)
            else:
                candidates = []
                for kw in [x for x in alikes if x in keyw or x[:2] in keyw]:
                    choice = [x for x in choices if kw in x.text]
                    candidates += choice
                    if choice:
                        print(kw)
                        shortkeyw = kw
                if candidates:
                    choice = max(candidates, key=lambda x: len(set(keyw) & set(x.text)))
                else:
                    print(f'同名无关({名字})')
                    time.sleep(0 if watch else 0.1)
                    return '', flg
            if driver.find_elements_by_xpath(f'//div[@id="content"]/div/div/a'):
                a = driver.find_elements_by_xpath(
                    f"//div[@id='content']/div/div/a/span[contains(text(),'{choice.text}')]/..")
            try:
                if choice.find_elements_by_tag_name('a'):
                    url = choice.find_element_by_tag_name('a').get_attribute('href')
                    driver.get(url)
                    time.sleep(0.3)
                elif 'a' in vars().keys() and a:
                    print(*[x.text for x in a], shortkeyw)
                    a = a[0]
                    url = a.get_attribute('href')
                    driver.get(url)
                    time.sleep(0.3)
                else:
                    time.sleep(0 if watch else 0.1)
                    url = driver.current_url
            except Exception as e:
                print(e, traceback.format_exc())
                url = driver.current_url
            if driver.find_elements_by_xpath('//span[text()="收起"]'):
                driver.execute_script("arguments[0].click();", driver.find_element_by_xpath('//span[text()="收起"]'))
        else:
            url = driver.current_url

        ft = driver.find_element_by_tag_name('body').text
        if (f'{shortkeyw if shortkeyw else keyw}' not in ft) or (
                名字 not in driver.find_element_by_tag_name('h1').text):
            if not (len(keyw) > 3 and len(
                    max([''] + re.findall(f'[{keyw[keyw.index("市") + 1:] if "市" in keyw[:-1] else keyw}]+', ft),
                        key=len)) > 3):
                if rigid:
                    go = '0'
                    print(f"没有百科({名字})")
                else:
                    go = input(f"打开百科({名字})")
                if go == '0':
                    # close
                    # windows = driver.window_handles
                    # for window in windows[1:]:
                    #     driver.switch_to.window(window)
                    #     driver.close()
                    # driver.switch_to.window(windows[0])
                    return '', flg
                if go in ['00', '名字错误']:
                    return 搜索百科(input(名字), keyw, watch, ylk, flg, rigid)
        # windows = driver.window_handles  # 获取句柄
        # driver.switch_to.window(windows[-1])

        # close
        # windows = driver.window_handles
        # for window in windows[1:]:
        #     try:
        #         driver.switch_to.window(window)
        #         driver.close()
        #     except:
        #         pass
        # driver.switch_to.window(windows[0])
    except Exception as e:
        if 'selenium.common.exceptions.WebDriverException' not in traceback.format_exc():
            print(e)
            print(traceback.format_exc())
        if not watch or (datetime.now().hour > 17 or datetime.now().hour < 9):
            windows = driver.window_handles
            cdrv_refresh()
            if ylk:
                driver.get(ylk)
            if flg:
                flg = 0
                return 搜索百科(名字, keyw, watch, ylk, flg, rigid)
        else:
            if '验证码' not in driver.find_element_by_tag_name('body').text or input(
                    "请检查是否出现验证界面 1/0") not in ['0', '']:
                return 搜索百科(名字, keyw, watch, ylk, flg, rigid)
            else:
                if input(f"搜不到此人({名字})信息 1/0") not in ['0', '']:
                    # close
                    # windows = driver.window_handles
                    # for window in windows[1:]:
                    #     driver.switch_to.window(window)
                    #     driver.close()
                    # driver.switch_to.window(windows[0])
                    return '', flg
                else:
                    cdrv_refresh()
                    if ylk:
                        driver.get(ylk)
                    if flg:
                        flg = 0
                        return 搜索百科(名字, keyw, watch, ylk, flg, rigid)
                    url = driver.current_url
        with open(f'{pth}log{sd}.txt', 'a') as f:
            f.write(名字 + '\n')
    if 'url' not in vars().keys():
        url = ''
    return url, flg


def output_table(df_, rootkeyw='', outfile='百科链接', watch=True, auxcol='市或区'):
    global yz_failed
    try:
        driver.switch_to.window(driver.window_handles[0])
    except:
        cdrv_refresh()
    fakenamelist = []
    cols = list(set(df_.columns) & {'姓名', '单位', '职务', '分工', '职位'})
    job_col = [x for x in cols if x[0]=='职'][0]
    有效ind = list(df_.drop_duplicates(cols).index)
    def save_data(df_):
        try:
            df_.drop_duplicates(['姓名', '单位', job_col], inplace=True)
            df_.to_excel(pth + f"{outfile}{datetime.strftime(datetime.now(), '%m%d%H%M') if len(outfile) < 6 else ''}.xlsx",
                         index=False)
            return True
        except:
            return False
    for i in range(0, len(df_)):
        try:
            if i not in 有效ind:
                continue
            elif '链接' in df_.columns and not pd.isna(df_.loc[i, '链接']):
                continue
            keyw = df_.loc[i, '单位'] if not pd.isna(df_.loc[i, '单位']) else df_.loc[i, job_col] #备用keyw
            if pd.isna(keyw) or keyw == '':
                keyw = df_.loc[i, auxcol] if auxcol in df_.columns else ''
            keyw = '' if pd.isna(keyw) else keyw
            if rootkeyw:
                keyw = rootkeyw + keyw
            nm = df_.loc[i, '姓名']
            if not nm or pd.isna(nm):
                continue
            if '（' in nm:
                nm = nm[:nm.index('（')]
            if len(nm)>3:
                fakenamelist.append(nm)
            res, flg = 搜索百科(nm, keyw, watch=watch)

            if yz_failed >= 3:
                watch = True
                chrome_options = webdriver.ChromeOptions()
                cdrv_refresh()
                yz_failed = 0

            tries = 3
            while not res:
                res, flg = 搜索百科(nm, keyw, watch=watch, flg=flg)
                tries -= 1
                if tries < 1:
                    break
                if flg:
                    break
            if res:
                df_.loc[i, '链接'] = res
            if i % 20 == 9:
                save_data(df_)
        except Exception as e:
            print(e, i)
    while not save_data(df_):
        input('请关闭文件(press Enter)')
    with open(pth + f'fakenames{outfile}.txt', 'w', encoding="utf-8") as f:
        f.write(json.dumps(fakenamelist, ensure_ascii=False))


def reach_files(topdown=True):
    for root, dirs, files in os.walk(pth, topdown):
        if len(files) > 0:
            break
    return files


if __name__  == '__main__':
    ######
    map_cols = {"DUTY_NAME": "职位", "ALUMNI_NAME": "姓名"}#"COMPANY_NAME": "单位",
    ######
    # have = []
    # for root, dirs, files in os.walk(f"{pth}0205/", topdown=False):
    #     if len(files) > 0:
    #         break

    # for fn in files:
    #     if '百科采集' in fn:
    #         df1 = pd.read_excel(f"{pth}0205/{fn}")
    #         df1['采集来源'] = fn[:fn.index('_')]
    #         have.append(df1)
    # have = pd.concat(have).reset_index().drop(columns='index')
    #
    # output_table(have, rootkeyw='水利部', outfile='水利部官网百科链接', watch=True)
    for fn in ['人物信息管理-标签数据1.xlsx']:
        while fn not in reach_files(True):
            time.sleep(60)
            if datetime.now().hour in range(20,24):
                break
        if fn in reach_files():
            df_ins = pd.read_excel(pth + fn, sheet_name=None)  # '0205/地级市百科.xlsx'
            for sn in df_ins.keys():
                df_in = df_ins[sn]
                for col in map_cols:
                    if col in df_in.columns:
                        df_in[map_cols[col]] = df_in[col]
                df_in['采集来源'] = '搜狗+百科'#'地级市百科'
                output_table(df_in, outfile=f"人物百科链接-{re.search('[-][^.]+[.]', fn).group()[1:-1]}-{sn}", auxcol="INDUSTRY", watch=datetime.now().hour in list(range(9, 12)) + list(range(14, 18)))

    # pd.DataFrame(unsure, columns=['姓名', '单位']).drop_duplicates().to_excel(pth + 'unsure.xlsx', index=False)
    if 'unsure' in vars().keys():
        with open(pth + f"unsure{datetime.strftime(datetime.now(), '%m%d%H%M')}.txt", 'w', encoding="utf-8") as f:
            f.write(json.dumps(unsure, ensure_ascii=False))
    print()
    # os.system('shutdown -s -f -t 14400')
