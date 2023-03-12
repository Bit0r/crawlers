#!/usr/bin/python

import random

import httpx
from loguru import logger
from selectolax.parser import HTMLParser

import settings
from util import delay


class Spis:

    def __init__(self, base_url):
        self.base_url = base_url
        self.headers = settings.headers | {'referer': base_url}
        self.client = httpx.Client(headers=self.headers,
                                   follow_redirects=True,
                                   event_hooks={'request': [delay(1.0, 2.0)]})

    def login(self, login_url, username, password, service, source):
        r = self.client.get(login_url,
                            params={
                                'service': service,
                                'source': source,
                            })
        parser = HTMLParser(r.content)
        execution = parser.css_first(
            'input[name="execution"]').attributes['value']

        r = self.client.post(login_url,
                             params={
                                 'service': service,
                                 'source': source,
                             },
                             data={
                                 'username': username,
                                 'password': password,
                                 'execution': execution,
                                 '_eventId': 'submit',
                                 'rememberMe': 'on',
                             })
        logger.info(r.cookies)

    def operate(self, operate_type):
        r = self.client.post(self.base_url + '/integral/operate',
                             params={'_': random.uniform(0.9, 1.0)},
                             data={'type': operate_type})
        r_json = r.json()
        if r_json['error']:
            logger.error(r_json)
        else:
            logger.info(r_json)

    def share(self, invite):
        r = self.client.post(
            self.base_url + '/integral/share',
            params={'_': random.uniform(0.9, 1.0)},
            headers=self.headers | {
                'User-Agent':
                'Mozilla/5.0 (Linux; Android 12; PGZ110 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.5304.141 Mobile Safari/537.36 XWEB/5015 MMWEBSDK/20221109 MMWEBID/2568 MicroMessenger/8.0.31.2280(0x28001F59) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64'  # noqa
            },
            data={
                'type': 'shareQl',
                'invite': invite
            })
        r_json = r.json()
        if r_json['error']:
            logger.error(r_json)
        else:
            logger.info(r_json)

    def daily(self):
        for opreate, repeat in {
                'login': 1,
                'search': 4,
                'collect': 4,
                'download': 4,
        }.items():
            for _ in range(repeat):
                self.operate(opreate)

    def permanent(self, invite):
        for _ in range(4):
            self.share(invite)


if __name__ == '__main__':
    from pathlib import Path

    import rtoml

    env = rtoml.load(Path('env.toml'))['spis']
    logger.configure(**{'handlers': [{'sink': 'spis.log', 'level': 'INFO'}]})
    spis = Spis(env['base_url'])
    spis.login(env['login_url'], env['username'], env['password'],
               env['service'], env['source'])
    spis.daily()
