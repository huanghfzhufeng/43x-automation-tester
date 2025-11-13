#!/usr/bin/env python3
"""
43X Agent Service 启动脚本

快速启动 Python Agent Service
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_environment():
    """检查必要的环境变量"""
    print("🔍 检查环境配置...")

    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ 错误: .env 文件不存在")
        print("请创建 .env 文件并配置以下变量:")
        print("  LLM_API_KEY=your_api_key_here")
        print("  APP_AGENT_SERVICE_PORT=8001")
        return False

    # 加载环境变量
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("❌ 错误: LLM_API_KEY 未配置")
        print("请在 .env 文件中设置 LLM_API_KEY")
        return False

    print("✅ 环境配置检查通过")
    return True


def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查 Python 依赖...")

    required_packages = [
        "fastapi",
        "uvicorn",
        "dotenv",
        "google.adk",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            import importlib

            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ 错误: 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False

    print("✅ 依赖检查通过")
    return True


def start_service():
    """启动服务"""
    print("\n" + "=" * 60)
    print("🚀 启动 43X Agent Service")
    print("=" * 60 + "\n")

    # 检查环境
    if not check_environment():
        return 1

    # 检查依赖
    if not check_dependencies():
        return 1

    # 启动服务
    print("\n📡 启动 FastAPI 服务器...")
    port = int(os.getenv("APP_AGENT_SERVICE_PORT", 8001))
    print(f"服务地址: http://localhost:{port}")
    print(f"健康检查: http://localhost:{port}/health")
    print("\n按 Ctrl+C 停止服务\n")

    try:
        # 导入并启动服务
        import uvicorn

        from automation_tester.entrepreneur_agent_service import app

        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    except KeyboardInterrupt:
        print("\n\n⏹️  服务已停止")
        return 0
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(start_service())
