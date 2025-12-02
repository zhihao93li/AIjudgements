"""二选一模式的数据库 CRUD 操作"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.binary_choice_database import (
    BinaryChoiceEntry,
    BinaryChoiceResult,
    BinaryChoiceDebateSession,
    BinaryChoiceMessage,
)


async def save_binary_choice_entry(
    db: AsyncSession,
    entry_id: str,
    question: str,
    option_a: str,
    option_b: str,
    image_url: str = None,
    text_content: str = None,
    extra_context: str = None,
) -> BinaryChoiceEntry:
    """
    保存二选一作品
    
    Args:
        db: 数据库会话
        entry_id: 作品 ID
        question: 二选一问题
        option_a: 选项 A
        option_b: 选项 B
        image_url: 图片 URL（可选）
        text_content: 文本内容（可选）
        extra_context: 额外上下文（可选）
    
    Returns:
        保存的 BinaryChoiceEntry 对象
    """
    entry = BinaryChoiceEntry(
        entry_id=entry_id,
        question=question,
        option_a=option_a,
        option_b=option_b,
        image_url=image_url,
        text_content=text_content,
        extra_context=extra_context,
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    logger.info(f"二选一作品保存成功: {entry_id}")
    return entry


async def save_binary_choice_results(
    db: AsyncSession,
    entry_id: str,
    judge_results: list[dict],
) -> None:
    """
    保存二选一评委结果
    
    Args:
        db: 数据库会话
        entry_id: 作品 ID
        judge_results: 评委结果列表
    """
    for result_data in judge_results:
        # 跳过有错误的结果
        if "error" in result_data:
            continue
        
        result = BinaryChoiceResult(
            entry_id=entry_id,
            judge_id=result_data["judge_id"],
            judge_display_name=result_data["judge_display_name"],
            choice=result_data["choice"],
            choice_label=result_data["choice_label"],
            reasoning=result_data["reasoning"],
            inner_monologue=result_data.get("inner_monologue"),
            raw_output=result_data.get("raw_output"),
            system_message=result_data.get("system_message"),
            user_instruction=result_data.get("user_instruction"),
            model_name=result_data.get("model_name"),
            debug_context=result_data.get("debug_context"),
        )
        
        db.add(result)
    
    await db.commit()
    logger.info(f"二选一评委结果保存成功: entry_id={entry_id}, 共 {len(judge_results)} 个评委")


async def save_binary_choice_debate(
    db: AsyncSession,
    entry_id: str,
    debate_id: str,
    participants: list[str],
    messages: list[dict],
    config: dict = None,
    judge_contexts: dict = None,
    selector_prompt: str = None,
    initial_message: str = None,
) -> None:
    """
    保存二选一讨论会话
    
    Args:
        db: 数据库会话
        entry_id: 作品 ID
        debate_id: 讨论 ID
        participants: 参与评委列表
        messages: 消息列表
        config: 配置信息
        judge_contexts: 评委上下文
        selector_prompt: 选择器提示词
        initial_message: 初始消息
    """
    # 创建讨论会话
    session = BinaryChoiceDebateSession(
        debate_id=debate_id,
        entry_id=entry_id,
        participants=participants,
        config=config,
        judge_contexts=judge_contexts,
        selector_prompt=selector_prompt,
        initial_message=initial_message,
    )
    
    db.add(session)
    await db.flush()  # flush 以获取会话 ID
    
    # 添加消息
    for idx, msg_data in enumerate(messages):
        message = BinaryChoiceMessage(
            debate_id=debate_id,
            sequence=idx + 1,
            speaker=msg_data["speaker"],
            content=msg_data["content"],
            context_history=msg_data.get("context_history"),
            raw_response=msg_data.get("raw_response"),
            model_name=msg_data.get("model_name"),
        )
        db.add(message)
    
    await db.commit()
    logger.info(f"二选一讨论会话保存成功: debate_id={debate_id}, 共 {len(messages)} 条消息")


async def get_binary_choice_entry_by_id(
    db: AsyncSession,
    entry_id: str,
) -> BinaryChoiceEntry | None:
    """
    查询二选一作品及其关联数据
    
    Args:
        db: 数据库会话
        entry_id: 作品 ID
    
    Returns:
        BinaryChoiceEntry 对象或 None
    """
    stmt = (
        select(BinaryChoiceEntry)
        .where(BinaryChoiceEntry.entry_id == entry_id)
        .options(
            selectinload(BinaryChoiceEntry.judge_results),
            selectinload(BinaryChoiceEntry.debate_sessions).selectinload(
                BinaryChoiceDebateSession.messages
            ),
        )
    )
    
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    
    if entry:
        logger.info(f"查询到二选一作品: {entry_id}")
    else:
        logger.warning(f"二选一作品不存在: {entry_id}")
    
    return entry
