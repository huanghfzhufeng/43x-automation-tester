"""
Entrepreneur Agent Definition

创业者 Agent 的定义和管理
"""

import json
import logging
import time
from typing import Any, Dict

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from automation_tester.config import Config
from automation_tester.prompts import build_entrepreneur_instruction
from automation_tester.services.local_storage import LocalFileStorage
from automation_tester.services.memory_manager import MemoryManager
from automation_tester.services.rag_service import RAGService
from automation_tester.utils import (
    format_project_info,
    build_memory_context,
    build_user_message,
)
from automation_tester.utils.text_chunker import ChunkingStrategy, TextChunker

logger = logging.getLogger(__name__)

# ============================================================================
# Agent 配置
# ============================================================================

agent_config = Config()

# ============================================================================
# Agent 创建函数
# ============================================================================

def create_entrepreneur_agent(
    scenario_config: Dict[str, Any],
    rag_service=None,
    memory_manager=None
) -> LlmAgent:
    """
    创建创业者 Agent（仅支持 RAG 模式）
    
    Args:
        scenario_config: 场景配置字典
        rag_service: RAG 服务实例（可选，但强烈推荐）
        memory_manager: 记忆管理器实例（可选）
        
    Returns:
        配置好的 LlmAgent 实例
        
    Note:
        如果未提供 rag_service，将使用简化的 BP 提示，
        建议始终提供 rag_service 以获得最佳性能
    """
    company_name = scenario_config.get("company_name", "本公司")
    project_info = format_project_info(scenario_config)
    
    # 统一使用 RAG 模式的 BP 内容提示
    bp_content = "（项目详细材料已向量化存储，将根据投资人问题动态检索相关内容）"
    
    if rag_service:
        logger.info("✅ 使用 RAG 模式（推荐）")
    else:
        logger.warning("⚠️ 未提供 RAG 服务，Agent 将无法访问详细项目资料")
    
    # 构建 instruction
    instruction = build_entrepreneur_instruction(
        company_name=company_name,
        project_info=project_info,
        bp_content=bp_content,
        include_memory=False,  # 初始不包含记忆
        memory_context=""
    )
    
    # 创建 Agent
    # 从配置中提取 LlmAgent 接受的参数
    agent_params = agent_config.entrepreneur
    model_config = {
        "model": agent_params.get("model"),
    }
    
    agent = LlmAgent(
        model=model_config["model"],
        name="entrepreneur",
        description=f"{company_name} 创始人",
        instruction=instruction,
        tools=[],  # 测试场景不需要工具
    )
    
    logger.info(f"✅ Agent 创建成功: {agent.name}")
    
    return agent


# ============================================================================
# Agent 管理器
# ============================================================================

class EntrepreneurAgentManager:
    """
    创业者 Agent 管理器
    
    职责：
    - 管理 Agent 生命周期
    - 协调 RAG、Memory、Storage 等服务
    - 处理对话流程
    """
    
    def __init__(
        self,
        scenario_config: Dict[str, Any],
        rag_config: Dict[str, Any] = None,
        memory_config: Dict[str, Any] = None,
        storage_config: Dict[str, Any] = None
    ):
        """
        初始化 Entrepreneur Agent Manager
        
        Args:
            scenario_config: 场景配置，包含公司信息、项目资料等
            rag_config: RAG 配置（可选）
            memory_config: 记忆管理配置（可选）
            storage_config: 存储配置（可选）
        """
        logger.info("=" * 80)
        logger.info("🎯 Agent Manager 初始化")
        
        self.scenario_config = scenario_config
        self.session_id = self._generate_session_id()
        self.app_name = "agents"
        self.user_id = "test_investor"
        self.round_count = 0
        self.start_time = time.time()
        
        # 🔥 配置管理：使用提供的配置或默认值
        self.rag_config = rag_config or {
            "chunk_size": 800,
            "chunk_overlap": 100,
            "persist_dir": "./chroma_db",
            "top_k": 3,
        }
        
        self.memory_config = memory_config or {
            "max_short_term_rounds": 8,
            "compress_rounds": 5,
        }
        
        self.storage_config = storage_config or {
            "base_dir": "./sessions",
        }
        
        logger.info(f"   Session ID: {self.session_id}")
        logger.info(f"   场景名称: {scenario_config.get('scenario_name', 'N/A')}")
        logger.info(f"   公司名称: {scenario_config.get('company_name', 'N/A')}")
        
        # 初始化服务（注意顺序：local_storage 必须在 memory_manager 之前）
        self.local_storage = self._initialize_local_storage()
        self.rag_service = self._initialize_rag_service()
        self.memory_manager = self._initialize_memory_manager()
        
        # 创建 Agent
        self.agent = create_entrepreneur_agent(
            scenario_config,
            rag_service=self.rag_service,
            memory_manager=self.memory_manager
        )
        
        # 创建 Runner（不使用自定义 session_service，让 Runner 自动管理）
        self.runner = Runner(
            app_name=self.app_name,
            agent=self.agent,
        )
        
        logger.debug(f"📝 Session ID: {self.session_id}")
        
        logger.info("✅ Agent Manager 初始化完成")
        logger.info("=" * 80)
    
    def _generate_session_id(self) -> str:
        """生成会话 ID（只包含安全字符）"""
        import re
        
        scenario_name = self.scenario_config.get('scenario_name', 'unknown')
        timestamp = int(time.time())
        
        logger.info(f"🔧 原始 scenario_name: {scenario_name}")
        
        # 清理 scenario_name，只保留字母、数字、下划线、连字符
        # 将中文和其他特殊字符替换为下划线
        safe_scenario_name = re.sub(r'[^a-zA-Z0-9_-]', '_', scenario_name)
        
        # 移除连续的下划线
        safe_scenario_name = re.sub(r'_+', '_', safe_scenario_name)
        
        # 限制长度（避免过长）
        if len(safe_scenario_name) > 50:
            safe_scenario_name = safe_scenario_name[:50]
        
        # 移除首尾的下划线
        safe_scenario_name = safe_scenario_name.strip('_')
        
        session_id = f"test_{safe_scenario_name}_{timestamp}"
        logger.info(f"✅ 生成安全 session_id: {session_id}")
        
        return session_id
    
    def _initialize_rag_service(self):
        """初始化 RAG 服务并将 BP 内容向量化（必需）"""
        try:
            bp_content = self.scenario_config.get("bp_content", "")
            
            if not bp_content or bp_content == "暂无商业计划书内容":
                logger.warning("⚠️ 没有 BP 内容，Agent 将无法访问详细项目资料")
                logger.warning("⚠️ 建议上传商业计划书或项目资料文件")
                return None
            
            logger.info("🔥 开始初始化 RAG 服务...")
            
            # 创建 RAG 服务
            rag_service = RAGService(
                session_id=self.session_id,
                persist_dir=self.rag_config["persist_dir"],
            )
            
            # 分块 BP 内容
            logger.info(f"📄 BP 内容长度: {len(bp_content)} 字符")
            
            chunk_config = TextChunker.create_config(
                strategy=ChunkingStrategy.RECURSIVE,
                chunk_size=self.rag_config["chunk_size"],
                chunk_overlap=self.rag_config["chunk_overlap"],
            )
            
            chunks = TextChunker.chunk_text_sync(bp_content, chunk_config)
            logger.info(f"✅ 文本分块完成: {len(chunks)} 个块")
            
            # 准备元数据
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadatas.append({
                    "session_id": self.session_id,
                    "company_name": self.scenario_config.get("company_name", "Unknown"),
                    "chunk_index": i,
                    "chunk_length": len(chunk),
                })
            
            # 存入向量数据库
            logger.info("🔄 正在向量化并存储到数据库...")
            ids = rag_service.add_chunks(chunks, metadatas)
            logger.info(f"✅ RAG 服务初始化完成: {len(ids)} 个文本块已存储")
            
            return rag_service
            
        except Exception as e:
            logger.error(f"❌ RAG 服务初始化失败: {e}", exc_info=True)
            logger.error("⚠️ Agent 将无法访问项目详细资料，可能影响回答质量")
            return None
    
    def _initialize_memory_manager(self):
        """初始化 MemoryManager（三层记忆管理）"""
        try:
            logger.info("🔥 初始化 MemoryManager...")
            
            # 获取 LLM 客户端用于生成摘要
            llm_client = self._get_llm_client_for_summary()
            
            # 创建 MemoryManager
            memory_manager = MemoryManager(
                session_id=self.session_id,
                max_short_term_rounds=self.memory_config["max_short_term_rounds"],
                compress_rounds=self.memory_config["compress_rounds"],
                llm_client=llm_client,
            )
            
            # 尝试从本地文件恢复记忆
            if self.local_storage:
                self._load_memory_from_file(memory_manager)
            
            logger.info("✅ MemoryManager 初始化完成")
            logger.info(f"   短期记忆阈值: 8 轮")
            logger.info(f"   压缩轮次: 5 轮")
            
            return memory_manager
            
        except Exception as e:
            logger.error(f"❌ MemoryManager 初始化失败: {e}", exc_info=True)
            logger.warning("⚠️ 将继续运行，但不会使用三层记忆管理")
            return None
    
    def _get_llm_client_for_summary(self):
        """获取用于生成摘要的 LLM 客户端"""
        try:
            from openai import OpenAI
            from automation_tester.config import LLMConfig
            
            client = OpenAI(
                api_key=LLMConfig.api_key,
                base_url=LLMConfig.base_url,
            )
            
            logger.info("✅ LLM 客户端已创建用于摘要生成")
            return client
            
        except Exception as e:
            logger.warning(f"⚠️ 无法创建 LLM 客户端: {e}")
            logger.warning("⚠️ 将使用简单规则生成摘要")
            return None
    
    def _initialize_local_storage(self):
        """初始化本地文件存储"""
        try:
            logger.info("🔥 初始化本地文件存储...")
            
            # 创建本地存储服务
            local_storage = LocalFileStorage(
                session_id=self.session_id,
                base_dir=self.storage_config["base_dir"],
            )
            
            # 保存会话元信息
            metadata = {
                "session_id": self.session_id,
                "scenario_name": self.scenario_config.get("scenario_name", "unknown"),
                "company_name": self.scenario_config.get("company_name", "unknown"),
                "created_at": time.time(),
            }
            local_storage.save_metadata(metadata)
            
            logger.info(f"✅ 本地文件存储初始化完成: {local_storage.session_dir}")
            
            return local_storage
            
        except Exception as e:
            logger.error(f"❌ 本地文件存储初始化失败: {e}", exc_info=True)
            logger.warning("⚠️ 将继续运行，但不会持久化数据")
            return None
    
    def _load_memory_from_file(self, memory_manager):
        """从本地文件恢复记忆"""
        if not self.local_storage:
            logger.debug("⚠️ 本地存储未初始化，跳过记忆恢复")
            return
        
        try:
            import os
            
            summary_file = os.path.join(self.local_storage.session_dir, "summary.json")
            
            if not os.path.exists(summary_file):
                logger.debug("📝 没有找到历史记忆文件，从头开始")
                return
            
            # 读取摘要文件
            with open(summary_file, encoding="utf-8") as f:
                data = json.load(f)
            
            # 恢复长期记忆
            from automation_tester.services.memory_manager import ConversationSummary, Message
            
            for summary_data in data.get("long_term_summaries", []):
                summary = ConversationSummary(
                    summary=summary_data["summary"],
                    key_facts=summary_data["key_facts"],
                    round_range=tuple(summary_data["round_range"]),
                    timestamp=summary_data["timestamp"],
                )
                memory_manager.long_term.add_summary(summary)
            
            # 恢复短期记忆
            for msg_data in data.get("short_term_messages", []):
                message = Message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=msg_data["timestamp"],
                    round_number=msg_data["round_number"],
                )
                memory_manager.short_term.messages.append(message)
            
            # 恢复当前轮次
            memory_manager.short_term.current_round = data.get("current_round", 0)
            
            logger.info(
                f"✅ 记忆恢复完成: "
                f"{len(memory_manager.long_term.summaries)} 个摘要, "
                f"{len(memory_manager.short_term.messages)} 条短期消息"
            )
            
        except Exception as e:
            logger.warning(f"⚠️ 记忆恢复失败: {e}", exc_info=True)
    
    def _save_memory_to_file(self):
        """保存记忆到本地文件（summary.json）"""
        if not self.local_storage or not self.memory_manager:
            return
        
        try:
            import os
            
            summary_file = os.path.join(self.local_storage.session_dir, "summary.json")
            
            # 构建数据结构
            data = {
                "session_id": self.session_id,
                "current_round": self.memory_manager.short_term.current_round,
                "long_term_summaries": [
                    {
                        "summary": s.summary,
                        "key_facts": s.key_facts,
                        "round_range": list(s.round_range),
                        "timestamp": s.timestamp,
                    }
                    for s in self.memory_manager.long_term.summaries
                ],
                "short_term_messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp,
                        "round_number": m.round_number,
                    }
                    for m in self.memory_manager.short_term.messages
                ],
                "updated_at": time.time(),
            }
            
            # 写入文件
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ 记忆已保存到 {summary_file}")
            
        except Exception as e:
            logger.warning(f"⚠️ 记忆保存失败: {e}", exc_info=True)
    

    async def answer(self, question: str) -> str:
        """
        回答投资人的问题
        
        Args:
            question: 投资人的问题
            
        Returns:
            str: 创业者的回答
        """
        self.round_count += 1
        round_start = time.time()
        
        logger.info(f"📝 [Round {self.round_count}] 收到问题")
        logger.info(f"   问题内容: {question}")
        logger.debug(f"   问题长度: {len(question)} 字符")
        
        try:
            # 使用 MemoryManager 管理记忆
            if self.memory_manager:
                self.memory_manager.add_user_message(question)
                logger.debug("✅ 用户消息已添加到 MemoryManager")
            
            # 🔥 核心修复：使用 RAG 检索相关内容
            rag_context = ""
            if self.rag_service:
                try:
                    rag_start = time.time()
                    # 检索与问题相关的内容
                    results = self.rag_service.search(question, top_k=self.rag_config["top_k"])
                    rag_elapsed = time.time() - rag_start
                    
                    if results:
                        # 构建 RAG 上下文
                        # RagChunk 是 dataclass，使用 .chunk 属性访问内容
                        rag_chunks = [result.chunk for result in results]
                        rag_context = "\n\n## 📚 相关项目资料\n\n" + "\n\n---\n\n".join(rag_chunks)
                        logger.info(f"🔍 RAG 检索完成: {len(results)} 个相关片段 ({rag_elapsed:.2f}s)")
                    else:
                        logger.warning("⚠️ RAG 检索未找到相关内容")
                except Exception as e:
                    logger.warning(f"⚠️ RAG 检索失败: {e}")
            
            # 构建完整的 BP 内容（包含 RAG 检索结果）
            bp_content_with_rag = "（项目详细材料已向量化存储，将根据投资人问题动态检索相关内容）"
            if rag_context:
                bp_content_with_rag += rag_context
            
            # 每次调用前更新 Agent 的 instruction，注入长期记忆和 RAG 内容
            memory_context = ""
            if self.memory_manager and self.memory_manager.long_term.get_summary_count() > 0:
                memory_context = build_memory_context(self.memory_manager)
            
            updated_instruction = build_entrepreneur_instruction(
                company_name=self.scenario_config.get("company_name", "本公司"),
                project_info=format_project_info(self.scenario_config),
                bp_content=bp_content_with_rag,  # 🔥 注入 RAG 检索结果
                include_memory=bool(memory_context),
                memory_context=memory_context
            )
            self.agent.instruction = updated_instruction
            
            if memory_context:
                logger.info(f"🔄 已更新 Agent Instruction（包含 {self.memory_manager.long_term.get_summary_count()} 个长期记忆摘要）")
            
            # 使用 Runner 处理消息
            answer = ""
            llm_start = time.time()
            
            # 使用 Runner 处理消息
            # Runner 会自动管理 session，如果不存在会自动创建
            async for event in self.runner.run_async(
                user_id=self.user_id,
                session_id=self.session_id,
                new_message=build_user_message(question),
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        answer = event.content.parts[0].text or ""
                    break
            
            llm_elapsed = time.time() - llm_start
            elapsed = time.time() - round_start
            
            logger.info(f"✅ [Round {self.round_count}] 回答生成成功")
            logger.info(f"   LLM 耗时: {llm_elapsed:.2f}s")
            logger.info(f"   总耗时: {elapsed:.2f}s")
            
            # 使用 MemoryManager 管理记忆
            if self.memory_manager:
                self.memory_manager.add_assistant_message(answer)
                logger.debug("✅ 助手回答已添加到 MemoryManager")
                self._save_memory_to_file()
            
            # 持久化对话到本地文件
            if self.local_storage:
                try:
                    self.local_storage.append_event({
                        "role": "user",
                        "content": question,
                        "round": self.round_count,
                    })
                    
                    self.local_storage.append_event({
                        "role": "entrepreneur",
                        "content": answer,
                        "round": self.round_count,
                    })
                    
                    self.local_storage.save_state({
                        "round_count": self.round_count,
                        "total_elapsed_time": time.time() - self.start_time,
                        "scenario_config": self.scenario_config,
                    })
                    
                    logger.debug(f"✅ 第 {self.round_count} 轮对话已持久化")
                except Exception as e:
                    logger.warning(f"⚠️ 持久化失败: {e}")
            
            return answer
            
        except Exception as e:
            logger.error(f"❌ [Round {self.round_count}] 生成回答失败", exc_info=True)
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {str(e)}")
            
            # 🔥 降级方案：根据轮次决定是否抛出异常
            if self.round_count == 1:
                # 第一轮失败，无法继续，抛出异常
                logger.error("❌ 第一轮对话失败，无法继续")
                raise
            else:
                # 非第一轮，返回友好的错误提示
                error_message = (
                    f"抱歉，我在处理您的问题时遇到了技术问题。"
                    f"错误类型：{type(e).__name__}。"
                    f"请稍后重试，或者换一个问题。"
                )
                logger.warning(f"⚠️ 返回降级响应: {error_message}")
                return error_message
    
    def close(self):
        """清理资源"""
        logger.info("🧹 清理 Agent Manager 资源...")
        
        # 保存最终状态
        if self.memory_manager:
            try:
                self._save_memory_to_file()
                logger.debug("✅ 记忆已保存")
            except Exception as e:
                logger.warning(f"⚠️ 保存记忆失败: {e}")
        
        # 关闭 RAG 服务
        if self.rag_service:
            try:
                if hasattr(self.rag_service, 'close'):
                    self.rag_service.close()
                    logger.debug("✅ RAG 服务已关闭")
            except Exception as e:
                logger.warning(f"⚠️ 关闭 RAG 服务失败: {e}")
        
        logger.info("✅ 资源清理完成")
    
    def __enter__(self):
        """支持上下文管理器"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时自动清理"""
        self.close()
        return False
    
    async def __aenter__(self):
        """支持异步上下文管理器"""
        # Runner 会自动创建 session，无需手动初始化
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步退出时清理"""
        self.close()
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            dict: 包含 session_id、轮次、耗时等统计信息
        """
        stats = {
            "session_id": self.session_id,
            "scenario_name": self.scenario_config.get("scenario_name"),
            "company_name": self.scenario_config.get("company_name"),
            "round_count": self.round_count,
            "elapsed_time": time.time() - self.start_time,
            "avg_time_per_round": (time.time() - self.start_time) / max(self.round_count, 1),
        }
        
        # 添加简化的记忆统计信息
        if self.memory_manager:
            try:
                memory_stats = self.memory_manager.get_stats()
                # 只保留关键指标
                stats["memory"] = {
                    "short_term_messages": memory_stats.get("short_term_messages", 0),
                    "long_term_summaries": memory_stats.get("long_term_summaries", 0),
                }
            except Exception as e:
                logger.debug(f"⚠️ 获取记忆统计信息失败: {e}")
                # 失败时不添加 memory 字段
        
        return stats