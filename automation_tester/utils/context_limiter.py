"""
Agent Context Limiter

用于管理和限制不同 Agent 的上下文长度，防止上下文过长导致 token 超限。
通过 monkey patch litellm 的方法实现上下文截断。
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AgentContextLimiter:
    """
    Agent 上下文限制器
    
    用于管理和限制不同 Agent 的上下文长度，防止上下文过长导致性能问题。
    通过覆盖 litellm 的 _get_completion_inputs 方法实现上下文截断。
    """

    initialized = False
    current_agent_name: str = ""
    limits_by_agent_name: dict[str, int] = {}

    @staticmethod
    def set_current_agent_name(agent_name: str):
        """
        设置当前 Agent 名称
        
        Args:
            agent_name: Agent 名称
        """
        if not AgentContextLimiter.initialized:
            AgentContextLimiter.init_context_limiter()
        AgentContextLimiter.current_agent_name = agent_name

    @staticmethod
    def set_limit(agent_name: str, max_messages: int):
        """
        为指定 Agent 设置消息数量限制
        
        Args:
            agent_name: Agent 名称
            max_messages: 最大消息数量
        """
        if not AgentContextLimiter.initialized:
            AgentContextLimiter.init_context_limiter()
        AgentContextLimiter.limits_by_agent_name[agent_name] = max_messages
        logger.info(f"为 Agent '{agent_name}' 设置消息限制: {max_messages} 条")

    @staticmethod
    def get_limit() -> int:
        """
        获取当前 Agent 的消息限制
        
        Returns:
            int: 消息数量限制，0 表示不限制
        """
        return AgentContextLimiter.limits_by_agent_name.get(
            AgentContextLimiter.current_agent_name,
            0,  # 默认不限制
        )

    @staticmethod
    def init_context_limiter():
        """
        初始化上下文限制器
        
        通过装饰器模式覆盖 litellm._get_completion_inputs 方法，
        在获取完成输入时自动应用上下文长度限制。
        当 messages 超过限制时，保留第一条 system message 和最后 N 条消息。
        """
        try:
            import google.adk.models.lite_llm as litellm_module
        except ImportError:
            logger.error("无法导入 google.adk.models.lite_llm，上下文限制器初始化失败")
            return

        def with_context_limits(func: Callable) -> Callable:
            """
            上下文限制装饰器
            
            Args:
                func: 被装饰的原始函数
                
            Returns:
                function: 带有上下文限制功能的包装函数
            """

            def wrapper(*args: Any, **kwargs: Any) -> tuple:
                """
                包装函数，在原函数基础上添加上下文长度限制
                
                Returns:
                    tuple: (messages, tools, response_format, generation_params) 经过长度限制处理的参数
                """
                messages, tools, response_format, generation_params = func(
                    *args, **kwargs
                )
                max_messages = AgentContextLimiter.get_limit()

                # 如果设置了限制且消息数量超过限制
                if max_messages and len(messages) > max_messages:
                    original_count = len(messages)
                    
                    # 合法截断：确保 function/tool call-response 配对
                    truncated_messages = AgentContextLimiter._valid_truncate(
                        messages, max_messages
                    )
                    messages = truncated_messages
                    
                    logger.info(
                        f"[AgentContextLimiter] Agent '{AgentContextLimiter.current_agent_name}' "
                        f"消息截断: {original_count} → {len(messages)} 条 "
                        f"(限制: {max_messages} 条)"
                    )

                return messages, tools, response_format, generation_params

            return wrapper

        # 覆盖原来的 _get_completion_inputs 方法
        litellm_module._get_completion_inputs = with_context_limits(
            litellm_module._get_completion_inputs
        )

        AgentContextLimiter.initialized = True
        logger.info("AgentContextLimiter 初始化成功")

    @staticmethod
    def _valid_truncate(messages: list, max_messages: int) -> list:
        """
        合法截断消息列表，确保 tool/function call-response 配对关系不被破坏
        
        Args:
            messages: 原始消息列表
            max_messages: 最大消息数量限制
            
        Returns:
            list: 截断后的消息列表，保持 tool/function call-response 配对
        """
        if len(messages) <= max_messages:
            return messages

        # messages[0] 第一条为 system_message 保留
        system_message = messages[0] if messages else None
        remaining_messages = messages[1:] if len(messages) > 1 else []

        if not remaining_messages:
            return messages

        # 计算除 system_message 外可保留的消息数量
        max_count = max_messages - 1 if system_message else max_messages

        if max_count <= 0:
            return [system_message] if system_message else []

        # 从后往前找到可合法截断位置
        valid_start_index = AgentContextLimiter._find_valid_truncation_point(
            remaining_messages, max_count
        )

        # 构建最终消息列表
        result = []
        if system_message:
            result.append(system_message)
        result.extend(remaining_messages[valid_start_index:])

        return result

    @staticmethod
    def _find_valid_truncation_point(messages: list, max_count: int) -> int:
        """
        找到合法截断点，确保不会破坏 assistant 消息及其相关的 tool/function 的 call-response 配对关系
        从后向前搜索，在 max_count 之前寻找 assistant message
        如果找到，则从该处截断，保留完整对话回合
        如果没有找到，保留所有 messages
        
        Args:
            messages: 消息列表（不包含系统消息）
            max_count: 要保留的最大消息数
            
        Returns:
            int: 截断后保留的消息在 remaining_messages 列表中的起始索引
        """
        num_messages = len(messages)
        if num_messages <= max_count:
            return 0

        # 最多保留 max_count 条消息
        # 理想截断点是 num_messages - max_count
        # 从理想截断点开始寻找 assistant message 作为安全截断起始点
        # 搜索范围 [0, num_messages - max_count], 从 num_messages - max_count 处截断正好为 max_count
        search_end_index = num_messages - max_count

        for i in range(search_end_index, -1, -1):
            message = messages[i]
            role = ""
            if hasattr(message, "role"):
                role = message.role
            elif isinstance(message, dict) and "role" in message:
                role = message.get("role") or ""
            
            if role == "assistant":
                logger.debug(
                    f"[AgentContextLimiter] 找到安全截断点: 索引 {i}, "
                    f"保留 {num_messages - i} 条消息"
                )
                return i
        
        # 没有找到 assistant message, 保留所有
        logger.warning(
            f"[AgentContextLimiter] 未找到安全截断点，保留所有 {num_messages} 条消息"
        )
        return 0
