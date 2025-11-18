"""Pydantic 数据模型（API 请求/响应）"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ 请求模型 ============

class EntryCreate(BaseModel):
    """创建参赛作品的请求"""
    entry_id: str = Field(..., description="作品唯一 ID")
    image_url: str = Field(..., description="图片 URL")
    competition_type: str = Field(..., description="比赛类型，如 outfit/funny")
    extra_text: Optional[str] = Field(None, description="补充说明文本")


class JudgeEntryRequest(BaseModel):
    """评委评分请求（完整流程：阶段一+二）"""
    entry_id: str = Field(..., description="作品唯一 ID")
    image_url: str = Field(..., description="图片 URL")
    competition_type: str = Field(default="outfit", description="比赛类型")
    extra_text: Optional[str] = Field(None, description="补充说明")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entry_id": "entry_001",
                "image_url": "https://example.com/image.jpg",
                "competition_type": "outfit",
                "extra_text": "日常通勤穿搭"
            }
        }


# ============ 响应模型 ============

class DimensionScore(BaseModel):
    """维度评分"""
    name: str = Field(..., description="维度名称")
    score: float = Field(..., description="该维度得分")
    comment: Optional[str] = Field(None, description="该维度点评")


class JudgeResultResponse(BaseModel):
    """单个评委的评分结果"""
    judge_id: str = Field(..., description="评委 ID")
    judge_display_name: str = Field(..., description="评委显示名称")
    overall_score: float = Field(..., description="总分")
    dimension_scores: Optional[List[DimensionScore]] = Field(None, description="维度评分")
    strengths: Optional[List[str]] = Field(None, description="优点列表")
    weaknesses: Optional[List[str]] = Field(None, description="缺点列表")
    one_liner: Optional[str] = Field(None, description="一句话点评")
    comment_for_audience: Optional[str] = Field(None, description="给观众的评语")
    safety_notes: Optional[List[str]] = Field(None, description="安全/合规提示")
    
    class Config:
        from_attributes = True


class DebateMessageResponse(BaseModel):
    """群聊消息"""
    sequence: int = Field(..., description="消息序号")
    speaker: str = Field(..., description="发言者 ID")
    content: str = Field(..., description="发言内容")
    
    class Config:
        from_attributes = True


class DebateResponse(BaseModel):
    """群聊讨论结果"""
    debate_id: str = Field(..., description="讨论会话 ID")
    participants: List[str] = Field(..., description="参与评委列表")
    messages: List[DebateMessageResponse] = Field(..., description="讨论消息列表")
    
    class Config:
        from_attributes = True


class EntryResponse(BaseModel):
    """作品完整信息（包含评分和讨论）"""
    entry_id: str
    image_url: str
    competition_type: str
    extra_text: Optional[str] = None
    created_at: datetime
    judge_results: List[JudgeResultResponse] = Field(default_factory=list)
    debate: Optional[DebateResponse] = None
    
    class Config:
        from_attributes = True


class JudgeEntryResponse(BaseModel):
    """评委评分完整响应（阶段一+二）"""
    entry_id: str = Field(..., description="作品 ID")
    competition_type: str = Field(..., description="比赛类型")
    judge_results: List[JudgeResultResponse] = Field(..., description="所有评委的评分")
    sorted_results: List[JudgeResultResponse] = Field(..., description="按分数排序的评委评分")
    debate: Optional[DebateResponse] = Field(None, description="群聊讨论内容")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entry_id": "entry_001",
                "competition_type": "outfit",
                "judge_results": [
                    {
                        "judge_id": "chatgpt5_judge",
                        "judge_display_name": "ChatGPT-5 评委",
                        "overall_score": 8.5,
                        "strengths": ["色彩搭配好", "风格统一"],
                        "weaknesses": ["配饰简单"],
                        "one_liner": "整体不错，有提升空间"
                    }
                ],
                "sorted_results": [],
                "debate": {
                    "debate_id": "entry_001_debate",
                    "participants": ["chatgpt5_judge", "grok_judge"],
                    "messages": [
                        {
                            "sequence": 1,
                            "speaker": "grok_judge",
                            "content": "我觉得鞋子和上半身风格有点分裂..."
                        }
                    ]
                }
            }
        }

