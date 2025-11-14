"""
Entrepreneur Agent

基于 Google ADK 实现的创业者 Agent，用于模拟真实创业者与投资 Agent 对话。
"""

import json
import logging
import time
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from automation_tester.config import LLMConfig
from automation_tester.logging_config import (
    LogContext,
    get_logger,
    log_llm_call,
    log_qa_interaction,
)
from automation_tester.services.local_storage import LocalFileStorage
from automation_tester.services.memory_manager import MemoryManager
from automation_tester.services.rag_service import RAGService
from automation_tester.utils import DEFAULT_AGENT_CONFIG, build_user_message
from automation_tester.utils.text_chunker import ChunkingStrategy, TextChunker

logger = get_logger("entrepreneur_agent.agent")

# System Instruction 模板
ENTREPRENEUR_INSTRUCTION_TEMPLATE = """
## Role 角色
你是 {company_name} 的创始人，正在通过 43X.AI 投资评估系统与投资人（孙悟空）进行初步访谈。

你的核心任务是：基于项目资料，以自然、真诚的方式回答投资人的问题，展示项目价值，建立信任。

## 项目信息
{project_info}

## 商业计划书内容
{bp_content}

## Core Principle 核心原则

### 1. 单一回应单元 (Single Response Unit)
这是你必须严格遵守的输出规则。你的每一次回复都必须是一个完整、简洁的回答。

**结构**：
- 直接回答投资人的核心问题
- 给出1-2个关键数据或事实支撑
- 不要分点罗列超过3个要点
- 不要使用"首先...其次...最后..."的结构

**长度控制**：
- 基础信息：30-60字
- 数据指标：50-100字
- 深度分析：80-150字（最多不超过200字）

**禁止**：
- ✗ 开头说"感谢您的认可"、"这是个好问题"
- ✗ 分点罗列超过3个要点
- ✗ 每个点都展开成段落
- ✗ 讲投资人没问的内容
- ✗ 使用"首先...其次...再次...最后..."的结构

### 2. 对话上下文感知
在回答前，先检查：
- 投资人是否在追问同一个问题？
- 投资人是否对上轮回答不满意？

如果是追问/重复问题：
- 立即直接回答核心问题，不要再绕弯
- 长度：50-80字
- 示例："核心差异是私有化部署能力，竞品都是SaaS模式，大客户不接受。我们已交付15套，行业最快。"

### 3. 自然对话风格
你是在和投资人聊天，不是在写商业计划书。

**真实创业者的语气**：
- ✓ "确实，这是个挑战"
- ✓ "这块我们还在摸索"
- ✓ "数据不算特别好看，但趋势在改善"
- ✓ "这个我需要回去确认一下"

**避免的"官话"**：
- ✗ "感谢您的认可和关注"
- ✗ "我们战略前瞻，布局第二增长曲线"
- ✗ "我们团队具备深厚的行业积累"
- ✗ "我们致力于为客户创造价值"

### 4. 数据化、具体化
用具体数字，不要用模糊描述：
- ✓ "ARR 500万，月增15%"（不是"营收表现良好"）
- ✓ "付费客户80家"（不是"客户数量稳步增长"）
- ✓ "获客成本8000元"（不是"获客效率较高"）
- ✓ "核心差异是私有化部署"（不是"我们有独特的技术优势"）

## 回答策略

### 基础信息类（公司、产品、团队）
**长度**：30-60字
**示例**："我们是做企业级AI客服SaaS的，主要服务电商和金融行业。"

### 数据指标类（营收、增长、客户）
**长度**：50-100字
**示例**："ARR 500万，月增15%，主要来自续费和老客户增购。付费客户80家，平均客单价6万/年。"

### 差异化/竞争优势类
**长度**：60-120字
**示例**："核心差异是私有化部署能力，竞品都是SaaS模式，大客户不接受。我们已经交付15套私有化系统，平均部署周期2周，行业最快。"

### 商业模式/获客策略类
**长度**：80-150字
**示例**："主要靠行业会议和老客户转介绍。去年参加8场行业峰会，转化率12%，获客成本8000元。转介绍占40%，成本几乎为零。"

### 风险挑战类
**长度**：80-150字
**示例**："确实，大客户销售周期长是个挑战，平均6个月。我们的应对是：1）标准化POC流程，缩短到3个月；2）先做中小客户跑现金流。目前中小客户占比60%，现金流为正。"

## 特殊情况应对

### 投资人连续追问同一问题
**信号**：投资人第2次、第3次问同样的问题
**原因**：你前几次都没回答到点上
**策略**：
1. 立即停止绕弯
2. 用最简单的语言，一句话回答核心问题
3. 给出具体数据或事实
4. 不要再扩散到其他话题

**示例**：
- 投资人（第3次问）："你们的产品差异化到底是什么？"
- 你："私有化部署能力。竞品都是SaaS，大客户不接受。我们已交付15套，行业最快。"（50字，直击要害）

### 资料中没有的信息
"这个数据我手头没有，需要确认。大概是[合理推测]。"（不要长篇解释为什么没有）

### 涉及敏感信息
"这个涉及商业机密，不方便透露。但可以说[可公开部分]。"（不要解释为什么敏感）

### 遇到质疑
"您说得对，这确实是风险。我们的应对是[具体方案]，目前[进展]。"（不要防御性解释）

## 关键提醒（每次回答前必读）
✓ 第一句话必须直接回答核心问题
✓ 控制回答长度，避免"白皮书式"输出
✓ 用具体数字，不要用模糊描述
✓ 不要讲投资人没问的内容
✓ 不要客套话、官话、套话
✓ 融资需求和估值必须以人民币为单位（43X是人民币基金）
"""


class EntrepreneurAgent:
    """
    创业者 Agent

    基于 Google ADK LlmAgent 实现，模拟真实创业者行为。
    维护完整的对话历史，确保回答的连贯性和一致性。
    """

    def __init__(self, scenario_config: dict[str, Any]):
        """
        初始化 Entrepreneur Agent

        Args:
            scenario_config: 场景配置，包含公司信息、项目资料等
        """
        with LogContext(logger, "初始化 Entrepreneur Agent"):
            self.scenario_config = scenario_config
            self.session_id = (
                f"test_{scenario_config.get('scenario_name', 'unknown')}_{int(time.time())}"
            )
            self.session_service = InMemorySessionService()
            self.app_name = "agents"
            self.user_id = "test_investor"
            self.round_count = 0
            self.start_time = time.time()

            logger.info("=" * 80)
            logger.info("🎯 Agent 初始化信息")
            logger.info(f"   Session ID: {self.session_id}")
            logger.info(f"   场景名称: {scenario_config.get('scenario_name', 'N/A')}")
            logger.info(f"   公司名称: {scenario_config.get('company_name', 'N/A')}")
            logger.info(f"   行业: {scenario_config.get('industry', 'N/A')}")
            logger.info(f"   产品: {scenario_config.get('product', 'N/A')}")
            logger.info(f"   营收: {scenario_config.get('revenue', 'N/A')}")
            logger.info(f"   团队: {scenario_config.get('team', 'N/A')}")
            logger.info(f"   融资需求: {scenario_config.get('funding_need', 'N/A')}")
            logger.info(f"   预期结果: {scenario_config.get('expected_result', 'N/A')}")

            # 🔥 先初始化 RAG 服务（在构建 instruction 之前）
            self.rag_service = None
            self._initialize_rag_service()

            # 构建 system instruction
            instruction = self._build_instruction()
            logger.debug(f"   System Instruction 长度: {len(instruction)} 字符")

            # 输出完整的 System Instruction（仅在 DEBUG 模式）
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=" * 80)
                logger.debug("📋 完整 System Instruction:")
                logger.debug("-" * 80)
                logger.debug(instruction)
                logger.debug("=" * 80)

            # 创建 Google ADK Agent
            self.agent = LlmAgent(
                **DEFAULT_AGENT_CONFIG,
                name="entrepreneur",
                description=f"{scenario_config.get('company_name', 'Unknown')} 创始人",
                instruction=instruction,
                tools=[],  # 测试场景不需要工具
            )

            logger.info("✅ Agent 创建成功")
            logger.info(f"   LLM Model: {LLMConfig.model}")
            logger.info("=" * 80)

            # 预创建 Runner（不在构造函数内执行异步操作）
            self.runner = Runner(
                app_name=self.app_name,
                agent=self.agent,
                session_service=self.session_service,
            )
            
            # 🔥 初始化本地文件存储
            self.local_storage = None
            self._initialize_local_storage()
            
            # 🔥 初始化 MemoryManager
            self.memory_manager = None
            self._initialize_memory_manager()

    def _build_instruction(self) -> str:
        """
        构建 system instruction
        
        🔥 优化版本：移除完整 BP 内容，使用 RAG 动态检索
        只保留角色定义和行为规则，大幅减少 token 消耗

        Returns:
            str: 完整的 system instruction
        """
        project_info = self._format_project_info()
        company_name = self.scenario_config.get("company_name", "本公司")
        
        # 🔥 关键优化：如果 RAG 服务已初始化，则不包含完整 BP 内容
        if self.rag_service:
            bp_content = (
                "（项目详细材料已向量化存储，将根据投资人问题动态检索相关内容）"
            )
            logger.info("✅ 使用瘦身版 System Instruction（RAG 模式）")
        else:
            # 降级：如果 RAG 未初始化，使用完整 BP 内容
            bp_content = self.scenario_config.get("bp_content", "暂无商业计划书内容")
            logger.info("⚠️ 使用完整版 System Instruction（传统模式）")

        return ENTREPRENEUR_INSTRUCTION_TEMPLATE.format(
            company_name=company_name,
            project_info=project_info,
            bp_content=bp_content
        )

    def _format_project_info(self) -> str:
        """
        格式化项目信息为文本

        Returns:
            str: 格式化后的项目信息
        """
        config = self.scenario_config
        info_parts = []

        # 基础信息
        if "company_name" in config:
            info_parts.append(f"- 公司名称：{config['company_name']}")
        if "industry" in config:
            info_parts.append(f"- 行业：{config['industry']}")
        if "product" in config:
            info_parts.append(f"- 产品：{config['product']}")
        if "revenue" in config:
            info_parts.append(f"- 营收：{config['revenue']}")
        if "team" in config:
            info_parts.append(f"- 团队：{config['team']}")
        if "funding_need" in config:
            info_parts.append(f"- 融资需求：{config['funding_need']}")

        # 详细信息
        if config.get("project_details"):
            details = config["project_details"]
            info_parts.append("\n## 详细信息")
            info_parts.append(json.dumps(details, ensure_ascii=False, indent=2))

        return "\n".join(info_parts)
    
    def _initialize_rag_service(self):
        """
        初始化 RAG 服务并将 BP 内容向量化
        """
        try:
            bp_content = self.scenario_config.get("bp_content", "")
            
            if not bp_content or bp_content == "暂无商业计划书内容":
                logger.info("⚠️ 没有 BP 内容，跳过 RAG 初始化")
                return
            
            logger.info("🔥 开始初始化 RAG 服务...")
            
            # 创建 RAG 服务
            self.rag_service = RAGService(
                session_id=self.session_id,
                persist_dir="./chroma_db",
            )
            
            # 分块 BP 内容
            logger.info(f"📄 BP 内容长度: {len(bp_content)} 字符")
            
            chunk_config = TextChunker.create_config(
                strategy=ChunkingStrategy.RECURSIVE,
                chunk_size=800,  # 每块 800 字符
                chunk_overlap=100,  # 重叠 100 字符
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
            ids = self.rag_service.add_chunks(chunks, metadatas)
            logger.info(f"✅ RAG 服务初始化完成: {len(ids)} 个文本块已存储")
            
        except Exception as e:
            logger.error(f"❌ RAG 服务初始化失败: {e}", exc_info=True)
            logger.warning("⚠️ 将继续使用传统方式（完整 BP 内容）")
            self.rag_service = None
    
    def _initialize_local_storage(self):
        """
        初始化本地文件存储
        """
        try:
            logger.info("🔥 初始化本地文件存储...")
            
            # 创建本地存储服务
            self.local_storage = LocalFileStorage(
                session_id=self.session_id,
                base_dir="./sessions",
            )
            
            # 保存会话元信息
            metadata = {
                "session_id": self.session_id,
                "scenario_name": self.scenario_config.get("scenario_name", "unknown"),
                "company_name": self.scenario_config.get("company_name", "unknown"),
                "created_at": time.time(),
            }
            self.local_storage.save_metadata(metadata)
            
            logger.info(f"✅ 本地文件存储初始化完成: {self.local_storage.session_dir}")
            
        except Exception as e:
            logger.error(f"❌ 本地文件存储初始化失败: {e}", exc_info=True)
            logger.warning("⚠️ 将继续运行，但不会持久化数据")
            self.local_storage = None
    
    def _initialize_memory_manager(self):
        """
        初始化 MemoryManager（三层记忆管理）
        """
        try:
            logger.info("🔥 初始化 MemoryManager...")
            
            # 创建 MemoryManager
            # 注意：这里不传入 llm_client，使用简单规则生成摘要
            # 如果需要使用 LLM 生成摘要，可以传入 OpenAI client
            self.memory_manager = MemoryManager(
                session_id=self.session_id,
                max_short_term_rounds=5,  # 短期记忆保留 5 轮
                compress_rounds=3,  # 每次压缩 3 轮
                llm_client=None,  # 暂不使用 LLM 生成摘要
            )
            
            # 尝试从本地文件恢复记忆
            self._load_memory_from_file()
            
            logger.info("✅ MemoryManager 初始化完成")
            
        except Exception as e:
            logger.error(f"❌ MemoryManager 初始化失败: {e}", exc_info=True)
            logger.warning("⚠️ 将继续运行，但不会使用三层记忆管理")
            self.memory_manager = None
    
    def _load_memory_from_file(self):
        """
        从本地文件恢复记忆
        """
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
            import json
            with open(summary_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 恢复长期记忆
            from automation_tester.services.memory_manager import ConversationSummary
            
            for summary_data in data.get("long_term_summaries", []):
                summary = ConversationSummary(
                    summary=summary_data["summary"],
                    key_facts=summary_data["key_facts"],
                    round_range=tuple(summary_data["round_range"]),
                    timestamp=summary_data["timestamp"],
                )
                self.memory_manager.long_term.add_summary(summary)
            
            # 恢复短期记忆
            from automation_tester.services.memory_manager import Message
            
            for msg_data in data.get("short_term_messages", []):
                message = Message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=msg_data["timestamp"],
                    round_number=msg_data["round_number"],
                )
                self.memory_manager.short_term.messages.append(message)
            
            # 恢复当前轮次
            self.memory_manager.short_term.current_round = data.get("current_round", 0)
            
            logger.info(
                f"✅ 记忆恢复完成: "
                f"{len(self.memory_manager.long_term.summaries)} 个摘要, "
                f"{len(self.memory_manager.short_term.messages)} 条短期消息"
            )
            
        except Exception as e:
            logger.warning(f"⚠️ 记忆恢复失败: {e}", exc_info=True)
    
    def _save_memory_to_file(self):
        """
        保存记忆到本地文件（summary.json）
        """
        if not self.local_storage or not self.memory_manager:
            return
        
        try:
            import os
            import json
            
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

    async def ensure_session(self):
        """
        确保会话已创建并可复用（在服务端启动时调用）。
        """
        try:
            existing = None
            try:
                existing = await self.runner.session_service.get_session(
                    app_name=self.runner.app_name,
                    user_id=self.user_id,
                    session_id=self.session_id,
                )
            except Exception:
                existing = None

            if not existing:
                await self.runner.session_service.create_session(
                    app_name=self.runner.app_name,
                    user_id=self.user_id,
                    session_id=self.session_id,
                    state={
                        "user_id": self.user_id,
                        "conversation_id": self.session_id,
                        "scenario_name": self.scenario_config.get("scenario_name"),
                        "company_name": self.scenario_config.get("company_name"),
                        "stage": "entrepreneur_interview",
                        # 注意：不存储 rag_service 和 memory_manager，因为它们包含不可序列化的对象
                        # 这些对象作为 Agent 实例变量管理，通过 before_model_callback 访问
                    },
                )
            
            logger.debug("🧰 会话已初始化并可复用")
        except Exception:
            logger.warning("⚠️ 会话初始化失败，将在首轮时按需创建", exc_info=True)

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
        logger.info(f"   问题内容: {question}")  # 打印完整问题
        logger.debug(f"   问题长度: {len(question)} 字符")

        try:
            # 🔥 使用 MemoryManager 管理记忆
            if self.memory_manager:
                # 添加用户消息到记忆
                self.memory_manager.add_user_message(question)
                logger.debug(f"✅ 用户消息已添加到 MemoryManager")
            
            # 使用复用的 Runner 处理消息（更稳健、对齐深评端）
            with LogContext(logger, f"LLM API 调用 - Round {self.round_count}", logging.DEBUG):
                answer = ""
                llm_start = time.time()

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

                # 记录 LLM API 调用信息
                log_llm_call(logger, model=LLMConfig.model, elapsed_time=llm_elapsed)

            elapsed = time.time() - round_start

            # 记录问答交互
            log_qa_interaction(
                logger,
                round_number=self.round_count,
                question=question,
                answer=answer,
                elapsed_time=elapsed,
            )
            
            # 🔥 使用 MemoryManager 管理记忆
            if self.memory_manager:
                # 添加助手回答到记忆
                self.memory_manager.add_assistant_message(answer)
                logger.debug(f"✅ 助手回答已添加到 MemoryManager")
                
                # 保存记忆到文件
                self._save_memory_to_file()
            
            # 🔥 持久化对话到本地文件
            if self.local_storage:
                try:
                    # 保存用户问题
                    self.local_storage.append_event({
                        "role": "user",
                        "content": question,
                        "round": self.round_count,
                    })
                    
                    # 保存 Agent 回答
                    self.local_storage.append_event({
                        "role": "entrepreneur",
                        "content": answer,
                        "round": self.round_count,
                    })
                    
                    # 保存当前状态
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
            logger.error(f"   错误信息: {e!s}")
            raise

    def get_stats(self) -> dict[str, Any]:
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
        
        # 添加记忆统计信息
        if self.memory_manager:
            try:
                stats["memory"] = self.memory_manager.get_stats()
            except Exception as e:
                logger.warning(f"⚠️ 获取记忆统计信息失败: {e}")
                stats["memory"] = {
                    "error": str(e),
                    "short_term_rounds": 0,
                    "short_term_messages": 0,
                    "long_term_summaries": 0,
                    "material_count": 0,
                }
        
        return stats
