import logging
import time
import os

import multiprocessing as multiprocessing
import numpy as numpy
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

configPath = './config.txt'
keyword = ''
if os.path.exists(configPath):
    # 读取配置
    with open('config.txt', 'r', encoding='utf-8')as filedd:
        rr_list = filedd.readlines()
    con = {}
    for line in rr_list:
        line = line.replace('\n', '')
        ll = line.split('=')
        con[ll[0]] = ll[1]
    SLEEP_SECONDS = int(con['SLEEP_SECONDS'])
    keyword = con['keyword']
    BROWSER_EXECUTABLE_PATH = con['BROWSER_EXECUTABLE_PATH']
else:
    print("当前文件夹下配置文件不存在")
if len(keyword) == 0:
    print("当前未输入搜索关键字，程序退出！")
    exit(0)
PEXELS_URL = 'https://www.pexels.com/zh-cn/search/' + keyword
SCROLL_HEIGHT = 20000  # 滚屏像素点


def get_image_ids(browser, url):
    time.sleep(SLEEP_SECONDS)
    browser.get(url)
    browser.maximize_window()
    total_img_num_element = browser.find_element(By.XPATH, '//*[@id="__next"]/main/div[2]/div[1]/div/a[1]/span')
    elements = browser.find_elements(By.XPATH, '//article/a')
    scroll_height = SCROLL_HEIGHT
    total_img_num = int(total_img_num_element.text)
    if len(elements) < total_img_num:
        scroll_num = ((total_img_num - len(elements)) // 16) + 2
        print('共计尝试下拉' + str(scroll_num) + '次，加载图片，每次下拉间隔时间：' + str(SLEEP_SECONDS))
        for i in range(3):
            browser.execute_script('window.scrollBy(0, {})'.format(scroll_height))  # 利用 selenium 执行 js 滚动到页面底部
            time.sleep(SLEEP_SECONDS)
        elements = browser.find_elements(By.XPATH, '//article/a')
    image_ids = [ele.get_attribute('href').rsplit('/', 2).__getitem__(1) for ele in elements]
    return image_ids


def main():
    browser = uc.Chrome(browser_executable_path=BROWSER_EXECUTABLE_PATH, driver_executable_path='chromedriver.exe')
    image_ids = get_image_ids(browser, PEXELS_URL)
    logging.info('To save all image ids: \n'.join(image_ids))
    numpy.save('image_ids', image_ids)
    logging.info("保存图片id数量" + str(len(image_ids)))
    browser.close()
    return


if __name__ == "__main__":
    # 支持Win10 下 具有子线程打包
    multiprocessing.freeze_support()
    logging.basicConfig(filename='searchIds.log')
    main()
