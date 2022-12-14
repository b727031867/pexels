import logging
import multiprocessing as multiprocessing
import os
import time

import numpy as numpy
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

configPath = './config.txt'
keyword = ''
if os.path.exists(configPath):
    # 读取配置
    with open('config.txt', 'r', encoding='utf-8') as filedd:
        rr_list = filedd.readlines()
    con = {}
    for line in rr_list:
        line = line.replace('\n', '')
        ll = line.split('=')
        con[ll[0]] = ll[1]
    SLEEP_SECONDS = int(con['SLEEP_SECONDS'])
    EACH_LOAD_PIC_NUM = int(con['EACH_LOAD_PIC_NUM'])
    keyword = con['keyword']
    BROWSER_EXECUTABLE_PATH = con['BROWSER_EXECUTABLE_PATH']
else:
    print("当前文件夹下配置文件不存在")
if len(keyword) == 0:
    print("当前未输入搜索关键字，程序退出！")
    exit(0)
PEXELS_URL = 'https://www.pexels.com/zh-cn/search/' + keyword
SCROLL_HEIGHT = 200000000000  # 滚屏像素点


def get_image_ids(url):
    browser = uc.Chrome(browser_executable_path=BROWSER_EXECUTABLE_PATH, driver_executable_path='chromedriver.exe')
    time.sleep(SLEEP_SECONDS)
    browser.get(url)
    browser.maximize_window()
    total_img_num_element = browser.find_element(By.XPATH, '//*[@id="__next"]/main/div[2]/div[1]/div/a[1]/span')
    elements = browser.find_elements(By.XPATH, '//article/a')
    scroll_height = SCROLL_HEIGHT
    # 针对不同的搜索情况 需要对页面获取的搜索图片总数文本进行单位转换
    total_img_num = handle_total_num(total_img_num_element.text)
    if len(elements) < total_img_num:
        scroll_num = ((total_img_num - len(elements)) // EACH_LOAD_PIC_NUM) + 3
        logging.info('共计尝试下拉' + str(scroll_num) + '次，加载图片，每次下拉间隔时间：' + str(SLEEP_SECONDS) + '秒\n')
        for i in range(scroll_num):
            logging.info('进行第' + str(i) + '次下拉中...\n')
            browser.execute_script('window.scrollBy(0, {})'.format(scroll_height))  # 利用 selenium 执行 js 滚动到页面底部
            time.sleep(SLEEP_SECONDS)
            logging.info('进行第' + str(i) + '次下拉完成!\n')
        elements = browser.find_elements(By.XPATH, '//article/a')
    image_ids = [ele.get_attribute('href').rsplit('/', 2).__getitem__(1) for ele in elements]
    logging.info('将要保存的下载ID列表: \n' + ' '.join(image_ids))
    numpy.save('image_ids', image_ids)
    logging.info("保存图片id数量" + str(len(image_ids)))
    logging.info("尝试关闭浏览器...")
    browser.close()
    logging.info("关闭浏览器成功")


def handle_total_num(total_pic_number):
    try:
        return int(total_pic_number)
    except ValueError:
        logging.info('转换单位中')
        if total_pic_number.rsplit(' ', 1).__getitem__(1) == '千':
            total_pic_number = float(total_pic_number.rsplit(' ', 1).__getitem__(0)) * 1000
    logging.info('转换单位后总下载数量是:' + str(int(total_pic_number)) + '\n')
    return int(total_pic_number)


def main():
    get_image_ids(PEXELS_URL)
    return


if __name__ == "__main__":
    # 支持Win10 下 具有子线程打包
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S"
                        , filename='searchIds.log', filemode='w')
    # 创建一个handler，用于输出到控制台，并且调整格式
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(ch)
    logging.info('start search pic Ids...')
    main()
