"""
日志配置模块

为 Entrepreneur Agent Service 提供统一的日志配置。
支持控制台输出和文件输出，可通过环境变量配置日志级别。
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_level: str | None = None, log_dir: str | None = None) -> logging.Logger:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)，默认从环境变量读取
        log_dir: 日志目录路径，默认为当前目录下的 logs

    Returns:
        logging.Logger: 配置好的 logger 实例
    """
    # 从环境变量读取日志级别，默认 INFO
    if log_level is None:
        log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()

    log_dir_path: Path = Path.cwd() / "logs" if log_dir is None else Path(log_dir)
    log_dir_path.mkdir(exist_ok=True)

    # 生成日志文件名（按日期）
    log_filename = f"agent_service_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = log_dir_path / log_filename

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # 清除已有的 handlers（避免重复）
    root_logger.handlers.clear()

    # 定义日志格式
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # 控制台 Handler（使用简单格式）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # 文件 Handler（使用详细格式，支持日志轮转）
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    app_logger = logging.getLogger("entrepreneur_agent")

    # 记录日志配置信息
    app_logger.info("=" * 80)
    app_logger.info("日志系统已初始化")
    app_logger.info(f"日志级别: {log_level}")
    app_logger.info(f"日志文件: {log_filepath}")
    app_logger.info("控制台输出: 启用")
    app_logger.info("=" * 80)

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger

    Args:
        name: logger 名称

    Returns:
        logging.Logger: logger 实例
    """
    return logging.getLogger(name)


class LogContext:
    """
    日志上下文管理器

    用于记录代码块的执行时间和状态。
    """

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        """
        初始化日志上下文

        Args:
            logger: logger 实例
            operation: 操作描述
            level: 日志级别
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time: datetime | None = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = datetime.now()
        self.logger.log(self.level, f" 开始: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.start_time is None:
            return False
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            # 成功完成
            self.logger.log(self.level, f"完成: {self.operation} (耗时: {elapsed:.2f}s)")
        else:
            # 发生异常
            self.logger.error(
                f"失败: {self.operation} (耗时: {elapsed:.2f}s) - {exc_type.__name__}: {exc_val}",
                exc_info=True,
            )

        return False  # 不抑制异常


def log_llm_call(
    logger: logging.Logger,
    model: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    elapsed_time: float | None = None,
):
    """
    记录 LLM API 调用信息

    Args:
        logger: logger 实例
        model: 模型名称
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数
        total_tokens: 总 token 数
        elapsed_time: 调用耗时（秒）
    """
    log_parts = [f"LLM API 调用: model={model}"]

    if prompt_tokens is not None:
        log_parts.append(f"prompt_tokens={prompt_tokens}")
    if completion_tokens is not None:
        log_parts.append(f"completion_tokens={completion_tokens}")
    if total_tokens is not None:
        log_parts.append(f"total_tokens={total_tokens}")
    if elapsed_time is not None:
        log_parts.append(f"elapsed={elapsed_time:.2f}s")

    logger.info(", ".join(log_parts))


def log_qa_interaction(
    logger: logging.Logger, round_number: int, question: str, answer: str, elapsed_time: float
):
    """
    记录问答交互

    Args:
        logger: logger 实例
        round_number: 轮次编号
        question: 问题内容
        answer: 回答内容
        elapsed_time: 交互耗时（秒）
    """
    logger.info("=" * 80)
    logger.info(f"问答交互 - Round {round_number}")
    logger.info(f"⏱耗时: {elapsed_time:.2f}s")
    logger.info("-" * 80)
    logger.info(f"问题: {question[:200]}{'...' if len(question) > 200 else ''}")
    logger.info("-" * 80)
    logger.info(f"回答: {answer[:200]}{'...' if len(answer) > 200 else ''}")
    logger.info("=" * 80)

    logger.debug(f"[Round {round_number}] 完整问题: {question}")
    logger.debug(f"[Round {round_number}] 完整回答: {answer}")
