from selenium import webdriver
import pandas
import os
import time
from lxml import etree
import re

driver_path = os.path.abspath(os.path.join(os.path.abspath(__file__), '..', '..' ,'谷歌驱动器','chromedriver.exe'))
prefs = {'profile.managed_default_content_settings.images': 2}
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option('prefs',prefs)
driver = webdriver.Chrome(driver_path,options=chrome_options)
driver.set_page_load_timeout(10)

url = 'https://baike.baidu.com/item/%E6%B8%9D%E4%B8%AD%E5%8C%BA/2531227?fromModule=lemma_inlink'
driver.get(url)
time.sleep(0.3)
html = etree.HTML(driver.page_source)
table_select = False
tables = html.xpath('//table')
print(tables)
table = tables[0]
print(''.join(table.xpath('.//caption//text()')))
# div = table.xpath('./preceding-sibling::div[@class="para-title level-2  J-chapter"]')[-1]
# print(div)