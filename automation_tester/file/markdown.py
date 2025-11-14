import json

from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from markdown import markdown

from automation_tester.file.base_file import BaseFile
from automation_tester.utils.file_utils import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


class MarkdownFile(BaseFile):
    """Markdown文件解析类，支持文本提取"""

    def __init__(self, source: str):
        super().__init__(source)

    async def parse_text(self, **kwargs):
        if not self._path:
            raise ValueError("path is not set")

        try:
            window_size = kwargs.get("window_size", DEFAULT_CHUNK_SIZE)
            window_overlap = kwargs.get("window_overlap", DEFAULT_CHUNK_OVERLAP)

            with open(self._path, encoding="utf-8") as file:
                md_text = file.read()
                html = markdown(md_text, extensions=["tables"])
                soup = BeautifulSoup(html, "html.parser")

                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=window_size,
                    chunk_overlap=window_overlap,
                )

                buffer = ""
                elements = list(soup.body.children) if soup.body else list(soup.children)
                for el in elements:
                    if hasattr(el, "name") and el.name == "table":
                        if buffer.strip():
                            for chunk in splitter.split_text(buffer.strip()):
                                yield chunk
                            buffer = ""

                        rows = el.find_all("tr")
                        if not rows:
                            continue
                        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
                        data_rows = []
                        for tr in rows[1:]:
                            cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                            if len(cells) == len(headers):
                                data_rows.append(dict(zip(headers, cells, strict=False)))
                        table_json = json.dumps(data_rows, ensure_ascii=False)
                        yield f"START_TABLE\n{table_json}\nEND_TABLE"
                    else:
                        text = (
                            el.get_text(strip=True) if hasattr(el, "get_text") else str(el).strip()
                        )
                        if text:
                            buffer += text + "\n\n"

                if buffer.strip():
                    for chunk in splitter.split_text(buffer.strip()):
                        yield chunk

        except Exception as e:
            raise RuntimeError(f"解析 Markdown 文件 {self._path} 失败: {e}") from e
