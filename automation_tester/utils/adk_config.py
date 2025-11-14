"""
Google ADK 配置模块

提供 LLM 和 Agent 的默认配置
"""

import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from automation_tester.config import LLMConfig
from automation_tester.utils.context_limiter import AgentContextLimiter

logger = logging.getLogger(__name__)

# 初始化 AgentContextLimiter
AgentContextLimiter.init_context_limiter()

# 为 Entrepreneur Agent 设置消息限制（默认 20 条）
AgentContextLimiter.set_limit("entrepreneur", 20)

logger.info("✅ AgentContextLimiter 已初始化，entrepreneur agent 消息限制: 20 条")

# 创建默认 LLM 实例
DEFAULT_LLM = LiteLlm(
    model=LLMConfig.model,
    base_url=LLMConfig.base_url,
    api_key=LLMConfig.api_key,
    num_retries=LLMConfig.num_retries,
    temperature=LLMConfig.temperature,
    max_tokens=LLMConfig.max_tokens,
)


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """
    LLM 调用前的回调函数
    
    核心功能：
    1. 设置当前 Agent 名称（启用 AgentContextLimiter）
    2. 过滤历史消息，只保留纯文本对话，移除 function calls 等无关事件
    3. 🔥 RAG 检索：根据当前问题检索相关材料片段
    4. AgentContextLimiter 会自动截断超长消息（通过 monkey patch）

    Args:
        callback_context: 回调上下文
        llm_request: LLM 请求

    Returns:
        Optional[LlmResponse]: 自定义的 LLM 响应，返回 None 则继续正常流程
    """
    from google.adk.flows.llm_flows.contents import _get_contents
    from google.genai import types
    
    llm_logger = logging.getLogger("entrepreneur_agent.llm_debug")
    
    try:
        # 🔥 启用 AgentContextLimiter：设置当前 Agent 名称
        agent_name = callback_context.agent_name
        AgentContextLimiter.set_current_agent_name(agent_name)
        
        # 获取 invocation_context 和 session
        invocation_context = callback_context._invocation_context
        session = invocation_context.session
        
        original_event_count = len(session.events)
        
        # 找到第一条 "user" 消息的位置
        cut_idx = None
        for i, e in enumerate(session.events):
            if getattr(e, "author", None) == "user":
                cut_idx = i
                break
        
        # 从第一条 user 消息开始保留
        if cut_idx is not None:
            filtered_events = session.events[cut_idx:]
        else:
            filtered_events = session.events
        
        # 过滤掉 function calls 和 function responses，只保留纯文本对话
        filtered_events = [
            e for e in filtered_events
            if (
                e.author in {"user", "entrepreneur"}  # 只保留用户和创业者的消息
                and not (bool(e.get_function_calls()) or bool(e.get_function_responses()))  # 移除工具调用
            )
        ]
        
        filtered_event_count = len(filtered_events)
        
        # 重新构建 llm_request.contents
        llm_request.contents = _get_contents(
            invocation_context.branch, 
            filtered_events, 
            callback_context.agent_name
        )
        
        contents_count_before = len(llm_request.contents)
        
        # 📊 记录截断前的消息数量
        logger.info(
            f"[before_model_callback] Agent: {agent_name} | "
            f"原始事件: {original_event_count} → 过滤后: {filtered_event_count} → "
            f"Contents: {contents_count_before} 条"
        )
        
        # 注意：AgentContextLimiter 会在后续的 litellm 调用中自动截断 llm_request.contents
        # 这里不需要手动截断，只需要记录日志
        
        # 调试日志
        if llm_logger.isEnabledFor(logging.DEBUG):
            llm_logger.debug("=" * 80)
            llm_logger.debug("🔍 LLM 请求内容（已过滤，待 AgentContextLimiter 截断）:")
            llm_logger.debug(f"   原始事件数: {original_event_count}")
            llm_logger.debug(f"   过滤后事件数: {filtered_event_count}")
            llm_logger.debug(f"   Contents 数量: {contents_count_before}")
            llm_logger.debug(f"   Agent 消息限制: {AgentContextLimiter.get_limit()} 条")
            
            for i, content in enumerate(llm_request.contents):
                role = getattr(content, 'role', 'unknown')
                parts = getattr(content, 'parts', [])
                text = parts[0].text[:100] if parts and hasattr(parts[0], 'text') else 'N/A'
                llm_logger.debug(f"   Content {i+1} [{role}]: {text}...")
            
            llm_logger.debug("=" * 80)
        
        # 🔥 RAG 检索：根据当前问题检索相关材料
        try:
            # 提取当前用户问题（最后一条 user 消息）
            current_question = None
            if llm_request.contents:
                for content in reversed(llm_request.contents):
                    if getattr(content, 'role', '') == 'user':
                        parts = getattr(content, 'parts', [])
                        if parts and hasattr(parts[0], 'text'):
                            current_question = parts[0].text
                            break
            
            if current_question and agent_name == "entrepreneur":
                # 尝试从 session.state 获取 RAG service
                rag_service = session.state.get("rag_service")
                
                if rag_service:
                    logger.info(f"🔍 RAG 检索: query='{current_question[:50]}...'")
                    
                    # 检索相关材料片段
                    results = rag_service.search(current_question, top_k=3)
                    
                    if results:
                        # 格式化检索结果
                        relevant_materials = []
                        for i, result in enumerate(results):
                            relevant_materials.append(
                                f"[相关材料 {i+1}]\n{result.chunk}"
                            )
                        
                        materials_text = "\n\n".join(relevant_materials)
                        
                        # 注入到 llm_request.contents 的开头（在 system message 之后）
                        rag_content = types.Content(
                            role="user",
                            parts=[types.Part(
                                text=f"## 相关项目材料\n\n{materials_text}\n\n## 投资人问题\n"
                            )]
                        )
                        
                        # 插入到第一条 user 消息之前
                        llm_request.contents.insert(1, rag_content)
                        
                        logger.info(
                            f"✅ RAG 检索完成: 注入 {len(results)} 个相关片段, "
                            f"总长度 {len(materials_text)} 字符"
                        )
                else:
                    llm_logger.debug("⚠️ RAG service 未初始化，跳过检索")
        
        except Exception as e:
            logger.warning(f"⚠️ RAG 检索失败: {e}", exc_info=True)
        
    except Exception as e:
        # 如果过滤失败，记录错误但不影响主流程
        logger.warning(f"⚠️ 历史消息过滤失败: {e}", exc_info=True)
    
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
