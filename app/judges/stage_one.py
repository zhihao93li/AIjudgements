"""阶段一：多评委并发看图评分"""

import asyncio
from typing import Optional
from io import BytesIO

import requests
from PIL import Image as PILImage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage, TextMessage
from autogen_core import Image as AGImage
from loguru import logger

from app.judges.prompts import COMMON_SCORING_GUIDE, JUDGE_PERSONAS, parse_judge_response
from app.judges.utils import make_vision_client, get_model_for_judge


def build_vision_judges(
    custom_scoring_guide: Optional[str] = None,
    custom_personas: Optional[dict] = None
) -> tuple[list[AssistantAgent], dict]:
    """
    构建所有评委 Agent（阶段一：评分模式）
    
    Args:
        custom_scoring_guide: 自定义评分规范
        custom_personas: 自定义评委人设
    
    Returns:
        (评委 Agent 列表, 调试上下文字典)
    """
    judges = []
    debug_contexts = {}  # 保存每个评委的调试信息
    
    # 使用自定义或默认的评分规范
    scoring_guide = custom_scoring_guide or COMMON_SCORING_GUIDE
    personas = custom_personas or JUDGE_PERSONAS
    
    for judge_id, persona_info in personas.items():
        model_name = get_model_for_judge(judge_id)
        display_name = persona_info.get("display_name", judge_id)
        persona = persona_info.get("persona", "")
        
        # 构建完整的 system message
        system_message = scoring_guide + persona
        
        # 保存调试上下文
        debug_contexts[judge_id] = {
            "model_name": model_name,
            "display_name": display_name,
            "system_message": system_message,
            "persona": persona,
            "scoring_guide": scoring_guide,
        }
        
        try:
            model_client = make_vision_client(model=model_name, family="openai")
            
            judge = AssistantAgent(
                name=judge_id,
                model_client=model_client,
                system_message=system_message,
            )
            
            judges.append(judge)
            
            logger.info("="*80)
            logger.info(f"[阶段一] 创建评委: {judge_id} ({display_name})")
            logger.info(f"模型: {model_name}")
            logger.debug(f"System Message 长度: {len(system_message)} 字符")
            # logger.debug(f"System Message:\n{system_message[:500]}...")  # 只显示前500字符
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"创建评委失败: {judge_id} - {e}")
            continue
    
    return judges, debug_contexts


def build_multimodal_message(
    image_url: str,
    entry_id: str,
    competition_type: str,
    extra_text: Optional[str] = None,
) -> MultiModalMessage:
    """
    构建多模态消息（图片 + 文本指令）
    
    Args:
        image_url: 图片 URL
        entry_id: 作品 ID
        competition_type: 比赛类型
        extra_text: 补充说明
    
    Returns:
        MultiModalMessage 实例
    """
    # 下载图片
    try:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        pil_image = PILImage.open(BytesIO(resp.content))
        
        # 转换为 AutoGen 的 Image 对象
        ag_image = AGImage(pil_image)
        
    except Exception as e:
        logger.error(f"下载图片失败: {image_url} - {e}")
        raise
    
    # 构建指令文本
    instruction = f"""这是参赛作品 {entry_id} 的图片，比赛类型为 {competition_type}。

请你直接观察图片，根据系统提示中的评分规范，对作品进行打分和点评，并输出约定好的 JSON 结构。
"""
    
    if extra_text:
        instruction += f"\n\n补充说明：{extra_text}"
    
    # 返回多模态消息
    return MultiModalMessage(
        content=[instruction, ag_image],
        source="user",
    )


async def score_image_with_all_judges(
    image_url: str,
    entry_id: str,
    competition_type: str = "outfit",
    extra_text: Optional[str] = None,
    custom_scoring_guide: Optional[str] = None,
    custom_personas: Optional[dict] = None,
) -> dict:
    """
    阶段一主函数：所有评委并发看图评分
    
    Args:
        image_url: 图片 URL
        entry_id: 作品 ID
        competition_type: 比赛类型
        extra_text: 补充说明
    
    Returns:
        包含所有评委评分和排序结果的字典
    """
    logger.info(f"开始阶段一评分: entry_id={entry_id}, competition_type={competition_type}")
    
    # 1. 构建多模态消息
    try:
        mm_msg = build_multimodal_message(
            image_url=image_url,
            entry_id=entry_id,
            competition_type=competition_type,
            extra_text=extra_text,
        )
    except Exception as e:
        logger.error(f"构建多模态消息失败: {e}")
        return {
            "entry_id": entry_id,
            "competition_type": competition_type,
            "error": f"构建消息失败: {str(e)}",
            "judge_results": [],
            "sorted_results": [],
        }
    
    # 2. 构建评委团队
    judges, debug_contexts = build_vision_judges(
        custom_scoring_guide=custom_scoring_guide,
        custom_personas=custom_personas
    )
    
    if not judges:
        logger.error("没有可用的评委")
        return {
            "entry_id": entry_id,
            "competition_type": competition_type,
            "error": "没有可用的评委",
            "judge_results": [],
            "sorted_results": [],
        }
    
    # 保存用户指令内容（用于调试）
    user_instruction = mm_msg.content[0] if isinstance(mm_msg.content, list) else str(mm_msg.content)
    
    # 3. 并发调用所有评委
    logger.info(f"开始并发调用 {len(judges)} 个评委...")
    
    tasks = [judge.on_messages([mm_msg], cancellation_token=None) for judge in judges]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. 解析评委响应
    judge_outputs = []
    
    for judge, result in zip(judges, results):
        judge_display_name = JUDGE_PERSONAS[judge.name]["display_name"]
        
        # 处理异常
        if isinstance(result, Exception):
            logger.error(f"评委 {judge.name} 调用失败: {result}")
            judge_outputs.append({
                "judge_id": judge.name,
                "judge_display_name": judge_display_name,
                "competition_type": competition_type,
                "error": str(result),
                "overall_score": 0.0,
            })
            continue
        
        # 提取响应内容
        try:
            response = result.chat_message
            raw_content = response.content if isinstance(response.content, str) else str(response.content)
            
            logger.info("="*80)
            logger.info(f"[阶段一] 评委 {judge.name} 原始输出:")
            logger.info(f"{raw_content}")
            logger.info("="*80)
            
            # 解析 JSON
            data = parse_judge_response(raw_content)
            
            if data and "overall_score" in data:
                # 确保必要字段存在
                data["judge_id"] = judge.name
                data["judge_display_name"] = judge_display_name
                data["competition_type"] = competition_type
                data["raw_output"] = raw_content
                
                # 添加调试信息
                if judge.name in debug_contexts:
                    ctx = debug_contexts[judge.name]
                    data["system_message"] = ctx["system_message"]
                    data["user_instruction"] = user_instruction
                    data["model_name"] = ctx["model_name"]
                    data["debug_context"] = {
                        "persona": ctx["persona"],
                        "scoring_guide": ctx["scoring_guide"],
                    }
                
                judge_outputs.append(data)
                logger.success(f"评委 {judge.name} 评分成功: {data.get('overall_score')}")
            else:
                logger.warning(f"评委 {judge.name} 返回的 JSON 格式不正确")
                judge_outputs.append({
                    "judge_id": judge.name,
                    "judge_display_name": judge_display_name,
                    "competition_type": competition_type,
                    "error": "JSON 格式不正确",
                    "overall_score": 0.0,
                    "raw_output": raw_content,
                })
        
        except Exception as e:
            logger.error(f"解析评委 {judge.name} 响应失败: {e}")
            judge_outputs.append({
                "judge_id": judge.name,
                "judge_display_name": judge_display_name,
                "competition_type": competition_type,
                "error": f"解析失败: {str(e)}",
                "overall_score": 0.0,
            })
    
    # 5. 排序（按总分降序）
    valid_results = [r for r in judge_outputs if r.get("overall_score", 0) > 0]
    sorted_results = sorted(valid_results, key=lambda r: r["overall_score"], reverse=True)
    
    logger.info(f"阶段一评分完成: 共 {len(judge_outputs)} 个评委，有效 {len(valid_results)} 个")
    
    return {
        "entry_id": entry_id,
        "competition_type": competition_type,
        "judge_results": judge_outputs,
        "sorted_results": sorted_results,
    }

