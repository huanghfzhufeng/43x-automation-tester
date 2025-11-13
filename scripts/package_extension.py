#!/usr/bin/env python3
"""
Chrome 插件打包脚本

将 Chrome 插件打包为 .zip 文件，便于分发
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path


def create_extension_package():
    """创建插件包"""
    print("=" * 60)
    print("📦 打包 Chrome 插件")
    print("=" * 60 + "\n")

    # 源目录
    source_dir = Path(__file__).parent / "chrome-extension"
    if not source_dir.exists():
        print("❌ 错误: chrome-extension 目录不存在")
        return 1

    # 输出目录
    output_dir = Path(__file__).parent / "dist"
    output_dir.mkdir(exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"43x-agent-tester_{timestamp}.zip"
    zip_path = output_dir / zip_filename

    # 排除的文件
    exclude_patterns = ["*.crx", "*.pem", "*.zip", ".DS_Store", "Thumbs.db"]

    print(f"📁 源目录: {source_dir}")
    print(f"📦 输出文件: {zip_path}\n")

    # 创建 ZIP 文件
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # 排除隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                # 检查是否应该排除
                if any(file.endswith(pattern.replace("*", "")) for pattern in exclude_patterns):
                    continue

                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir.parent)

                zipf.write(file_path, arcname)
                file_count += 1
                print(f"  ✅ {arcname}")

    # 显示结果
    file_size = zip_path.stat().st_size
    size_mb = file_size / (1024 * 1024)

    print(f"\n{'=' * 60}")
    print("✅ 打包完成!")
    print(f"{'=' * 60}")
    print(f"📦 文件: {zip_path}")
    print(f"📊 大小: {size_mb:.2f} MB ({file_size:,} bytes)")
    print(f"📁 文件数: {file_count}")
    print("\n💡 安装方法:")
    print("   1. 打开 Chrome 浏览器")
    print("   2. 访问 chrome://extensions/")
    print("   3. 开启'开发者模式'")
    print("   4. 点击'加载已解压的扩展程序'")
    print("   5. 选择解压后的目录\n")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(create_extension_package())
