import logging
from pathlib import Path

from automation_tester.file.base_file import BaseFile

logger = logging.getLogger(__name__)


class PDFFile(BaseFile):
    """
    PDF 文件解析类，支持文本提取

    注意：需要安装 PyPDF2 或 pdfplumber
    推荐使用 pdfplumber 以获得更好的效果

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
            # 尝试使用 pdfplumber（推荐）
            try:
                import pdfplumber

                with pdfplumber.open(self._path) as pdf:
                    total_pages = len(pdf.pages)
                    logger.info(f"PDF 打开成功，共 {total_pages} 页")

                    pages_with_text = 0
                    total_chars = 0

                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text and text.strip():
                            pages_with_text += 1
                            total_chars += len(text)
                            yield f"[第{page_num}页]\n{text.strip()}"

                    logger.info(
                        f"PDF 解析完成: {pages_with_text}/{total_pages} 页有文本，共 {total_chars} 字符"
                    )

                    # 如果没有提取到任何文本，给出警告
                    if pages_with_text == 0:
                        logger.warning("PDF 文件没有可提取的文本内容，可能是图片型 PDF（扫描件）")
                        yield "[警告] 此 PDF 文件没有可提取的文本内容，可能是图片型 PDF（扫描件），需要 OCR 处理"

                return

            except ImportError:
                logger.debug("pdfplumber 未安装，尝试使用 PyPDF2")

            # 备选方案：使用 PyPDF2
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(self._path)
                total_pages = len(reader.pages)
                logger.info(f"PDF 打开成功（PyPDF2），共 {total_pages} 页")

                pages_with_text = 0
                total_chars = 0

                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        pages_with_text += 1
                        total_chars += len(text)
                        yield f"[第{page_num}页]\n{text.strip()}"

                logger.info(
                    f"PDF 解析完成: {pages_with_text}/{total_pages} 页有文本，共 {total_chars} 字符"
                )

                # 如果没有提取到任何文本，给出警告
                if pages_with_text == 0:
                    logger.warning("PDF 文件没有可提取的文本内容，可能是图片型 PDF（扫描件）")
                    yield "[警告] 此 PDF 文件没有可提取的文本内容，可能是图片型 PDF（扫描件），需要 OCR 处理"

                return

            except ImportError as import_err:
                raise ImportError(
                    "PDF解析需要安装 pdfplumber 或 PyPDF2\n"
                    "推荐安装: uv pip install pdfplumber\n"
                    "或者: uv pip install PyPDF2"
                ) from import_err

        except Exception as e:
            logger.error(f"解析PDF文件失败: {e}")
            raise RuntimeError(f"解析PDF文件 {self._path} 失败: {e}") from e
