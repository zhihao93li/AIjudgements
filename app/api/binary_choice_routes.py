"""二选一模式的 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import uuid

from app.models.binary_choice_schemas import (
    BinaryChoiceRequest,
    BinaryChoiceResponse,
    BinaryChoiceJudgeResult,
    BinaryChoiceDebateResponse,
    BinaryChoiceDebateMessage,
)
from app.db.database import get_db
from app.db.binary_choice_crud import (
    save_binary_choice_entry,
    save_binary_choice_results,
    save_binary_choice_debate,
    get_binary_choice_entry_by_id,
)
from app.judges.binary_choice_stage_one import binary_choice_with_all_judges
from app.judges.binary_choice_stage_two import run_binary_choice_debate


router = APIRouter()


@router.post("/judge", response_model=BinaryChoiceResponse)
async def judge_binary_choice(
    request: BinaryChoiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    二选一评判完整流程（阶段一 + 阶段二）
    
    1. 保存二选一作品信息
    2. 阶段一：评委选择并给出理由
    3. 保存评委选择结果
    4. 阶段二：评委群聊讨论
    5. 保存讨论记录
    6. 返回完整结果
    """
    logger.info(f"收到二选一评判请求: entry_id={request.entry_id}")
    logger.info(f"问题: {request.question}")
    logger.info(f"选项 A: {request.option_a}, 选项 B: {request.option_b}")
    
    # 验证至少有图片或文本之一
    if not request.image_url and not request.text_content:
        raise HTTPException(
            status_code=400,
            detail="必须提供 image_url 或 text_content 之一"
        )
    
    # 自动生成 entry_id（如果未提供）
    if not request.entry_id or request.entry_id.strip() == "":
        request.entry_id = f"binary_{uuid.uuid4().hex[:12]}"
        logger.info(f"自动生成 entry_id: {request.entry_id}")
    
    try:
        # 1. 保存二选一作品信息
        entry = await save_binary_choice_entry(
            db=db,
            entry_id=request.entry_id,
            question=request.question,
            option_a=request.option_a,
            option_b=request.option_b,
            image_url=request.image_url,
            text_content=request.text_content,
            extra_context=request.extra_context,
        )
        logger.info(f"二选一作品保存成功: {entry.entry_id}")
        
    except Exception as e:
        logger.error(f"保存二选一作品失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存作品失败: {str(e)}")
    
    # 2. 阶段一：评委选择并给出理由
    try:
        stage_one_result = await binary_choice_with_all_judges(
            question=request.question,
            option_a=request.option_a,
            option_b=request.option_b,
            entry_id=request.entry_id,
            image_url=request.image_url,
            text_content=request.text_content,
            extra_context=request.extra_context,
        )
        
        if "error" in stage_one_result:
            logger.error(f"阶段一选择失败: {stage_one_result['error']}")
            raise HTTPException(status_code=500, detail=stage_one_result["error"])
        
        judge_results = stage_one_result["judge_results"]
        choice_a_count = stage_one_result["choice_a_count"]
        choice_b_count = stage_one_result["choice_b_count"]
        
        logger.info(f"阶段一选择完成，共 {len(judge_results)} 个评委")
        logger.info(f"选择 A: {choice_a_count} 票, 选择 B: {choice_b_count} 票")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"阶段一选择异常: {e}")
        raise HTTPException(status_code=500, detail=f"阶段一选择失败: {str(e)}")
    
    # 3. 保存评委选择结果
    try:
        await save_binary_choice_results(
            db=db,
            entry_id=request.entry_id,
            judge_results=judge_results,
        )
        logger.info(f"评委选择结果保存成功")
        
    except Exception as e:
        logger.error(f"保存评委结果失败: {e}")
        # 不中断流程，继续执行
    
    # 4. 阶段二：评委群聊讨论
    debate_result = None
    
    try:
        # 只传递有效的结果（有choice的）
        valid_results = [r for r in judge_results if r.get("choice")]
        
        stage_two_result = await run_binary_choice_debate(
            entry_id=request.entry_id,
            question=request.question,
            option_a=request.option_a,
            option_b=request.option_b,
            judge_results=valid_results,
        )
        
        if "error" in stage_two_result:
            logger.warning(f"阶段二讨论失败: {stage_two_result['error']}")
        else:
            debate_messages = stage_two_result["messages"]
            participants = stage_two_result.get("participants", [])
            debug_info = stage_two_result.get("debug_info", {})
            
            logger.info(f"阶段二讨论完成，共 {len(debate_messages)} 条消息")
            
            # 5. 保存讨论记录
            try:
                debate_id = f"{request.entry_id}_debate"
                await save_binary_choice_debate(
                    db=db,
                    entry_id=request.entry_id,
                    debate_id=debate_id,
                    participants=participants,
                    messages=debate_messages,
                    config={"max_messages": 12},
                    judge_contexts=debug_info.get("judge_contexts"),
                    selector_prompt=debug_info.get("selector_prompt"),
                    initial_message=debug_info.get("initial_message"),
                )
                logger.info(f"讨论记录保存成功")
                
                # 构建返回的 debate 对象
                debate_result = BinaryChoiceDebateResponse(
                    debate_id=debate_id,
                    participants=participants,
                    messages=[
                        BinaryChoiceDebateMessage(
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
        BinaryChoiceJudgeResult(
            judge_id=r["judge_id"],
            judge_display_name=r["judge_display_name"],
            choice=r["choice"],
            choice_label=r["choice_label"],
            reasoning=r["reasoning"],
            inner_monologue=r.get("inner_monologue"),
        )
        for r in judge_results
        if r.get("choice")  # 只包含有效的选择
    ]
    
    response = BinaryChoiceResponse(
        entry_id=request.entry_id,
        question=request.question,
        option_a=request.option_a,
        option_b=request.option_b,
        image_url=request.image_url,
        text_content=request.text_content,
        choice_a_count=choice_a_count,
        choice_b_count=choice_b_count,
        judge_results=judge_result_responses,
        debate=debate_result,
    )
    
    logger.success(f"二选一评判流程完成: entry_id={request.entry_id}")
    logger.success(f"投票结果: A={choice_a_count}, B={choice_b_count}")
    
    return response


@router.get("/entry/{entry_id}", response_model=BinaryChoiceResponse)
async def get_binary_choice_result(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    查询某个二选一作品的评判结果和讨论记录
    
    Args:
        entry_id: 作品 ID
    
    Returns:
        二选一完整信息
    """
    logger.info(f"查询二选一作品: entry_id={entry_id}")
    
    # 查询作品及关联数据
    entry = await get_binary_choice_entry_by_id(db=db, entry_id=entry_id)
    
    if not entry:
        logger.warning(f"二选一作品不存在: {entry_id}")
        raise HTTPException(status_code=404, detail=f"作品不存在: {entry_id}")
    
    # 构建评委结果
    judge_results = [
        BinaryChoiceJudgeResult(
            judge_id=jr.judge_id,
            judge_display_name=jr.judge_display_name,
            choice=jr.choice,
            choice_label=jr.choice_label,
            reasoning=jr.reasoning,
            inner_monologue=jr.inner_monologue,
        )
        for jr in entry.judge_results
    ]
    
    # 统计选择
    choice_a_count = len([r for r in entry.judge_results if r.choice == "A"])
    choice_b_count = len([r for r in entry.judge_results if r.choice == "B"])
    
    # 处理讨论记录
    debate = None
    if entry.debate_sessions:
        debate_session = entry.debate_sessions[0]
        debate = BinaryChoiceDebateResponse(
            debate_id=debate_session.debate_id,
            participants=debate_session.participants,
            messages=[
                BinaryChoiceDebateMessage(
                    sequence=msg.sequence,
                    speaker=msg.speaker,
                    content=msg.content,
                )
                for msg in sorted(debate_session.messages, key=lambda m: m.sequence)
            ],
        )
    
    response = BinaryChoiceResponse(
        entry_id=entry.entry_id,
        question=entry.question,
        option_a=entry.option_a,
        option_b=entry.option_b,
        image_url=entry.image_url,
        text_content=entry.text_content,
        choice_a_count=choice_a_count,
        choice_b_count=choice_b_count,
        judge_results=judge_results,
        debate=debate,
    )
    
    logger.info(f"查询成功: entry_id={entry_id}, 评委数={len(judge_results)}")
    
    return response


@router.get("/debug/entry/{entry_id}")
async def get_binary_choice_debug_info(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取二选一作品的完整调试信息
    包含每个评委的请求上下文和响应详情
    """
    logger.info(f"获取二选一调试信息: entry_id={entry_id}")
    
    try:
        # 获取作品及关联数据
        entry = await get_binary_choice_entry_by_id(db, entry_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail=f"作品不存在: {entry_id}")
        
        # 构建调试信息
        debug_info = {
            "entry_id": entry.entry_id,
            "question": entry.question,
            "option_a": entry.option_a,
            "option_b": entry.option_b,
            "image_url": entry.image_url,
            "text_content": entry.text_content,
            "extra_context": entry.extra_context,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            
            # 阶段一：独立评分详情
            "stage_one": {
                "judges": []
            },
            
            # 阶段二：群聊讨论详情
            "stage_two": {
                "debate_sessions": []
            }
        }
        
        # 收集阶段一评委评分详情
        for judge_result in entry.judge_results:
            judge_debug = {
                "judge_id": judge_result.judge_id,
                "judge_display_name": judge_result.judge_display_name,
                "model_name": judge_result.model_name,
                
                # 请求上下文
                "request_context": {
                    "system_message": judge_result.system_message,
                    "user_instruction": judge_result.user_instruction,
                    "debug_context": judge_result.debug_context,
                },
                
                # 响应结果
                "response": {
                    "choice": judge_result.choice,
                    "choice_label": judge_result.choice_label,
                    "reasoning": judge_result.reasoning,
                    "inner_monologue": judge_result.inner_monologue,
                    "raw_output": judge_result.raw_output,
                },
                
                "created_at": judge_result.created_at.isoformat() if judge_result.created_at else None,
            }
            debug_info["stage_one"]["judges"].append(judge_debug)
        
        # 收集阶段二群聊讨论详情
        for debate_session in entry.debate_sessions:
            debate_debug = {
                "debate_id": debate_session.debate_id,
                "participants": debate_session.participants,
                "config": debate_session.config,
                
                # 调试信息
                "judge_contexts": debate_session.judge_contexts,
                "selector_prompt": debate_session.selector_prompt,
                "initial_message": debate_session.initial_message,
                
                "messages": [
                    {
                        "sequence": msg.sequence,
                        "speaker": msg.speaker,
                        "content": msg.content,
                        "context_history": msg.context_history,
                        "raw_response": msg.raw_response,
                        "model_name": msg.model_name,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in sorted(debate_session.messages, key=lambda m: m.sequence)
                ],
                "created_at": debate_session.created_at.isoformat() if debate_session.created_at else None,
            }
            debug_info["stage_two"]["debate_sessions"].append(debate_debug)
        
        return debug_info
        
    except Exception as e:
        logger.error(f"获取调试信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调试信息失败: {str(e)}")
