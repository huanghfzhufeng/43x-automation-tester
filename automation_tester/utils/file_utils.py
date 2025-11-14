"""
文件处理工具模块
"""

import os
from pathlib import Path

# 默认分块配置
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_CHUNK_OVERLAP = 200


def is_local_path(source: str) -> bool:
    """判断是否为本地文件路径"""
    return os.path.exists(source) or Path(source).exists()


def is_oss_path(source: str) -> bool:
    """判断是否为OSS路径（暂不支持）"""
    return source.startswith("http://") or source.startswith("https://")


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower().lstrip(".")
