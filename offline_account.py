#!/usr/bin/python3
import logging
import re
from hashlib import md5
from pathlib import Path

import httpx
import rtoml
from ddddocr import DdddOcr
from selectolax.parser import HTMLParser

from settings import headers

env = rtoml.load(Path('env.toml'))['offline_account']
base_url = env['base_url']
username = env['username']
password = env['password']

headers['referer'] = base_url
headers['x-requested-with'] = 'XMLHttpRequest'

prog = re.compile(r'\d{5}')
ocr, ocr_old = DdddOcr(), DdddOcr(old=True)


def delay(_):
    from random import randint
    from time import sleep
    logging.info('sleep...')
    sleep(randint(1, 3))


def recognize_captcha(client: httpx.Client):
    for _ in range(5):
        r = client.get('vcode.htm')
        logging.info('识别验证码...')
        res = ocr.classification(r.content)
        if not prog.fullmatch(res):
            res = ocr_old.classification(r.content)
            if not prog.fullmatch(res):
                continue
        return res


def log_in(client: httpx.Client):
    for _ in range(6):
        r = client.post('user-login.htm',
                        data={
                            'email': username,
                            'password': md5(password.encode()).hexdigest(),
                            'vcode': recognize_captcha(client),
                        }).json()
        logging.info(r)
        if r['code'] == '0':
            logging.warning('登录成功！')
            return True
    else:
        logging.warning('登陆失败')
        return False


def check_in(client: httpx.Client):
    r = client.get('', headers=headers)
    parser = HTMLParser(r.content)
    url = parser.css_first(
        'button[data-modal-title="签到"]').attributes['data-modal-url']
    logging.info(url)
    for _ in range(4):
        r = client.post(url, data={'vcode': recognize_captcha(client)}).json()
        logging.info(r)
        if r['code'] == '0' and '成功' in r['message']:
            logging.warning('签到成功！')
            break
        elif r['code'] == '-1' and '已经' in r['message']:
            logging.warning('今日已签到！')
            break
    else:
        logging.warning('签到失败！')


if __name__ == '__main__':
    logging.basicConfig(filename=Path(__file__).with_suffix('.log'),
                        level=logging.INFO)
    with httpx.Client(base_url=base_url,
                      headers=headers,
                      follow_redirects=True,
                      event_hooks={'request': [delay]}) as client:
        if log_in(client):
            check_in(client)
