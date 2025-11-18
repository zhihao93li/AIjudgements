"""数据库 CRUD 操作"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.database import Entry, JudgeResult, DebateSession, DebateMessage


async def save_entry(
    db: AsyncSession,
    entry_id: str,
    image_url: str,
    competition_type: str,
    extra_text: Optional[str] = None,
) -> Entry:
    """保存或更新参赛作品"""
    # 检查是否已存在
    result = await db.execute(select(Entry).where(Entry.entry_id == entry_id))
    entry = result.scalar_one_or_none()
    
    if entry:
        # 更新现有作品
        entry.image_url = image_url
        entry.competition_type = competition_type
        entry.extra_text = extra_text
    else:
        # 创建新作品
        entry = Entry(
            entry_id=entry_id,
            image_url=image_url,
            competition_type=competition_type,
            extra_text=extra_text,
        )
        db.add(entry)
    
    await db.commit()
    await db.refresh(entry)
    return entry


async def save_judge_results(
    db: AsyncSession,
    entry_id: str,
    judge_results: List[dict],
) -> List[JudgeResult]:
    """保存评委评分结果"""
    results = []
    
    for judge_data in judge_results:
        result = JudgeResult(
            entry_id=entry_id,
            judge_id=judge_data.get("judge_id", ""),
            judge_display_name=judge_data.get("judge_display_name", ""),
            competition_type=judge_data.get("competition_type", ""),
            overall_score=judge_data.get("overall_score", 0.0),
            dimension_scores=judge_data.get("dimension_scores"),
            strengths=judge_data.get("strengths"),
            weaknesses=judge_data.get("weaknesses"),
            one_liner=judge_data.get("one_liner"),
            comment_for_audience=judge_data.get("comment_for_audience"),
            safety_notes=judge_data.get("safety_notes"),
            raw_output=judge_data.get("raw_output"),
        )
        db.add(result)
        results.append(result)
    
    await db.commit()
    return results


async def save_debate_session(
    db: AsyncSession,
    entry_id: str,
    debate_id: str,
    participants: List[str],
    messages: List[dict],
    config: Optional[dict] = None,
) -> DebateSession:
    """保存群聊讨论会话"""
    # 检查是否已存在，如果存在则先删除旧的
    result = await db.execute(select(DebateSession).where(DebateSession.debate_id == debate_id))
    existing_session = result.scalar_one_or_none()
    
    if existing_session:
        # 删除旧的消息
        await db.execute(
            select(DebateMessage).where(DebateMessage.debate_id == debate_id)
        )
        await db.delete(existing_session)
        await db.commit()
    
    # 创建新会话
    session = DebateSession(
        debate_id=debate_id,
        entry_id=entry_id,
        participants=participants,
        config=config or {},
    )
    db.add(session)
    
    # 创建消息
    for idx, msg_data in enumerate(messages):
        message = DebateMessage(
            debate_id=debate_id,
            sequence=idx + 1,
            speaker=msg_data.get("speaker", ""),
            content=msg_data.get("content", ""),
        )
        db.add(message)
    
    await db.commit()
    await db.refresh(session)
    return session


async def get_entry_by_id(db: AsyncSession, entry_id: str) -> Optional[Entry]:
    """根据 ID 获取作品（包含关联数据）"""
    result = await db.execute(
        select(Entry)
        .where(Entry.entry_id == entry_id)
        .options(
            selectinload(Entry.judge_results),
            selectinload(Entry.debate_sessions).selectinload(DebateSession.messages),
        )
    )
    return result.scalar_one_or_none()


async def get_judge_results_by_entry(
    db: AsyncSession, entry_id: str
) -> List[JudgeResult]:
    """获取某个作品的所有评委评分"""
    result = await db.execute(
        select(JudgeResult)
        .where(JudgeResult.entry_id == entry_id)
        .order_by(JudgeResult.overall_score.desc())
    )
    return list(result.scalars().all())


async def get_debate_by_entry(
    db: AsyncSession, entry_id: str
) -> Optional[DebateSession]:
    """获取某个作品的群聊讨论"""
    result = await db.execute(
        select(DebateSession)
        .where(DebateSession.entry_id == entry_id)
        .options(selectinload(DebateSession.messages))
    )
    return result.scalar_one_or_none()

