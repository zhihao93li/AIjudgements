"""数据库模型定义"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Entry(Base):
    """参赛作品表"""
    __tablename__ = "entries"
    
    entry_id = Column(String(100), primary_key=True, index=True)
    image_url = Column(String(500), nullable=False)
    competition_type = Column(String(50), nullable=False, index=True)
    extra_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    judge_results = relationship("JudgeResult", back_populates="entry", cascade="all, delete-orphan")
    debate_sessions = relationship("DebateSession", back_populates="entry", cascade="all, delete-orphan")


class JudgeResult(Base):
    """评委评分结果表"""
    __tablename__ = "judge_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(100), ForeignKey("entries.entry_id"), nullable=False, index=True)
    judge_id = Column(String(50), nullable=False)
    judge_display_name = Column(String(100), nullable=False)
    competition_type = Column(String(50), nullable=False)
    
    # 评分数据
    overall_score = Column(Float, nullable=False)
    dimension_scores = Column(JSON, nullable=True)  # [{"name": "风格统一度", "score": 8, ...}, ...]
    strengths = Column(JSON, nullable=True)  # ["优点1", "优点2", ...]
    weaknesses = Column(JSON, nullable=True)  # ["缺点1", "缺点2", ...]
    one_liner = Column(Text, nullable=True)
    comment_for_audience = Column(Text, nullable=True)
    safety_notes = Column(JSON, nullable=True)
    
    # 调试信息
    raw_output = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    entry = relationship("Entry", back_populates="judge_results")


class DebateSession(Base):
    """群聊讨论会话表"""
    __tablename__ = "debate_sessions"
    
    debate_id = Column(String(150), primary_key=True, index=True)
    entry_id = Column(String(100), ForeignKey("entries.entry_id"), nullable=False, index=True)
    participants = Column(JSON, nullable=False)  # ["chatgpt5_judge", "grok_judge", ...]
    config = Column(JSON, nullable=True)  # {"max_messages": 12, "selector_model": "gpt-4o-mini"}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    entry = relationship("Entry", back_populates="debate_sessions")
    messages = relationship("DebateMessage", back_populates="session", cascade="all, delete-orphan")


class DebateMessage(Base):
    """群聊讨论消息表"""
    __tablename__ = "debate_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    debate_id = Column(String(150), ForeignKey("debate_sessions.debate_id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)  # 消息顺序
    speaker = Column(String(50), nullable=False)  # 发言评委 ID
    content = Column(Text, nullable=False)  # 发言内容
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    session = relationship("DebateSession", back_populates="messages")

