#!/usr/bin/python

import logging
from pathlib import Path

import httpx
from corpwechatbot.app import AppMsgSender

import xtu_covid_env

headers = {
    'user-agent':
    'Mozilla/5.0 (Linux; Android 12; PGZ110 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/104.0.5112.97 Mobile Safari/537.36jianronghuixue/1.3.0',
    'X-Requested-With': 'com.ccb.xiangdaxiaoyuan',
    'Referer': 'https://app.xiaoyuan.ccb.com/EMTSTATIC/DZK01'
}
cookies = {'sid': xtu_covid_env.sid}

# 保存成功或者失败的用户微信id
success_users = []
failed_users = []


def check_in():
    # 发送打卡请求
    r = httpx.post(
        'https://app.xiaoyuan.ccb.com/channelManage/outbreak/addOutbreak',
        json=xtu_covid_env.json_body,
        headers=headers,
        cookies=cookies,
        follow_redirects=True)

    # 记录打卡情况
    if r.is_success:
        logging.warning('打卡成功！')
        success_users.append(xtu_covid_env.wechat_id)
    else:
        logging.error(f'{r.status_code}: {r.text}')
        failed_users.append(xtu_covid_env.wechat_id)


# 发送企业微信通知
def send_wechat():
    app = AppMsgSender(key_path="env.ini")
    if success_users:
        app.send_text('打卡成功！', touser=success_users)
    if failed_users:
        app.send_text('打卡失败！', touser=failed_users)


if __name__ == '__main__':
    logging.basicConfig(filename=Path(__file__).with_suffix('.log'),
                        level=logging.WARNING)
    check_in()
    send_wechat()
