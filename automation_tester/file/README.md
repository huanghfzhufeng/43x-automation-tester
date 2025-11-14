# 文件处理模块使用说明

## 概述

这个模块提供了统一的文件解析接口，支持多种文档格式的文本提取，包括：

- **PDF**: 使用 pyzerox 进行智能解析
- **Word** (docx/doc): 提取文本、表格和图片（通过LLM识别）
- **PowerPoint** (pptx/ppt): 提取文本和图片
- **Markdown** (md): 解析文本和表格
- **文本** (txt): 分块处理
- **图片** (jpg/png/webp): 通过LLM识别内容

## 快速开始

### 基本使用

```python
from automation_tester.file import FileService, FileType

# 解析PDF文件
async for text_chunk in FileService.read_content("document.pdf", FileType.PDF):
    print(text_chunk)

# 解析Word文档
async for text_chunk in FileService.read_content("report.docx", FileType.WORD):
    print(text_chunk)
```

### 在 Agent Service 中使用

现在 `entrepreneur_agent_service.py` 支持两种方式传入文件：

#### 方式1: 直接传入文件内容（兼容旧方式）

```json
{
  "scenario_config": {...},
  "files_content": {
    "商业计划书.txt": "文件内容字符串..."
  }
}
```

#### 方式2: 传入文件路径（新方式，推荐）

```json
{
  "scenario_config": {...},
  "files_path": {
    "商业计划书.pdf": "C:/path/to/document.pdf",
    "财务报表.docx": "C:/path/to/report.docx"
  }
}
```

使用方式2时，系统会：
1. 根据文件扩展名自动识别文件类型
2. 使用对应的解析器提取文本
3. 对图片进行LLM识别
4. 自动分块和长度限制

## 文件类型映射

| 扩展名 | FileType | 解析器 |
|--------|----------|--------|
| .pdf | PDF | PDFFile (pyzerox) |
| .docx, .doc | WORD | WordFile (python-docx) |
| .pptx, .ppt | PPT | PPTFile (python-pptx) |
| .md | MD | MarkdownFile |
| .txt | TXT | TextFile |
| .jpg, .jpeg, .png, .webp | IMAGE | ImageFile |

## 配置选项

### 文本分块参数

```python
async for chunk in FileService.read_content(
    "document.txt", 
    FileType.TXT,
    chunk_size=1024,        # 分块大小
    chunk_overlap=200       # 重叠大小
):
    print(chunk)
```

### 图片识别

Word和PPT中的图片会自动通过LLM识别，使用配置：
- 模型: `LLMConfig.model`
- API: `LLMConfig.base_url`
- 密钥: `LLMConfig.api_key`

## 架构设计

```
automation_tester/file/
├── __init__.py           # 模块入口
├── base_file.py          # 基类，定义统一接口
├── file.py               # FileService，统一调度
├── pdf.py                # PDF解析器
├── word.py               # Word解析器
├── ppt.py                # PPT解析器
├── markdown.py           # Markdown解析器
├── text.py               # 文本解析器
└── image.py              # 图片解析器

automation_tester/utils/
├── file_utils.py         # 文件工具函数
├── text_chunker.py       # 文本分块工具
└── image_parser.py       # 图片识别工具
```

## 核心特性

### 1. 统一接口
所有文件类型通过 `FileService.read_content()` 统一调用

### 2. 异步生成器
使用 `AsyncGenerator` 逐块返回文本，支持大文件处理

### 3. 智能识别
- 自动根据扩展名识别文件类型
- Word/PPT中的图片自动通过LLM识别
- 表格转JSON格式保持结构

### 4. 长度控制
- 单个文件最大50,000字符（约12,500 tokens）
- 超长自动截断并标记

### 5. 错误处理
- 文件不存在、格式错误等异常统一捕获
- 返回友好的错误信息

## 依赖项

确保安装以下依赖：

```bash
pip install pyzerox python-docx python-pptx pillow markdown beautifulsoup4 langchain openai
```

## 测试

运行测试脚本：

```bash
python tests/test_file_processing.py
```

## 注意事项

1. **OSS支持**: 当前版本暂不支持OSS文件，仅支持本地文件
2. **图片识别**: 需要配置有效的LLM API密钥
3. **PDF解析**: pyzerox需要额外的系统依赖
4. **内存占用**: 大文件会占用较多内存，建议分块处理

## 未来改进

- [ ] 支持OSS文件直接解析
- [ ] 引入RAG技术，智能检索相关片段
- [ ] 支持更多文件格式（Excel、CSV等）
- [ ] 优化图片识别性能
- [ ] 添加缓存机制
