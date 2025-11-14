"""
文件处理模块使用示例

演示如何使用文件处理模块解析各种格式的文档
"""

import asyncio
import json

from automation_tester.file import FileService, FileType


async def example_parse_single_file():
    """示例1: 解析单个文件"""
    print("\n" + "=" * 60)
    print("示例1: 解析单个文件")
    print("=" * 60)
    
    # 假设有一个PDF文件
    file_path = "商业计划书.pdf"
    
    print(f"\n正在解析: {file_path}")
    
    try:
        all_text = []
        async for chunk in FileService.read_content(file_path, FileType.PDF):
            all_text.append(chunk)
            print(f"  提取了 {len(chunk)} 字符")
        
        full_text = "\n\n".join(all_text)
        print(f"\n✅ 解析完成，总共 {len(full_text)} 字符")
        print(f"   前100字符: {full_text[:100]}...")
        
    except FileNotFoundError:
        print(f"⚠️  文件不存在: {file_path}")
    except Exception as e:
        print(f"❌ 解析失败: {e}")


async def example_parse_multiple_files():
    """示例2: 批量解析多个文件"""
    print("\n" + "=" * 60)
    print("示例2: 批量解析多个文件")
    print("=" * 60)
    
    files = {
        "商业计划书.pdf": FileType.PDF,
        "财务报表.docx": FileType.WORD,
        "产品介绍.pptx": FileType.PPT,
        "README.md": FileType.MD,
    }
    
    results = {}
    
    for filename, file_type in files.items():
        print(f"\n正在解析: {filename}")
        
        try:
            chunks = []
            async for chunk in FileService.read_content(filename, file_type):
                chunks.append(chunk)
            
            full_text = "\n\n".join(chunks)
            results[filename] = {
                "success": True,
                "chunks": len(chunks),
                "total_chars": len(full_text),
                "preview": full_text[:100],
            }
            print(f"  ✅ 成功: {len(chunks)} 个文本块, {len(full_text)} 字符")
            
        except FileNotFoundError:
            results[filename] = {
                "success": False,
                "error": "文件不存在",
            }
            print(f"  ⚠️  文件不存在")
            
        except Exception as e:
            results[filename] = {
                "success": False,
                "error": str(e),
            }
            print(f"  ❌ 失败: {e}")
    
    print("\n" + "-" * 60)
    print("解析结果汇总:")
    print(json.dumps(results, ensure_ascii=False, indent=2))


async def example_auto_detect_type():
    """示例3: 自动检测文件类型"""
    print("\n" + "=" * 60)
    print("示例3: 自动检测文件类型")
    print("=" * 60)
    
    from automation_tester.utils.file_utils import get_file_extension
    
    files = [
        "商业计划书.pdf",
        "财务报表.docx",
        "产品介绍.pptx",
        "README.md",
        "数据.txt",
        "logo.png",
    ]
    
    file_type_map = {
        "pdf": FileType.PDF,
        "docx": FileType.WORD,
        "doc": FileType.WORD,
        "pptx": FileType.PPT,
        "ppt": FileType.PPT,
        "md": FileType.MD,
        "txt": FileType.TXT,
        "jpg": FileType.IMAGE,
        "jpeg": FileType.IMAGE,
        "png": FileType.IMAGE,
        "webp": FileType.IMAGE,
    }
    
    print("\n文件类型检测:")
    for filename in files:
        ext = get_file_extension(filename)
        file_type = file_type_map.get(ext, FileType.UNKNOWN)
        print(f"  {filename:30s} -> {ext:10s} -> {file_type.value}")


async def example_with_options():
    """示例4: 使用自定义选项"""
    print("\n" + "=" * 60)
    print("示例4: 使用自定义选项")
    print("=" * 60)
    
    file_path = "长文档.txt"
    
    print(f"\n正在解析: {file_path}")
    print("使用自定义分块参数:")
    print("  - chunk_size: 512")
    print("  - chunk_overlap: 100")
    
    try:
        chunks = []
        async for chunk in FileService.read_content(
            file_path,
            FileType.TXT,
            chunk_size=512,
            chunk_overlap=100,
        ):
            chunks.append(chunk)
            print(f"  文本块 {len(chunks)}: {len(chunk)} 字符")
        
        print(f"\n✅ 解析完成，共 {len(chunks)} 个文本块")
        
    except FileNotFoundError:
        print(f"⚠️  文件不存在: {file_path}")
    except Exception as e:
        print(f"❌ 解析失败: {e}")


async def example_api_integration():
    """示例5: 与API集成"""
    print("\n" + "=" * 60)
    print("示例5: 与API集成（模拟）")
    print("=" * 60)
    
    # 模拟API请求数据
    request_data = {
        "scenario_config": {
            "scenario_name": "AI SaaS项目",
            "company_name": "智能科技有限公司",
            "industry": "人工智能",
        },
        "files_path": {
            "商业计划书.pdf": "C:/docs/bp.pdf",
            "财务报表.docx": "C:/docs/finance.docx",
        },
    }
    
    print("\n模拟API请求:")
    print(json.dumps(request_data, ensure_ascii=False, indent=2))
    
    print("\n处理文件...")
    
    from automation_tester.utils.file_utils import get_file_extension
    
    bp_content_parts = []
    
    for filename, filepath in request_data["files_path"].items():
        print(f"\n  处理: {filename}")
        
        try:
            # 检测文件类型
            ext = get_file_extension(filename)
            file_type_map = {
                "pdf": FileType.PDF,
                "docx": FileType.WORD,
                "pptx": FileType.PPT,
                "md": FileType.MD,
                "txt": FileType.TXT,
            }
            file_type = file_type_map.get(ext, FileType.TXT)
            
            print(f"    文件类型: {file_type.value}")
            
            # 解析文件
            content_chunks = []
            async for chunk in FileService.read_content(filepath, file_type):
                content_chunks.append(chunk)
            
            content = "\n\n".join(content_chunks)
            
            # 长度限制
            max_chars = 50000
            if len(content) > max_chars:
                print(f"    ⚠️  内容过长，截断到 {max_chars} 字符")
                content = content[:max_chars] + "\n\n[... 内容过长，已截断 ...]"
            
            bp_content_parts.append(f"## 文件: {filename}\n\n{content}")
            print(f"    ✅ 成功: {len(content)} 字符")
            
        except FileNotFoundError:
            print(f"    ⚠️  文件不存在")
            bp_content_parts.append(f"## 文件: {filename}\n\n[文件不存在]")
            
        except Exception as e:
            print(f"    ❌ 失败: {e}")
            bp_content_parts.append(f"## 文件: {filename}\n\n[解析失败: {str(e)}]")
    
    # 合并内容
    final_content = "\n\n".join(bp_content_parts)
    
    print("\n" + "-" * 60)
    print(f"最终内容长度: {len(final_content)} 字符")
    print(f"内容预览:\n{final_content[:200]}...")


async def main():
    """运行所有示例"""
    print("=" * 60)
    print("文件处理模块使用示例")
    print("=" * 60)
    
    # 运行各个示例
    await example_auto_detect_type()
    # await example_parse_single_file()  # 需要实际文件
    # await example_parse_multiple_files()  # 需要实际文件
    # await example_with_options()  # 需要实际文件
    await example_api_integration()
    
    print("\n" + "=" * 60)
    print("示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
