from 采集某网页的百科页面的领导名单 import fangwen
from selenium import webdriver
import pandas
import re
import random
import traceback
import pandas as pd
from datetime import datetime
import os

#########################################
pth = 'F:/0/0304/'
output_path = pth + '交通运输单位采集-{}.xlsx'
args = ["2", "0"]  # "-1",
skip = 0
###########################################

# 修改谷歌驱动器的位置
# driver_path = r'C:\Users\laungee\Downloads\chromedriver_win32\chromedriver.exe'
driver_path = r'D:\chromedriver-win64\chromedriver.exe'
prefs = {'profile.managed_default_content_settings.images': 2}
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option('prefs', prefs)
chrome_options.add_argument("headless")
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(driver_path, options=chrome_options)
# driver.set_page_load_timeout(10)

sd = round(10E5 * random.random())  # 错误 log

def get_ins_name(city, provience, type, ctype=True, prov=False, count=False):  # update: 交通版!
    ctype = ctype or (provience==city)
    if (city[-1] != '市') and ('省' not in city) and ('区' not in city) and ('县' not in city) and ('乡' not in city) and ('自治' not in city) and ('市' not in provience):
        city += '市' if not prov or city in ['北京', '上海', '天津', '重庆'] else '省'
    if count and ('市' not in provience):
        provience += '市'
    if type == 0:
        return '{}交通运输厅'.format(city) if ctype else '{}{}交通运输厅'.format(provience, city)
    elif type == 1:
        return '{}铁路监督局'.format(city) if ctype else '{}{}铁路监督局'.format(provience, city)
        # return '中国共产党{}{}委员会'.format(provience, city)
    elif type == 2:
        return '{}交通运输局'.format(city) if ctype else '{}{}交通运输局'.format(provience, city)
        # return '{}{}人民代表大会常务委员会'.format(provience, city)
    elif type == 3:
        return '{}道路运输管理局'.format(city) if ctype else '{}{}道路运输管理局'.format(provience, city)
        # return '{}{}人民政府'.format(provience, city)
    elif type == 4:
        return '{}城市交通运输管理处'.format(city) if ctype else '{}{}城市交通运输管理处'.format(provience, city)
        # return '中国人民政治协商会议{}{}委员会'.format(provience, city)
    elif type == 5:
        return '{}交通港航业务受理中心'.format(city) if ctype else '{}{}交通港航业务受理中心'.format(provience, city)
        # return '中国共产党{}委员会'.format(city)
    elif type == 6:
        return '{}水利局'.format(city) if ctype else '{}{}水利局'.format(provience, city)
        # return '{}人民代表大会常务委员会'.format(city)
    elif type == 7:
        return '{}人民政府'.format(city)
    elif type == 8:
        return '中国人民政治协商会议{}委员会'.format(city)


url = 'https://baike.baidu.com/item/{}?force=1'
url搜人 = 'https://baike.baidu.com/search/none?word={}'
# input_frame_path = pth + '水利部官网直属单位链接.xlsx'
fnames = ['2023-03-17行政区划.xlsx', '地区名单.xlsx']  # pth+'铁道科学研究院-院属单位.xlsx',
input_frames = []
input_types = []
for fname in fnames:
    input_frame_path = os.path.abspath(os.path.join(os.path.abspath(__file__), '..', '配置文件', fname) if "\\" not in fname else fname)  #地区名单.xlsx edit 更新地区名单，来源https://zhuanlan.zhihu.com/p/640200205
    input_frame = pandas.read_excel(input_frame_path, sheet_name='Sheet1')
    go = args[fnames.index(fname)] #input('市层面/省层面/区层面？(0/1/2)')
    input_types.append(go)
    if go == '1':
        input_frame = input_frame.drop_duplicates('provience').reset_index().drop(columns='index')
    elif go == '2':
        input_frame = pandas.read_excel(input_frame_path, sheet_name='2023-03-17行政区划')
        input_frame = input_frame.loc[:,['城市', '区县']]
        input_frame = input_frame.rename(columns={'城市': 'provience', '区县': 'city'}).dropna().reset_index().drop(columns='index')
    input_frames.append(input_frame)  # update 多个源名单连续运行
table_list = []
output = pandas.DataFrame(columns=[])
output2 = pandas.DataFrame(columns=[])
if skip == -1:
    skips = [0, 0]
else:
    skips = []
    for fname in fnames:
        skips.append(int(input(f'{fname} lines_to_skip = ')))

# 写数据
def write_data(output_path, output, output2, tried=0):
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            output.fillna(value='')
            output.drop_duplicates(subset=output.columns, inplace=True)
            output2.drop_duplicates(subset=output2.columns, inplace=True)
            output.to_excel(writer, index=False, sheet_name='领导名单')
            output2.to_excel(writer, index=False, sheet_name='引用来源及时间')
            return True
    except:
        if tried > 5:
            return False
        return write_data(output_path, output, output2, tried+1)

# 刷新网页
def cdrv_refresh():
    global driver
    driver = webdriver.Chrome(driver_path, options=chrome_options)
    driver.set_page_load_timeout(10)


with open(f'tocheck.txt', 'r', encoding='utf-8') as f:
    links = f.read().split('\n')

for link in ['https://baike.baidu.com/item/%E6%B8%A9%E5%B7%9E%E5%B8%82%E6%B4%9E%E5%A4%B4%E5%8C%BA%E4%BA%A4%E9%80%9A%E8%BF%90%E8%BE%93%E5%B1%80?force=1']*1:#links[12:]:
    try:
        try:
            driver.get(link)
        except:
            cdrv_refresh()
            driver.get(link)
        print(link)
        table, table_ref = fangwen(link, driver=driver)
    except Exception as e:
        print(e, traceback.format_exc())

'''# with open(f'list.txt', 'r', encoding='utf-8') as f:
#     单位s = f.read().split('#')[0].strip().split('、')
单位s = input_frames[0]['单位'].values.tolist() #可改
rootword = '中国铁道科学研究院'  # '中国民用航空局''中国民用航空''交通运输直属'
judgeword = '所'
单位s = list(map(lambda x: rootword + x if judgeword in x and '铁' not in x else x, 单位s))#len(set(rootword) & set(x) - set('中国局'))==0'''

if __name__ == '__main__':
    # #  按已知单位名称遍历
    # for 单位 in 单位s:
    #     link = url.format(单位)
    #     try:
    #         try:
    #             driver.get(link)
    #         except:
    #             cdrv_refresh()
    #             driver.get(link)
    #         table, table_ref = fangwen(link, driver=driver)
    #     except Exception as e:
    #         print(f'log at ./log{sd}.txt')
    #         with open(f'{pth}log{sd}.txt', 'a', encoding='utf-8') as f:
    #             f.write(单位 + '...' + traceback.format_exc() + '\n\n')
    #         continue
    #     print(len(table)) if len(table) else 1
    #     if len(table) == 0:
    #         kw = 单位.replace(rootword, '')
    #         driver.get(url搜人.format(kw + '领导'))
    #         aas = driver.find_elements_by_xpath('//div[@class="searchResult"]//dl//dd/a')
    #         if len(aas) > 0:
    #             row = len(output)
    #             c = 0
    #             for a in aas:
    #                 try:
    #                     if len(set(kw) & set(a.text + '管理')) < len(kw) - round(len(kw) / 9) or '(' not in a.text[:6]:
    #                         continue
    #                     output.loc[row, '姓名'] = a.text.strip().split('(')[0]
    #                     output.loc[row, '单位'] = kw
    #                     if '(' in a.text:
    #                         job = re.search('[(][^.)]+[.)]', a.text.strip()).group()[1:-1]
    #                         unit = re.search('[^团公司场]+([公][司]|[集][团]|[机][场]|[局厅部])', job)
    #                         unit = unit.group() if unit else kw
    #                         shortjob = job.replace(unit, '')
    #                         output.loc[row, '职位'] = shortjob
    #                         output.loc[row, '单位'] = unit
    #                     output.loc[row, '链接'] = a.get_attribute('href')
    #                     c += 1
    #                 except Exception as e:
    #                     print(f'log at ./log{sd}.txt')
    #                     with open(f'{pth}log{sd}.txt', 'a', encoding='utf-8') as f:
    #                         f.write(url搜人.format(kw) + '...' + traceback.format_exc() + '\n\n')
    #             print(kw, c, sep='\t') if c > 0 else 1
    #     table['来源百科'] = link
    #     output = pd.concat([output, table])
    #     output2 = pd.concat([output2, table_ref])
    # f = 0
    # rootword = fnames[0].split('/')[-1].split('.')[0]
    # while not f:
    #     f = write_data(output_path.format(rootword), output, output2)

    output_path = output_path.format('区交通运输局2')

    #  按地级市遍历
    for input_frame in input_frames[:1]:  # update
        wrote = False
        for row in range(skips[input_frames.index(input_frame)], len(input_frame)):
            for i in range(2, 3):  #一轮1, 7 # , 9
                # link = 'https://baike.baidu.com/item/重庆市綦江区水利局?force=1'#url.format(get_ins_name('长治市', '', 6, ctype=len(input_frame)<=400))
                # link = url.format(get_ins_name(input_frame.loc[row, 'provience'], input_frame.loc[row, 'city'], i, ctype=len(input_frame) <= 400))
                kw = get_ins_name(input_frame.loc[row, 'city'], input_frame.loc[row, 'provience'], i, ctype=len(input_frame) <= 400,
                                               prov=input_types[input_frames.index(input_frame)] == '1',
                                               count=input_types[input_frames.index(input_frame)] == '2')
                link = url.format(kw)  ##### 从不同等级进行查询
                # link = url.format(input_frame.loc[row, '单位'])  # get_ins_name(input_frame.loc[row, 'city'], input_frame.loc[row, 'provience'], i)
                try:
                    try:
                        driver.get(link)
                    except:
                        cdrv_refresh()
                        driver.get(link)
                    ft = driver.find_element_by_tag_name('body').text
                    keyw = kw
                    shortkeyw = re.search('机场|运输|局|铁道|铁路|公司|集团|大学', keyw)
                    alikes = '机场|运输|局|铁道|铁路|公司|集团|大学'.split('|')
                    shortkeyw = shortkeyw.group() if shortkeyw else ''
                    if '错误页' in ft:
                        continue
                    elif '请在下列义项' in ft:
                        choices = driver.find_elements_by_tag_name('li')
                        if not choices or '个同名词条' in ft:
                            choices = driver.find_elements_by_xpath('//a/span[2]')
                        if [x for x in choices if keyw in x.text]:
                            choice = [x for x in choices if keyw in x.text][0]
                        elif shortkeyw and [x for x in choices if shortkeyw in x.text]:
                            choice = [x for x in choices if shortkeyw in x.text][0]
                            print(keyw, [x for x in choices if shortkeyw in x.text][0].text)
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
                                continue
                        if driver.find_elements_by_xpath(f'//div[@id="content"]/div/div/a'):
                            a = driver.find_elements_by_xpath(
                                f"//div[@id='content']/div/div/a/span[contains(text(),'{choice.text}')]/..")
                        try:
                            if choice.find_elements_by_tag_name('a'):
                                url = choice.find_element_by_tag_name('a').get_attribute('href')
                                driver.get(url)
                            elif 'a' in vars().keys() and a:
                                print(*[x.text for x in a], shortkeyw)
                                a = a[0]
                                url = a.get_attribute('href')
                                driver.get(url)
                        except Exception as e:
                            print(e, traceback.format_exc())
                        link = driver.current_url
                    table, table_ref = fangwen(link, driver=driver); table.reset_index(inplace=True); table.drop(columns='index', inplace=True)
                except Exception as e:
                    print(f'log at ./log{sd}.txt')
                    with open(f'{pth}log{sd}.txt', 'a', encoding='utf-8') as f:
                        f.write(get_ins_name(input_frame.loc[row, 'city'], input_frame.loc[row, 'provience'],
                                             i) + '...' + traceback.format_exc() + '\n\n')
                    continue
                for col in input_frame.columns:
                    if col not in ['city', 'provience']:
                        table[col] = input_frame.loc[row, col]
                table['市或区'] = input_frame.loc[row, 'city']
                table['省或市'] = input_frame.loc[row, 'provience']
                table['来源百科'] = link
                print(len(table)) if len(table) else 1
                if len(table) > 0:
                    for row in range(len(table)):
                        output_row = len(output)
                        for column in table.columns:
                            output.loc[output_row, column] = table.loc[row, column]
                else:
                    driver.get(url搜人.format(kw))
                    aas = driver.find_elements_by_xpath('//div[@class="searchResult"]//dl//dd/a')
                    if len(aas) > 0:
                        row = len(output)
                        c = 0
                        for a in aas:
                            try:
                                if len(set(kw) & set(a.text + '管理')) < len(kw) - round(len(kw)/9) or '(' not in a.text[:6]:
                                    continue
                                output.loc[row, '姓名'] = a.text.strip().split('(')[0]
                                output.loc[row, '单位'] = kw
                                if '(' in a.text:
                                    job = re.search('[(][^.)]+[.)]', a.text.strip()).group()[1:-1]
                                    unit = re.search('[^局厅]+[局厅]', job)
                                    unit = unit.group() if unit else kw
                                    shortjob = job.replace(unit, '')
                                    output.loc[row, '职位'] = shortjob
                                    output.loc[row, '单位'] = unit
                                output.loc[row, '链接'] = a.get_attribute('href')
                                table['市或区'] = input_frame.loc[row, 'city']
                                table['省或市'] = input_frame.loc[row, 'provience']
                                c += 1
                            except Exception as e:
                                print(f'log at ./log{sd}.txt')
                                with open(f'{pth}log{sd}.txt', 'a', encoding='utf-8') as f:
                                    f.write(url搜人.format(kw) + '...' + traceback.format_exc() + '\n\n')
                        print(kw, c, sep='\t') if c>0 else 1
                if len(table_ref) > 0:
                    for row2 in range(len(table_ref)):
                        output_row2 = len(output2)
                        for column2 in table_ref.columns:
                            output2.loc[output_row2, column2] = table_ref.loc[row2, column2]
            if len(output) % 100 >= 49 and (not wrote):
                wrote = write_data(output_path, output, output2)
            if len(output) % 100 >= 80:
                wrote = False
        driver.close()
        f = 0
        while not f:
            f = write_data(output_path, output, output2)
    print(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M'))
    print('done')
    print()
    # os.system('shutdown -s -f -t 5')