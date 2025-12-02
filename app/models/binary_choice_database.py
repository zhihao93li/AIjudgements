"""二选一模式的数据库模型定义"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.database import Base


class BinaryChoiceEntry(Base):
    """二选一作品表"""
    __tablename__ = "binary_choice_entries"
    
    entry_id = Column(String(100), primary_key=True, index=True)
    
    # 内容（图片或文本，至少一个）
    image_url = Column(String(500), nullable=True)
    text_content = Column(Text, nullable=True)
    
    # 二选一问题设置
    question = Column(Text, nullable=False)  # 问题：如"男朋友有没有错？"
    option_a = Column(String(200), nullable=False)  # 选项 A：如"有错"
    option_b = Column(String(200), nullable=False)  # 选项 B：如"没错"
    
    extra_context = Column(Text, nullable=True)  # 补充说明
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    judge_results = relationship(
        "BinaryChoiceResult", 
        back_populates="entry", 
        cascade="all, delete-orphan"
    )
    debate_sessions = relationship(
        "BinaryChoiceDebateSession", 
        back_populates="entry", 
        cascade="all, delete-orphan"
    )


class BinaryChoiceResult(Base):
    """二选一评委结果表"""
    __tablename__ = "binary_choice_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(
        String(100), 
        ForeignKey("binary_choice_entries.entry_id"), 
        nullable=False, 
        index=True
    )
    
    judge_id = Column(String(50), nullable=False)
    judge_display_name = Column(String(100), nullable=False)
    
    # 选择结果
    choice = Column(String(1), nullable=False)  # 'A' 或 'B'
    choice_label = Column(String(200), nullable=False)  # 对应的选项标签
    
    # 理由
    reasoning = Column(Text, nullable=False)  # 选择理由
    inner_monologue = Column(Text, nullable=True)  # 内心独白
    
    # 调试信息
    raw_output = Column(Text, nullable=True)  # 原始输出
    system_message = Column(Text, nullable=True)  # 系统消息
    user_instruction = Column(Text, nullable=True)  # 用户指令
    model_name = Column(String(100), nullable=True)  # 使用的模型
    debug_context = Column(JSON, nullable=True)  # 调试上下文
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    entry = relationship("BinaryChoiceEntry", back_populates="judge_results")


class BinaryChoiceDebateSession(Base):
    """二选一讨论会话表"""
    __tablename__ = "binary_choice_debate_sessions"
    
    debate_id = Column(String(150), primary_key=True, index=True)
    entry_id = Column(
        String(100), 
        ForeignKey("binary_choice_entries.entry_id"), 
        nullable=False, 
        index=True
    )
    
    participants = Column(JSON, nullable=False)  # 参与评委列表
    config = Column(JSON, nullable=True)  # 配置信息
    
    # 调试信息
    judge_contexts = Column(JSON, nullable=True)
    selector_prompt = Column(Text, nullable=True)
    initial_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    entry = relationship("BinaryChoiceEntry", back_populates="debate_sessions")
    messages = relationship(
        "BinaryChoiceMessage", 
        back_populates="session", 
        cascade="all, delete-orphan"
    )


class BinaryChoiceMessage(Base):
    """二选一讨论消息表"""
    __tablename__ = "binary_choice_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    debate_id = Column(
        String(150), 
        ForeignKey("binary_choice_debate_sessions.debate_id"), 
        nullable=False, 
        index=True
    )
    
    sequence = Column(Integer, nullable=False)  # 消息顺序
    speaker = Column(String(50), nullable=False)  # 发言评委 ID
    content = Column(Text, nullable=False)  # 发言内容
    
    # 调试信息
    context_history = Column(JSON, nullable=True)
    raw_response = Column(Text, nullable=True)
    model_name = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    session = relationship("BinaryChoiceDebateSession", back_populates="messages")
