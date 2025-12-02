"""二选一模式的 Pydantic 数据模型"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============ 请求模型 ============

class BinaryChoiceRequest(BaseModel):
    """二选一评判请求"""
    entry_id: Optional[str] = Field(default="", description="作品唯一 ID（留空则自动生成）")
    
    # 内容：图片或文本
    image_url: Optional[str] = Field(None, description="图片 URL（与 text_content 至少提供一个）")
    text_content: Optional[str] = Field(None, description="文本内容（与 image_url 至少提供一个）")
    
    # 二选一问题设置
    question: str = Field(..., description="二选一问题，如：男朋友有没有错？")
    option_a: str = Field(..., description="选项 A，如：有错")
    option_b: str = Field(..., description="选项 B，如：没错")
    
    # 可选的补充说明
    extra_context: Optional[str] = Field(None, description="补充说明/背景信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "男朋友有没有错？",
                "option_a": "有错",
                "option_b": "没错",
                "image_url": "https://example.com/image.jpg",
                "extra_context": "情侣吵架场景"
            }
        }


# ============ 响应模型 ============

class BinaryChoiceJudgeResult(BaseModel):
    """单个评委的二选一结果"""
    judge_id: str = Field(..., description="评委 ID")
    judge_display_name: str = Field(..., description="评委显示名称")
    
    # 选择
    choice: str = Field(..., description="选择的答案: 'A' 或 'B'")
    choice_label: str = Field(..., description="选择的选项标签，如 '有错' 或 '没错'")
    
    # 理由
    reasoning: str = Field(..., description="选择该答案的简短理由")
    inner_monologue: Optional[str] = Field(None, description="内心独白")
    
    class Config:
        from_attributes = True


class BinaryChoiceDebateMessage(BaseModel):
    """二选一讨论消息"""
    sequence: int = Field(..., description="消息序号")
    speaker: str = Field(..., description="发言者 ID")
    content: str = Field(..., description="发言内容")
    
    class Config:
        from_attributes = True


class BinaryChoiceDebateResponse(BaseModel):
    """二选一讨论结果"""
    debate_id: str = Field(..., description="讨论会话 ID")
    participants: List[str] = Field(..., description="参与评委列表")
    messages: List[BinaryChoiceDebateMessage] = Field(..., description="讨论消息列表")
    
    class Config:
        from_attributes = True


class BinaryChoiceResponse(BaseModel):
    """二选一评判完整响应"""
    entry_id: str = Field(..., description="作品 ID")
    
    # 问题信息
    question: str = Field(..., description="二选一问题")
    option_a: str = Field(..., description="选项 A")
    option_b: str = Field(..., description="选项 B")
    
    # 内容
    image_url: Optional[str] = Field(None, description="图片 URL")
    text_content: Optional[str] = Field(None, description="文本内容")
    
    # 统计
    choice_a_count: int = Field(..., description="选择 A 的评委数量")
    choice_b_count: int = Field(..., description="选择 B 的评委数量")
    
    # 评委结果
    judge_results: List[BinaryChoiceJudgeResult] = Field(..., description="所有评委的选择和理由")
    
    # 讨论
    debate: Optional[BinaryChoiceDebateResponse] = Field(None, description="群聊讨论内容")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entry_id": "binary_entry_001",
                "question": "男朋友有没有错？",
                "option_a": "有错",
                "option_b": "没错",
                "choice_a_count": 3,
                "choice_b_count": 2,
                "judge_results": [
                    {
                        "judge_id": "ChatGPT",
                        "judge_display_name": "ChatGPT",
                        "choice": "A",
                        "choice_label": "有错",
                        "reasoning": "从沟通角度来看，他应该主动道歉"
                    }
                ],
                "debate": {
                    "debate_id": "binary_entry_001_debate",
                    "participants": ["ChatGPT", "Grok"],
                    "messages": [
                        {
                            "sequence": 1,
                            "speaker": "Grok",
                            "content": "我觉得这事儿得两说着..."
                        }
                    ]
                }
            }
        }
