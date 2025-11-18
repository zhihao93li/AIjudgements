"""评委系统工具函数"""

from typing import Optional
from autogen_ext.models.openai import OpenAIChatCompletionClient
from app.config import get_settings

settings = get_settings()


def make_vision_client(model: str, family: str = "openai") -> OpenAIChatCompletionClient:
    """
    创建支持多模态的模型客户端
    
    Args:
        model: 模型名称（如 gpt-4o）
        family: 模型家族（如 openai）
    
    Returns:
        OpenAIChatCompletionClient 实例
    """
    return OpenAIChatCompletionClient(
        model=model,
        api_key=settings.llm_gateway_api_key,
        base_url=settings.llm_gateway_base_url,
        model_capabilities={
            "vision": True,  # 关键：告诉 AutoGen 这是多模态模型
            "function_calling": False,
            "json_output": True,
        },
    )


def make_text_client(model: str, family: str = "openai") -> OpenAIChatCompletionClient:
    """
    创建纯文本模型客户端（用于选择器等）
    
    Args:
        model: 模型名称
        family: 模型家族
    
    Returns:
        OpenAIChatCompletionClient 实例
    """
    return OpenAIChatCompletionClient(
        model=model,
        api_key=settings.llm_gateway_api_key,
        base_url=settings.llm_gateway_base_url,
        model_capabilities={
            "vision": False,
            "function_calling": False,
            "json_output": False,
        },
    )


def get_model_for_judge(judge_id: str) -> str:
    """
    根据评委 ID 获取对应的模型名称
    
    Args:
        judge_id: 评委 ID（如 chatgpt5_judge）
    
    Returns:
        模型名称
    """
    model_mapping = {
        "chatgpt5_judge": settings.model_chatgpt5,
        "grok_judge": settings.model_grok,
        "gemini_judge": settings.model_gemini,
        "doubao_judge": settings.model_doubao,
        "qwen_judge": settings.model_qwen,
    }
    
    return model_mapping.get(judge_id, settings.model_chatgpt5)


def parse_json_from_response(content: str) -> Optional[dict]:
    """
    从模型响应中提取 JSON
    
    支持：
    - 纯 JSON
    - Markdown 代码块包裹的 JSON
    
    Args:
        content: 模型响应内容
    
    Returns:
        解析后的 dict，失败返回 None
    """
    import json
    import re
    
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 尝试从 markdown 代码块中提取
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(code_block_pattern, content, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试查找第一个完整的 JSON 对象
    json_pattern = r"\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}"
    match = re.search(json_pattern, content, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None

