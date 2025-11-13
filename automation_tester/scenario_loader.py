"""
Scenario Loader

场景配置加载器，负责解析 JSON 配置文件和项目资料文件。
支持 JSON、MD、TXT 等格式。
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ScenarioLoader:
    """场景配置加载器"""

    @staticmethod
    def load_json_config(file_path: str) -> dict[str, Any]:
        """
        加载 JSON 配置文件

        Args:
            file_path: JSON 文件路径

        Returns:
            dict: 解析后的配置

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式错误
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"配置文件不存在: {file_path}")

            with open(path, encoding="utf-8") as f:
                config: dict[str, Any] = json.load(f)

            logger.info(f"✅ 加载配置文件成功: {file_path}")
            return config

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 格式错误: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            raise

    @staticmethod
    def load_text_file(file_path: str) -> str:
        """
        加载文本文件（MD/TXT）

        Args:
            file_path: 文件路径

        Returns:
            str: 文件内容
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            with open(path, encoding="utf-8") as f:
                content = f.read()

            logger.info(f"✅ 加载文本文件成功: {file_path} ({len(content)} 字符)")
            return content

        except Exception as e:
            logger.error(f"❌ 加载文本文件失败: {e}")
            raise

    @staticmethod
    async def load_file(file_path: str) -> str:
        """
        加载任意类型的文件（MD/TXT）

        Args:
            file_path: 文件路径

        Returns:
            str: 文件内容
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 根据文件扩展名判断类型
            suffix = path.suffix.lower()

            # 文本文件直接读取
            if suffix in [".txt", ".md"]:
                return ScenarioLoader.load_text_file(file_path)

            # 不支持的文件类型，尝试作为文本读取
            logger.warning(f"⚠️ 不支持的文件类型: {suffix}，尝试作为文本读取")
            return ScenarioLoader.load_text_file(file_path)

        except Exception as e:
            logger.error(f"❌ 加载文件失败: {e}")
            raise

    @staticmethod
    def validate_config(config: dict[str, Any]) -> bool:
        """
        验证配置文件的有效性

        Args:
            config: 配置字典

        Returns:
            bool: 是否有效

        Raises:
            ValueError: 配置无效
        """
        required_fields = ["scenario_name", "company_name"]

        for field in required_fields:
            if field not in config:
                raise ValueError(f"缺少必填字段: {field}")

        # 验证 expected_result 字段（如果存在）
        if "expected_result" in config:
            valid_results = ["passed", "rejected", "pending"]
            if config["expected_result"] not in valid_results:
                raise ValueError(
                    f"expected_result 必须是以下值之一: {valid_results}, "
                    f"当前值: {config['expected_result']}"
                )

        logger.info(f"✅ 配置验证通过: {config['scenario_name']}")
        return True

    @staticmethod
    async def load_scenario(
        config_path: str, files_paths: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """
        加载完整的场景配置

        Args:
            config_path: JSON 配置文件路径
            files_paths: 附加文件路径字典 {filename: filepath}

        Returns:
            dict: 完整的场景配置
        """
        # 加载 JSON 配置
        config = ScenarioLoader.load_json_config(config_path)

        # 验证配置
        ScenarioLoader.validate_config(config)

        # 加载附加文件
        if files_paths:
            files_content = {}
            for filename, filepath in files_paths.items():
                try:
                    # 使用新的 load_file 方法支持多种格式
                    content = await ScenarioLoader.load_file(filepath)
                    files_content[filename] = content
                except Exception as e:
                    logger.warning(f"⚠️ 加载文件失败，跳过: {filename} - {e}")

            if files_content:
                # 合并文件内容到 bp_content
                bp_parts = []
                for filename, content in files_content.items():
                    bp_parts.append(f"## 文件: {filename}\n\n{content}")
                config["bp_content"] = "\n\n".join(bp_parts)

        logger.info(f"✅ 场景加载完成: {config['scenario_name']}")
        return config
