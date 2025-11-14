"""
图片解析工具模块
"""

import base64
import io
import logging

from PIL import Image

from automation_tester.config import LLMConfig

logger = logging.getLogger(__name__)


async def parse_image_with_llm(pil_image: Image.Image) -> str:
    """
    使用LLM解析图片内容
    
    Args:
        pil_image: PIL Image对象
        
    Returns:
        str: 图片描述文本
    """
    try:
        # 将图片转换为base64
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # 使用OpenAI兼容的API解析图片
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            base_url=LLMConfig.base_url,
            api_key=LLMConfig.api_key,
        )
        
        response = await client.chat.completions.create(
            model=LLMConfig.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请详细描述这张图片的内容，包括文字、图表、数据等所有信息。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )
        
        return response.choices[0].message.content or "无法解析图片内容"
        
    except Exception as e:
        logger.error(f"图片解析失败: {e}")
        return f"[图片解析失败: {str(e)}]"
