"""
消息构建工具

提供构建 Google ADK 消息的工具函数
"""

from google.genai import types


def build_user_message(text: str) -> types.UserContent:
    """
    构建用户消息

    Args:
        text: 消息文本内容

    Returns:
        types.UserContent: 用户消息对象
    """
    return types.UserContent(parts=[types.Part(text=text)])


def build_model_message(text: str) -> types.ModelContent:
    """
    构建模型消息

    Args:
        text: 消息文本内容

    Returns:
        types.ModelContent: 模型消息对象
    """
    return types.ModelContent(parts=[types.Part(text=text)])
