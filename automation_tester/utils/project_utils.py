"""
项目信息和记忆管理工具函数
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def format_project_info(scenario_config: Dict[str, Any]) -> str:
    """
    格式化项目信息为文本
    
    Args:
        scenario_config: 场景配置字典
        
    Returns:
        str: 格式化后的项目信息
    """
    info_parts = []
    
    # 基础信息
    if "company_name" in scenario_config:
        info_parts.append(f"- 公司名称：{scenario_config['company_name']}")
    if "industry" in scenario_config:
        info_parts.append(f"- 行业：{scenario_config['industry']}")
    if "product" in scenario_config:
        info_parts.append(f"- 产品：{scenario_config['product']}")
    if "revenue" in scenario_config:
        info_parts.append(f"- 营收：{scenario_config['revenue']}")
    if "team" in scenario_config:
        info_parts.append(f"- 团队：{scenario_config['team']}")
    if "funding_need" in scenario_config:
        info_parts.append(f"- 融资需求：{scenario_config['funding_need']}")
    
    # 详细信息
    if scenario_config.get("project_details"):
        details = scenario_config["project_details"]
        info_parts.append("\n## 详细信息")
        info_parts.append(json.dumps(details, ensure_ascii=False, indent=2))
    
    return "\n".join(info_parts)


def build_memory_context(memory_manager) -> str:
    """
    构建长期记忆上下文
    
    优化策略：
    1. 只保留最近的 N 个摘要（避免无限增长）
    2. 压缩摘要格式（去掉冗余标题）
    3. 限制关键事实数量
    4. 总长度控制在 3000 字符以内
    
    Args:
        memory_manager: 记忆管理器实例
        
    Returns:
        str: 格式化的长期记忆摘要文本
    """
    if not memory_manager:
        return ""
    
    summaries = memory_manager.long_term.get_all_summaries()
    if not summaries:
        return ""
    
    # 策略1: 只保留最近的 5 个摘要（覆盖约 15 轮对话）
    MAX_SUMMARIES = 5
    recent_summaries = summaries[-MAX_SUMMARIES:] if len(summaries) > MAX_SUMMARIES else summaries
    
    context_parts = ["## 📚 历史对话摘要\n"]
    context_parts.append("⚠️ 以下是早期对话的关键信息，避免重复回答：\n")
    
    for i, summary in enumerate(recent_summaries, 1):
        # 策略2: 压缩格式，去掉冗余标题
        context_parts.append(f"**Round {summary.round_range[0]}-{summary.round_range[1]}**: {summary.summary[:200]}")
        
        # 策略3: 只保留前 3 个关键事实
        if summary.key_facts:
            facts_to_show = summary.key_facts[:3]
            for fact in facts_to_show:
                context_parts.append(f"  • {fact[:100]}")
            context_parts.append("")
    
    context_parts.append("---\n")
    
    result = "\n".join(context_parts)
    
    # 策略4: 总长度控制
    MAX_CONTEXT_LENGTH = 3000
    if len(result) > MAX_CONTEXT_LENGTH:
        result = result[:MAX_CONTEXT_LENGTH] + "\n...(更早的对话已省略)\n---\n"
        logger.warning(f"⚠️ 记忆上下文超长，已截断到 {MAX_CONTEXT_LENGTH} 字符")
    
    logger.debug(f"📝 构建记忆上下文: {len(result)} 字符, {len(recent_summaries)}/{len(summaries)} 个摘要")
    
    return result
