"""
43X Automation Tester

基于 RPA 技术的 43X 投资 Agent 自动化测试工具
"""

__version__ = "1.0.0"
__author__ = "43X Team"

# ============================================================================
# 导出核心模块
# ============================================================================

from automation_tester.agents import (
    EntrepreneurAgentManager,
    create_entrepreneur_agent,
)
from automation_tester.config import Config, LLMConfig, AppConfig
from automation_tester.prompts import build_entrepreneur_instruction
from automation_tester.utils import (
    build_user_message,
    build_model_message,
    format_project_info,
    build_memory_context,
    DEFAULT_AGENT_CONFIG,
)

__all__ = [
    # Agent
    "EntrepreneurAgentManager",
    "create_entrepreneur_agent",
    
    # Config
    "Config",
    "LLMConfig",
    "AppConfig",
    
    # Prompts
    "build_entrepreneur_instruction",
    
    # Utils
    "build_user_message",
    "build_model_message",
    "format_project_info",
    "build_memory_context",
    "DEFAULT_AGENT_CONFIG",
]
