# 43X Agent Tester - Chrome Extension

43X Agent 自动化测试工具的 Chrome 浏览器插件部分。

## 文件结构

```
chrome-extension/
├── manifest.json          # Chrome 插件配置文件
├── background.js          # 后台服务 Worker
├── content.js            # 内容脚本（注入到 43X 页面）
├── popup.html            # 弹出窗口 HTML
├── popup.js              # 弹出窗口逻辑
├── popup.css             # 弹出窗口样式
├── icons/                # 图标文件
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md             # 本文件
```

## 安装方法

1. 打开 Chrome 浏览器
2. 访问 `chrome://extensions/`
3. 启用"开发者模式"
4. 点击"加载已解压的扩展程序"
5. 选择 `chrome-extension` 目录

## 使用方法

1. 确保 Python Agent Service 已启动（`http://localhost:8001`）
2. 打开 43X 对话页面（`http://localhost:3000`）
3. 点击浏览器工具栏中的插件图标
4. 上传场景配置文件（.json）和项目资料
5. 点击"开始测试"按钮
6. 插件将自动完成对话测试

## 开发说明

- `content.js`: 负责 DOM 监听、消息提取、自动输入
- `background.js`: 负责与 Python Agent Service 通信、状态管理
- `popup.js`: 负责用户界面交互、文件上传、进度显示
