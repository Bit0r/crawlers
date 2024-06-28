#!/usr/bin/python3
import base64
import re
from hashlib import md5
from pathlib import Path

import httpx
import rtoml
from loguru import logger
from openai import OpenAI
from pydumpling import catch_any_exception
from selectolax.parser import HTMLParser

import settings

catch_any_exception()


class OfflineAccount:
    def __init__(
        self,
        headers=settings.headers,
        openai_api_key=settings.openai_api_key,
        openai_base_url=settings.openai_base_url,
    ):
        env = rtoml.load(Path("env.toml"))["offline_account"]

        base_url = env["base_url"]
        headers |= {
            "referer": base_url,
            "Cache-Control": "no-cache",
            # Add other headers from the original 'headers' dictionary
        }

        self.username = env["username"]
        self.password = env["password"]
        self.httpx_client = httpx.Client(
            base_url=base_url,
            headers=headers,
            follow_redirects=True,
            verify=False,
            event_hooks={"request": [self.delay]},
        )
        self.openai_client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)
        self.nums_pattern = re.compile(r"\d{5}")

    @staticmethod
    def delay(_):
        from random import randint
        from time import sleep

        logger.info("sleep...")
        sleep(randint(1, 3))

    def recognize_captcha(self, url="/vcode.htm"):
        for _ in range(5):
            r = self.httpx_client.get(url)
            logger.info("识别验证码...")

            # Convert image to base64
            image_base64 = base64.b64encode(r.content).decode("utf-8")

            # Use GPT-4 Vision to recognize the captcha
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请识别图中的5位数字，只需要输出数字即可，不用输出其他字符。",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            captcha_text = response.choices[0].message.content.strip()
            captcha_text = self.nums_pattern.search(captcha_text).group()
            logger.info(f"GPT-4O识别验证码：{captcha_text}")
            return captcha_text

    def get_vcode_url(self):
        r = self.httpx_client.get("/user-login.htm")
        parser = HTMLParser(r.content)
        url = parser.css_first("img.vcode").attributes["src"]
        return url

    def log_in(self):
        for _ in range(6):
            vcode_url = self.get_vcode_url()

            r = self.httpx_client.post(
                "/user-login.htm",
                headers={"x-requested-with": "XMLHttpRequest"},
                data={
                    "email": self.username,
                    "password": md5(self.password.encode()).hexdigest(),
                    "vcode": self.recognize_captcha(vcode_url),
                },
            ).json()
            logger.debug(r)
            if r["code"] == "0":
                logger.warning("登录成功！")
                return True
        logger.warning("登陆失败")
        return False

    def check_in(self):
        r = self.httpx_client.get("/")
        parser = HTMLParser(r.content)
        url = parser.css_first('button[data-modal-title="签到"]').attributes[
            "data-modal-url"
        ]
        logger.info(url)
        for _ in range(4):
            vcode_url = self.get_vcode_url()

            r = self.httpx_client.post(
                url,
                headers={"x-requested-with": "XMLHttpRequest"},
                data={"vcode": self.recognize_captcha(vcode_url)},
            ).json()

            logger.info(r)
            if r["code"] == "0" and "成功" in r["message"]:
                logger.warning("签到成功！")
                break
            elif r["code"] == "-1" and "已经" in r["message"]:
                logger.warning("今日已签到！")
                break
        else:
            logger.warning("签到失败！")

    def run(self):
        if self.log_in():
            self.check_in()


if __name__ == "__main__":
    logger.add("offline_account.log", rotation="1 day", retention="7 days")
    account = OfflineAccount()
    account.run()
