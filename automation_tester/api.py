"""
43X Entrepreneur Agent Service

FastAPI 服务，提供创业者 Agent 的 HTTP API 接口。
用于 Chrome 插件调用，模拟创业者与投资 Agent 对话。
"""

import asyncio
import contextlib
import logging
import time
from collections import OrderedDict
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from automation_tester.config import AppConfig, LLMConfig
from automation_tester.utils.logging_config import LogContext, get_logger, setup_logging

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

# ============================================================================
# LRU 会话缓存
# ============================================================================

# 缓存配置
MAX_CACHE_SIZE = 10  # 最多缓存 10 个会话
CACHE_TIMEOUT = 3600  # 缓存超时时间（秒），1小时
CLEANUP_INTERVAL = 300  # 自动清理间隔（秒），5分钟

# LRU 缓存：session_id -> {"agent": Agent, "last_activity": timestamp, "created_at": timestamp}
session_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

# 缓存统计
cache_stats = {
    "hits": 0,
    "misses": 0,
    "evictions": 0,
}

# 后台任务控制
_cleanup_task = None


def get_from_cache(session_id: str) -> Any | None:
    """
    从缓存获取 Agent 实例

    Args:
        session_id: 会话 ID

    Returns:
        Agent 实例，如果不存在或已过期则返回 None
    """
    if session_id in session_cache:
        cache_entry = session_cache[session_id]

        # 检查是否过期
        if time.time() - cache_entry["last_activity"] > CACHE_TIMEOUT:
            logger.info(f"🕐 缓存过期: {session_id}")
            session_cache.pop(session_id)
            cache_stats["evictions"] += 1
            cache_stats["misses"] += 1
            return None

        # 更新访问时间并移到末尾（LRU）
        cache_entry["last_activity"] = time.time()
        session_cache.move_to_end(session_id)

        cache_stats["hits"] += 1
        logger.debug(f"✅ 缓存命中: {session_id}")
        return cache_entry["agent"]

    cache_stats["misses"] += 1
    logger.debug(f"❌ 缓存未命中: {session_id}")
    return None


def add_to_cache(session_id: str, agent: Any):
    """
    添加 Agent 实例到缓存

    Args:
        session_id: 会话 ID
        agent: Agent 实例
    """
    # 如果缓存已满，移除最久未使用的项
    if len(session_cache) >= MAX_CACHE_SIZE and session_id not in session_cache:
        oldest_session_id, oldest_entry = session_cache.popitem(last=False)
        logger.info(
            f"🗑️  缓存已满，淘汰最久未使用的会话: {oldest_session_id} "
            f"(闲置 {time.time() - oldest_entry['last_activity']:.0f}秒)"
        )
        cache_stats["evictions"] += 1

    # 添加或更新缓存
    current_time = time.time()
    if session_id in session_cache:
        session_cache[session_id]["agent"] = agent
        session_cache[session_id]["last_activity"] = current_time
        logger.debug(f"🔄 更新缓存: {session_id}")
    else:
        session_cache[session_id] = {
            "agent": agent,
            "last_activity": current_time,
            "created_at": current_time,
        }
        logger.info(
            f"➕ 添加到缓存: {session_id} (缓存大小: {len(session_cache)}/{MAX_CACHE_SIZE})"
        )

    # 移到末尾（最近使用）
    session_cache.move_to_end(session_id)


def remove_from_cache(session_id: str):
    """
    从缓存移除 Agent 实例

    Args:
        session_id: 会话 ID
    """
    if session_id in session_cache:
        session_cache.pop(session_id)
        logger.info(f"🗑️  从缓存移除: {session_id}")


def get_cache_stats() -> dict[str, Any]:
    """
    获取缓存统计信息

    Returns:
        dict: 缓存统计信息
    """
    total_requests = cache_stats["hits"] + cache_stats["misses"]
    hit_rate = cache_stats["hits"] / total_requests if total_requests > 0 else 0

    return {
        "size": len(session_cache),
        "max_size": MAX_CACHE_SIZE,
        "hits": cache_stats["hits"],
        "misses": cache_stats["misses"],
        "evictions": cache_stats["evictions"],
        "hit_rate": f"{hit_rate:.2%}",
        "sessions": list(session_cache.keys()),
    }


async def cleanup_expired_sessions_background():
    """
    后台任务：定期清理过期的会话
    """
    logger.info(f"🧹 启动后台清理任务 (间隔: {CLEANUP_INTERVAL}秒)")

    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)

            expired_sessions = []
            current_time = time.time()

            # 查找并清理过期的会话
            for session_id, cache_entry in list(session_cache.items()):
                idle_time = current_time - cache_entry["last_activity"]
                if idle_time > CACHE_TIMEOUT:
                    expired_sessions.append(session_id)
                    session_cache.pop(session_id)
                    cache_stats["evictions"] += 1
                    logger.info(f"🗑️  自动清理过期会话: {session_id} (闲置 {idle_time:.0f}秒)")

            if expired_sessions:
                logger.info(f"✅ 自动清理完成: 移除 {len(expired_sessions)} 个过期会话")
                logger.info(f"📊 当前缓存: {len(session_cache)}/{MAX_CACHE_SIZE} 会话")

        except Exception as e:
            logger.error(f"❌ 后台清理任务出错: {e}", exc_info=True)


# 兼容性：保留 active_agents 别名
active_agents = session_cache

# ============================================================================
# 应用生命周期事件
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global _cleanup_task

    logger.info("🚀 应用启动中...")
    logger.info(f"📊 缓存配置: 最大 {MAX_CACHE_SIZE} 会话, 超时 {CACHE_TIMEOUT}秒")

    # 启动后台清理任务
    _cleanup_task = asyncio.create_task(cleanup_expired_sessions_background())
    logger.info("✅ 后台清理任务已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    global _cleanup_task

    logger.info("🛑 应用关闭中...")

    # 停止后台清理任务
    if _cleanup_task:
        _cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cleanup_task
        logger.info("✅ 后台清理任务已停止")

    # 清理所有缓存的会话
    session_count = len(session_cache)
    session_cache.clear()
    logger.info(f"✅ 已清理 {session_count} 个缓存会话")


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
    files_path: dict[str, str] | None = None  # 新增：文件路径映射


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

    如果会话已存在于缓存中，则复用现有 Runner 实例。

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

            # 记录缓存状态
            cache_stats_info = get_cache_stats()
            logger.info(
                f"📊 当前缓存状态: {cache_stats_info['size']}/{cache_stats_info['max_size']} "
                f"(命中率: {cache_stats_info['hit_rate']})"
            )

            # 处理文件内容
            bp_content_parts = []

            # 方式1: 直接传入文件内容（兼容旧方式）
            if request.files_content:
                logger.info(f"   直接上传文件数: {len(request.files_content)}")

                import base64
                import os
                import tempfile

                from automation_tester.file import FileService, FileType
                from automation_tester.utils.file_utils import get_file_extension

                for filename, content in request.files_content.items():
                    logger.info(f"     - {filename}")

                    try:
                        ext = get_file_extension(filename)

                        # 定义需要特殊处理的二进制文件类型
                        binary_extensions = ["pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls"]

                        # 检测是否为二进制文件（base64编码）
                        if ext in binary_extensions:
                            logger.info(f"       检测到二进制文件类型: {ext}")
                            logger.info(f"       内容长度: {len(content)} 字符")

                            # 尝试解码base64
                            try:
                                # 解码base64
                                file_data = base64.b64decode(content)
                                logger.info(f"       Base64解码成功: {len(file_data)} 字节")

                                # 创建临时文件
                                with tempfile.NamedTemporaryFile(
                                    delete=False, suffix=f".{ext}", mode="wb"
                                ) as tmp:
                                    tmp.write(file_data)
                                    tmp_path = tmp.name

                                logger.info(f"       临时文件: {tmp_path}")

                                # 使用文件处理模块解析
                                file_type_map = {
                                    "pdf": FileType.PDF,
                                    "docx": FileType.WORD,
                                    "doc": FileType.WORD,
                                    "pptx": FileType.PPT,
                                    "ppt": FileType.PPT,
                                }

                                file_type = file_type_map.get(ext, FileType.TXT)
                                logger.info(f"       使用解析器: {file_type.value}")

                                # 解析文件
                                content_chunks = []
                                async for chunk in FileService.read_content(tmp_path, file_type):
                                    content_chunks.append(chunk)

                                parsed_content = "\n\n".join(content_chunks)
                                logger.info(f"       解析成功: {len(parsed_content)} 字符")

                                # 删除临时文件
                                try:
                                    os.unlink(tmp_path)
                                    logger.debug("       临时文件已删除")
                                except Exception as e:
                                    logger.warning(f"       删除临时文件失败: {e}")

                                # 使用解析后的内容
                                content = parsed_content

                            except Exception as decode_error:
                                logger.error(f"       Base64解码或解析失败: {decode_error}")
                                # 如果解码失败，尝试作为普通文本处理
                                logger.info("       回退到文本模式")

                        # 限制每个文件的长度，避免超过 token 限制
                        max_chars = 50000  # 约 12,500 tokens
                        if len(content) > max_chars:
                            logger.warning(
                                f"   文件 [{filename}] 过长 ({len(content)} 字符)，截取前 {max_chars} 字符"
                            )
                            content = content[:max_chars] + "\n\n[... 内容过长，已截断 ...]"

                        bp_content_parts.append(f"## 文件: {filename}\n\n{content}")
                        logger.info(f"   文件处理完成 [{filename}]: {len(content)} 字符")

                    except Exception as e:
                        logger.error(f"   文件处理失败 [{filename}]: {e}", exc_info=True)
                        bp_content_parts.append(f"## 文件: {filename}\n\n[处理失败: {e!s}]")

            # 方式2: 传入文件路径，使用文件处理模块解析（新方式）
            if request.files_path:
                logger.info(f"   文件路径解析数: {len(request.files_path)}")
                from automation_tester.file import FileService, FileType
                from automation_tester.utils.file_utils import get_file_extension

                for filename, filepath in request.files_path.items():
                    logger.info(f"     - {filename} -> {filepath}")

                    try:
                        # 根据文件扩展名确定文件类型
                        ext = get_file_extension(filename)
                        file_type_map = {
                            "pdf": FileType.PDF,
                            "docx": FileType.WORD,
                            "doc": FileType.WORD,
                            "pptx": FileType.PPT,
                            "ppt": FileType.PPT,
                            "md": FileType.MD,
                            "txt": FileType.TXT,
                            "jpg": FileType.IMAGE,
                            "jpeg": FileType.IMAGE,
                            "png": FileType.IMAGE,
                            "webp": FileType.IMAGE,
                        }

                        file_type = file_type_map.get(ext, FileType.TXT)
                        logger.info(f"       文件类型: {file_type.value}")

                        # 使用文件处理模块解析
                        content_chunks = []
                        async for chunk in FileService.read_content(filepath, file_type):
                            content_chunks.append(chunk)

                        content = "\n\n".join(content_chunks)

                        # 限制长度
                        max_chars = 50000
                        if len(content) > max_chars:
                            logger.warning(
                                f"   文件 [{filename}] 解析后过长 ({len(content)} 字符)，截取前 {max_chars} 字符"
                            )
                            content = content[:max_chars] + "\n\n[... 内容过长，已截断 ...]"

                        bp_content_parts.append(f"## 文件: {filename}\n\n{content}")
                        logger.info(f"   文件解析成功 [{filename}]: {len(content)} 字符")

                    except Exception as e:
                        logger.error(f"   文件解析失败 [{filename}]: {e}")
                        bp_content_parts.append(f"## 文件: {filename}\n\n[解析失败: {e!s}]")

            # 合并所有文件内容
            if bp_content_parts:
                request.scenario_config["bp_content"] = "\n\n".join(bp_content_parts)
            else:
                logger.info("   上传文件数: 0")

            # 创建 Entrepreneur Agent（使用重构后的 Manager）
            from automation_tester.agents import EntrepreneurAgentManager

            agent = EntrepreneurAgentManager(request.scenario_config)

            # 🔥 添加到 LRU 缓存（如果已存在则更新）
            add_to_cache(agent.session_id, agent)
            logger.debug("🧰 Agent 会话已预初始化，准备进行多轮对话")

            logger.info("✅ Agent 创建成功")
            logger.info(f"   Session ID: {agent.session_id}")

            # 记录详细的缓存状态
            cache_stats_info = get_cache_stats()
            logger.info("📊 缓存状态更新:")
            logger.info(f"   - 缓存大小: {cache_stats_info['size']}/{cache_stats_info['max_size']}")
            logger.info(f"   - 命中率: {cache_stats_info['hit_rate']}")
            logger.info(f"   - 总命中: {cache_stats_info['hits']}")
            logger.info(f"   - 总未命中: {cache_stats_info['misses']}")
            logger.info(f"   - 总淘汰: {cache_stats_info['evictions']}")

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

    从缓存中获取 Runner 实例，自动处理缓存过期。

    Args:
        request: 包含 session_id 和问题的请求

    Returns:
        AnswerResponse: 包含回答和统计信息
    """
    with LogContext(logger, f"处理问题 - {request.session_id[:16]}..."):
        try:
            logger.info("💬 收到问题请求")
            logger.info(f"   Session ID: {request.session_id}")
            logger.info(f"   ⚠️ 问题完整内容: [{request.question}]")  # 打印完整问题，用方括号包裹
            logger.info(f"   问题长度: {len(request.question)} 字符")
            logger.info(
                f"   问题是否为空: {not request.question or request.question.strip() == ''}"
            )

            # 🔥 从缓存获取 Agent（自动处理过期）
            agent = get_from_cache(request.session_id)

            if agent is None:
                logger.error(f"❌ Session not found or expired: {request.session_id}")
                logger.error(f"   当前活跃会话: {list(session_cache.keys())}")

                # 记录缓存状态
                cache_stats_info = get_cache_stats()
                logger.error(
                    f"📊 缓存状态: {cache_stats_info['size']}/{cache_stats_info['max_size']} "
                    f"(命中率: {cache_stats_info['hit_rate']})"
                )

                raise HTTPException(status_code=404, detail="Session not found or expired")

            # 生成回答
            answer = await agent.answer(request.question)
            stats = agent.get_stats()

            logger.info("✅ 回答生成成功")
            logger.info(f"   轮次: {stats['round_count']}")
            logger.info(f"   总耗时: {stats['elapsed_time']:.2f}s")
            logger.info(f"   平均耗时: {stats['avg_time_per_round']:.2f}s/轮")

            # 记录缓存状态
            cache_stats_info = get_cache_stats()
            logger.debug(
                f"📊 缓存状态: {cache_stats_info['size']}/{cache_stats_info['max_size']} "
                f"(命中率: {cache_stats_info['hit_rate']})"
            )

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

            if request.session_id in session_cache:
                cache_entry = session_cache[request.session_id]
                agent = cache_entry["agent"]
                stats = agent.get_stats()

                logger.info("📊 测试统计信息:")
                logger.info(f"   场景: {stats['scenario_name']}")
                logger.info(f"   公司: {stats['company_name']}")
                logger.info(f"   总轮次: {stats['round_count']}")
                logger.info(f"   总耗时: {stats['elapsed_time']:.2f}s")
                logger.info(f"   平均耗时: {stats['avg_time_per_round']:.2f}s/轮")

                # 计算会话存活时间
                session_lifetime = time.time() - cache_entry["created_at"]
                logger.info(f"   会话存活时间: {session_lifetime:.0f}秒")

                # 🔥 使用缓存管理函数移除
                remove_from_cache(request.session_id)

                logger.info("✅ Session 已清理")
                logger.info(f"   剩余活跃会话数: {len(session_cache)}")
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

        # 🔥 使用缓存获取（自动处理过期）
        agent = get_from_cache(session_id)

        if agent is None:
            logger.warning(f"⚠️  Session 不存在或已过期: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found or expired")

        stats = agent.get_stats()

        logger.debug(f"   轮次: {stats['round_count']}, 耗时: {stats['elapsed_time']:.2f}s")

        return {"status": "running", **stats}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/cache/stats")
async def get_cache_statistics():
    """
    获取缓存统计信息

    Returns:
        dict: 详细的缓存统计信息
    """
    try:
        stats = get_cache_stats()

        # 添加每个会话的详细信息
        session_details = []
        for session_id, cache_entry in session_cache.items():
            agent = cache_entry["agent"]
            agent_stats = agent.get_stats()

            idle_time = time.time() - cache_entry["last_activity"]
            lifetime = time.time() - cache_entry["created_at"]

            session_details.append(
                {
                    "session_id": session_id,
                    "scenario_name": agent_stats["scenario_name"],
                    "company_name": agent_stats["company_name"],
                    "round_count": agent_stats["round_count"],
                    "idle_time_seconds": round(idle_time, 2),
                    "lifetime_seconds": round(lifetime, 2),
                    "created_at": cache_entry["created_at"],
                    "last_activity": cache_entry["last_activity"],
                }
            )

        logger.info(f"📊 缓存统计查询: {stats['size']}/{stats['max_size']} 会话")

        return {
            **stats,
            "timeout_seconds": CACHE_TIMEOUT,
            "session_details": session_details,
        }

    except Exception as e:
        logger.error(f"❌ 获取缓存统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/cache/cleanup")
async def cleanup_expired_sessions():
    """
    手动清理过期的会话

    Returns:
        dict: 清理结果
    """
    try:
        logger.info("🧹 开始手动清理过期会话")

        expired_sessions = []
        current_time = time.time()

        # 查找过期的会话
        for session_id, cache_entry in list(session_cache.items()):
            idle_time = current_time - cache_entry["last_activity"]
            if idle_time > CACHE_TIMEOUT:
                expired_sessions.append(session_id)
                session_cache.pop(session_id)
                cache_stats["evictions"] += 1
                logger.info(f"🗑️  清理过期会话: {session_id} (闲置 {idle_time:.0f}秒)")

        logger.info(f"✅ 清理完成: 移除 {len(expired_sessions)} 个过期会话")

        return {
            "status": "success",
            "cleaned_count": len(expired_sessions),
            "cleaned_sessions": expired_sessions,
            "remaining_sessions": len(session_cache),
        }

    except Exception as e:
        logger.error(f"❌ 清理过期会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/extract/info")
async def extract_info_from_files(request: Request):
    """
    从上传的文件中提取项目信息
    
    使用 LLM 分析文件内容，提取结构化的项目信息
    
    请求格式:
    {
        "files_content": {
            "filename.pdf": "base64_content" or "text_content",
            ...
        }
    }
    
    Returns:
        dict: 提取的结构化信息
    """
    # 在函数开头导入所有需要的模块
    import base64
    import json
    import os
    import re
    import tempfile

    from automation_tester.file import FileService, FileType
    from automation_tester.utils.file_utils import get_file_extension
    from openai import OpenAI
    
    with LogContext(logger, "AI提取信息"):
        try:
            body = await request.json()
            files_content = body.get("files_content", {})
            
            if not files_content:
                raise HTTPException(status_code=400, detail="未提供文件内容")
            
            logger.info(f"📄 收到 {len(files_content)} 个文件，开始AI提取")
            
            # 处理文件内容
            all_text = []
            
            for filename, content in files_content.items():
                try:
                    ext = get_file_extension(filename)
                    logger.info(f"   处理文件: {filename} ({ext})")
                    
                    # 二进制文件类型
                    binary_extensions = ["pdf", "docx", "doc", "pptx", "ppt"]
                    
                    if ext in binary_extensions:
                        # 解码base64
                        file_data = base64.b64decode(content)
                        
                        # 创建临时文件
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}", mode="wb") as tmp:
                            tmp.write(file_data)
                            tmp_path = tmp.name
                        
                        try:
                            # 解析文件
                            file_type_map = {
                                "pdf": FileType.PDF,
                                "docx": FileType.WORD,
                                "doc": FileType.WORD,
                                "pptx": FileType.PPT,
                                "ppt": FileType.PPT,
                            }
                            
                            file_type = file_type_map.get(ext, FileType.TXT)
                            
                            content_chunks = []
                            async for chunk in FileService.read_content(tmp_path, file_type):
                                content_chunks.append(chunk)
                            
                            parsed_content = "\n\n".join(content_chunks)
                            all_text.append(f"## 文件: {filename}\n\n{parsed_content}")
                            
                        finally:
                            # 删除临时文件
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    else:
                        # 文本文件直接使用
                        all_text.append(f"## 文件: {filename}\n\n{content}")
                    
                    logger.info(f"   ✅ 文件处理成功: {filename}")
                    
                except Exception as e:
                    logger.error(f"   ❌ 文件处理失败: {filename} - {e}")
                    continue
            
            if not all_text:
                raise HTTPException(status_code=400, detail="无法解析任何文件内容")
            
            combined_text = "\n\n---\n\n".join(all_text)
            
            # 限制文本长度
            max_chars = 20000
            if len(combined_text) > max_chars:
                combined_text = combined_text[:max_chars] + "\n\n[... 内容过长，已截断 ...]"
            
            logger.info(f"📝 合并文本长度: {len(combined_text)} 字符")
            
            # 使用 LLM 提取信息
            client = OpenAI(
                api_key=LLMConfig.api_key,
                base_url=LLMConfig.base_url,
            )
            
            extraction_prompt = f"""请从以下商业计划书或项目资料中提取关键信息，以JSON格式返回。

要提取的字段：
- company_name: 公司名称（字符串）
- industry: 行业类型（字符串，如"AI SaaS"、"企业服务"等）
- product: 产品描述（字符串，简要描述）
- revenue: 营收情况（字符串，如"ARR 500万"）
- team: 团队规模（字符串，如"15人"）
- funding_need: 融资需求（字符串，如"A轮 2000万"）
- customers: 客户案例（数组，如["阿里巴巴", "腾讯"]）
- technology: 核心技术（字符串，简要描述）

注意：
1. 只返回JSON格式，不要其他说明文字
2. 如果某个字段找不到信息，不要包含该字段
3. 确保JSON格式正确

文档内容：

{combined_text}

请返回JSON："""
            
            logger.info("🤖 调用 LLM 提取信息...")
            logger.info(f"   使用模型: {LLMConfig.model}")
            
            response = client.chat.completions.create(
                model=LLMConfig.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的商业计划书分析助手，擅长从文档中提取结构化信息。"},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.info(f"📤 LLM 返回: {result_text[:200]}...")
            
            # 解析JSON（尝试提取JSON，可能包含markdown代码块）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            
            extracted_info = json.loads(result_text)
            
            logger.info(f"✅ 信息提取成功: {list(extracted_info.keys())}")
            
            return {
                "success": True,
                "extracted_info": extracted_info,
                "files_processed": len(files_content)
            }
            
        except HTTPException:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"   原始文本: {result_text}")
            raise HTTPException(status_code=500, detail=f"AI返回的格式无法解析: {str(e)}")
        except Exception as e:
            logger.error(f"❌ 信息提取失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查"""
    logger.debug(f"💚 健康检查: 活跃会话数={len(session_cache)}")
    return {"status": "ok", "active_sessions": len(session_cache)}


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
