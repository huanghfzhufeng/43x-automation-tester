"""
RAG Service - 检索增强生成服务

使用 Chroma 向量数据库实现文本的向量化存储和语义检索
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RagChunk:
    """RAG 检索结果块"""

    chunk: str  # 文本内容
    metadata: dict[str, Any]  # 元数据（文件名、来源等）
    distance: float | None = None  # 相似度距离


class RAGService:
    """
    RAG 服务

    提供文本向量化、存储和检索功能
    使用 Chroma 向量数据库进行本地持久化
    """

    def __init__(
        self,
        session_id: str,
        persist_dir: str = "./chroma_db",
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化 RAG 服务

        Args:
            session_id: 会话 ID，用于隔离不同会话的数据
            persist_dir: 向量数据库持久化目录
            embedding_model: 向量化模型名称
        """
        self.session_id = session_id
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model

        # 延迟初始化（避免导入时就创建数据库）
        self._client = None
        self._collection = None
        self._embedding_function = None

        logger.info(
            f"RAGService 初始化: session_id={session_id}, "
            f"persist_dir={persist_dir}, embedding_model={embedding_model}"
        )

    def _ensure_initialized(self):
        """确保 Chroma 客户端已初始化"""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.utils import embedding_functions

            # 创建持久化客户端
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)

            # 🔥 优先尝试使用 Azure OpenAI Embeddings
            azure_endpoint = os.getenv("AZURE_EMBEDDING_AZURE_ENDPOINT")
            azure_api_key = os.getenv("AZURE_EMBEDDING_API_KEY")
            azure_deployment = os.getenv("AZURE_EMBEDDING_AZURE_DEPLOYMENT")
            azure_api_version = os.getenv("AZURE_EMBEDDING_API_VERSION")

            if azure_endpoint and azure_api_key and azure_deployment:
                logger.info("🔵 使用 Azure OpenAI Embeddings")
                try:
                    from openai import AzureOpenAI

                    # 创建 Azure OpenAI 客户端
                    azure_client = AzureOpenAI(
                        azure_endpoint=azure_endpoint,
                        api_key=azure_api_key,
                        api_version=azure_api_version or "2023-05-15",
                    )

                    # 创建自定义 embedding function
                    class AzureEmbeddingFunction:
                        def __init__(self, client, deployment):
                            self.client = client
                            self.deployment = deployment

                        def name(self):
                            """返回 embedding function 的名称（Chroma 要求）"""
                            return f"azure_{self.deployment}"

                        def __call__(self, input):
                            # Chroma 会传入文本列表（用于添加文档）
                            if isinstance(input, str):
                                input = [input]

                            response = self.client.embeddings.create(
                                input=input,
                                model=self.deployment,
                            )

                            return [item.embedding for item in response.data]

                        def embed_query(self, input):
                            """查询时使用的 embedding 方法（Chroma 要求）"""
                            # 查询时传入的是单个字符串
                            if isinstance(input, list):
                                input = input[0] if input else ""

                            response = self.client.embeddings.create(
                                input=[input],
                                model=self.deployment,
                            )

                            # 返回列表形式的 embedding
                            return [response.data[0].embedding]

                    self._embedding_function = AzureEmbeddingFunction(
                        azure_client, azure_deployment
                    )

                    logger.info(
                        f"✅ Azure OpenAI Embeddings 初始化成功: deployment={azure_deployment}"
                    )

                except Exception as e:
                    logger.warning(f"⚠️ Azure OpenAI 初始化失败: {e}，尝试使用 OpenAI")
                    raise
            else:
                # 降级到 OpenAI API
                logger.info("🟢 使用 OpenAI Embeddings")
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
                api_base = os.getenv("OPENAI_API_BASE") or os.getenv("LLM_BASE_URL")

                if not api_key:
                    raise ValueError("未设置 OPENAI_API_KEY 或 Azure 配置，请在 .env 文件中添加")

                # 如果使用 OpenRouter，警告
                if api_base and "openrouter" in api_base.lower():
                    logger.warning(
                        "⚠️ 检测到使用 OpenRouter，但 OpenRouter 不支持 embedding API。"
                        "建议配置 Azure OpenAI Embeddings。"
                    )

                self._embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    api_base=api_base
                    if api_base and "openrouter" not in api_base.lower()
                    else None,
                    model_name=self.embedding_model,
                )

            # 获取或创建 collection
            # ChromaDB 只允许 a-zA-Z0-9._- 字符，需要清理 session_id
            import re
            safe_session_id = re.sub(r'[^a-zA-Z0-9._-]', '_', self.session_id)
            # 限制长度（ChromaDB 要求 3-512 字符）
            if len(safe_session_id) > 500:
                safe_session_id = safe_session_id[:500]
            collection_name = f"session_{safe_session_id}"
            try:
                self._collection = self._client.get_collection(
                    name=collection_name,
                    embedding_function=self._embedding_function,
                )
                logger.info(f"✅ 加载已存在的 collection: {collection_name}")
            except Exception:
                self._collection = self._client.create_collection(
                    name=collection_name,
                    embedding_function=self._embedding_function,
                    metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
                )
                logger.info(f"✅ 创建新的 collection: {collection_name}")

        except ImportError as e:
            logger.error(
                "❌ 无法导入 chromadb，请安装: pip install chromadb",
                exc_info=True,
            )
            raise ImportError("chromadb 未安装，请运行: pip install chromadb") from e
        except Exception as e:
            logger.error(f"❌ RAGService 初始化失败: {e}", exc_info=True)
            raise

    def add_chunks(
        self,
        chunks: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        添加文本块到向量数据库

        Args:
            chunks: 文本块列表
            metadatas: 元数据列表（可选），每个文本块对应一个元数据字典

        Returns:
            list[str]: 文档 ID 列表
        """
        self._ensure_initialized()

        if not chunks:
            logger.warning("⚠️ 没有文本块需要添加")
            return []

        try:
            # 生成文档 ID
            ids = [f"{self.session_id}_{i}" for i in range(len(chunks))]

            # 如果没有提供元数据，创建空元数据
            if metadatas is None:
                metadatas = [{}] * len(chunks)

            # 添加到 collection
            self._collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"✅ 成功添加 {len(chunks)} 个文本块到向量数据库")
            return ids

        except Exception as e:
            logger.error(f"❌ 添加文本块失败: {e}", exc_info=True)
            raise

    def search(
        self,
        query: str,
        top_k: int = 3,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[RagChunk]:
        """
        检索相关文本块

        Args:
            query: 查询文本
            top_k: 返回最相关的 K 个结果
            filter_metadata: 元数据过滤条件（可选）

        Returns:
            list[RagChunk]: 检索结果列表
        """
        self._ensure_initialized()

        try:
            # 执行查询
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata,  # 元数据过滤
            )

            # 解析结果
            rag_chunks = []
            if results and results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = (
                    results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
                )
                distances = (
                    results["distances"][0] if results["distances"] else [None] * len(documents)
                )

                for doc, metadata, distance in zip(documents, metadatas, distances, strict=False):
                    rag_chunks.append(
                        RagChunk(
                            chunk=doc,
                            metadata=metadata,
                            distance=distance,
                        )
                    )

            logger.info(f"✅ 检索完成: query='{query[:50]}...', 返回 {len(rag_chunks)} 个结果")

            return rag_chunks

        except Exception as e:
            logger.error(f"❌ 检索失败: {e}", exc_info=True)
            raise

    def delete_all(self):
        """删除当前会话的所有数据"""
        self._ensure_initialized()

        try:
            # 删除 collection
            # ChromaDB 只允许 a-zA-Z0-9._- 字符，需要清理 session_id
            import re
            safe_session_id = re.sub(r'[^a-zA-Z0-9._-]', '_', self.session_id)
            if len(safe_session_id) > 500:
                safe_session_id = safe_session_id[:500]
            collection_name = f"session_{safe_session_id}"
            self._client.delete_collection(name=collection_name)

            # 重置状态
            self._collection = None

            logger.info(f"✅ 已删除 collection: {collection_name}")

        except Exception as e:
            logger.error(f"❌ 删除数据失败: {e}", exc_info=True)
            raise

    def get_count(self) -> int:
        """获取当前会话的文档数量"""
        try:
            self._ensure_initialized()
            count = self._collection.count()
            return count
        except Exception as e:
            logger.warning(f"⚠️ 获取文档数量失败: {e}")
            return 0
