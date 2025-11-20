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
from app.judges.prompts import COMMON_SCORING_GUIDE, JUDGE_PERSONAS, DEBATE_MODE_INSTRUCTION

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
        # 提取自定义配置
        custom_scoring_guide = None
        custom_personas = None
        custom_debate_instruction = None
        
        if request.custom_prompts:
            custom_scoring_guide = request.custom_prompts.scoring_guide
            custom_personas = request.custom_prompts.judge_personas
            custom_debate_instruction = request.custom_prompts.debate_instruction
        
        stage_one_result = await score_image_with_all_judges(
            image_url=request.image_url,
            entry_id=request.entry_id,
            competition_type=request.competition_type,
            extra_text=request.extra_text,
            custom_scoring_guide=custom_scoring_guide,
            custom_personas=custom_personas,
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
            custom_scoring_guide=custom_scoring_guide,
            custom_personas=custom_personas,
            custom_debate_instruction=custom_debate_instruction,
        )
        
        if "error" in stage_two_result:
            logger.warning(f"阶段二讨论失败: {stage_two_result['error']}")
        else:
            debate_messages = stage_two_result["messages"]
            participants = stage_two_result.get("participants", [])
            debug_info = stage_two_result.get("debug_info", {})
            
            logger.info(f"阶段二讨论完成，共 {len(debate_messages)} 条消息")
            
            # 5. 保存讨论记录（包含调试信息）
            try:
                debate_id = f"{request.entry_id}_debate"
                await save_debate_session(
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


@router.get("/default_prompts")
async def get_default_prompts():
    """获取默认的提示词配置"""
    return {
        "scoring_guide": COMMON_SCORING_GUIDE,
        "judge_personas": JUDGE_PERSONAS,
        "debate_instruction": DEBATE_MODE_INSTRUCTION
    }


@router.get("/config/models")
async def get_model_config():
    """获取当前的模型配置（用于诊断）"""
    from app.config import get_settings
    from app.judges.utils import get_model_for_judge
    
    settings = get_settings()
    
    return {
        "model_mapping": {
            "chatgpt5_judge": {
                "judge_id": "chatgpt5_judge",
                "display_name": "ChatGPT-5 评委",
                "model_name": get_model_for_judge("chatgpt5_judge"),
                "config_key": "model_chatgpt5",
                "config_value": settings.model_chatgpt5,
            },
            "grok_judge": {
                "judge_id": "grok_judge",
                "display_name": "Grok 评委",
                "model_name": get_model_for_judge("grok_judge"),
                "config_key": "model_grok",
                "config_value": settings.model_grok,
            },
            "gemini_judge": {
                "judge_id": "gemini_judge",
                "display_name": "Gemini 2.5 评委",
                "model_name": get_model_for_judge("gemini_judge"),
                "config_key": "model_gemini",
                "config_value": settings.model_gemini,
            },
            "doubao_judge": {
                "judge_id": "doubao_judge",
                "display_name": "豆包评委",
                "model_name": get_model_for_judge("doubao_judge"),
                "config_key": "model_doubao",
                "config_value": settings.model_doubao,
            },
            "qwen_judge": {
                "judge_id": "qwen_judge",
                "display_name": "千问评委",
                "model_name": get_model_for_judge("qwen_judge"),
                "config_key": "model_qwen",
                "config_value": settings.model_qwen,
            },
        },
        "selector_model": settings.model_selector,
        "gateway_url": settings.llm_gateway_base_url,
    }


@router.get("/debug/entry/{entry_id}")
async def get_debug_info(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取作品的完整调试信息
    包含每个评委的请求上下文和响应详情
    """
    logger.info(f"获取调试信息: entry_id={entry_id}")
    
    try:
        # 获取作品及关联数据
        entry = await get_entry_by_id(db, entry_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail=f"作品不存在: {entry_id}")
        
        # 构建调试信息
        debug_info = {
            "entry_id": entry.entry_id,
            "image_url": entry.image_url,
            "competition_type": entry.competition_type,
            "extra_text": entry.extra_text,
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
                    "overall_score": judge_result.overall_score,
                    "dimension_scores": judge_result.dimension_scores,
                    "strengths": judge_result.strengths,
                    "weaknesses": judge_result.weaknesses,
                    "one_liner": judge_result.one_liner,
                    "comment_for_audience": judge_result.comment_for_audience,
                    "safety_notes": judge_result.safety_notes,
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
                "judge_contexts": debate_session.judge_contexts,  # 每个评委的上下文
                "selector_prompt": debate_session.selector_prompt,  # 选择器提示词
                "initial_message": debate_session.initial_message,  # 初始消息
                
                "messages": [
                    {
                        "sequence": msg.sequence,
                        "speaker": msg.speaker,
                        "content": msg.content,
                        "context_history": msg.context_history,  # 发言时的上下文
                        "raw_response": msg.raw_response,  # 原始响应
                        "model_name": msg.model_name,  # 使用的模型
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in sorted(debate_session.messages, key=lambda m: m.sequence)
                ],
                "created_at": debate_session.created_at.isoformat() if debate_session.created_at else None,
            }
            debug_info["stage_two"]["debate_sessions"].append(debate_debug)
        
        return debug_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取调试信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调试信息失败: {str(e)}")

