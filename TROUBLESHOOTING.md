# 🔧 故障排查指南

## 常见问题及解决方案

---

## 1. ❌ Chrome 扩展加载失败

### 错误信息
```
未能成功加载扩展程序
清单文件缺失或不可读取
```

### 解决方案
✅ 确保选择 `chrome-extension` 目录，**不是** `icons` 子目录

---

## 2. ❌ 缺少 litellm 模块

### 错误信息
```
ModuleNotFoundError: No module named 'litellm'
```

### 解决方案
```bash
uv sync
```

---

## 3. ❌ API Key 认证失败

### 错误信息
```
AuthenticationError: Incorrect API key provided
```

### 原因
- API Key 和 Base URL 不匹配
- API Key 无效或过期

### 解决方案

编辑 `.env` 文件，确保配置匹配：

**使用 OpenRouter:**
```env
LLM_MODEL=openrouter/google/gemini-2.0-flash-exp:free
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-key-here
```

**使用 OpenAI:**
```env
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
```

---

## 4. ❌ 端口被占用

### 错误信息
```
Address already in use
```

### 解决方案

```bash
# 查找占用进程
netstat -ano | findstr :8001

# 杀死进程
taskkill /PID <PID> /F

# 或使用其他端口
uv run uvicorn automation_tester.entrepreneur_agent_service:app --port 8002
```

---

## 5. ❌ 虚拟环境问题

### 错误信息
```
Multiple top-level packages discovered
```

### 解决方案
```bash
# 重新同步
uv sync
```

---

## 6. ❌ 模块导入错误

### 错误信息
```
ModuleNotFoundError: No module named 'automation_tester'
```

### 解决方案
```bash
uv pip install -e .
```

---

## 7. ⚠️ 文件内容过长

### 警告信息
```
文件过长，截取前 50000 字符
```

### 说明
这是正常的保护机制，防止超过 LLM token 限制

---

## 8. 🔍 调试技巧

### 查看日志
```bash
# Windows
type logs\agent_service_20251113.log

# PowerShell
Get-Content logs\agent_service_20251113.log -Tail 50 -Wait
```

### 测试 API
```bash
# 健康检查
curl http://localhost:8001/health

# API 文档
# 浏览器访问: http://localhost:8001/docs
```

### 检查环境
```bash
uv run python scripts/test_env.py
uv run python scripts/test_import.py
```

---

## 9. 🚀 启动检查清单

- [ ] ✅ 已安装 uv
- [ ] ✅ 已运行 `uv sync`
- [ ] ✅ `.env` 文件配置正确
- [ ] ✅ API Key 有效
- [ ] ✅ 端口 8001 未被占用
- [ ] ✅ Chrome 插件已加载

---

## 10. 📞 获取帮助

如果问题仍未解决：

1. 查看完整日志
2. 检查服务状态
3. 重新初始化项目：
   ```bash
   rmdir /s /q .venv
   uv sync
   start.bat
   ```

---

**相关文档**: [START_GUIDE.md](START_GUIDE.md) | [README.md](README.md)
