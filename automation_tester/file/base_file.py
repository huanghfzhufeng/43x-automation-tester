from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from automation_tester.utils.file_utils import is_local_path, is_oss_path


class BaseFile(ABC):
    def __init__(self, source: str):
        self._url = ""
        self._path = ""
        if is_local_path(source):
            self._path = source
        elif is_oss_path(source):
            # OSS暂不支持，可以后续扩展
            raise ValueError(f"暂不支持OSS文件: {source}")
        else:
            raise ValueError(f"不支持的文件类型: {source}")

    @abstractmethod
    async def parse_text(self, **kwargs) -> AsyncGenerator[str, None]:
        """解析文件中的文本，返回一个 AsyncGenerator 对象，用于异步生成文本片段

        Returns:
            AsyncGenerator[str, None]: 异步生成文本片段
        """
        yield ""

    async def parse_oss(self, **kwargs) -> AsyncGenerator[str, Any]:
        """异步解析 OSS 文件内容（暂不支持）"""
        if not self._url:
            raise ValueError("url is not set")
        raise NotImplementedError("OSS文件解析暂未实现")

    async def parse(self, **kwargs) -> AsyncGenerator[str, Any]:
        """根据文件路径判断使用相应的方法解析文件文本，支持本地文件和 OSS 文件

        Args:
            extract_images: 是否提取图片
            kwargs: 解析参数
                window_size: 文本窗口大小,默认 1024
                window_overlap: 文本窗口重叠大小,默认 200

        Returns:
            AsyncGenerator[str, Any]: 异步生成文本片段
        """
        if self._url:
            async for text in self.parse_oss(**kwargs):
                yield text
        elif self._path:
            async for text in self.parse_text(**kwargs):
                yield text
        else:
            raise ValueError("Invalid file source")
