from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from automation_tester.file.image import ImageFile
from automation_tester.file.markdown import MarkdownFile
from automation_tester.file.pdf import PDFFile
from automation_tester.file.ppt import PPTFile
from automation_tester.file.text import TextFile
from automation_tester.file.word import WordFile


class FileType(Enum):
    PDF = "pdf"
    PPT = "ppt"
    MD = "md"
    TXT = "txt"
    WORD = "word"
    IMAGE = "image"
    UNKNOWN = "unknown"


class _FileService:
    async def read_content(
        self, source: str, file_type: FileType, **kwargs
    ) -> AsyncGenerator[str, Any]:
        """
        读取文件内容(纯文本)

        Args:
            source: 文件路径 或 OSS 文件 URL
            file_type: 文件类型
            extract_images: 是否提取图片
            kwargs: 解析参数
                window_size: 文本窗口大小,默认 1024
                window_overlap: 文本窗口重叠大小,默认 200

        Returns:
            AsyncGenerator[str, Any]: 异步生成文本片段
        """
        match file_type:
            case FileType.PDF:
                async for text in PDFFile(source).parse(**kwargs):
                    yield text
            case FileType.PPT:
                async for text in PPTFile(source).parse(**kwargs):
                    yield text
            case FileType.TXT:
                async for text in TextFile(source).parse(**kwargs):
                    yield text
            case FileType.MD:
                async for text in MarkdownFile(source).parse(**kwargs):
                    yield text
            case FileType.WORD:
                async for text in WordFile(source).parse(**kwargs):
                    yield text
            case FileType.IMAGE:
                async for text in ImageFile(source).parse(**kwargs):
                    yield text
            case _:
                raise ValueError(f"不支持的文件类型: {file_type}")


FileService = _FileService()
