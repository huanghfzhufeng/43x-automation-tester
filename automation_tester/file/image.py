import logging
from pathlib import Path

from PIL import Image

from automation_tester.file.base_file import BaseFile
from automation_tester.utils.image_parser import parse_image_with_llm

logger = logging.getLogger(__name__)


class ImageFile(BaseFile):
    """
    图片文件解析类，使用IMAGE_LLM_MODEL进行智能解析
    支持的格式：JPG, JPEG, PNG, WEBP

    Args:
        source: 文件路径
    """

    def __init__(self, source: str):
        super().__init__(source)

    async def parse_text(self, **kwargs):
        if not self._path:
            raise ValueError("path is not set")

        file_path = Path(self._path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self._path}")

        try:
            # 使用PIL打开图片
            with Image.open(self._path) as pil_image:
                # 调整图片大小以优化API调用
                pil_image.thumbnail((1024, 1024))

                # 使用新的图片解析工具
                result = await parse_image_with_llm(pil_image)
                yield result

        except Exception as e:
            logger.error(f"解析图片文件失败: {e}")
            raise RuntimeError(f"解析图片文件 {self._path} 失败: {e}")
