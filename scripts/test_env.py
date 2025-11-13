#!/usr/bin/env python3
"""
测试环境变量配置

验证 .env 文件是否正确加载
"""

from dotenv import load_dotenv
import os
from pathlib import Path

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

print("=" * 60)
print("📋 环境变量配置检查")
print("=" * 60)

# 必填配置
required_vars = {
