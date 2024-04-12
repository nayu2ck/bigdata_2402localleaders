from 采集某网页的百科页面的领导名单 import fangwen
from selenium import webdriver
import pandas
import os

#########################################
output_path =r'D:\Pycharm Projects\test_data_write\采地级市-v3_2.xlsx'
###########################################


driver_path = os.path.abspath(os.path.join(os.path.abspath(__file__), '..', '..', '谷歌驱动器2', 'chromedriver.exe'))
prefs = {'profile.managed_default_content_settings.images': 2}
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option('prefs', prefs)
driver = webdriver.Chrome(driver_path, options=chrome_options)
driver.set_page_load_timeout(10)

input_path = os.path.abspath(os.path.join(os.path.abspath(__file__), '..', '配置文件', '地区名单 - 副本.xlsx'))
input = pandas.read_excel(input_path)
table_list = []
output = pandas.DataFrame(columns=[])

for row in range(len(input)):
    link = input.loc[row, 'link']
    table = fangwen(link, driver=driver)
    table['city'] = input.loc[row, 'city']
    table['provience'] = input.loc[row, 'provience']
    print(len(table))
    if len(table) > 0:
        for row in range(len(table)):
            output_row = len(output)
            for column in table.columns:
                output.loc[output_row, column] = table.loc[row, column]
    else:
        print(link)
output.to_excel(output_path, index=None)