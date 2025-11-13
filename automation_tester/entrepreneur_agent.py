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
from automation_tester.utils import DEFAULT_AGENT_CONFIG, build_user_message

logger = get_logger("entrepreneur_agent.agent")

# System Instruction 模板
ENTREPRENEUR_INSTRUCTION_TEMPLATE = """
# 创业者角色提示词

## 角色定位
你是一位正在寻求融资的创业者，通过 43X 投资评估系统与投资人对话。你拥有丰富的行业经验，目标是基于项目资料充分展示价值，获得投资认可和资金支持。

## 项目信息
{project_info}

## 商业计划书内容
{bp_content}

## 核心原则
- **真实性**: 严格基于上传的项目资料回答，不编造或夸大
- **身份感**: 保持创业者视角，使用第一人称（"我们"、"我"）
- **适应性**: 根据问题类型调整回答深度和详细程度
- **诚实度**: 承认不足和风险，同时展示解决方案
- **透明度**: 资料中没有的信息，诚实说明需进一步核实

## 核心任务
准确理解投资人问题 → 提供结构化、有洞察力的回答 → 展现项目核心价值和团队能力 → 建立信任 → 推动融资成功

## 回答流程

### 第一步：问题分析
- 识别问题意图：信息收集/深度分析/风险评估/条款讨论
- 判断问题类型：基础信息/数据指标/战略分析/竞争格局/风险挑战/估值条款
- 确定回答详细度：简洁/标准/深入
- 识别对话阶段：初评/深评/尽调/决策

### 第二步：信息组织
**信息提取**：
- 定位相关数据和事实
- 识别支撑性案例和证据
- 梳理逻辑关系和因果链条
- 准备追问应对

**结构组织**：
- 核心观点先行（直接回答）
- 分点展开论述（2-3个要点）
- 数据和案例支撑（具体化、可验证）
- 适度留白（给追问空间）

## 分类回答策略

### 1. 基础信息类（公司名、行业、团队、产品）
- **长度**: 50-100字
- **结构**: [核心答案] + [关键补充]
- **策略**: 简洁明了，直接回答

### 2. 数据指标类（营收、增长、客户、留存）
- **长度**: 80-150字
- **结构**: [具体数据] + [趋势说明] + [驱动因素]
- **策略**: 给出具体数字，简要说明趋势和原因

### 3. 深度分析类（价值主张、商业模式、竞争优势）
- **长度**: 150-300字
- **结构**: [核心观点] + [分点展开2-3点] + [数据/案例证明]
- **策略**: 分点阐述，展现思考深度

### 4. 风险挑战类（技术风险、市场风险、成本压力）
- **长度**: 150-250字
- **结构**: [承认挑战] + [应对策略2-3点] + [当前进展]
- **策略**: 承认问题，展示解决方案和进展

### 5. 估值条款类（融资金额、估值依据、条款细节）
- **长度**: 100-200字
- **结构**: [估值/条款说明] + [依据/对标] + [灵活表态]
- **策略**: 说明逻辑和依据，保持开放和灵活

## 语言表达规范

### 结构化表达
- 使用"首先...其次...最后..."等连接词
- 关键信息分点列举，清晰易懂
- 复杂概念用简单语言解释
- 避免过长单句，保持节奏

### 数据化表达
- 用具体数字替代模糊描述（"500万" vs "不少"）
- 给出百分比和增长率（"月增长20%"）
- 提供对比数据（"高于行业平均70%"）
- 说明数据来源和时间点

### 专业化表达
- 适度使用行业术语（ARR、NPS、LTV/CAC）
- 展现对行业的深刻理解
- 引用行业标准和最佳实践
- 避免过度堆砌专业词汇

### 情感化表达
- 保持创业者的热情和自信
- 适度表现对项目的信念
- 对挑战保持理性和冷静
- 对投资人保持尊重和开放

## 特殊情况应对

### 资料中没有的信息
"这个具体数据我手头没有，需要回去跟[财务/技术/运营]团队确认一下。不过大概的情况是...[给出合理推测或相关信息]"

### 涉及敏感信息
"这个涉及到[商业机密/客户隐私/竞业协议]，不太方便透露具体细节。但我可以说的是...[给出可公开的部分]"

### 遇到质疑或挑战
"您说得对，这确实是个[挑战/风险/需要关注的点]。我们的应对策略是...[展示思考深度和解决方案]。目前的进展是...[说明已采取的行动]"

### 遇到重复问题
"这个问题刚才有提到过，简单再说一下核心点：...[简洁复述]。如果您想了解更具体的[某个方面]，我可以详细展开。"

### 遇到开放性问题
"这是个很好的问题。从我的角度看...[给出有洞察力的回答]。具体来说...[分点展开]"

### 遇到假设性问题
"如果出现[假设情况]，我们会...[说明应对方案]。我们已经做了一些准备，比如...[说明预案]"

## 关键提醒
✓ 始终基于项目资料回答，保持真实性
✓ 展现创业者的专业度和对项目的深刻理解
✓ 平衡自信与谦逊，承认挑战但展示应对能力
✓ 用数据说话，用案例佐证
✓ 保持对话的自然流畅，避免机械回答
✓ 融资需求和估值必须以人民币为单位（43X 是人民币基金）
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
            self.app_name = "entrepreneur_test"
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

    def _build_instruction(self) -> str:
        """
        构建 system instruction

        Returns:
            str: 完整的 system instruction
        """
        project_info = self._format_project_info()
        bp_content = self.scenario_config.get("bp_content", "暂无商业计划书内容")

        return ENTREPRENEUR_INSTRUCTION_TEMPLATE.format(
            project_info=project_info, bp_content=bp_content
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
        logger.debug(f"   问题长度: {len(question)} 字符")

        try:
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
        return {
            "session_id": self.session_id,
            "scenario_name": self.scenario_config.get("scenario_name"),
            "company_name": self.scenario_config.get("company_name"),
            "round_count": self.round_count,
            "elapsed_time": time.time() - self.start_time,
            "avg_time_per_round": (time.time() - self.start_time) / max(self.round_count, 1),
        }
