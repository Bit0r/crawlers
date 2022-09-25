#!/usr/bin/python

import logging
import sqlite3
from pathlib import Path

import httpx
from corpwechatbot.app import AppMsgSender

headers = {
    'user-agent':
    'Mozilla/5.0 (Linux; Android 12; PGZ110 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/104.0.5112.97 Mobile Safari/537.36jianronghuixue/1.3.0',
    'X-Requested-With': 'com.ccb.xiangdaxiaoyuan',
    'Referer': 'https://app.xiaoyuan.ccb.com/EMTSTATIC/DZK01'
}

body_base = {
    "stuClass": "9999",
    "schoolId": "10530",
    "schoolName": "湘潭大学",
    "locationAddr": "湖南省湘潭市雨湖区博学路",
    "departments": "",
    "isContact": "N",
    "isFever": "0",
    "isWuhan": "N",
    "nowArea": "湖南省湘潭市雨湖区",
    "familyaddress": "羊牯塘湘潭大学",
    "familyStatus": "0",
    "diagnosisTreatment": "",
    "nowStatus": "0",
    "healthStatus": "3",
    "isLevel": "N",
    "isbackLive": "N",
    "trafficTool": "",
    "backTrafficTool": "",
    "levelDate": "",
    "backtime": "",
    "arriveAddr": "",
    "trafficNo": "",
    "backTrafficNo": "",
    "professional": "",
    "personType": "",
    "personCategory": None,
    "temperature": 36.5,
    "remarks": None,
    "timeToLeaveHuBei": "",
    "dateOfDisengagement": "",
    "otherSymptoms": "",
    "nowStatusStartTime": "",
    "familyStatusStartTime": "",
    "feverStartTime": "",
    "coughStartTime": "",
    "fatigueStartTime": "",
    "diarrheaStartTime": "",
    "coldStartTime": "",
    "headacheStartTime": "",
    "noseStartTime": "",
    "runnyStartTime": "",
    "throatStartTime": "",
    "conjunctivaStartTime": "",
    "isAppearDiagnosis": "N",
    "isVaccinate": "1",
    "vaccineType": "2",
    "injectTimes": "3",
    "otherDesc": None,
    "isContactWithDiagnosis": "N",
    "isInSchool": "",
}

# 保存成功或者失败的用户微信id
success_users = []
failed_users = []


def get_body(base: dict, identity: dict):
    body = base.copy()

    # 设置用户个人信息
    body['stId'] = identity['stId']
    body['userId'] = identity['userId']
    body['stName'] = identity['stName']
    body['id'] = identity['id']

    # 如果在家，则修改地址为家庭地址
    if identity['at_home']:
        body['locationAddr'] = identity['homeLocation']
        body['nowArea'] = identity['homeArea']
        body['familyaddress'] = identity['homeAddress']

    return body


def check_in_all(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    for row in con.execute('select * from students'):
        check_in(get_body(body_base, row), row['wechat_id'])
    con.close()


def check_in(body, wechat_id=None):
    # 发送打卡请求
    r = httpx.post(
        'https://app.xiaoyuan.ccb.com/channelManage/outbreak/addOutbreak',
        json=body,
        headers=headers,
        follow_redirects=True)

    # 记录打卡情况
    if wechat_id is None:
        return
    if r.is_success:
        logging.warning('打卡成功！')
        success_users.append(wechat_id)
    else:
        logging.error(f'{r.status_code}: {r.text}')
        failed_users.append(wechat_id)


# 发送企业微信通知
def send_wechat(key_path):
    app = AppMsgSender(key_path=key_path)
    if success_users:
        app.send_text('打卡成功！', touser=success_users)
    if failed_users:
        app.send_text('打卡失败！', touser=failed_users)


if __name__ == '__main__':
    logging.basicConfig(filename=Path(__file__).with_suffix('.log'),
                        level=logging.WARNING)
    check_in_all('xtu_covid.db')
    send_wechat('env.ini')
