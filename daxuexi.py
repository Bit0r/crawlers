# %%
import json
import time
from pathlib import Path

import httpx
from loguru import logger

import settings


# %%
class Daxuexi:
    def __init__(self, guid, client: httpx.Client = None) -> None:
        self.guid = guid
        self.client = client

        if client is None:
            headers = settings.headers | {
                "Origin": "https://h5.cyol.com",
                "Referer": "https://h5.cyol.com/",
                "User-Agent": settings.weixin_ua,
            }
            self.client = httpx.Client(headers=headers, follow_redirects=True)

    def get_lates_fuck_post_datas(self, episode: str):
        url = "https://h5.cyol.com/special/weixin/sign.json"
        response = self.client.get(url)
        datas = response.json()

        latest_fuck_info = datas[list(datas.keys())[-1]]
        latest_fuck_video_link = latest_fuck_info["url"].strip()

        tc = int(round(time.time() * 1000))
        tn = tc + 10 * 60 * 1000
        temp_data = '{{"guid":"{guid}","tc":"{tc}","tn":"{tn}","n":"{n}","u":"{u}","d":"cyol.com","r":"{r}","w":448,"m":"[{{\\"c\\":\\"2023\\",\\"s\\":\\"{s}\\"{other}}}]"}}'
        steps = ["打开页面", "开始学习", "播放完成", "课后答题"]
        data = {
            "guid": self.guid,
            "tc": tc,
            "tn": tn,
            "n": "打开页面",
            "u": latest_fuck_video_link + "?t=1&z=201",
            "r": latest_fuck_video_link.replace("m.html", "index.html"),
            "s": episode,
            "other": r",\"prov\":\"18\",\"city\":\"1\"",
        }
        for i in steps:
            if i == "打开页面":
                temp = copy.deepcopy(data)
                temp["other"] = ""
                result = temp_data.format(**temp)
            else:
                data["n"] = i
                result = temp_data.format(**data)
            send_to_log_api(result)

    def send_to_log_api(self, data: str) -> bool:
        url = "https://gqti.zzdtec.com/api/event"
        res = self.client.post(url, data=data)
        print(data)
        print(res.text)
        if res.text == "ok" and res.status_code == 200:
            return True
        else:
            return False
