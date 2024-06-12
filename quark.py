# %%
import re
import uuid
from base64 import b64encode
from pathlib import Path

import httpx
from cairosvg import svg2png
from loguru import logger

import settings


# %%
class Quark:
    def __init__(self, user_id, sign, client: httpx.Client = None):
        self.regex_math = re.compile(r"\$.*?\$", re.S)
        self.regex_h1 = re.compile(r"\s*^# .*$\s*", re.M)

        self.user_id = user_id
        self.sign = sign

        self.datakeys = "question solution discuss answer".split()

        self.client = client

        if client is None:
            headers = settings.headers | {
                "Origin": "https://www.quark.cn",
                "Referer": "https://www.quark.cn/",
            }
            self.client = httpx.Client(headers=headers, follow_redirects=True)

    def path2data(self, path: str | Path):
        path = Path(path).expanduser()
        if path.is_file():
            data = self.file2data(path)
        elif path.is_dir():
            data = self.dir2data(path)
        else:
            data = None
        return data

    def file2data(self, path: str | Path):
        path = Path(path).expanduser()
        data = {}
        if not (path.is_file() and path.suffix == ".md"):
            return None

        text = path.read_text()
        texts = self.regex_h1.split(text)

        datakeys = [f"{k}Data" for k in self.datakeys]
        i = 0
        for text in texts:
            if not text:
                continue
            data[datakeys[i]] = self.text2data(text)
            i += 1

        return data

    def dir2data(self, path: str | Path):
        path = Path(path).expanduser()
        data = {}
        filenames = (f"{k}Data.md" for k in self.datakeys)
        for file in path.iterdir():
            if file.is_file() and file.name in filenames:
                text = file.read_text()
                data[file.stem + "Data"] = self.text2data(text)
        return data

    def text2data(self, text: str):
        jsonML, formulas = self.markdown2jsonML(text)
        return {
            "jsonML": jsonML,
            "module": {"formulas": formulas},
        }

    def markdown2jsonML(self, markdown: str):
        paragraphs = markdown.split("\n\n")
        jsonML = ["root", {}]
        formulas = {}

        for paragraph in paragraphs:
            p = self._node_p()
            jsonML.append(p)

            pos = 0
            for match in self.regex_math.finditer(paragraph):
                start, end = match.span()

                if start > pos:
                    p.append(self._node_span(paragraph[pos:start]))

                math = match.group().strip("$").strip()
                group_id = self._get_math(math, formulas)

                if group_id is None:
                    logger.error(f"get_math error: {match.group()}")

                p.append(self._node_math(formulas[group_id], group_id))
                pos = end

            if pos < len(paragraph):
                p.append(self._node_span(paragraph[pos:]))

        return jsonML, formulas

    def _get_math(self, math: str, formulas: dict):
        svg_data = self._get_svg(math)
        if svg_data is None:
            return None

        group_id = hex(int(uuid.uuid4()))[2:14]

        formula = {
            "format": "png",
            "class_name": "qk-formula-tag",
            "math": math,
            "frontend_group_id": group_id,
        }

        formula["svg_url"] = svg_data["svg_url"]
        for key in "width", "height", "style":
            formula["svg_" + key] = svg_data[key]

        png_data = self._upload_png(svg_data["svg"])
        if png_data is None:
            return None

        for key in "url", "width", "height", "size", "phash":
            formula[key] = png_data[key]

        formulas[group_id] = formula

        return group_id

    def _upload_png(self, svg_str: str):
        png_bin = svg2png(bytestring=svg_str)

        png_base64 = b64encode(png_bin).decode()
        data_url = f"data:image/png;base64,{png_base64}"

        resp = self.client.post(
            "https://qknow-node-service.quark.cn/c/api/editor/formula/upload_base64",
            params={
                "user_id": self.user_id,
                "sign": self.sign,
            },
            json={
                "content": data_url,
            },
        )
        if resp.is_error:
            logger.error(f"upload_png error: {resp.text}")
            return None

        data = resp.json()
        if data["code"] != 0:
            logger.error(f"upload_png error: {data}")
            return None

        return data["data"]

    def _get_svg(self, math: str) -> dict | None:
        resp = self.client.get(
            "https://qknow-node-service.quark.cn/c/api/editor/formula/preview",
            params={
                "math": math,
                "user_id": self.user_id,
                "sign": self.sign,
            },
        )
        if resp.is_error:
            logger.error(f"get_svg error: {resp.text}")
            return None

        data = resp.json()
        if data["code"] != 0:
            logger.error(f"get_svg error: {data}")
            return None

        return data["data"]

    def _node_math(self, formula: dict, group_id: str):
        height, width = formula["height"], formula["width"]

        return [
            "tag",
            {
                "height": height,
                "width": width,
                "tagType": "formula_tag",
                "metadata": {"frontend_group_id": group_id},
            },
        ]

    def _node_span(self, span: str):
        return [
            "span",
            {"data-type": "text"},
            ["span", {"data-type": "leaf"}, span],
        ]

    def _node_p(self):
        return ["p", {"jc": "left"}]


# %%
if __name__ == "__main__":
    import json

    quark = Quark("1118256655", "43b39286f4e7fa29e9c11e2f3fb8dd65")
    data = quark.path2data("test/quark/1.md")
    print(json.dumps(data, indent="\t", ensure_ascii=False))
