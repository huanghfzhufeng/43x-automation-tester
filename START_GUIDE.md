# 🚀 启动指南

## 📋 前置要求

1. **Python 3.10+**
2. **uv** (Python 包管理器)
3. **Chrome 浏览器**
4. **LLM API Key** (OpenRouter 或 OpenAI)

---

## 🔧 安装 uv

```bash
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证安装
uv --version
```

---

## 🎯 快速启动

### 方式 1：一键启动（推荐）

```bash
# Windows
start.bat

# PowerShell
.\start.ps1
```

### 方式 2：手动启动

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入 API Key

# 3. 启动服务
uv run python -m automation_tester.entrepreneur_agent_service
```

### 方式 3：开发模式（自动重载）

```bash
start-dev.bat
```

---

## ⚙️ 配置 API Key

编辑 `.env` 文件：

```env
# 使用 OpenRouter (推荐)
LLM_MODEL=openrouter/google/gemini-2.0-flash-exp:free
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-key-here

# 或使用 OpenAI
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
```

---

## 🔌 安装 Chrome 插件

1. 打开 `chrome://extensions/`
2. 开启"开发者模式"
3. 点击"加载已解压的扩展程序"
4. **选择 `chrome-extension` 目录**

⚠️ **注意**：不要选择 `icons` 子目录！

---

## ✅ 验证安装

```bash
# 健康检查
curl http://localhost:8001/health

# 查看 API 文档
# 浏览器访问: http://localhost:8001/docs
```

---

## 🧪 运行测试

```bash
# 测试导入
uv run python scripts/test_import.py

# 测试环境
uv run python scripts/test_env.py
```

---

## 📝 使用流程

1. ✅ 启动 Agent Service
2. ✅ 安装 Chrome 插件
3. ✅ 访问 43X 深评页面
4. ✅ 点击插件图标
5. ✅ 上传场景配置
6. ✅ 开始测试

---

## 🔍 常用命令

```bash
# 启动服务
uv run python -m automation_tester.entrepreneur_agent_service

# 开发模式（自动重载）
uv run uvicorn automation_tester.entrepreneur_agent_service:app --reload

# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check .

# 类型检查
uv run mypy automation_tester/
```

---

## 📚 相关文档

- [README.md](README.md) - 项目概览
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查
- [scenarios/SCENARIOS_GUIDE.md](scenarios/SCENARIOS_GUIDE.md) - 场景指南

---

**遇到问题？** 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
