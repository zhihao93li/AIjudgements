"""API 路由定义"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.schemas import (
    JudgeEntryRequest,
    JudgeEntryResponse,
    EntryResponse,
    JudgeResultResponse,
    DebateResponse,
    DebateMessageResponse,
    DimensionScore,
)
from app.db.database import get_db
from app.db.crud import (
    save_entry,
    save_judge_results,
    save_debate_session,
    get_entry_by_id,
)
from app.judges import score_image_with_all_judges, run_debate_for_entry

router = APIRouter()


@router.post("/judge_entry", response_model=JudgeEntryResponse)
async def judge_entry(
    request: JudgeEntryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    评委评分完整流程（阶段一 + 阶段二）
    
    1. 保存作品信息
    2. 阶段一：多评委并发看图评分
    3. 保存评分结果
    4. 阶段二：评委群聊讨论
    5. 保存讨论记录
    6. 返回完整结果
    """
    logger.info(f"收到评分请求: entry_id={request.entry_id}, type={request.competition_type}")
    
    try:
        # 1. 保存作品信息
        entry = await save_entry(
            db=db,
            entry_id=request.entry_id,
            image_url=request.image_url,
            competition_type=request.competition_type,
            extra_text=request.extra_text,
        )
        logger.info(f"作品保存成功: {entry.entry_id}")
        
    except Exception as e:
        logger.error(f"保存作品失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存作品失败: {str(e)}")
    
    # 2. 阶段一：多评委并发评分
    try:
        stage_one_result = await score_image_with_all_judges(
            image_url=request.image_url,
            entry_id=request.entry_id,
            competition_type=request.competition_type,
            extra_text=request.extra_text,
        )
        
        if "error" in stage_one_result:
            logger.error(f"阶段一评分失败: {stage_one_result['error']}")
            raise HTTPException(status_code=500, detail=stage_one_result["error"])
        
        judge_results = stage_one_result["judge_results"]
        sorted_results = stage_one_result["sorted_results"]
        
        logger.info(f"阶段一评分完成，共 {len(judge_results)} 个评委")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"阶段一评分异常: {e}")
        raise HTTPException(status_code=500, detail=f"阶段一评分失败: {str(e)}")
    
    # 3. 保存评分结果
    try:
        await save_judge_results(db=db, entry_id=request.entry_id, judge_results=judge_results)
        logger.info(f"评分结果保存成功")
        
    except Exception as e:
        logger.error(f"保存评分结果失败: {e}")
        # 不中断流程，继续执行
    
    # 4. 阶段二：评委群聊讨论
    debate_result = None
    
    try:
        stage_two_result = await run_debate_for_entry(
            entry_id=request.entry_id,
            competition_type=request.competition_type,
            judge_results=sorted_results,  # 使用排序后的结果
        )
        
        if "error" in stage_two_result:
            logger.warning(f"阶段二讨论失败: {stage_two_result['error']}")
        else:
            debate_messages = stage_two_result["messages"]
            participants = stage_two_result.get("participants", [])
            
            logger.info(f"阶段二讨论完成，共 {len(debate_messages)} 条消息")
            
            # 5. 保存讨论记录
            try:
                debate_id = f"{request.entry_id}_debate"
                await save_debate_session(
                    db=db,
                    entry_id=request.entry_id,
                    debate_id=debate_id,
                    participants=participants,
                    messages=debate_messages,
                    config={"max_messages": 12},
                )
                logger.info(f"讨论记录保存成功")
                
                # 构建返回的 debate 对象
                debate_result = DebateResponse(
                    debate_id=debate_id,
                    participants=participants,
                    messages=[
                        DebateMessageResponse(
                            sequence=idx + 1,
                            speaker=msg["speaker"],
                            content=msg["content"],
                        )
                        for idx, msg in enumerate(debate_messages)
                    ],
                )
                
            except Exception as e:
                logger.error(f"保存讨论记录失败: {e}")
        
    except Exception as e:
        logger.error(f"阶段二讨论异常: {e}")
        # 不中断流程，返回时 debate 为 None
    
    # 6. 构建响应
    judge_result_responses = [
        JudgeResultResponse(
            judge_id=r["judge_id"],
            judge_display_name=r["judge_display_name"],
            overall_score=r["overall_score"],
            dimension_scores=[
                DimensionScore(**ds) for ds in r.get("dimension_scores", [])
            ] if r.get("dimension_scores") else None,
            strengths=r.get("strengths"),
            weaknesses=r.get("weaknesses"),
            one_liner=r.get("one_liner"),
            comment_for_audience=r.get("comment_for_audience"),
            safety_notes=r.get("safety_notes"),
        )
        for r in judge_results
    ]
    
    sorted_result_responses = [
        JudgeResultResponse(
            judge_id=r["judge_id"],
            judge_display_name=r["judge_display_name"],
            overall_score=r["overall_score"],
            dimension_scores=[
                DimensionScore(**ds) for ds in r.get("dimension_scores", [])
            ] if r.get("dimension_scores") else None,
            strengths=r.get("strengths"),
            weaknesses=r.get("weaknesses"),
            one_liner=r.get("one_liner"),
            comment_for_audience=r.get("comment_for_audience"),
            safety_notes=r.get("safety_notes"),
        )
        for r in sorted_results
    ]
    
    response = JudgeEntryResponse(
        entry_id=request.entry_id,
        competition_type=request.competition_type,
        judge_results=judge_result_responses,
        sorted_results=sorted_result_responses,
        debate=debate_result,
    )
    
    logger.success(f"完整评分流程完成: entry_id={request.entry_id}")
    
    return response


@router.get("/judge_entry/{entry_id}", response_model=EntryResponse)
async def get_entry_result(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    查询某个作品的评分和讨论记录
    
    Args:
        entry_id: 作品 ID
    
    Returns:
        作品完整信息（包含评分和讨论）
    """
    logger.info(f"查询作品: entry_id={entry_id}")
    
    # 查询作品及关联数据
    entry = await get_entry_by_id(db=db, entry_id=entry_id)
    
    if not entry:
        logger.warning(f"作品不存在: {entry_id}")
        raise HTTPException(status_code=404, detail=f"作品不存在: {entry_id}")
    
    # 构建响应
    judge_results = [
        JudgeResultResponse(
            judge_id=jr.judge_id,
            judge_display_name=jr.judge_display_name,
            overall_score=jr.overall_score,
            dimension_scores=[
                DimensionScore(**ds) for ds in jr.dimension_scores
            ] if jr.dimension_scores else None,
            strengths=jr.strengths,
            weaknesses=jr.weaknesses,
            one_liner=jr.one_liner,
            comment_for_audience=jr.comment_for_audience,
            safety_notes=jr.safety_notes,
        )
        for jr in entry.judge_results
    ]
    
    # 处理讨论记录
    debate = None
    if entry.debate_sessions:
        debate_session = entry.debate_sessions[0]  # 假设只有一个讨论会话
        debate = DebateResponse(
            debate_id=debate_session.debate_id,
            participants=debate_session.participants,
            messages=[
                DebateMessageResponse(
                    sequence=msg.sequence,
                    speaker=msg.speaker,
                    content=msg.content,
                )
                for msg in sorted(debate_session.messages, key=lambda m: m.sequence)
            ],
        )
    
    response = EntryResponse(
        entry_id=entry.entry_id,
        image_url=entry.image_url,
        competition_type=entry.competition_type,
        extra_text=entry.extra_text,
        created_at=entry.created_at,
        judge_results=judge_results,
        debate=debate,
    )
    
    logger.info(f"查询成功: entry_id={entry_id}, 评委数={len(judge_results)}")
    
    return response


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "message": "AI Judge System is running"}

