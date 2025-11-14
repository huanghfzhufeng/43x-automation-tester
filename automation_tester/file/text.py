import logging

from automation_tester.file.base_file import BaseFile
from automation_tester.utils.file_utils import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from automation_tester.utils.text_chunker import ChunkingStrategy, TextChunker

logger = logging.getLogger(__name__)


class TextFile(BaseFile):
    """文本文件解析类，支持本地文本和 OSS 文件文本提取"""

    def __init__(self, source: str):
        super().__init__(source)

    async def parse_text(self, **kwargs):
        if not self._path:
            raise ValueError("path is not set")

        with open(self._path, "r", encoding="utf-8") as f:
            try:
                texts = f.read()
                chunk_size = kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE)
                chunk_overlap = kwargs.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)
                config = TextChunker.create_config(
                    strategy=ChunkingStrategy.RECURSIVE,
                    chunk_size=chunk_size
                    if isinstance(chunk_size, int)
                    else DEFAULT_CHUNK_SIZE,
                    chunk_overlap=chunk_overlap
                    if isinstance(chunk_overlap, int)
                    else DEFAULT_CHUNK_OVERLAP,
                )
                chunks = await TextChunker.chunk_text(texts, config)
                for chunk in chunks:
                    yield chunk
            except Exception as e:
                logger.error(f"解析文本文件失败: {e}")
                raise e
