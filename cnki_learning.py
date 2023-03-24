#!/usr/bin/python

from typing import Iterable

import httpx
from loguru import logger

import settings
from util import delay


class CnkiLearning:

    def __init__(self, token, visitorID, LID, userId, userName, orgId):
        self.headers = settings.headers | {
            # 'authToken': token,
            'eduToken': token,
            # 'orgToken': token,
            'referer': 'https://k.cnki.net/courseLearn',
        }

        self.body = {
            # "courseId": "23028",
            "courseTypeId": 3,
            # "courseName": "毕业论文快速入门指南",
            "typeId": 1,
            "duration": 60,
            # "endTime": "2023-03-24 13:58:12",
            "remark": "windows 10&&chrome 109.0.0.0",
            "source": "k-wb-edu-courseLearn",
            "userId": userId,
            "user_name": userName,
            # "watchTime": 239,
            # "lectureId": 49901,
            # "isComplete": False,
            "browserName": "chrome",
            "secondTerminalName": "windows",
            "terminalName": "pc",
            "organizationId": orgId,
        }

        self.client = httpx.Client(headers=self.headers,
                                   base_url='https://k.cnki.net',
                                   cookies={
                                       'cnkiAuth': token,
                                       'visitorID': visitorID,
                                       'LID': LID,
                                   },
                                   follow_redirects=True,
                                   event_hooks={'request': [delay(50, 60)]})

    def postRecord(self, lectureId, courseId):
        body = self.body | {
            'lectureId': lectureId,
            'courseId': courseId,
        }
        r = self.client.post('/kedu/record/recordlearnFoot', json=body)
        r_json = r.json()
        if r_json['data']:
            logger.info(r_json)
        else:
            logger.error(r_json)

    def postCourse(self, lectureId, courseId, recordCount=40):
        for _ in range(recordCount):
            self.postRecord(lectureId, courseId)

    def postLecture(self, lectureId, courses: Iterable, recordCount=40):
        for courseId in courses:
            self.postCourse(lectureId, courseId, recordCount)


if __name__ == '__main__':
    from pathlib import Path

    import rtoml

    env = rtoml.load(Path('env.toml'))['cnki_learning']
    logger.configure(
        **{'handlers': [{
            'sink': 'cnki_learning.log',
            'level': 'INFO'
        }]})
    lectureId = 49901
    courses = range(23029, 23034)
    cnki_learning = CnkiLearning(**env)
    cnki_learning.postLecture(lectureId, courses)
