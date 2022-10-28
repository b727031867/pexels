import logging
import multiprocessing
import os
import time
from urllib.parse import urlparse

import numpy as numpy
import requests

DOWNLOAD_URL_KEY = 'https://www.pexels.com/photo/{image_id}/download/'
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 '
                  'Safari/537.36 '
}
CONFIG_PATH = './config.txt'
IMAGE_PATH = './images/'
if not os.path.exists(IMAGE_PATH):
    os.makedirs(IMAGE_PATH)
EXISTED_IMAGES = set(os.listdir(IMAGE_PATH))
EVERY_DOWNLOAD_LENGTH_NUM = None
PAUSE_TIME_MINUTES = 1
PER_WAIT_DOWNLOAD_NUM = 1
HTTP_PROXY = None
HTTPS_PROXY = None


def load_config_and_init(config_path):
    if os.path.exists(config_path):
        # 读取配置
        with open('config.txt', 'r', encoding='utf-8') as config_file:
            rr_list = config_file.readlines()
        con = {}
        for line in rr_list:
            line = line.replace('\n', '')
            ll = line.split('=', 1)
            con[ll[0]] = ll[1]
        global EVERY_DOWNLOAD_LENGTH_NUM, PAUSE_TIME_MINUTES, PER_WAIT_DOWNLOAD_NUM, HTTP_PROXY, HTTPS_PROXY
        EVERY_DOWNLOAD_LENGTH_NUM = int(con['EVERY_DOWNLOAD_LENGTH_NUM'])
        PAUSE_TIME_MINUTES = int(con['PAUSE_TIME_MINUTES'])
        PER_WAIT_DOWNLOAD_NUM = int(con['PER_WAIT_DOWNLOAD_NUM'])
        HTTP_PROXY = str(con['HTTP_PROXY'])
        HTTPS_PROXY = str(con['HTTPS_PROXY'])
    else:
        logging.error("config.txt file not exist!")
        exit(-1)


def get_download_urls(image_ids):
    download_urls = []
    for _id in image_ids:
        if _id is not None:
            download_urls.append(DOWNLOAD_URL_KEY.format(image_id=_id))
        else:
            logging.warning('get_download_urls , _id is None !')
    return download_urls


def download_image(image_url, pause_time_minutes):
    parse_result = urlparse(image_url)
    path = parse_result.path
    image_name = path.split('/')[-1]
    if image_name in EXISTED_IMAGES:
        logging.info(f'pic {image_name} already download,will skip it.')
        return None
    response = None
    try:
        proxies = {
            'http': HTTP_PROXY,
            'https': HTTPS_PROXY
        }
        if HTTP_PROXY == 'None':
            response = requests.get(image_url, headers=headers)
        else:
            response = requests.get(image_url, headers=headers, proxies=proxies)
    except Exception as e:
        logging.error(e)
    if response.status_code != 200:
        message = 'download {} fail. status_code: {}'.format(image_url, response.status_code)
        logging.error(message)
        return None
    if response.status_code == 429:
        time.sleep(int(pause_time_minutes * 60))
        logging.info('download too many request , program will sleep for' + str(pause_time_minutes * 60) + ' seconds')
        return None
    prefix = IMAGE_PATH
    image_file_name = str(image_name).replace('jpeg', 'jpg')
    with open(prefix + str(image_file_name), 'wb') as image:
        image.write(response.content)
    message = 'download {} success. url: {} , file name : {}'.format(image_name, image_url, image_file_name)
    logging.info(message)


def get_image_url(need_redirect_url, pause_time_minutes):
    """
    因为没法解决反爬， 这里采取其他方式绕过反爬
    1. 利用 selenium 获取到页面上 download 按钮的 url
    2. 这个地方 download 按钮的 url 并不能拿到图片的 url， 经过测试发现进行了重定向然后重定向的 url 才是图片 url
    3. 这个 download 按钮的 url 也有反爬， 测试发现 get 请求绕不过
    4. 但是测试发现可以用 head 请求获取到重定向的图片 url
    5. http code 302 返回的 response headers 里面的 location 即为重定向的 url
    """
    response = requests.head(need_redirect_url, headers=headers)
    if response.status_code == 429:
        logging.info('download too many request , program will sleep for ' + str(pause_time_minutes * 60) + ' seconds')
        time.sleep(int(pause_time_minutes * 60))
        return None
    if response.status_code == 404:
        logging.info('download url is not exist , program will skip this url : [' + need_redirect_url + ']')
        return '-1'
    if response.status_code != 302:
        message = '{} don\'t have redirect. code: {}'.format(need_redirect_url, response.status_code)
        logging.error(message)
        return None
    location = response.headers.get('location')
    logging.info(f'get_image_url success. location: {location}' + '\n')
    return location


def download(need_redirect_url, pause_time_minutes):
    try:
        image_url = get_image_url(need_redirect_url, pause_time_minutes)
        if image_url:
            # 如果404 则默认跳过这张图片不下载也不等待
            if image_url == '-1':
                return True
            download_image(image_url, pause_time_minutes)
            return True
    except Exception as e:
        logging.error(e)
    return False


def main():
    load_config_and_init(CONFIG_PATH)
    image_ids = numpy.load('image_ids.npy', allow_pickle=True)
    logging.info("total download id num is:" + str(len(image_ids)))
    if len(image_ids) > 0:
        download_ids = image_ids[:EVERY_DOWNLOAD_LENGTH_NUM]
        save_ids = image_ids[EVERY_DOWNLOAD_LENGTH_NUM:]
        logging.info("Number of pictures remaining :" + str(len(save_ids)))
        download_urls = get_download_urls(download_ids)
        current_times = 0
        for url in download_urls:
            current_times = current_times + 1
            if current_times % PER_WAIT_DOWNLOAD_NUM == 0:
                time.sleep(PAUSE_TIME_MINUTES * 60)
            for i in range(0, 3):
                if not download(url, PAUSE_TIME_MINUTES):
                    logging.warning('download fail , will retry 3 times! current retry num is ' + str(i + 1))
                    time.sleep(PAUSE_TIME_MINUTES * 60)
                    download(url, PAUSE_TIME_MINUTES)
                else:
                    break
        numpy.save('image_ids', save_ids)
        logging.info('download finished ,remaining  num :' + str(len(numpy.load('image_ids.npy', allow_pickle=True))))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S"
                        , filename='downloadIds.log', filemode='w')
    # 创建一个handler，用于输出到控制台，并且调整格式
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(ch)
    logging.info('start download pic...')
    main()
