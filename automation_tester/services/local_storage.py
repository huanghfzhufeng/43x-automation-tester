"""
Local File Storage Service

提供本地文件存储功能，用于持久化会话数据
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LocalFileStorage:
    """
    本地文件存储服务

    提供会话数据的本地持久化功能，包括：
    - metadata.json: 会话元信息
    - events.jsonl: 对话历史（每行一个事件）
    - state.json: 结构化状态数据
    """

    def __init__(self, session_id: str, base_dir: str = "./sessions"):
        """
        初始化本地文件存储

        Args:
            session_id: 会话 ID
            base_dir: 存储根目录
        """
        self.session_id = session_id
        self.base_dir = base_dir
        self.session_dir = Path(base_dir) / session_id

        # 文件路径
        self.metadata_file = self.session_dir / "metadata.json"
        self.events_file = self.session_dir / "events.jsonl"
        self.state_file = self.session_dir / "state.json"

        # 创建会话目录
        self.session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LocalFileStorage 初始化: session_id={session_id}, dir={self.session_dir}")

    def save_metadata(self, metadata: dict[str, Any]):
        """
        保存会话元信息

        Args:
            metadata: 元信息字典
        """
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.debug(f"✅ 保存元信息: {self.metadata_file}")
        except Exception as e:
            logger.error(f"❌ 保存元信息失败: {e}", exc_info=True)
            raise

    def load_metadata(self) -> dict[str, Any] | None:
        """
        加载会话元信息

        Returns:
            元信息字典，如果文件不存在则返回 None
        """
        if not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

            logger.debug(f"✅ 加载元信息: {self.metadata_file}")
            return metadata
        except Exception as e:
            logger.error(f"❌ 加载元信息失败: {e}", exc_info=True)
            return None

    def append_event(self, event: dict[str, Any]):
        """
        追加对话事件到 JSONL 文件

        Args:
            event: 事件字典
        """
        try:
            # 添加时间戳
            if "timestamp" not in event:
                event["timestamp"] = time.time()

            # 追加到文件
            with open(self.events_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

            logger.debug(f"✅ 追加事件: role={event.get('role', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ 追加事件失败: {e}", exc_info=True)
            raise

    def load_events(self, last_n: int | None = None) -> list[dict[str, Any]]:
        """
        加载对话历史

        Args:
            last_n: 只加载最后 N 条事件（可选）

        Returns:
            事件列表
        """
        if not self.events_file.exists():
            return []

        try:
            events = []
            with open(self.events_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))

            # 只返回最后 N 条
            if last_n is not None and len(events) > last_n:
                events = events[-last_n:]

            logger.debug(f"✅ 加载事件: {len(events)} 条")
            return events
        except Exception as e:
            logger.error(f"❌ 加载事件失败: {e}", exc_info=True)
            return []

    def save_state(self, state: dict[str, Any]):
        """
        保存结构化状态数据

        Args:
            state: 状态字典
        """
        try:
            # 过滤掉不可序列化的对象（如 RAGService）
            serializable_state = {}
            for key, value in state.items():
                try:
                    # 尝试序列化
                    json.dumps(value)
                    serializable_state[key] = value
                except (TypeError, ValueError):
                    # 跳过不可序列化的对象
                    logger.debug(f"⚠️ 跳过不可序列化的状态: {key}")

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(serializable_state, f, ensure_ascii=False, indent=2)

            logger.debug(f"✅ 保存状态: {len(serializable_state)} 个键")
        except Exception as e:
            logger.error(f"❌ 保存状态失败: {e}", exc_info=True)
            raise

    def load_state(self) -> dict[str, Any] | None:
        """
        加载结构化状态数据

        Returns:
            状态字典，如果文件不存在则返回 None
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, encoding="utf-8") as f:
                state = json.load(f)

            logger.debug(f"✅ 加载状态: {len(state)} 个键")
            return state
        except Exception as e:
            logger.error(f"❌ 加载状态失败: {e}", exc_info=True)
            return None

    def get_event_count(self) -> int:
        """
        获取事件数量

        Returns:
            事件总数
        """
        if not self.events_file.exists():
            return 0

        try:
            count = 0
            with open(self.events_file, encoding="utf-8") as f:
                for _ in f:
                    count += 1
            return count
        except Exception as e:
            logger.error(f"❌ 获取事件数量失败: {e}", exc_info=True)
            return 0

    def clear_all(self):
        """清空所有数据文件"""
        try:
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            if self.events_file.exists():
                self.events_file.unlink()
            if self.state_file.exists():
                self.state_file.unlink()

            logger.info(f"✅ 清空会话数据: {self.session_id}")
        except Exception as e:
            logger.error(f"❌ 清空数据失败: {e}", exc_info=True)
            raise
