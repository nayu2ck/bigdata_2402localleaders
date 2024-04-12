import time
import re
import pandas
from selenium import webdriver
from lxml import etree
import traceback
import hanlp
import copy
from datetime import datetime

#  upd 使用模型
tok = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)  # 分词
ner = hanlp.load(hanlp.pretrained.ner.MSRA_NER_ELECTRA_SMALL_ZH)  # 实体识别
srl = hanlp.load('CPB3_SRL_ELECTRA_SMALL') #角色识别

job_list = ['市长', '书记', '秘书', '区长', '主任', '常委', '部长', '主席', '成员', '党委', '政府', '人大', '政协', '干部'] #干部
job_list += ['局长', '司长', '院长', '副局长', '工程师', '调研员', '调查员', '组长', '党组成员', '处长', '总工', '经理', '党组成员', '总监', '主任', '巡视员', '厅长', '会计师', '经理', '指挥', '站长']  # edit 更新 3.8
specialization_list = ['分工', '工作', '负责', '主管', '职责', '分管', '主持', '协调', '协助', '联系', '指导', '履行', '参与', '个人简历'] #更新 3.8

def bk_t(t):
    tokens = tok(t)  # 分词
    # ners = ner(tokens)  # 实体识别。必须使用分词后的列表来进行实体识别
    srls = srl(tokens)
    return [x[0][0] for x in srls]
def hebing(names):
    real_name_list = []
    for name in names:
        name_singles = re.split(' ', name)
        if len(name_singles) > 1:
            remember = []
            for i in range(len(name_singles)):
                if i not in remember:
                    if len(name_singles[i]) == 1 and i < len(name_singles) - 1 and len(name_singles[i + 1]) == 1:
                        real_name_list.append(name_singles[i] + name_singles[i + 1])
                        remember.append(i + 1)
                    else:
                        real_name_list.append(name_singles[i])
        else:
            for i in range(len(name_singles)):
                real_name_list.append(name_singles[i])
    return real_name_list


def clean_name(name):
    p1 = re.compile(r'[（](.*?)[）]', re.S)
    name = re.sub(p1, '', name)
    p2 = re.compile(r'[\[](.*?)[\]]', re.S)
    name = re.sub(p2, '', name)
    p3 = re.compile(r'[(](.*?)[)]', re.S)
    name = re.sub(p3, '', name)
    name = re.sub('[^\u4e00-\u9fff]+', '', name)
    return name


def is_job(a, loose=False):  #edit loose
    for job in job_list:
        if job in a:
            return True
    if loose:
        if len(set(a) & set('总委员会局组副主任编辑院长书处工记')) > len(a)/2:
            return True
    return False


def is_Chinese(a):
    false_names = ['姓名', '截至', '名单', '年月']
    for false_name in false_names:
        if (false_name in a) and (len(a) - 2 < 3):
            return False
    for ch in a:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


def handle_with_person_td(person_xpath_td, driver, mkref=True):
    name_count = []
    dic = {}
    references = {}
    global output_row
    for a in person_xpath_td.find_elements_by_xpath('./div//a'):
        name = a.text
        try:
            person_url = 'https://baike.baidu.com' + a.find_elements_by_xpath('.//@href')[0]
        except:
            person_url = ''
        for name1 in name.split('、'):
            if is_Chinese(name1):
                dic[name] = person_url
                name_count.append(name)
    try:
        word_list = [x.text for x in person_xpath_td.find_elements_by_xpath('.//span')]
        if not word_list:
            word_list = [x.text for x in person_xpath_td.find_elements_by_xpath('.//div')]
        clean_word_list = ['']
        for word in word_list:
            if is_Chinese(word[0]):
                clean_word_list[-1] += word
        for word in clean_word_list:
            if is_Chinese(word):
                names = word.split('、')
                for name in names:
                    name = clean_name(name)
                    if name not in name_count and is_Chinese(name):
                        dic[name] = ''
                        name_count.append(name)
                        if mkref and person_xpath_td.find_elements_by_xpath('./parent::tr//sup'):
                            refs = ''.join([x.text.strip() for x in person_xpath_td.find_elements_by_xpath('./parent::tr//sup')])
                            refs = spillt(refs, '[]-,')
                            while '' in refs:  # refs == ['']
                                refs.remove('')
                            if '参考' not in person_xpath_td.find_element_by_xpath('./parent::tr').text.strip()[:2]:
                                references[name] = get_reference(driver, refs)
                            else:
                                references['a'] = get_reference(driver, refs)

    except:
        pass
    if mkref:
        return dic, name_count, references
    return dic, name_count  #edit - return dic


def panduan_table(table):
    caption = table.find_elements_by_tag_name('caption')#table.xpath('.//caption//text()')  # 表格的标题
    if caption:
        table_title = caption[0].text
    else:
        table_title = table.find_elements_by_xpath('./preceding::div')[-1].text
    # 获取表格的h2上方标题
    if len(table.find_elements_by_xpath('./preceding::h2')) != 0:
        h2_title = table.find_elements_by_xpath('./preceding::h2')[-1].text
    else:
        h2_title = ''
    # print('h2_title', h2_title)

    # 获取表格的h3上方标题
    if len(table.find_elements_by_xpath('./preceding::h3')) != 0:
        h3_title = table.find_elements_by_xpath('./preceding::h3')[-1].text
    else:
        h3_title = ''

    # 先搜索表格标题有‘现任领导’和‘主要领导的’且h3标签不含'历任'和'历届'
    titles = [h3_title, h2_title, table_title]
    if '现任领导' in titles:
        return True
    if len(table_title) != 0:
        if '历届' in ''.join(h3_title if h3_title else h2_title if h2_title else table_title) or '历任' in ''.join(h3_title if h3_title else h2_title if h2_title else table_title):
            return False
        if '领导' in ''.join(titles) or '主要领导' in ''.join(titles):
            return True
    # 再搜索h2标题为'政治' 或'政治体制' 的
    if '政治' in ''.join(titles) or '政治体制' in ''.join(titles):
        return True
    return False


def handle_with_person_span(form, driver, mkref=True):
    dic = {}
    yl = []
    references = {}; boldsr = []
    for i in range(1, 99):
        try:
            div = driver.find_element_by_xpath(form + '/following-sibling::div'*i)
        except:
            if mkref:
                return dic, yl, references
            return dic, yl
        spans = div.find_elements_by_tag_name('span')
        try:
            person_url = 'https://baike.baidu.com' + div.xpath('.//@href')[0]
        except:
            person_url = ''
        try:
            t = ''.join([x.text for x in spans if x.text and (x.text[0] != '[')])
        except:
            if mkref:  # 检查到的情况是有块地图
                return dic, yl, references
            return dic, yl
        if mkref:
            refs = ''.join([x.text.strip() for x in spans if x.text.strip() and (x.text.strip()[0] == '[')])
            refs = spillt(refs, '[]-,')
            while '' in refs:  # refs == ['']
                refs.remove('')
            if '参考资料' in div.text[:4]:
                references['a'] = get_reference(driver, refs)
        if div.find_elements_by_tag_name('h3' if 'h3' in form else 'h2') or div.find_elements_by_tag_name('h2') or ('历任' in div.text) or ('参考资料' in div.text[:4]) or ('直属单位' in div.text[:4]) or (div.get_attribute('data-module-type')=='map') or (div.text[:2] == '以上'):
            # check = input(t)
            break
        # try:  # 定位到的表格，可以不在这里处理
        #     table = div.find_element_by_xpath('/table')
        #     trs = table.find_elements_by_tag_name('tr')
        #     for j1 in range(len(trs)):
        #         tr = trs[j1]
        #         t = tr.text.strip()
        # except:
        #     pass
        # name = t.replace('\u3000', '').replace('\u2002', '').replace('\u0200B', '')  #edit 2.1取消删除空格.replace(' ', '')# edit: 更新
        name = t[:2].strip().replace('\u3000', '').replace('\u2002', '').replace('\u0200B', '') + t[2:] #edit 2.1 11:28
        name = name.replace('职责：', '\n职责：') if re.search('.+职责', name[:12]) else name #notdone # edit 2.2
        name = "职位：" +name  if name[:4]=='区水利局' else name
        name = name.replace('（女）', '').replace('(女)', '')  #update 2.7
        if '；' not in name:
            name = name.replace(';', '；')
        if '：' not in name:
            name = name.replace(':', '：')
        if '，' not in name:
            name = name.replace(',', '，')  # edit 2.1 同时存在全半角符号, 半角符号不做转换  # update
        序号 = re.match('[（(]?[0-9一二三四五六七八九十贰叁肆伍陆]+[\W\s]+', name)
        bold = 'bold' in ''.join([x.get_attribute('class') for x in spans]) #edit
        if bold:
            有序号 = True
            if len(boldsr) > 3 and False not in boldsr:
                有序号 = False
        boldsr.append(bold)
        if 序号:
            序号 = 序号.group()
            有序号 = True
            name = name.replace(序号, '')
        elif (('有序号' in vars().keys() and 有序号) or (name[:2] in ['分管', '中共', '牵头', '负责', '主管', '协调', '（与', '协助', '对口'] + specialization_list)) and (not bold):
            if yl and ((len(yl[-1]) > 6 and is_redundancy(yl[-1])) or (name[:2] in ['分管', '中共', '牵头', '负责', '主管', '协调', '（与', '协助', '对口'] + specialization_list) or (not bold and ((len(min(spillt(name, re.findall('[：，；。（]', name)), key=len)) >= min(4, len(name[:-1]))) if re.search('[\W]', name) else not (is_job(name) or len(catch_xingming(name)) <= 3)))):  #edit 2.1 增加长度限制 必须不包含姓名职位 #edit 和非粗体合并  # edit:把分工分多行写的合并 len(yl[-1]) > 6 and is_redundancy(yl[-1])
                name = name.replace('\u3000', '').replace('\u2002', '').replace('\u0200B', '')
                nk = '\n'.join([yl[-1], name[:-1] if name and (name[-1] in ['；', '。']) else name])
                dic[nk] = dic.pop(yl[-1])
                if yl[-1] in references:
                    references[nk] = references.pop(yl[-1])
                yl[-1] = nk
                continue
        if ' ' in name.replace("姓名", "")[4:] or '\u2002' in name.replace("姓名", "")[4:] or '\u3000' in name.replace("姓名", "")[4:] and "职" not in name: #3.8 15:40
            name = name[:4] + name[4:].replace(' ', '').replace('\u3000', '').replace('\u2002', '').replace('\u0200B', '')
        if re.findall('[\W]', name[:6]) and "职" not in name:
            name = name.replace(' ', '')

        if name:
            if name[-1] in ['；', '。', '：', '，']:
                name = name[:-1]
            if ('姓名' in name) and ('职务' in name or '职位' in name):
                sp = re.search('[\w]{2,3}[\W\s]+[\w]+[：]', name)
                if sp:
                    sp = re.search('[\W\s]+', sp.group()).group()
                    name1 = []
                    for segment in name.split(sp):
                        segment = re.search('[\w].+', segment).group()
                        if segment[:2] in ['姓名', '职务', '职位']:
                            name1.append(segment)
                    if len(name1) > 1:
                        for nm in name1:
                            dic[nm] = person_url
                            yl.append(nm)
                        if mkref and refs:
                            references[nm] = get_reference(driver, refs)
                        continue
            elif '：' in name:
                name1 = name.split('：')[-1]
                if len(set(name1) & set('总委员会副主任编辑院长书记')) < 2:
                    if '、' in name1[:4]:
                        for nm in name1.split('、'):
                            dic[name.split('：')[0] + '：' + nm] = person_url
                            yl.append(name.split('：')[0] + '：' + nm)
                        if mkref and refs:
                            references[nm] = get_reference(driver, refs)
                        continue
            if is_Chinese(name):
                dic[name] = person_url
                yl.append(name)
                if mkref and refs:
                    references[name] = get_reference(driver, refs)

    if mkref:
        return dic, yl, references
    return dic, yl  # edit: dic


def catch_xingming(nm, *argv):
    words = ['省', '市'] + list(argv) + ['党', '一级', '二级', '调', '院', '局', '三级', '四级', '五级', '书记', '委', '副', '总', '区', '组']
    if len(set(nm[:3]) - set('局党交通市委正副总主组织' + (百科标题 if '百科标题' in vars().keys() else (argv[0] if argv else '')))) < 2:
        return nm
    for word in words:
        if len(nm) <= 2:
            break
        if word in nm:  # edit 分割完单位名称后匹配1个关键字可能为人物名字本身
            if nm.index(word) in [2, 3] and len(set(nm[:3]) & set('一二三四五六级党局委员公共交通运输总副主席首区组会')) < 2:
                nm = nm[:nm.index(word)]
                if (word in argv) and (len(nm) <= 3):
                    break
    if re.match('[\w]{2,3}[\W\s]', nm):
        return re.match('[\w]+', nm).group()
    return nm


def yx(s: set, yl):
    l = list(s)
    l.sort(key=lambda x: yl.index(x))
    return l


def spillt(t: str, s):
    if type(t)==list:
        r = []
        for tt in t:
            if '.' in tt[1:-1]:
                if str.isdigit(tt[tt.index('.')-1]) and str.isdigit(tt[tt.index('.')+1]):
                    r.append(s)
                    continue
            r += tt.split(s)
        return r
    for sp in s:
        t = spillt([t] if type(t)==str else t, sp)
    while type(t) == list and '' in t:  # refs == ['']
        t.remove('')
    return t if type(t)==list else [t]


def seg_date(t, starty=0, rety=False):
    result = re.search('[\d]{4}[-][\d]{1,2}[-][\d]{1,2}', t)
    if result:
        result = result.group()
        if int(re.search('[\d]+', result).group()) < starty:
            return seg_date(t.replace(result, ''), starty)
        if rety:
            return int(re.search('[\d]+', result).group())
        else:
            return result
    return False


def get_reference(driver, il: list):  #auxiliary 定位参考资料和引用时间
    # il: 引用序号 列表
    result = {}
    try:
        div = driver.find_element_by_xpath("//div[text()=\"参考资料\"]/parent::div")
    except:
        return False
    lis = div.find_elements_by_tag_name('li')
    li_il = [li for li in lis if re.findall('[\d]+', li.text) and (re.findall('[\d]+', li.text)[0] in il)]
    for li in li_il:
        result[li.find_elements_by_tag_name('a')[1].text] = seg_date(li.text)
    return result


def is_redundancy(nm):
    alike = ['分工', '负责', '协助', '职务', '工作', '职责', '互为AB岗'] + specialization_list[2:]
    if len(nm) > 4:
        if (nm[:2] in alike) or (nm[2:4] in alike):
            return True
    if len(nm.split('：')[0].split('、')[0].split('，')[0].replace('同志', '')) <= 3:
        return False
    for word in alike:
        if word in (catch_xingming(nm) if len(nm) < 10 else nm):
            return True
    return False


def fangwen(url, driver):
    output = pandas.DataFrame(columns=[])
    output_ref = pandas.DataFrame(columns=[])
    output_row = 0
    ref_row = 0
    time.sleep(0.3)  #edit driver不可用时自动刷新
    html = etree.HTML(driver.page_source)
    百科标题 = driver.find_element_by_tag_name('h1').text.strip() if driver.find_elements_by_tag_name('h1') else ''
    table_select = False
    tables = driver.find_elements_by_tag_name('table')  # tables = html.xpath('//table')
    table_collect = False

    def matchjob(x):
        dang = re.search('|'.join(specialization_list), x)
        if dang:
            dang = dang.group()
            x = x[:x.index(dang)]
        x = re.match('([^助师长书记员王李姚黄吴潘]+[^。：；]*)?(调查员|调研员|巡视员|总工程师|总监|总工|支书|主席|级）|[站部队处组会司局厅科]长|助理|经理|干部|主任|指挥|[师记员])', x)  #更新2.7 #edit 调查员>局长 #notdone 2.2 工 长 # edit 2.1 ^协助
        return x.group() if x else ''

    def shortjob(job):
        x = re.match(
            '([^助师长书记员负责持王李姚黄吴潘]{1,6}[市交通运输公路铁道管理处委员会事工程设计]*)?[书长正]?(调查员|调研员|巡视员|总工程师|总监|总工|支书|主席|级）|[站部队处组会司局厅科]长|助理|经理|指挥|干部|主任|[师记员])',
            job)
        return x.group() if x else ''

    # 遍历所有的table
    for table in tables:
        if panduan_table(table) == True:
            unit_name = ''
            for tr in table.find_elements_by_xpath('./tbody/tr'):
                if len(set(re.findall('[\w]', tr.text)) - set('参考文献资料1234567890')) < 3:
                    refs = ''.join([x.text.strip() for x in tr.find_elements_by_tag_name('sup')])
                    refs = spillt(refs, '[]-,')
                    while '' in refs:  # refs == ['']
                        refs.remove('')
                    ref = get_reference(driver, refs)
                    for title in ref:
                        output_ref.loc[ref_row, '姓名'] = ''
                        output_ref.loc[ref_row, '职位'] = ''
                        output_ref.loc[ref_row, '引用标题'] = title
                        output_ref.loc[ref_row, '日期'] = ref[title]
                        ref_row += 1
                    break
                if '表头' not in vars().keys():
                    表头 = {}
                    for itag in range(len(tr.find_elements_by_xpath('./*'))):  # edit: xpath
                        表头[tr.find_elements_by_xpath('./*')[itag].text] = itag
                    print(*表头.keys())
                    # modify = input()
                    # while modify:
                    #     exec(modify)
                    #     modify = input('ok?')
                    if '名单' in 表头:
                        表头['姓名'] = 表头['名单']
                    elif '名称' in 表头:
                        表头['姓名'] = 表头['名称']
                    if '姓名' in 表头 and not is_job(tr.text):  # edit 1.31 # or (len(tr.text) < 5)
                        continue
                    elif ('姓名' in 表头) and ('职务' in 表头):
                        表头['职务'] = 表头[[x for x in 表头.keys() if is_job(x)][0]]
                        表头['姓名'] = 表头[[x for x in 表头.keys() if len(x)>=2 and x not in ['职务', '姓名', '工作分工', '分工', '职位'] and not is_job(x)][0]]
                try:
                    job = ''; i = 0
                    if '职务' in 表头:
                        i = 表头['职务']; 表头['职位'] = 表头['职务']
                    elif '职位' in 表头:
                        i = 表头['职位']
                    elif '姓名职位' in 表头:
                        i = 表头['姓名职位']
                        infs = spillt(tr.find_elements_by_xpath('./*')[i].text.replace(' ', '').replace('\u3000', '').replace('\u2002', ''),
                               re.findall('[\W]', tr.find_elements_by_xpath('./*')[i].text))
                    else:
                        for i in range(len(tr.find_elements_by_xpath('./*'))):
                            if is_job(tr.find_elements_by_xpath('./*')[i].text): #edit 暂不需要unit name
                                if re.search('[\W\s]', tr.find_elements_by_xpath('./*')[i].text) and not shortjob(tr.find_elements_by_xpath('./*')[i].text.replace(百科标题, '')):
                                    表头['姓名职位'] = i
                                    infs = spillt(tr.find_elements_by_xpath('./*')[i].text.replace(' ', '').replace('\u3000', '').replace('\u2002', ''),
                                                  re.findall('[\W]', tr.find_elements_by_xpath('./*')[i].text))
                                else:
                                    表头['职务'] = i
                                    if len(tr.find_elements_by_xpath('./*')) == 2:
                                        表头['姓名'] = [x for x in range(2) if x!=i][0]
                                break
                            if len(max(tr.find_elements_by_xpath('./*')[i].text.split('、'), key=len)) in [2,3]:
                                表头['姓名'] = i

                    red = False
                    yl = []
                    if len(set(表头.keys()) & {'姓名', '职位', '姓名职位', '分工', '参考文献'}) < 2:
                        for i2 in list(set(range(itag + 1)) - {i}):
                            try:
                                if is_redundancy(tr.find_elements_by_xpath('./*')[i2].text) or is_redundancy(tr.find_element_by_xpath("//following-sibling::tr").find_elements_by_xpath('./*')[i2].text):
                                    表头['分工'] = i2
                                elif tr.find_elements_by_xpath('./*')[i2].find_elements_by_tag_name('sup'):
                                    表头['参考文献'] = i2
                            except:
                                pass
                    if '姓名职位' in 表头:
                        job = '、'.join([x for x in infs if is_job(x)])
                        yl = [x for x in infs if not x.isdigit() and not is_job(x)]; dic = {}; references = {}
                        for name in yl:
                            dic[name] = ''
                        for i in range(itag + 1) if '参考文献' not in 表头 else [表头['参考文献']]:
                            if tr.find_elements_by_xpath('./*')[i].find_elements_by_tag_name('sup'):
                                refs = ''.join(
                                    [x.text.strip() for x in tr.find_elements_by_xpath('./*')[i].find_elements_by_tag_name('sup')])
                                refs = spillt(refs, '[]-,')
                                for name in yl:
                                    references[name] = get_reference(driver, refs)
                        refs = references
                        if '分工' in 表头:
                            red = tr.find_elements_by_xpath('./*')[表头['分工']].text.strip()
                            red = red[:red.index('[')] if '[' in red else red
                    elif len(tr.find_elements_by_xpath('./*')) <= max([i] + list(表头.values())):
                        t = spillt(tr.text, ['\n', ' ', '\t', '、'])
                        if is_job(tr.text):
                            job = list(filter(is_job, t))[0]
                        else:
                            job = ''
                        if is_redundancy(tr.text):
                            red = max(t, key=len)
                        else:
                            red = ''
                        if job and (job not in red):
                            output.loc[output_row - 1, '职位'] = job
                        if red:
                            red = red.split('：')[-1]
                            output.loc[output_row - 1, '分工'] = red
                        if job == '':
                            output.loc[output_row, '姓名'] = t[0]
                            if output_row > 0:
                                output.loc[output_row, '职位'] = output.loc[output_row - 1, '职位']
                            output_row += 1
                        continue
                    else:
                        job = unit_name + tr.find_elements_by_xpath('./*')[i].text.strip().replace(' ', '').replace('\u3000', '').replace('\u2002', '').replace('\u0020', '').replace('\u200A', '').replace('\u0200B', '')  # edit: 更新
                        if '[' in job:
                            job = job[:job.index('[')]
                        if len(job) > 1 and (re.match('[\W]', job[-1])):
                            job = job[:-1]
                        if '分工' in 表头:
                            red = tr.find_elements_by_xpath('./*')[表头['分工']].text.strip()
                        if '姓名' in 表头:
                            dic, yl, refs = handle_with_person_td(tr.find_elements_by_xpath('./*')[表头['姓名']], driver)
                        else:
                            if itag == 1:
                                name = spillt(job, re.findall('[\s\W]', job))
                                for nm in name:
                                    if not yl and not is_job(nm) and not is_redundancy(nm):
                                        yl = [name]
                                        dic = {name: ''}
                                    elif is_job(nm):
                                        job = nm
                                    else:
                                        red = nm
                            else:
                                dic, yl, refs = handle_with_person_td(tr.find_elements_by_xpath('./*')[min(list(set(range(itag)) - {i}))], driver)
                    table_collect = True
                    for name in yl:  #edit yl
                        name1 = name
                        if len(name) == 6 and ('·' not in name):
                            name = [name[:3], name[3:]]
                        for name in name if type(name) == list else [name]:
                            output.loc[output_row, '姓名'] = name
                            output.loc[output_row, '职位'] = job
                            output.loc[output_row, '链接'] = dic[name1]
                            if red:
                                output.loc[output_row, '分工'] = red
                            output_row += 1
                            if name1 in refs:
                                ref = refs[name1]
                                for title in ref:
                                    output_ref.loc[ref_row, '姓名'] = name
                                    output_ref.loc[ref_row, '职位'] = job
                                    output_ref.loc[ref_row, '引用标题'] = title
                                    output_ref.loc[ref_row, '日期'] = ref[title]
                                    ref_row += 1
                    if 'a' in refs:
                        ref = refs['a']
                        for title in ref:
                            output_ref.loc[ref_row, '姓名'] = ''
                            output_ref.loc[ref_row, '职位'] = ''
                            output_ref.loc[ref_row, '引用标题'] = title
                            output_ref.loc[ref_row, '日期'] = ref[title]
                            ref_row += 1
                except Exception as e:
                    print(e)
                    print(driver.current_url, traceback.format_exc())
                    with open(f'logtr.txt', 'a', encoding='utf-8') as f:
                        f.write(url + ' ' + tr.text.replace('\n', '\t') + datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M ') + traceback.format_exc() + '\n\n')

    if table_collect == False:
        big_title_collect = False
        name_ready = ['女', '姓名']
        big_title_list = html.xpath('//h2')
        for big_title in big_title_list:
            big_title_words = big_title.xpath('.//text()')
            if '领导' in ''.join(big_title_words) or '政治' in ''.join(big_title_words):
                big_title_collect = True
                for div in big_title.xpath('../following-sibling::div'):
                    if len(div.xpath('./h2')) != 0:
                        break
                    for a in div.xpath('./a'):

                        name = ''.join(a.xpath('.//text()'))
                        try:
                            person_url = 'https://baike.baidu.com' + a.xpath('.//@href')[0]
                        except:
                            person_url = ''
                        if is_Chinese(name):
                            output.loc[output_row, '姓名'] = name
                            output.loc[output_row, '职位'] = ''
                            output.loc[output_row, '链接'] = person_url
                            output.loc[output_row, '部门'] = ''
                            output_row += 1
                            name_ready.append(name)

                div_list = []
                wangye_type = '标准'
                for div in big_title.xpath('../following-sibling::div'):
                    text_single = ''.join(div.xpath('.//text()'))
                    if len(div.xpath('./@class')) > 0 and div.xpath('./@class')[0] != 'para':
                        break
                    if len(div.xpath('./h2')) != 0:
                        break
                    div_list.append(div)
                    count_maohao = 0
                    for word in text_single:
                        if word == '：':
                            count_maohao += 1

                    if count_maohao == 1:
                        text_single = ''.join(div.xpath('.//text()'))
                        job = text_single.split('：')[0]
                        name_all = text_single.split('：')[1]
                        for single_job in job_list:
                            if single_job in name_all:
                                job = text_single.split('：')[1]
                                name_all = text_single.split('：')[0]
                                break
                        pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！|…|（|）'
                        names = re.split(pattern, name_all)
                        names = hebing(names)
                        for name in names:
                            name = clean_name(name)
                            if is_Chinese(name) and name not in name_ready:
                                output.loc[output_row, '姓名'] = name
                                output.loc[output_row, '职位'] = job
                                output.loc[output_row, '链接'] = ''
                                output.loc[output_row, '部门'] = ''
                                output_row += 1
                    if count_maohao != 1:
                        job = ''
                        pattern = r' |：|,|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
                        for word in re.split(pattern, text_single):
                            if is_job(word):
                                job = word
                            else:
                                name = clean_name(word)
                                if is_Chinese(name) and name not in name_ready:
                                    output.loc[output_row, '姓名'] = name
                                    output.loc[output_row, '职位'] = job
                                    output.loc[output_row, '链接'] = ''
                                    output.loc[output_row, '部门'] = ''
                                    output_row += 1

                break
        if big_title_collect == False:
            small_title_list = html.xpath('/html/body//div[@class="para"]')
            for small_title in small_title_list:
                small_title_words = small_title.xpath('./b/text()')
                if '领导' in ''.join(small_title_words):
                    for div in small_title.xpath('./following-sibling::div'):
                        if len(div.xpath('./h2')) != 0:
                            break
                        for a in div.xpath('./a'):

                            name = ''.join(a.xpath('.//text()'))
                            try:
                                person_url = 'https://baike.baidu.com' + a.xpath('.//@href')[0]
                            except:
                                person_url = ''
                            if is_Chinese(name):
                                output.loc[output_row, '姓名'] = name
                                output.loc[output_row, '职位'] = ''
                                output.loc[output_row, '链接'] = person_url
                                output.loc[output_row, '部门'] = ''
                                output_row += 1
                                name_ready.append(name)

                    div_list = []
                    wangye_type = '标准'
                    for div in small_title.xpath('./following-sibling::div'):
                        text_single = ''.join(div.xpath('.//text()'))
                        if len(div.xpath('./h2')) != 0:
                            break
                        div_list.append(div)
                        count_maohao = 0
                        for word in text_single:
                            if word == '：':
                                count_maohao += 1

                        if count_maohao == 1:
                            text_single = ''.join(div.xpath('.//text()'))
                            job = text_single.split('：')[0]
                            name_all = text_single.split('：')[1]
                            for single_job in job_list:
                                if single_job in name_all:
                                    job = text_single.split('：')[1]
                                    name_all = text_single.split('：')[0]
                                    break
                            pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
                            for name in re.split(pattern, name_all):
                                name = clean_name(name)
                                if is_Chinese(name) and name not in name_ready:
                                    output.loc[output_row, '姓名'] = name
                                    output.loc[output_row, '职位'] = job
                                    output.loc[output_row, '链接'] = ''
                                    output.loc[output_row, '部门'] = ''
                                    output_row += 1
                        if count_maohao != 1:
                            job = ''
                            pattern = r'：|,|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
                            for word in re.split(pattern, text_single):
                                if is_job(word):
                                    job = word
                                else:
                                    name = clean_name(word)
                                    if is_Chinese(name) and name not in name_ready:
                                        output.loc[output_row, '姓名'] = name
                                        output.loc[output_row, '职位'] = job
                                        output.loc[output_row, '链接'] = ''
                                        output.loc[output_row, '部门'] = ''
                                        output_row += 1

                    break
        if len(output) == 0:
            err = 0
            xpaths = ["//h2[text()=\"现任领导\"]/parent::div", "//h3[text()=\"现任领导\"]/parent::div", "//div[text()=\"现任领导\"]/parent::div", "//span[text()=\"现任领导\"]/parent::div", "//h2[starts-with(text(),\"领导\")]/parent::div", "//h2[starts-with(text(),\"现任\")]/parent::div", "//h3[contains(text(),\"领导\")]/parent::div"]
            for pth in xpaths:
                try:
                    titlediv = driver.find_element_by_xpath(pth)
                    break
                except:
                    pth = ''
            dic, yl, refs = handle_with_person_span(pth, driver)  #增加引用

            # 换行多的简化处理
            yl1 = copy.copy(yl)
            if len(yl) > 3 and len(set([(' ' in x) or (re.search('[：\s]', x[:5]) is not None) for x in yl])) > 1 and (sum([' ' in x for x in yl]) in range(2, round(len(yl)/2) - 1)):
                isimportant = [(' ' in x) or (re.search('[：\s]', x[:5]) is not None) for x in yl]
                j = 0
                for s in yl1:
                    i = yl.index(s)
                    if not isimportant[j] and j > 0:
                        nk = '\n'.join([yl[i-1], s[:-1] if s and (s[-1] in ['；', '。']) else s])
                        dic[nk] = dic.pop(yl[i-1])
                        yl[i-1] = nk
                        yl.remove(s)
                    j += 1

            不分段 = False
            def insert_ref(refs, name, job, output_ref, ref_row):
                ref = refs[name1]  #global
                for title in ref:
                    output_ref.loc[ref_row, '姓名'] = name if name != 'a' else ''
                    output_ref.loc[ref_row, '职位'] = job
                    output_ref.loc[ref_row, '引用标题'] = title
                    output_ref.loc[ref_row, '日期'] = ref[title]
                    ref_row += 1
                return output_ref, ref_row
            未赋值 = lambda x: pandas.isna(x) or x==''
            for name1 in yl:  # edit: 原序
                try:
                    if '：' in name1:
                        key_ = name1.split('：')[0].replace(' ', '').replace('职务', '职位')
                        if key_ in ['姓名', '职位']:# update 姓名：xxxx\n 职务：xxx
                            try:
                                last = ''
                                if key_ in output.columns and output_row > 0:
                                    last = output.loc[output_row, key_]
                                if not 未赋值(last):
                                    output_row += 1
                            except:
                                last = ''
                                if key_ in output.columns and output_row > 0:
                                    last = output.loc[output_row - 1, key_]  # output_row == 0 未赋值->False
                                    if 未赋值(last):
                                        output_row -= 1
                            val = name1.split('：')[1]
                            if key_ == '职位' and '\n' in val:
                                red = val[val.index('\n')+1:]
                                output.loc[output_row, '分工'] = red
                                val = val.split('\n')[0]
                            output.loc[output_row, key_] = val
                            if name1 in refs:
                                output_ref, ref_row = insert_ref(refs, output.loc[output_row, '姓名'], output.loc[output_row, '职位'] if '职位' in output.columns else '', output_ref, ref_row)
                            elif output_row == 0 and ref_row>0 and key_ == '职位':
                                output_ref.loc[output_ref['姓名']==output.loc[0, '姓名'], '职位'] = val
                            if len(set(output.columns) & {'姓名', '职位'}) == 2 and not (未赋值(output.loc[output_row, '姓名']) or 未赋值(output.loc[output_row, '职位'])):
                                output.loc[output_row, '链接'] = ''
                                output_row += 1
                            continue
                        elif is_redundancy(name1.replace(key_, '')) and is_job(key_) and (len(key_) < 3 + round(len(name1) / 2)):  #edit! 职务姓名：分 工
                            job = matchjob(key_)
                            name = key_.replace(job, '')
                            if name:
                                output.loc[output_row, '姓名'] = name
                            output.loc[output_row, '职位'] = job
                            output.loc[output_row, '链接'] = dic[name1]
                            output_row += 1
                    if is_redundancy(name1):
                        if (name1[:2] in specialization_list + ['主要']) or (not 不分段) and (output_row > 0) and is_redundancy(spillt(name1, re.findall('[\W]', name1))[0]):
                            output.loc[output_row - 1, '分工'] = name1.split('：')[-1]
                            if name1 in refs:
                                output_ref, ref_row = insert_ref(refs, output.loc[output_row - 1, '姓名'], output.loc[output_row - 1, '职位'], output_ref, ref_row)
                            continue
                        elif len(catch_xingming(name1)) <= 3 or shortjob(name1):  # 即是不分段大长句
                            不分段 = True  # 1.31是前面有有用信息(姓名/职位)的情况
                        elif 不分段:
                            pass #edit 2.1 移到后面
                            # output.loc[output_row, '分工'] = name1
                            # output_row += 1
                            # if name1 in refs:
                            #     output_ref, ref_row = insert_ref(refs, name1, '', output_ref, ref_row)
                        else:
                            continue
                    name = name1
                    if len(re.findall('：', name1)) == 1:
                        if '：' in name1[-4:]:
                            name = name1.split('：')[-1].strip()
                    elif '）' in name1[-1:] or '（' in name1[:4]:
                        name = name1[:name1.index('（')] if ('级）' not in name1) and ('兼）' not in name1) else name1
                        name = name1 if name == '' else name
                    if ' ' in name[:3]:
                        name = name.split()[0]
                    red = False  # 多余语句可能为分工描述
                    if '同志' in name:
                        pob_name = re.search('[\w]+[同][志]', name)
                        if pob_name:
                            pob_name = pob_name.group().replace('同志', '')
                            job = matchjob(pob_name)
                            if job:
                                pob_name = pob_name.replace(job, '')
                            if len(pob_name) <=3:
                                name = pob_name
                    preps = ['是', '为']
                    for prep in preps:
                        if prep in name[:-2]:
                            name = name.split(prep)[1]
                    if ('，' in (spillt(name, specialization_list)[0].strip()[:-1]) if name else '') and len(re.findall('，', name)) == 1 and ('：' not in name): #update 2.1 name->spillt(name, ['分工', '工作', '主管', '分管'])[0]
                        name = name[:name.index('，')] if not is_redundancy(name[:name.index('，')]) else name[name.index('，')+1:]# edit 1.31 判断前后那一部分是姓名信息(不是分工信息)
                    if re.search('.+：[\w]{2,3}', spillt(name, specialization_list)[0].strip()[-5:]) and len(set(spillt(name, specialization_list)[0].strip()[-3:]) & set('总委员会局组副主任编辑院长书处工记')) < 2:
                        name = spillt(name, specialization_list)[0].strip().split('：')[-1]
                    elif (('：' in name.replace(百科标题, '')[:10]) or ('：' in spillt(name, specialization_list)[0].strip()[-4:])) and len(re.findall('：', name)) == 1:  #edit 2.2 统一分工变量
                        name = spillt(name, ['：', '\n'])
                        if len(name) >= 3:
                            red = name1[name1.index(name[2]):]
                        try:
                            name = list(filter(lambda x: len(x) in [2,3] and len(set(x) & set('总委员会局组副主任编辑院长书处工记')) < 2, name))[0]
                        except:
                            try:
                                name = list(filter(lambda x: not is_job(x) or (len(matchjob(x)) < len(x) - 1), name))[0]  #edit 2.1副局长XXX：#  not is_job(x)
                            except:
                                name = name1
                                mess = spillt(name, re.findall('[\W]', name))
                                if len(min(mess, key=len)) in [2,3]:
                                    name = list(filter(lambda x: len(x) in [2,3], name))[0]#notdone
                    elif '；' in name[:10]:
                        name = name.split('；')
                        if min([len(x) for x in name]) in [2, 3]:
                            name = list(filter(lambda x: len(x) in [2,3] and len(set(x) & set('总委员会局组副主任编辑院长书处工记')) < 2, name))[0]  #edit: 更新
                        else:
                            name = '；'.join(name)

                    if len(name) > 3:
                        name = re.search('([\w、]+[（）挂兼职副院长]{3,4})*[\w、]+', name1).group()
                        if len(name) > 3:
                            name = catch_xingming(name, 百科标题[:2], '交', '同志')  #edit 更新: 同志
                    if (name == name1) and not is_job(name):
                        job = ''  # edit 职务未分割成功设定为空值
                    elif is_job(name) and (len(name) - len(matchjob(name)) in range(2, 4)):  # edit 仅职务+姓名 无分割符号, 职务在姓名前面
                        job = matchjob(name)
                        if job:
                            name = name.replace(job, '')
                    elif matchjob(name) == name and not re.search('[^\w、（）]', name1):
                        if output_row > 0:
                            if 未赋值(output.loc[output_row - 1, '职位']):
                                output.loc[output_row - 1, '职位'] = name
                                continue
                        job = ''
                    else:
                        if re.search('[\w|、]+', name1.replace(name, '')):
                            job = re.search('([\w|、|（|）|(|)|]+[，][^' + '|'.join(specialization_list) + '])?[\w|、|（|）|(|)|]+', name1.replace(name, '').replace('同志', '')).group()
                            if job[0] == '（' and min([len(x) for x in spillt(job, '（）')]) > min([len(job)/2] + [len(x) for x in spillt(job, re.findall('\W' ,job))]) :
                                job = spillt(job, '（）')[0]
                            if is_redundancy(job) and (len(shortjob(job)) < len(job[job.index(shortjob(job))+len(shortjob(job)):]) - 2 or len(job) < len(name1[name1.index(job)+len(job):] if job in name1 else '') - 2 or (matchjob(job) == '' and len(re.findall('[\W]', job)) > 1)):  # alright
                                got = [x for x in spillt(name1, re.findall('[\W]', name1)) if name in x and len(x.replace(name, ''))<4]
                                while '' in got:
                                    got.remove('')
                                got = got[0] if got else ''
                                if got:
                                    red = name1.replace(re.search(got+'[），：；。]*', name1).group(), '')
                                else:
                                    red = name1
                                if matchjob(job):
                                    job = matchjob(job) if min(
                                        [len(x) for x in spillt(matchjob(job), re.findall('\W', job))]) <= len(
                                        shortjob(job)) + 8 else shortjob(job)  # edit 2.2
                                    if re.match('[\W]', job[0]):
                                        job = job[1:] if len(job) > 1 else ''   # added
                                    if ('（' in job) and ('）' not in job):
                                        job = job[:job.index('（')]
                                    if ('）' in job[-1:]) and ('（' not in job):
                                        job = job[:job.index('）')] #.
                                elif is_redundancy(job):
                                    job = ''
                            else:
                                if re.match('[\W]', job[0]):
                                    job = job[1:] if len(job) > 1 else ''
                                if ('（' in job) and ('）' not in job):# edit
                                    job = job[:job.index('（')]
                                if ('）' in job[-1:]) and ('（' not in job):
                                    job = job[:job.index('）')] #edit
                                if is_job(name) and len(job) < max(7, len(name) + 2):  #如果'job'是未分开的人名AAABBB后面也可以处理
                                    z = name
                                    name = job
                                    job = z
                                if is_redundancy(job) and len(max(spillt(job.replace(百科标题, '').replace('交通运输局', ''), '、，'), key=len)) > 7:
                                    brev_job = matchjob(job)  #edit 可能是具体职位+分  工, 需提取前面的职务 # edit 合并为一个方法 <-re.match('[^师长书记员]{1,6}[书]?[师长记员]', job)
                                    if brev_job and not is_job(job.replace(brev_job, '')[-10:]):
                                        red = job.replace(brev_job, '')
                                        if red and re.match('[\W]', red[0]):
                                            red = red[1:] if len(red) > 1 else ''
                                        job = brev_job
                        else:
                            job = ''
                    if '同志' in name:
                        name = name.replace('同志', '')
                    if (not red) and len(set(re.findall('[\w]', name1)) - set(job+name)) > 5:
                        mess = [x for x in spillt(name1, re.findall('[\W]', name1)) if len(set(x) - set(name + job + '同志')) > 0]
                        if mess and matchjob(mess[0]) and max([len(x) for x in spillt(name1, re.findall('[\W]', name1))] + [0]) <= 12 and not is_redundancy(name1):
                            job = name1.replace(name, '').replace('同志', '')
                            if re.match('[\W]', job):
                                job = job[1:]
                        else:
                            red = ''.join([re.search(f'[（]*{x}[\W]*', name1.replace('：\n', '：')).group() for x in mess])  #edit 1.31
                            red = red[:-1] if red[-1] in ['；', '，', '。'] else red
                    if red:
                        if re.match('[\W]', red[-1:]) and red[-1:] not in ['）', '。']:
                            red = red[:-1]
                        red = red.replace('，，', '，').replace('（（', '（').replace('。。', '。')
                    if (len(name) == 0) or (len(name) > 3) and ('·' not in name):
                        s = bk_t(name1)
                        if s:
                            name = s
                            left = name1
                            for nm in name:
                                left = left.replace(nm, '')
                            job = matchjob(left)
                    if (name == '' or len(name) > 3) and 不分段:
                        output.loc[output_row, '分工'] = name1
                        output_row += 1
                        if name1 in refs:
                            output_ref, ref_row = insert_ref(refs, name1, '', output_ref, ref_row)
                    elif len(name) == 6:
                        name = [name[:3], name[3:]]
                    elif len(name) == 5:
                        print(name, end=',')
                        name = [name[:3], name[3:]]
                    for name in name if type(name) == list else [name]:
                        output.loc[output_row, '姓名'] = name
                        output.loc[output_row, '职位'] = job
                        output.loc[output_row, '链接'] = dic[name1]
                        if red:
                            output.loc[output_row, '分工'] = red
                        output_row += 1
                        if name1 in refs:
                            output_ref, ref_row = insert_ref(refs, name, job, output_ref, ref_row)
                except Exception as e:
                    print(name1, e)
                    print(driver.current_url, traceback.format_exc())
                    with open(f'logsp.txt', 'a', encoding='utf-8') as f:
                        f.write(url + ' ' + name1 + '\t' + datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M ') + traceback.format_exc() + '\n\n')
                    err += 1
            if 'a' in refs:
                name1 = 'a'
                output_ref, ref_row = insert_ref(refs, 'a', '', output_ref, ref_row)

            if len(dic) == 0:
                pass# print(url, '无信息')  #switch 无信息太多节省输出
            else:
                print(百科标题, end='\t')
            if err:
                print(url, f'不符合格式({err}/{len(dic)})')

    try:
        单位 = 百科标题
        单位 = 单位 if '错误页' not in 单位 else False
        if 单位 and (output_row == 0):
            print(url, '无(领导)信息')
        output['单位'] = 单位
        output_ref['单位'] = 单位
        output_ref = output_ref[['单位'] + output_ref.columns[:-1].tolist()]
    except:
        pass
    return output, output_ref


if __name__ == '__main__':
    driver_path = r'C:\Users\laungee\Downloads\chromedriver_win32 (1)\chromedriver.exe'
    prefs = {'profile.managed_default_content_settings.images': 2}
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option('prefs', prefs)
    driver = webdriver.Chrome(driver_path, options=chrome_options)
    driver.set_page_load_timeout(10)
    table = fangwen('https://baike.baidu.com/item/%E6%B1%A0%E5%B7%9E%E5%B8%82/211733?fr=aladdin#6', driver=driver)
    # table.to_excel('池州市吕梁市.xlsx')
    print(table)
