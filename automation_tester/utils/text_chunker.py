"""
文本分块工具模块

提供智能文本分块功能，支持多种分块策略
"""

import logging
import re
from enum import Enum
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """分块策略"""
    
    RECURSIVE = "recursive"  # 递归分块（推荐）
    FIXED = "fixed"  # 固定长度分块
    PARAGRAPH = "paragraph"  # 按段落分块


class ChunkConfig:
    """分块配置"""
    
    def __init__(
        self,
        strategy: ChunkingStrategy,
        chunk_size: int,
        chunk_overlap: int,
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap


class TextChunker:
    """
    文本分块器
    
    提供多种分块策略，支持智能分块和语义完整性保持
    """
    
    # 默认配置
    DEFAULT_CHUNK_SIZE = 800  # 默认块大小（字符数）
    DEFAULT_CHUNK_OVERLAP = 100  # 默认重叠区域（字符数）
    
    @staticmethod
    def create_config(
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> ChunkConfig:
        """
        创建分块配置
        
        Args:
            strategy: 分块策略
            chunk_size: 块大小（字符数）
            chunk_overlap: 重叠区域大小（字符数）
            
        Returns:
            ChunkConfig: 分块配置对象
        """
        return ChunkConfig(strategy, chunk_size, chunk_overlap)
    
    @staticmethod
    async def chunk_text(text: str, config: ChunkConfig) -> list[str]:
        """
        对文本进行分块
        
        Args:
            text: 待分块的文本
            config: 分块配置
            
        Returns:
            list[str]: 分块后的文本列表
        """
        if not text or not text.strip():
            logger.warning("⚠️ 输入文本为空，返回空列表")
            return []
        
        try:
            if config.strategy == ChunkingStrategy.RECURSIVE:
                return TextChunker._chunk_recursive(text, config)
            elif config.strategy == ChunkingStrategy.PARAGRAPH:
                return TextChunker._chunk_by_paragraph(text, config)
            else:  # FIXED
                return TextChunker._chunk_fixed(text, config)
        except Exception as e:
            logger.error(f"❌ 文本分块失败: {e}", exc_info=True)
            # 降级到简单分块
            return TextChunker._chunk_fixed(text, config)
    
    @staticmethod
    def _chunk_recursive(text: str, config: ChunkConfig) -> list[str]:
        """
        递归分块（推荐）
        
        使用 langchain 的 RecursiveCharacterTextSplitter，
        会尝试按段落、句子等自然边界分块
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", " ", ""],
        )
        chunks = splitter.split_text(text)
        logger.info(f"✅ 递归分块完成: {len(text)} 字符 → {len(chunks)} 个块")
        return chunks
    
    @staticmethod
    def _chunk_by_paragraph(text: str, config: ChunkConfig) -> list[str]:
        """
        按段落分块
        
        保持段落完整性，如果段落过长则进一步分割
        """
        # 按段落分割（双换行符）
        paragraphs = re.split(r'\n\n+', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块 + 新段落不超过限制，合并
            if len(current_chunk) + len(para) + 2 <= config.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个段落过长，需要分割
                if len(para) > config.chunk_size:
                    # 使用递归分块处理长段落
                    sub_chunks = TextChunker._chunk_fixed(
                        para,
                        ChunkConfig(
                            ChunkingStrategy.FIXED,
                            config.chunk_size,
                            config.chunk_overlap,
                        ),
                    )
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.info(f"✅ 段落分块完成: {len(paragraphs)} 个段落 → {len(chunks)} 个块")
        return chunks
    
    @staticmethod
    def _chunk_fixed(text: str, config: ChunkConfig) -> list[str]:
        """
        固定长度分块
        
        简单按字符数分块，带重叠区域
        """
        chunks = []
        step = config.chunk_size - config.chunk_overlap
        
        for i in range(0, len(text), step):
            chunk = text[i : i + config.chunk_size]
            if chunk.strip():  # 只添加非空块
                chunks.append(chunk)
        
        logger.info(f"✅ 固定长度分块完成: {len(text)} 字符 → {len(chunks)} 个块")
        return chunks
    
    @staticmethod
    def chunk_text_sync(text: str, config: ChunkConfig) -> list[str]:
        """
        同步版本的文本分块（不使用 async）
        
        Args:
            text: 待分块的文本
            config: 分块配置
            
        Returns:
            list[str]: 分块后的文本列表
        """
        if not text or not text.strip():
            return []
        
        try:
            if config.strategy == ChunkingStrategy.RECURSIVE:
                return TextChunker._chunk_recursive(text, config)
            elif config.strategy == ChunkingStrategy.PARAGRAPH:
                return TextChunker._chunk_by_paragraph(text, config)
            else:
                return TextChunker._chunk_fixed(text, config)
        except Exception as e:
            logger.error(f"❌ 文本分块失败: {e}", exc_info=True)
            return TextChunker._chunk_fixed(text, config)
