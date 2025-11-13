"""
测试导入模块

验证所有模块是否可以正常导入
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")

    try:
        # 测试配置模块
        print("  ✓ 导入 config...")
        from automation_tester.config import AppConfig, LLMConfig

        print(f"    - LLM Model: {LLMConfig.model}")
        print(f"    - Agent Service Port: {AppConfig.agent_service_port}")

        # 测试工具模块
        print("  ✓ 导入 utils...")
        from automation_tester.utils import (
            DEFAULT_AGENT_CONFIG,
            build_model_message,
            build_user_message,
        )

        print(f"    - DEFAULT_AGENT_CONFIG keys: {list(DEFAULT_AGENT_CONFIG.keys())}")

        # 测试日志模块
        print("  ✓ 导入 logging_config...")
        from automation_tester.logging_config import (
            LogContext,
            get_logger,
            setup_logging,
        )

        logger = get_logger("test")
        print(f"    - Logger name: {logger.name}")

        # 测试场景加载器
        print("  ✓ 导入 scenario_loader...")
        from automation_tester.scenario_loader import ScenarioLoader

        print(f"    - ScenarioLoader methods: {dir(ScenarioLoader)[:5]}...")

        # 测试 Agent
        print("  ✓ 导入 entrepreneur_agent...")
        from automation_tester.entrepreneur_agent import EntrepreneurAgent

        print(f"    - EntrepreneurAgent class: {EntrepreneurAgent.__name__}")

        # 测试 Service
        print("  ✓ 导入 entrepreneur_agent_service...")
        from automation_tester.entrepreneur_agent_service import app

        print(f"    - FastAPI app title: {app.title}")

        print("\n✅ 所有模块导入成功！")
        return True

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
