"""
Google ADK 配置模块

提供 LLM 和 Agent 的默认配置
"""

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from automation_tester.config import LLMConfig

# 创建默认 LLM 实例
DEFAULT_LLM = LiteLlm(
    model=LLMConfig.model,
    base_url=LLMConfig.base_url,
    api_key=LLMConfig.api_key,
    num_retries=LLMConfig.num_retries,
)


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """
    LLM 调用前的回调函数

    Args:
        callback_context: 回调上下文
        llm_request: LLM 请求

    Returns:
        Optional[LlmResponse]: 自定义的 LLM 响应，返回 None 则继续正常流程
    """
    return None


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> LlmResponse | None:
    """
    LLM 调用后的回调函数

    Args:
        callback_context: 回调上下文
        llm_response: LLM 响应

    Returns:
        Optional[LlmResponse]: 修改后的 LLM 响应
    """
    return llm_response


def before_agent_callback(
    callback_context: CallbackContext,
) -> None:
    """
    Agent 调用前的回调函数

    Args:
        callback_context: 回调上下文

    Returns:
        None: 返回 None 则继续正常流程
    """
    return None


def after_agent_callback(callback_context: CallbackContext) -> None:
    """
    Agent 调用后的回调函数

    Args:
        callback_context: 回调上下文

    Returns:
        None: 返回 None 则继续正常流程
    """
    return None


# 默认 LLM 配置
DEFAULT_LLM_CONFIG = {
    "model": DEFAULT_LLM,
    "before_model_callback": before_model_callback,
    "after_model_callback": after_model_callback,
}

# 默认 Tool 配置
DEFAULT_TOOL_CONFIG = {
    "before_tool_callback": None,
    "after_tool_callback": None,
}

# 默认 Agent 配置
DEFAULT_AGENT_CONFIG = {
    **DEFAULT_LLM_CONFIG,
    **DEFAULT_TOOL_CONFIG,
    "before_agent_callback": before_agent_callback,
    "after_agent_callback": after_agent_callback,
}
