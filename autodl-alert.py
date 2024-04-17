#!/usr/bin/python

import random
import time
from pathlib import Path

import httpx
import rtoml
import semver
from box import Box
from loguru import logger
from notifypy import Notify
from pint import UnitRegistry

import settings
from util import delay


class Autodl:
    def __init__(self, list_path: str, auth_token: str, cookie: str):
        base_url = "https://www.autodl.com"

        self.list_path = list_path
        self.headers = settings.headers | {
            "referer": base_url,
            "Authorization": auth_token,
            # "Cookie": cookie,
        }

        self.client = httpx.Client(
            headers=self.headers,
            follow_redirects=True,
            base_url=base_url,
        )

        self.request_body = settings.autodl_a40

    def has_machine_idle(
        self,
        gpu_type_name="A40",
        data_disk_size="50GB",
        cuda_version="12.0",
        kernel_version="5.4",
    ):
        if isinstance(gpu_type_name, str):
            gpu_type_name = [gpu_type_name]

        body = Box(self.request_body)
        body.gpu_type_name = gpu_type_name

        cuda_version = semver.VersionInfo.parse(
            cuda_version, optional_minor_and_patch=True
        )
        kernel_version = semver.VersionInfo.parse(
            kernel_version, optional_minor_and_patch=True
        )

        r = self.client.post(self.list_path, json=body.to_dict())
        r_json = Box(r.json())

        if r_json.code != "Success":
            logger.error(r_json)
        else:
            logger.info(r_json)

        ureg = UnitRegistry()
        Q_ = ureg.Quantity
        data_disk_size = Q_(data_disk_size)

        for machine in r_json.data.list:
            gpu_idle_num = machine.gpu_idle_num

            max_data_disk_expand_size = machine.max_data_disk_expand_size * ureg.byte

            highest_cuda_version = semver.VersionInfo.parse(
                machine.highest_cuda_version, optional_minor_and_patch=True
            )

            machine_kernel_version = semver.VersionInfo.parse(
                machine.machine_base_info.kernel_version, optional_minor_and_patch=True
            )
            # 将 patch 和 prerelease 信息去掉，只比较主要版本号
            machine_kernel_version = machine_kernel_version.replace(
                patch=0, prerelease=None, build=None
            )

            if (
                gpu_idle_num > 0
                and max_data_disk_expand_size >= data_disk_size
                and highest_cuda_version >= cuda_version
                and machine_kernel_version >= kernel_version
            ):
                return True

        return False

    def watch_machine_idle(self, gpu_type_name="A40", data_disk_size="50GB", **kwargs):
        while True:
            if self.has_machine_idle(gpu_type_name=gpu_type_name, **kwargs):
                notify = Notify()
                notify.title = "AutoDL"
                notify.message = f"""GPU: {gpu_type_name}
硬盘: {data_disk_size}
有空闲机器！"""
                notify.send()
                break

            time.sleep(60)


if __name__ == "__main__":
    env = rtoml.load(Path("env.toml"))
    env = Box(env).autodl
    logger.configure(**{"handlers": [{"sink": "autodl.log", "level": "INFO"}]})

    autodl = Autodl(env.list_path, env.auth_token, env.cookie)
    autodl.watch_machine_idle(
        gpu_type_name="A40",
        data_disk_size="50GB",
        cuda_version="12.0",
        kernel_version="5.4",
    )
