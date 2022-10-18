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
CPU_COUNT = os.cpu_count()
configPath = './config.txt'
if os.path.exists(configPath):
    # 读取配置
    with open('config.txt', 'r', encoding='utf-8') as filedd:
        rr_list = filedd.readlines()
    con = {}
    for line in rr_list:
        line = line.replace('\n', '')
        ll = line.split('=', 1)
        con[ll[0]] = ll[1]
    EVERY_DOWNLOAD_LENGTH_NUM = int(con['EVERY_DOWNLOAD_LENGTH_NUM'])
    PAUSE_TIME_MINUTES = int(con['PAUSE_TIME_MINUTES'])
    HTTP_PROXY = str(con['HTTP_PROXY'])
    HTTPS_PROXY = str(con['HTTPS_PROXY'])
else:
    logging.error("config.txt file not exist!")
logging.basicConfig(
    filename='log.txt',
    level=logging.INFO,
    filemode='w+',
    format='%(levelname)s:%(asctime)s: %(message)s',
    datefmt='%Y-%d-%m %H:%M:%S'
)
# proxy = requests.get(IP_URL).text
# print(proxy)
IMAGE_PATH = './images/'
if not os.path.exists(IMAGE_PATH):
    os.makedirs(IMAGE_PATH)
EXISTED_IMAGES = set(os.listdir(IMAGE_PATH))


def get_download_urls(image_ids):
    download_urls = []
    for _id in image_ids:
        if _id is not None:
            download_urls.append(DOWNLOAD_URL_KEY.format(image_id=_id))
        else:
            logging.warning('get_download_urls , _id is None !')
    return download_urls


def download_image(image_url):
    parse_result = urlparse(image_url)
    path = parse_result.path
    image_name = path.split('/')[-1]
    if image_name in EXISTED_IMAGES:
        logging.info(f'图片 {image_name} 已存在无需重新下载')
        return None
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
        time.sleep(int(PAUSE_TIME_MINUTES * 60))
        logging.info('download too many request , program will sleep for' + str(PAUSE_TIME_MINUTES * 60) + ' seconds')
        return None
    prefix = IMAGE_PATH
    with open(prefix + image_name, 'wb') as image:
        image.write(response.content)
    message = 'download {} success. url: {}'.format(image_name, image_url)
    logging.info(message)


def get_image_url(need_redirect_url):
    """
    因为没法解决反爬， 这里采取其他方式绕过反爬
    1. 利用 selenium 获取到页面上 download 按钮的 url
    2. 这个地方 download 按钮的 url 并不能拿到图片的 url， 经过测试发现进行了重定向然后重定向的 url 才是图片 url
    3. 这个 download 按钮的 url 也有反爬， 测试发现 get 请求绕不过
    4. 但是测试发现可以用 head 请求获取到重定向的图片 url
    5. http code 302 返回的 response headers 里面的 location 即为重定向的 url
    """
    response = requests.head(need_redirect_url, headers=headers)
    if response.status_code != 302:
        message = '{} don\'t have redirect. code: {}'.format(need_redirect_url, response.status_code)
        logging.error(message)
        return None
    location = response.headers.get('location')
    logging.info(f'get_image_url success. location: {location}' + '\n')
    return location


def download(need_redirect_url):
    try:
        image_url = get_image_url(need_redirect_url)
        if image_url:
            download_image(image_url)
        return True
    except Exception as e:
        print(e)
    return False


def main():
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
            if current_times % 100 == 0:
                time.sleep(PAUSE_TIME_MINUTES * 60)
            for i in range(0, 3):
                if not download(url):
                    logging.warning('download fail , will retry 3 times! current retry num is ' + str(i + 1))
                    time.sleep(3)
                    download(url)
                else:
                    break
        numpy.save('image_ids', save_ids)
        logging.info('download finished ,remaining  num :' + str(len(numpy.load('image_ids.npy', allow_pickle=True))))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S"
                        , filename='downloadIds.log', filemode='a')
    # 创建一个handler，用于输出到控制台，并且调整格式
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(ch)
    logging.info('start download pic...')
    main()
