"""
43X Entrepreneur Agent Service

FastAPI 服务，提供创业者 Agent 的 HTTP API 接口。
用于 Chrome 插件调用，模拟创业者与投资 Agent 对话。
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from automation_tester.config import AppConfig, LLMConfig
from automation_tester.logging_config import LogContext, get_logger, setup_logging

# 初始化日志系统
setup_logging()
logger = get_logger("entrepreneur_agent.service")


# 过滤 uvicorn 的访问日志中针对 /health 的记录，避免日志过于冗长
class _HealthAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(getattr(record, "msg", ""))
        # 仅当不是 /health 请求时才记录
        return "/health" not in msg


logging.getLogger("uvicorn.access").addFilter(_HealthAccessFilter())

# 创建 FastAPI 应用
app = FastAPI(
    title="43X Entrepreneur Agent Service",
    description="模拟创业者 Agent 的 HTTP API 服务",
    version="1.0.0",
)

# 配置 CORS - 允许所有来源（包括 Chrome 插件）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，包括 chrome-extension://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态：存储活跃的 Agent 实例
active_agents: dict[str, Any] = {}

# ============================================================================
# 异常处理
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误，返回详细信息"""
    body = await request.body()
    body_str = body.decode("utf-8", errors="replace")

    logger.error("=" * 60)
    logger.error("❌ 请求验证失败 (422)")
    logger.error(f"   URL: {request.url}")
    logger.error(f"   Method: {request.method}")
    logger.error(f"   错误详情: {exc.errors()}")
    logger.error(f"   请求体: {body_str}")
    logger.error("=" * 60)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body_str},
    )


# ============================================================================
# 数据模型
# ============================================================================


class StartTestRequest(BaseModel):
    """启动测试请求"""

    scenario_config: dict[str, Any]
    files_content: dict[str, str] | None = None


class StartTestResponse(BaseModel):
    """启动测试响应"""

    session_id: str
    scenario_name: str
    company_name: str


class AnswerRequest(BaseModel):
    """获取回答请求"""

    session_id: str
    question: str


class AnswerResponse(BaseModel):
    """获取回答响应"""

    answer: str
    round_number: int
    elapsed_time: float


class StopTestRequest(BaseModel):
    """停止测试请求"""

    session_id: str


# ============================================================================
# API 端点
# ============================================================================


@app.post("/api/test/start", response_model=StartTestResponse)
async def start_test(request: StartTestRequest):
    """
    启动测试，创建 Entrepreneur Agent 实例

    请求格式:
    {
        "scenario_config": {
            "scenario_name": "必填",
            "company_name": "必填",
            ...其他字段
        },
        "files_content": {
            "filename.txt": "文件内容字符串",
            ...
        } 或 null
    }

    Args:
        request: 包含场景配置和文件内容的请求

    Returns:
        StartTestResponse: 包含 session_id 和场景信息
    """
    scenario_name = request.scenario_config.get("scenario_name", "unknown")
    company_name = request.scenario_config.get("company_name", "unknown")

    with LogContext(logger, f"启动测试 - {scenario_name}"):
        try:
            logger.info("🚀 收到启动测试请求")
            logger.info(f"   场景名称: {scenario_name}")
            logger.info(f"   公司名称: {company_name}")
            logger.info(f"   行业: {request.scenario_config.get('industry', 'N/A')}")

            # 合并文件内容到场景配置
            if request.files_content:
                logger.info(f"   上传文件数: {len(request.files_content)}")
                for filename in request.files_content:
                    logger.info(f"     - {filename}")

                # 将上传的文件内容添加到配置中
                bp_content_parts = []
                for filename, content in request.files_content.items():
                    # 限制每个文件的长度，避免超过 token 限制
                    max_chars = 50000  # 约 12,500 tokens
                    if len(content) > max_chars:
                        logger.warning(
                            f"   文件 [{filename}] 过长 ({len(content)} 字符)，截取前 {max_chars} 字符"
                        )
                        content = content[:max_chars] + "\n\n[... 内容过长，已截断 ...]"

                    bp_content_parts.append(f"## 文件: {filename}\n\n{content}")
                    logger.info(f"   文件内容长度 [{filename}]: {len(content)} 字符")

                request.scenario_config["bp_content"] = "\n\n".join(bp_content_parts)
            else:
                logger.info("   上传文件数: 0")

            # 创建 Entrepreneur Agent
            from automation_tester.entrepreneur_agent import EntrepreneurAgent

            agent = EntrepreneurAgent(request.scenario_config)

            # 预热：确保会话已初始化（异步方法）
            await agent.ensure_session()
            active_agents[agent.session_id] = agent
            logger.debug("🧰 Agent 会话已预初始化，准备进行多轮对话")

            logger.info("✅ Agent 创建成功")
            logger.info(f"   Session ID: {agent.session_id}")
            logger.info(f"   活跃会话数: {len(active_agents)}")

            return StartTestResponse(
                session_id=agent.session_id, scenario_name=scenario_name, company_name=company_name
            )

        except Exception as e:
            logger.error(f"❌ 启动测试失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/test/answer", response_model=AnswerResponse)
async def get_answer(request: AnswerRequest):
    """
    获取 Agent 对问题的回答

    Args:
        request: 包含 session_id 和问题的请求

    Returns:
        AnswerResponse: 包含回答和统计信息
    """
    with LogContext(logger, f"处理问题 - {request.session_id[:16]}..."):
        try:
            logger.info("💬 收到问题请求")
            logger.info(f"   Session ID: {request.session_id}")
            logger.debug(f"   问题内容: {request.question[:100]}...")

            # 检查 session 是否存在
            if request.session_id not in active_agents:
                logger.error(f"❌ Session not found: {request.session_id}")
                logger.error(f"   当前活跃会话: {list(active_agents.keys())}")
                raise HTTPException(status_code=404, detail="Session not found")

            # 获取 Agent 并生成回答
            agent = active_agents[request.session_id]
            answer = await agent.answer(request.question)
            stats = agent.get_stats()

            logger.info("✅ 回答生成成功")
            logger.info(f"   轮次: {stats['round_count']}")
            logger.info(f"   总耗时: {stats['elapsed_time']:.2f}s")
            logger.info(f"   平均耗时: {stats['avg_time_per_round']:.2f}s/轮")

            return AnswerResponse(
                answer=answer, round_number=stats["round_count"], elapsed_time=stats["elapsed_time"]
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 获取回答失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/test/stop")
async def stop_test(request: StopTestRequest):
    """
    停止测试，清理 Agent 实例
    Args:
        request: 包含 session_id 的请求

    Returns:
        dict: 状态信息
    """
    with LogContext(logger, f"停止测试 - {request.session_id[:16]}..."):
        try:
            logger.info("🛑 收到停止测试请求")
            logger.info(f"   Session ID: {request.session_id}")

            if request.session_id in active_agents:
                agent = active_agents[request.session_id]
                stats = agent.get_stats()

                logger.info("📊 测试统计信息:")
                logger.info(f"   场景: {stats['scenario_name']}")
                logger.info(f"   公司: {stats['company_name']}")
                logger.info(f"   总轮次: {stats['round_count']}")
                logger.info(f"   总耗时: {stats['elapsed_time']:.2f}s")
                logger.info(f"   平均耗时: {stats['avg_time_per_round']:.2f}s/轮")

                del active_agents[request.session_id]
                logger.info("✅ Session 已清理")
                logger.info(f"   剩余活跃会话数: {len(active_agents)}")
            else:
                logger.warning(f"⚠️  Session 不存在: {request.session_id}")

            return {"status": "success", "message": "Test stopped"}

        except Exception as e:
            logger.error(f"❌ 停止测试失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/test/status/{session_id}")
async def get_status(session_id: str):
    """
    获取测试状态

    Args:
        session_id: 会话 ID

    Returns:
        dict: 状态信息
    """
    try:
        logger.debug(f"📊 查询状态: session_id={session_id}")

        if session_id not in active_agents:
            logger.warning(f"⚠️  Session 不存在: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")

        agent = active_agents[session_id]
        stats = agent.get_stats()

        logger.debug(f"   轮次: {stats['round_count']}, 耗时: {stats['elapsed_time']:.2f}s")

        return {"status": "running", **stats}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/health")
async def health_check():
    """健康检查"""
    logger.debug(f"💚 健康检查: 活跃会话数={len(active_agents)}")
    return {"status": "ok", "active_sessions": len(active_agents)}


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # 验证配置
    if not LLMConfig.api_key:
        logger.error("❌ 配置错误: LLM_API_KEY 未设置")
        exit(1)

    logger.info("=" * 80)
    logger.info("🚀 启动 Entrepreneur Agent Service")
    logger.info(f"   监听地址: 0.0.0.0:{AppConfig.agent_service_port}")
    logger.info(f"   环境: {AppConfig.env}")
    logger.info(f"   日志级别: {AppConfig.log_level}")
    logger.info(f"   LLM 模型: {LLMConfig.model}")
    logger.info("=" * 80)

    uvicorn.run(app, host="0.0.0.0", port=AppConfig.agent_service_port, log_level="info")
