# 43X Automation Tester

> 基于 RPA 技术的 43X 投资 Agent 自动化测试工具

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📖 项目简介

43X Automation Tester 是一个专为 43X.AI 投资评估系统设计的自动化测试工具。它通过 RPA（机器人流程自动化）技术，模拟创业者与投资 Agent 的真实对话场景，实现端到端的自动化测试。

### 核心特性

- 🤖 **智能 Agent 模拟**：基于 Google ADK 构建的创业者 Agent，能够根据项目资料智能回答投资人问题
- 📚 **RAG 检索增强**：使用 ChromaDB 向量数据库，实现项目资料的语义检索和动态注入
- 🧠 **三层记忆管理**：短期记忆、长期记忆和素材库的协同管理，支持长对话上下文
- 📄 **多格式文件支持**：支持 PDF、Word、PPT、Markdown 等多种文件格式的智能解析
- 🔄 **会话持久化**：本地文件存储，支持会话恢复和历史记录查询
- 🎯 **AI 信息提取**：自动从上传的商业计划书中提取结构化信息，快速生成测试配置
- 🌐 **Chrome 插件集成**：无缝集成到 43X.AI 网页端，实现一键启动测试

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Chrome Extension                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Popup   │  │Background│  │ Content  │                  │
│  │   UI     │◄─┤  Worker  │◄─┤  Script  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Service (Port 8001)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    API Layer                          │   │
│  │  /api/test/start  /api/test/answer  /api/test/stop  │   │
│  │  /api/extract/info  /api/cache/stats                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────┼────────────────────────────┐   │
│  │         EntrepreneurAgentManager                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │   RAG    │  │  Memory  │  │  Local   │          │   │
│  │  │ Service  │  │ Manager  │  │ Storage  │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────┼────────────────────────────┐   │
│  │              Google ADK Agent                        │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  LlmAgent (Entrepreneur)                     │   │   │
│  │  │  - Instruction (Prompts)                     │   │   │
│  │  │  - Model Config (GPT-4o-mini)                │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ OpenAI   │  │ ChromaDB │  │   File   │                  │
│  │   API    │  │ (Vector) │  │  System  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 📦 项目结构

```
43x-automation-tester/
├── automation_tester/              # Python 后端核心模块
│   ├── __init__.py                # 模块导出
│   ├── agents.py                  # Agent 定义和管理器
│   ├── api.py                     # FastAPI 服务入口
│   ├── config.py                  # 配置管理（LLM、App、Agent）
│   ├── prompts.py                 # Prompt 模板库
│   ├── utils.py                   # 工具函数
│   │
│   ├── services/                  # 服务层
│   │   ├── __init__.py
│   │   ├── rag_service.py        # RAG 检索服务（ChromaDB）
│   │   ├── memory_manager.py     # 三层记忆管理
│   │   └── local_storage.py      # 本地文件存储
│   │
│   ├── file/                      # 文件处理模块
│   │   ├── __init__.py
│   │   ├── file.py               # 文件服务入口
│   │   ├── base_file.py          # 文件基类
│   │   ├── pdf.py                # PDF 解析
│   │   ├── word.py               # Word 解析
│   │   ├── ppt.py                # PPT 解析
│   │   ├── markdown.py           # Markdown 解析
│   │   ├── text.py               # 文本解析
│   │   └── image.py              # 图片解析（OCR）
│   │
│   └── utils/                     # 工具模块
│       ├── __init__.py
│       ├── adk_config.py         # ADK 配置
│       ├── message.py            # 消息构建
│       ├── project_utils.py      # 项目信息格式化
│       ├── text_chunker.py       # 文本分块
│       ├── file_utils.py         # 文件工具
│       └── logging_config.py     # 日志配置
│
├── chrome-extension/               # Chrome 插件
│   ├── manifest.json              # 插件配置文件
│   ├── popup.html                 # 弹窗界面
│   ├── popup.js                   # 弹窗逻辑（1382行）
│   ├── popup.css                  # 弹窗样式
│   ├── background.js              # 后台服务（Service Worker）
│   ├── content.js                 # 内容脚本（页面注入）
│   ├── settings.html              # 设置页面
│   ├── settings.js                # 设置逻辑
│   ├── settings.css               # 设置样式
│   └── icons/                     # 插件图标
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
│
├── tests/                         # 测试文件
├── sessions/                      # 会话数据存储（运行时生成）
├── chroma_db/                     # ChromaDB 向量数据库（运行时生成）
├── logs/                          # 日志文件（运行时生成）
│
├── .env                           # 环境变量配置
├── .env.example                   # 环境变量示例
├── requirements.txt               # Python 依赖
├── pyproject.toml                 # 项目配置（Ruff、Mypy、Pytest）
└── README.md                      # 项目文档
```

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Chrome 浏览器
- OpenAI API Key（或兼容的 API）

### 1. 克隆项目

```bash
git clone <repository-url>
cd 43x-automation-tester
```

### 2. 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，并填写必要的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置以下必填项：

```env
# LLM 配置（必填）
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-api-key-here

# 或使用 OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-openrouter-api-key-here

# Azure OpenAI Embeddings（推荐，用于 RAG）
AZURE_EMBEDDING_AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_EMBEDDING_API_KEY=your-azure-api-key
AZURE_EMBEDDING_AZURE_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_API_VERSION=2023-05-15
```

### 4. 启动 FastAPI 服务

```bash
python -m uvicorn automation_tester.api:app --host 0.0.0.0 --port 8001 --reload
```

服务启动后，访问 http://localhost:8001/docs 查看 API 文档。

### 5. 安装 Chrome 插件

1. 打开 Chrome 浏览器
2. 访问 `chrome://extensions/`
3. 开启右上角的"开发者模式"
4. 点击"加载已解压的扩展程序"
5. 选择项目中的 `chrome-extension` 目录
6. 插件安装成功后，会在浏览器工具栏显示图标

### 6. 开始测试

1. 打开 43X.AI 对话页面（localhost:3000 或 43x.ai）
2. 点击 Chrome 工具栏的插件图标
3. 上传商业计划书文件（支持 PDF、Word、PPT 等）
4. AI 自动提取信息并填充表单
5. 检查配置后，点击"开始测试"
6. 插件会自动模拟创业者回答投资人的问题

## 🎯 核心功能详解

### 1. 智能 Agent 模拟

**EntrepreneurAgentManager** 是核心管理器，负责：

- **Agent 生命周期管理**：创建、运行、销毁
- **服务协调**：RAG、Memory、Storage 的统一调度
- **对话流程控制**：问题接收、回答生成、状态更新

```python
# 创建 Agent Manager
agent_manager = EntrepreneurAgentManager(
    scenario_config={
        "scenario_name": "AI SaaS 测试",
        "company_name": "示例科技",
        "industry": "企业服务",
        "product": "AI 客服系统",
        # ... 更多配置
    },
    rag_config={
        "chunk_size": 800,
        "chunk_overlap": 100,
        "top_k": 3
    }
)

# 回答问题
answer = await agent_manager.answer("你们的核心竞争力是什么？")
```

### 2. RAG 检索增强生成

**RAGService** 基于 ChromaDB 实现语义检索：

- **文本向量化**：使用 OpenAI Embeddings 或 Azure Embeddings
- **语义检索**：根据投资人问题检索相关项目资料
- **动态注入**：将检索结果注入到 Agent 的 Prompt 中

```python
# 初始化 RAG 服务
rag_service = RAGService(
    session_id="test_session_123",
    persist_dir="./chroma_db"
)

# 添加文档
chunks = ["公司成立于2020年...", "核心产品是AI客服...", ...]
rag_service.add_chunks(chunks, metadatas=[...])

# 检索相关内容
results = rag_service.search("核心竞争力", top_k=3)
for result in results:
    print(result.chunk)  # 相关文本片段
```

### 3. 三层记忆管理

**MemoryManager** 实现了短期、长期和素材库的协同管理：

- **短期记忆（ShortTermMemory）**：保留最近 5-8 轮对话
- **长期记忆（LongTermMemory）**：存储历史对话的摘要
- **素材库（MaterialStore）**：封装 RAG 服务，管理项目资料

```python
# 初始化记忆管理器
memory_manager = MemoryManager(
    session_id="test_session_123",
    max_short_term_rounds=8,
    compress_rounds=5
)

# 添加对话
memory_manager.add_user_message("你们的营收情况如何？")
memory_manager.add_assistant_message("我们去年 ARR 达到 500 万...")

# 自动压缩：当短期记忆满时，自动生成摘要并移入长期记忆
```

### 4. 多格式文件支持

**FileService** 支持多种文件格式的智能解析：

| 文件类型 | 支持格式 | 解析方式 |
|---------|---------|---------|
| PDF | .pdf | pyzerox（OCR + 文本提取） |
| Word | .docx, .doc | python-docx |
| PPT | .pptx, .ppt | python-pptx |
| Markdown | .md | markdown + beautifulsoup4 |
| 文本 | .txt | 直接读取 |
| 图片 | .jpg, .png, .webp | OCR（可选） |

```python
from automation_tester.file import FileService, FileType

# 异步读取文件内容
async for chunk in FileService.read_content("bp.pdf", FileType.PDF):
    print(chunk)
```

### 5. AI 信息提取

**智能表单填充**：上传商业计划书后，自动调用 LLM 提取结构化信息：

```python
# API 端点：POST /api/extract/info
{
  "files_content": {
    "商业计划书.pdf": "base64_encoded_content"
  }
}

# 返回提取的信息
{
  "success": true,
  "extracted_info": {
    "company_name": "示例科技",
    "industry": "AI SaaS",
    "product": "企业级 AI 客服系统",
    "revenue": "ARR 500万",
    "team": "15人",
    "funding_need": "A轮 2000万",
    "customers": ["阿里巴巴", "腾讯"],
    "technology": "私有化部署 + 端侧推理"
  }
}
```

### 6. 会话持久化

**LocalFileStorage** 提供本地文件存储：

```
sessions/
└── test_scenario_1234567890/
    ├── metadata.json      # 会话元信息
    ├── events.jsonl       # 对话历史（每行一个事件）
    ├── state.json         # 结构化状态
    └── summary.json       # 记忆摘要
```

## 🔧 API 接口文档

### 测试管理

#### 启动测试
```http
POST /api/test/start
Content-Type: application/json

{
  "scenario_config": {
    "scenario_name": "AI SaaS 测试",
    "company_name": "示例科技",
    "industry": "企业服务",
    "product": "AI 客服系统",
    "revenue": "ARR 500万",
    "team": "15人",
    "funding_need": "A轮 2000万"
  },
  "files_content": {
    "商业计划书.pdf": "base64_encoded_content"
  }
}

Response:
{
  "session_id": "test_scenario_1234567890",
  "scenario_name": "AI SaaS 测试",
  "company_name": "示例科技"
}
```

#### 获取回答
```http
POST /api/test/answer
Content-Type: application/json

{
  "session_id": "test_scenario_1234567890",
  "question": "你们的核心竞争力是什么？"
}

Response:
{
  "answer": "我们的核心竞争力是私有化部署能力...",
  "round_number": 1,
  "elapsed_time": 2.5
}
```

#### 停止测试
```http
POST /api/test/stop
Content-Type: application/json

{
  "session_id": "test_scenario_1234567890"
}

Response:
{
  "status": "success",
  "message": "Test stopped"
}
```

### 信息提取

#### AI 提取信息
```http
POST /api/extract/info
Content-Type: application/json

{
  "files_content": {
    "商业计划书.pdf": "base64_encoded_content"
  }
}

Response:
{
  "success": true,
  "extracted_info": {
    "company_name": "示例科技",
    "industry": "AI SaaS",
    ...
  },
  "files_processed": 1
}
```

### 缓存管理

#### 获取缓存统计
```http
GET /api/cache/stats

Response:
{
  "size": 3,
  "max_size": 10,
  "hits": 15,
  "misses": 3,
  "evictions": 1,
  "hit_rate": "83.33%",
  "timeout_seconds": 3600,
  "session_details": [...]
}
```

#### 清理过期会话
```http
POST /api/cache/cleanup

Response:
{
  "status": "success",
  "cleaned_count": 2,
  "cleaned_sessions": ["session_1", "session_2"],
  "remaining_sessions": 1
}
```

### 健康检查

```http
GET /health

Response:
{
  "status": "ok",
  "active_sessions": 3
}
```

## ⚙️ 配置说明

### LLM 配置

支持多种 LLM 提供商：

**OpenAI**
```env
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
```

**OpenRouter**
```env
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-...
```

**Azure OpenAI**
```env
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://your-resource.openai.azure.com/
LLM_API_KEY=...
```

### RAG 配置

```env
# ChromaDB 存储路径
CHROMA_DB_PATH=./chroma_db

# 文本分块配置
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# 检索配置
RAG_TOP_K=3
RAG_SIMILARITY_THRESHOLD=0.7
```

### 记忆管理配置

```env
# 短期记忆最大轮次
MAX_SHORT_TERM_ROUNDS=8

# 压缩触发轮次
COMPRESS_ROUNDS=5

# 会话存储路径
SESSION_STORAGE_PATH=./sessions
```

### Chrome 插件配置

在插件设置页面可配置：

- **Agent Service URL**：默认 `http://localhost:8001`
- **最大轮次**：默认 50
- **输入延迟**：默认 1000ms
- **消息超时**：默认 60s
- **自动重试**：默认开启
- **调试模式**：默认关闭
- **自动截图**：默认开启

## 🧪 开发指南

### 代码规范

项目使用 Ruff 进行代码检查和格式化：

```bash
# 检查代码
ruff check automation_tester/

# 自动修复
ruff check --fix automation_tester/

# 格式化代码
ruff format automation_tester/
```

### 类型检查

使用 Mypy 进行类型检查：

```bash
mypy automation_tester/
```

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_agents.py

# 生成覆盖率报告
pytest --cov=automation_tester --cov-report=html
```

### 日志配置

日志系统支持多种级别和格式：

```python
from automation_tester.utils.logging_config import setup_logging, get_logger

# 初始化日志系统
setup_logging()

# 获取 logger
logger = get_logger("my_module")

# 使用日志上下文
from automation_tester.utils.logging_config import LogContext

with LogContext(logger, "处理任务"):
    # 自动记录开始和结束
    do_something()
```

### 添加新的文件格式支持

1. 在 `automation_tester/file/` 创建新的解析器
2. 继承 `BaseFile` 类
3. 实现 `parse_text()` 方法
4. 在 `FileService` 中注册新类型

```python
from automation_tester.file.base_file import BaseFile

class ExcelFile(BaseFile):
    async def parse_text(self, **kwargs):
        # 实现 Excel 解析逻辑
        yield "parsed content"
```

## 📊 性能优化

### LRU 会话缓存

- **缓存大小**：最多 10 个会话
- **超时时间**：1 小时
- **自动清理**：每 5 分钟清理过期会话
- **命中率**：通常 > 80%

### RAG 检索优化

- **分块策略**：递归分块，保持语义完整性
- **向量维度**：1536（text-embedding-3-small）
- **检索算法**：HNSW（余弦相似度）
- **Top-K**：默认 3，可配置

### 记忆压缩策略

- **短期记忆**：保留最近 8 轮
- **压缩触发**：每 5 轮生成摘要
- **摘要长度**：< 150 字符
- **关键事实**：最多 3 个

## 🐛 常见问题

### 1. 服务启动失败

**问题**：`LLM_API_KEY 未设置`

**解决**：检查 `.env` 文件是否正确配置，确保 `LLM_API_KEY` 已填写。

### 2. RAG 检索失败

**问题**：`chromadb 未安装`

**解决**：
```bash
pip install chromadb
```

### 3. 文件解析失败

**问题**：`不支持的文件类型`

**解决**：检查文件扩展名，确保在支持列表中（.pdf, .docx, .pptx, .md, .txt）。

### 4. Chrome 插件无法连接

**问题**：`Could not establish connection`

**解决**：
1. 确保 FastAPI 服务正在运行（http://localhost:8001）
2. 检查 CORS 配置
3. 刷新 43X.AI 页面

### 5. 回答质量不佳

**问题**：Agent 回答不准确或重复

**解决**：
1. 检查上传的商业计划书是否完整
2. 调整 RAG 检索参数（top_k, chunk_size）
3. 优化 Prompt 模板（`automation_tester/prompts.py`）

## 📈 性能指标

基于实际测试的性能数据：

| 指标 | 数值 |
|-----|------|
| 平均响应时间 | 2-5 秒 |
| 缓存命中率 | 80-90% |
| 并发会话数 | 10 个 |
| 文件解析速度 | 1-3 秒/MB |
| RAG 检索延迟 | 100-300ms |
| 记忆压缩时间 | 500-1000ms |

## 🔐 安全性

- **API Key 保护**：环境变量存储，不提交到代码库
- **输入验证**：所有 API 端点进行参数验证
- **文件大小限制**：最大 10MB
- **会话隔离**：每个会话独立的向量数据库
- **CORS 配置**：仅允许特定域名访问

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码审查标准

- ✅ 通过 Ruff 检查
- ✅ 通过 Mypy 类型检查
- ✅ 添加单元测试
- ✅ 更新文档
- ✅ 遵循现有代码风格

## 📝 更新日志

### v1.0.0 (2024-01-XX)

- ✨ 初始版本发布
- 🤖 实现创业者 Agent 模拟
- 📚 集成 RAG 检索增强
- 🧠 实现三层记忆管理
- 📄 支持多种文件格式
- 🌐 Chrome 插件集成
- 🎯 AI 信息提取功能

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👥 团队

43X Team

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至：[your-email@example.com]

---

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**