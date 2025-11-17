"""
Memory Manager - 三层记忆管理模块

实现短期记忆、长期记忆和素材库的管理，支持自动摘要生成和压缩。
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from automation_tester.services.rag_service import RAGService

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """对话消息"""

    role: str  # "user" 或 "assistant"
    content: str  # 消息内容
    timestamp: float = field(default_factory=time.time)  # 时间戳
    round_number: int = 0  # 轮次编号


@dataclass
class ConversationSummary:
    """对话摘要"""

    summary: str  # 摘要内容
    key_facts: list[str]  # 关键事实列表
    round_range: tuple[int, int]  # 覆盖的轮次范围 (start, end)
    timestamp: float = field(default_factory=time.time)  # 生成时间


class ShortTermMemory:
    """
    短期记忆

    管理最近的 N 轮对话，当容量满时触发压缩
    """

    def __init__(self, max_rounds: int = 5):
        """
        初始化短期记忆

        Args:
            max_rounds: 最多保留的对话轮次数
        """
        self.max_rounds = max_rounds
        self.messages: list[Message] = []
        self.current_round = 0

        logger.info(f"ShortTermMemory 初始化: max_rounds={max_rounds}")

    def add_message(self, role: str, content: str) -> Message:
        """
        添加消息到短期记忆

        Args:
            role: 角色 ("user" 或 "assistant")
            content: 消息内容

        Returns:
            Message: 添加的消息对象
        """
        # 如果是用户消息，增加轮次
        if role == "user":
            self.current_round += 1

        message = Message(
            role=role,
            content=content,
            round_number=self.current_round,
        )

        self.messages.append(message)

        logger.debug(f"添加消息: role={role}, round={self.current_round}, length={len(content)}")

        return message

    def is_full(self) -> bool:
        """检查短期记忆是否已满"""
        # 计算完整的对话轮次数（一轮 = 一个 user + 一个 assistant）
        complete_rounds = sum(1 for msg in self.messages if msg.role == "user")
        return complete_rounds >= self.max_rounds

    def get_oldest_rounds(self, num_rounds: int = 3) -> list[Message]:
        """
        获取最老的 N 轮对话

        Args:
            num_rounds: 要获取的轮次数

        Returns:
            list[Message]: 消息列表
        """
        if not self.messages:
            return []

        # 找到最老的 N 轮的轮次编号
        round_numbers = sorted({msg.round_number for msg in self.messages})
        target_rounds = round_numbers[:num_rounds]

        # 提取这些轮次的所有消息
        oldest_messages = [msg for msg in self.messages if msg.round_number in target_rounds]

        return oldest_messages

    def remove_rounds(self, round_numbers: list[int]):
        """
        从短期记忆中移除指定轮次的消息

        Args:
            round_numbers: 要移除的轮次编号列表
        """
        before_count = len(self.messages)

        self.messages = [msg for msg in self.messages if msg.round_number not in round_numbers]

        removed_count = before_count - len(self.messages)
        logger.info(f"从短期记忆移除 {removed_count} 条消息")

    def get_all_messages(self) -> list[Message]:
        """获取所有消息"""
        return self.messages.copy()

    def get_round_count(self) -> int:
        """获取当前轮次数"""
        return len({msg.round_number for msg in self.messages if msg.role == "user"})


class LongTermMemory:
    """
    长期记忆

    管理历史对话的摘要，用于保持长期上下文
    """

    def __init__(self):
        """初始化长期记忆"""
        self.summaries: list[ConversationSummary] = []

        logger.info("LongTermMemory 初始化")

    def add_summary(self, summary: ConversationSummary):
        """
        添加摘要到长期记忆

        Args:
            summary: 对话摘要对象
        """
        self.summaries.append(summary)

        logger.info(f"添加摘要: rounds={summary.round_range}, facts={len(summary.key_facts)}")

    def get_all_summaries(self) -> list[ConversationSummary]:
        """获取所有摘要"""
        return self.summaries.copy()

    def get_summary_count(self) -> int:
        """获取摘要数量"""
        return len(self.summaries)


class MaterialStore:
    """
    素材库

    封装 RAGService，管理 BP 等素材的向量化存储和检索
    """

    def __init__(self, session_id: str):
        """
        初始化素材库

        Args:
            session_id: 会话 ID
        """
        self.session_id = session_id

        # 尝试初始化 RAG 服务，如果失败则设为 None
        try:
            self.rag_service = RAGService(session_id=session_id)
            logger.info(f"MaterialStore 初始化: session_id={session_id}")
        except Exception as e:
            logger.warning(f"⚠️ RAG 服务初始化失败，MaterialStore 将以降级模式运行: {e}")
            self.rag_service = None

    def add_material(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        添加素材到向量库

        Args:
            content: 素材内容
            metadata: 元数据（可选）

        Returns:
            list[str]: 文档 ID 列表
        """
        if self.rag_service is None:
            logger.warning("⚠️ RAG 服务不可用，跳过素材添加")
            return []

        # 将内容分块（简单按段落分割）
        chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]

        # 添加到 RAG
        metadatas = [metadata or {}] * len(chunks)
        ids = self.rag_service.add_chunks(chunks, metadatas)

        logger.info(f"添加素材: {len(chunks)} 个块")

        return ids

    def search_material(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[str]:
        """
        检索相关素材

        Args:
            query: 查询文本
            top_k: 返回最相关的 K 个结果

        Returns:
            list[str]: 相关素材文本列表
        """
        if self.rag_service is None:
            logger.warning("⚠️ RAG 服务不可用，返回空结果")
            return []

        results = self.rag_service.search(query, top_k=top_k)

        # 提取文本内容
        materials = [result.chunk for result in results]

        logger.debug(f"检索素材: query='{query[:50]}...', 返回 {len(materials)} 个结果")

        return materials

    def get_material_count(self) -> int:
        """获取素材数量"""
        if self.rag_service is None:
            return 0

        try:
            return self.rag_service.get_count()
        except Exception as e:
            logger.warning(f"⚠️ 获取素材数量失败: {e}")
            return 0
            return 0


class MemoryManager:
    """
    记忆管理器

    统一管理短期记忆、长期记忆和素材库，实现自动压缩机制
    """

    def __init__(
        self,
        session_id: str,
        max_short_term_rounds: int = 5,
        compress_rounds: int = 3,
        llm_client: Any | None = None,
    ):
        """
        初始化记忆管理器

        Args:
            session_id: 会话 ID
            max_short_term_rounds: 短期记忆最多保留的轮次数
            compress_rounds: 每次压缩时处理的轮次数
            llm_client: LLM 客户端（用于生成摘要）
        """
        self.session_id = session_id
        self.compress_rounds = compress_rounds
        self.llm_client = llm_client

        # 初始化三层记忆
        self.short_term = ShortTermMemory(max_rounds=max_short_term_rounds)
        self.long_term = LongTermMemory()
        self.material_store = MaterialStore(session_id=session_id)

        logger.info(
            f"MemoryManager 初始化: session_id={session_id}, "
            f"max_short_term_rounds={max_short_term_rounds}, "
            f"compress_rounds={compress_rounds}"
        )

    def add_user_message(self, content: str) -> Message:
        """
        添加用户消息

        Args:
            content: 消息内容

        Returns:
            Message: 添加的消息对象
        """
        # 先检查是否需要压缩（在添加新消息之前）
        if self.short_term.is_full():
            logger.info("🔥 短期记忆已满，触发自动压缩")
            self._compress_memory()

        # 添加消息
        message = self.short_term.add_message("user", content)

        return message

    def add_assistant_message(self, content: str) -> Message:
        """
        添加助手消息

        Args:
            content: 消息内容

        Returns:
            Message: 添加的消息对象
        """
        return self.short_term.add_message("assistant", content)

    def _compress_memory(self):
        """
        压缩短期记忆

        将最老的 N 轮对话生成摘要，移入长期记忆
        """
        try:
            # 获取最老的 N 轮对话
            oldest_messages = self.short_term.get_oldest_rounds(self.compress_rounds)

            if not oldest_messages:
                logger.warning("⚠️ 没有消息需要压缩")
                return

            # 生成摘要
            summary = self._generate_summary(oldest_messages)

            # 添加到长期记忆
            self.long_term.add_summary(summary)

            # 从短期记忆中移除
            round_numbers = list({msg.round_number for msg in oldest_messages})
            self.short_term.remove_rounds(round_numbers)

            logger.info(
                f"✅ 压缩完成: 处理 {len(oldest_messages)} 条消息, "
                f"生成 {len(summary.key_facts)} 个关键事实"
            )

        except Exception as e:
            logger.error(f"❌ 压缩失败: {e}", exc_info=True)

    def _generate_summary(self, messages: list[Message]) -> ConversationSummary:
        """
        生成对话摘要

        Args:
            messages: 消息列表

        Returns:
            ConversationSummary: 对话摘要对象
        """
        # 构建对话文本
        conversation_text = "\n\n".join(
            [f"{'用户' if msg.role == 'user' else '助手'}: {msg.content}" for msg in messages]
        )

        # 获取轮次范围
        round_numbers = [msg.round_number for msg in messages]
        round_range = (min(round_numbers), max(round_numbers))

        # 如果没有 LLM 客户端，使用改进的规则生成摘要
        if self.llm_client is None:
            logger.warning("⚠️ 未提供 LLM 客户端，使用改进规则生成摘要")

            # 🔥 改进的摘要生成：提取问答对
            qa_pairs = []
            current_question = None

            for msg in messages:
                if msg.role == "user":
                    current_question = msg.content
                elif msg.role == "assistant" and current_question:
                    # 截取问题和回答的关键部分
                    q_short = current_question[:80] + ("..." if len(current_question) > 80 else "")
                    a_short = msg.content[:120] + ("..." if len(msg.content) > 120 else "")
                    qa_pairs.append(f"Q: {q_short}\nA: {a_short}")
                    current_question = None

            # 生成摘要文本
            summary_text = f"第 {round_range[0]}-{round_range[1]} 轮对话涉及 {len(qa_pairs)} 个问答。\n" + "\n\n".join(qa_pairs[:3])  # 最多保留3个问答对

            # 🔥 改进的关键事实提取：提取助手回答中的关键信息
            key_facts = []
            for msg in messages:
                if msg.role == "assistant":
                    # 尝试提取数字、百分比、关键词
                    content = msg.content
                    # 简单规则：提取包含数字的句子
                    sentences = content.replace("。", ".").split(".")
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence and (any(char.isdigit() for char in sentence) or len(sentence) < 100):
                            if sentence not in key_facts:  # 去重
                                key_facts.append(sentence[:150])
                                if len(key_facts) >= 5:  # 最多5个关键事实
                                    break
                    if len(key_facts) >= 5:
                        break

            # 如果没有提取到关键事实，使用用户问题作为备选
            if not key_facts:
                key_facts = [
                    msg.content[:100] + ("..." if len(msg.content) > 100 else "")
                    for msg in messages
                    if msg.role == "user"
                ][:3]

            return ConversationSummary(
                summary=summary_text,
                key_facts=key_facts,
                round_range=round_range,
            )

        # 使用 LLM 生成摘要
        try:
            summary_text, key_facts = self._call_llm_for_summary(conversation_text)

            return ConversationSummary(
                summary=summary_text,
                key_facts=key_facts,
                round_range=round_range,
            )

        except Exception as e:
            logger.error(f"❌ LLM 生成摘要失败: {e}", exc_info=True)

            # 降级到简单规则
            summary_text = conversation_text[:200] + "..."
            key_facts = [
                msg.content[:100] + ("..." if len(msg.content) > 100 else "")
                for msg in messages
                if msg.role == "user"
            ]

            return ConversationSummary(
                summary=summary_text,
                key_facts=key_facts,
                round_range=round_range,
            )

    def _call_llm_for_summary(self, conversation_text: str) -> tuple[str, list[str]]:
        """
        调用 LLM 生成摘要
        
        🔥 根本性优化：生成极度压缩的摘要，使用 | 分隔关键事实

        Args:
            conversation_text: 对话文本

        Returns:
            tuple[str, list[str]]: (摘要文本, 关键事实列表)
        """
        # 🔥 优化 Prompt：要求极度压缩
        prompt = f"""请将以下投资人与创业者的对话压缩为极简摘要（不超过150字）：

{conversation_text}

要求：
1. 只提取最关键的 2-3 个事实
2. 保留具体数字和指标（如：35万用户、50ms延迟、ARR 500万）
3. 使用 | 分隔事实
4. 格式：事实1 | 事实2 | 事实3

示例：
讨论项目起源和核心功能音音保护音音分身 | 35万用户零推广增长 | 端侧部署50ms延迟4.5分自然度

直接输出摘要，不要其他内容："""

        # 调用 LLM
        response = self.llm_client.chat.completions.create(
            model="gpt-4o-mini",  # 使用较小的模型节省成本
            messages=[
                {"role": "system", "content": "你是一个专业的对话摘要助手，擅长提取关键信息并极度压缩。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=100,  # 🔥 限制输出长度
        )

        # 解析响应
        content = response.choices[0].message.content.strip()

        # 🔥 简化解析：直接使用 LLM 输出作为摘要
        summary_text = content[:150]  # 限制长度

        # 🔥 提取关键事实（按 | 分割）
        key_facts = [f.strip() for f in content.split("|") if f.strip()]
        
        # 限制关键事实数量
        key_facts = key_facts[:3]

        logger.debug(f"LLM 生成摘要: {len(summary_text)} 字符, {len(key_facts)} 个事实")

        return summary_text, key_facts

    def get_context_for_prompt(self, query: str) -> str:
        """
        获取用于 Prompt 的上下文

        包括：
        1. 长期记忆的摘要
        2. 短期记忆的完整对话
        3. 相关的素材（通过 RAG 检索）

        Args:
            query: 当前查询

        Returns:
            str: 格式化的上下文文本
        """
        context_parts = []

        # 1. 长期记忆摘要
        summaries = self.long_term.get_all_summaries()
        if summaries:
            context_parts.append("## 历史对话摘要\n")
            for i, summary in enumerate(summaries, 1):
                context_parts.append(
                    f"### 摘要 {i} (第 {summary.round_range[0]}-{summary.round_range[1]} 轮)\n"
                )
                context_parts.append(f"{summary.summary}\n")
                if summary.key_facts:
                    context_parts.append("关键事实：\n")
                    for fact in summary.key_facts:
                        context_parts.append(f"- {fact}\n")
                context_parts.append("\n")

        # 2. 短期记忆
        messages = self.short_term.get_all_messages()
        if messages:
            context_parts.append("## 最近对话\n")
            for msg in messages:
                role_name = "用户" if msg.role == "user" else "助手"
                context_parts.append(f"{role_name}: {msg.content}\n\n")

        # 3. 相关素材
        materials = self.material_store.search_material(query, top_k=3)
        if materials:
            context_parts.append("## 相关素材\n")
            for i, material in enumerate(materials, 1):
                context_parts.append(f"### 素材 {i}\n{material}\n\n")

        return "".join(context_parts)

    def get_stats(self) -> dict[str, Any]:
        """
        获取记忆统计信息

        Returns:
            dict: 统计信息
        """
        # 尝试获取素材数量，如果失败则返回 0
        try:
            material_count = self.material_store.get_material_count()
        except Exception as e:
            logger.warning(f"⚠️ 获取素材数量失败: {e}")
            material_count = 0

        return {
            "short_term_rounds": self.short_term.get_round_count(),
            "short_term_messages": len(self.short_term.messages),
            "long_term_summaries": self.long_term.get_summary_count(),
            "material_count": material_count,
        }
