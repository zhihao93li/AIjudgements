"""二选一模式阶段一：多评委做出选择并给出理由"""

import asyncio
from typing import Optional
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image as PILImage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage, TextMessage
from autogen_core import Image as AGImage
from loguru import logger

from app.judges.binary_choice_prompts import (
    BINARY_CHOICE_GUIDE,
    JUDGE_PERSONAS,
    parse_binary_choice_response
)
from app.judges.utils import make_vision_client, get_model_for_judge


def build_binary_choice_judges() -> tuple[list[AssistantAgent], dict]:
    """
    构建所有评委 Agent（二选一模式）
    
    Returns:
        (评委 Agent 列表, 调试上下文字典)
    """
    judges = []
    debug_contexts = {}
    
    for judge_id, persona_info in JUDGE_PERSONAS.items():
        model_name = get_model_for_judge(judge_id)
        display_name = persona_info.get("display_name", judge_id)
        persona = persona_info.get("persona", "")
        
        # 构建完整的 system message（二选一指南 + 评委人设）
        system_message = BINARY_CHOICE_GUIDE + persona
        
        # 保存调试上下文
        debug_contexts[judge_id] = {
            "model_name": model_name,
            "display_name": display_name,
            "system_message": system_message,
            "persona": persona,
            "guide": BINARY_CHOICE_GUIDE,
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
            logger.info(f"[二选一-阶段一] 创建评委: {judge_id} ({display_name})")
            logger.info(f"模型: {model_name}")
            logger.debug(f"System Message 长度: {len(system_message)} 字符")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"创建评委失败: {judge_id} - {e}")
            continue
    
    return judges, debug_contexts


def build_binary_choice_message(
    question: str,
    option_a: str,
    option_b: str,
    entry_id: str,
    image_url: Optional[str] = None,
    text_content: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> MultiModalMessage | TextMessage:
    """
    构建二选一消息（可能包含图片或纯文本）
    
    Args:
        question: 二选一问题
        option_a: 选项 A
        option_b: 选项 B
        entry_id: 作品 ID
        image_url: 图片 URL（可选）
        text_content: 文本内容（可选）
        extra_context: 额外上下文（可选）
    
    Returns:
        MultiModalMessage 或 TextMessage
    """
    # 构建指令文本
    instruction_parts = [
        f"【二选一问题】{question}",
        f"【选项 A】{option_a}",
        f"【选项 B】{option_b}",
        "",
        "请你根据以下内容做出选择并给出理由：",
    ]
    
    # 如果有文本内容
    if text_content:
        instruction_parts.append(f"\n【文本内容】\n{text_content}\n")
    
    # 如果有额外上下文
    if extra_context:
        instruction_parts.append(f"\n【补充说明】\n{extra_context}\n")
    
    instruction_parts.append("\n请按照系统提示中的格式输出你的选择和理由。")
    
    instruction = "\n".join(instruction_parts)
    
    # 如果有图片，构建多模态消息
    if image_url:
        try:
            if image_url.startswith("/static/uploads/"):
                # 处理本地文件
                filename = image_url.split("/")[-1]
                local_path = Path(__file__).parent.parent.parent / "frontend" / "uploads" / filename
                
                if not local_path.exists():
                    raise FileNotFoundError(f"本地文件不存在: {local_path}")
                    
                pil_image = PILImage.open(local_path)
            else:
                # 处理远程 URL
                resp = requests.get(image_url, timeout=30)
                resp.raise_for_status()
                pil_image = PILImage.open(BytesIO(resp.content))
            
            # 转换为 AutoGen 的 Image 对象
            ag_image = AGImage(pil_image)
            
            # 返回多模态消息
            return MultiModalMessage(
                content=[instruction, ag_image],
                source="user",
            )
            
        except Exception as e:
            logger.error(f"获取图片失败: {image_url} - {e}")
            # 图片获取失败，降级为纯文本
            instruction += f"\n\n（图片获取失败: {str(e)}）"
            return TextMessage(content=instruction, source="user")
    
    # 纯文本消息
    return TextMessage(content=instruction, source="user")


async def binary_choice_with_all_judges(
    question: str,
    option_a: str,
    option_b: str,
    entry_id: str,
    image_url: Optional[str] = None,
    text_content: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> dict:
    """
    二选一阶段一主函数：所有评委做出选择并给出理由
    
    Args:
        question: 二选一问题
        option_a: 选项 A
        option_b: 选项 B
        entry_id: 作品 ID
        image_url: 图片 URL（可选）
        text_content: 文本内容（可选）
        extra_context: 额外上下文（可选）
    
    Returns:
        包含所有评委选择结果的字典
    """
    logger.info(f"开始二选一阶段一: entry_id={entry_id}")
    logger.info(f"问题: {question}")
    logger.info(f"选项 A: {option_a}, 选项 B: {option_b}")
    
    # 验证至少有图片或文本之一
    if not image_url and not text_content:
        return {
            "entry_id": entry_id,
            "error": "必须提供 image_url 或 text_content 之一",
            "judge_results": [],
        }
    
    # 1. 构建消息
    try:
        msg = build_binary_choice_message(
            question=question,
            option_a=option_a,
            option_b=option_b,
            entry_id=entry_id,
            image_url=image_url,
            text_content=text_content,
            extra_context=extra_context,
        )
    except Exception as e:
        logger.error(f"构建消息失败: {e}")
        return {
            "entry_id": entry_id,
            "error": f"构建消息失败: {str(e)}",
            "judge_results": [],
        }
    
    # 2. 构建评委团队
    judges, debug_contexts = build_binary_choice_judges()
    
    if not judges:
        logger.error("没有可用的评委")
        return {
            "entry_id": entry_id,
            "error": "没有可用的评委",
            "judge_results": [],
        }
    
    # 保存用户指令内容（用于调试）
    if isinstance(msg, MultiModalMessage):
        user_instruction = msg.content[0] if isinstance(msg.content, list) else str(msg.content)
    else:
        user_instruction = msg.content
    
    # 3. 并发调用所有评委
    logger.info(f"开始并发调用 {len(judges)} 个评委...")
    
    tasks = [judge.on_messages([msg], cancellation_token=None) for judge in judges]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. 解析评委响应
    judge_outputs = []
    
    for judge, result in zip(judges, results):
        # 获取评委显示名称
        judge_display_name = JUDGE_PERSONAS.get(judge.name, {}).get("display_name", judge.name)
        
        # 处理异常
        if isinstance(result, Exception):
            logger.error(f"评委 {judge.name} 调用失败: {result}")
            judge_outputs.append({
                "judge_id": judge.name,
                "judge_display_name": judge_display_name,
                "error": str(result),
                "choice": None,
                "reasoning": None,
            })
            continue
        
        # 提取响应内容
        try:
            response = result.chat_message
            raw_content = response.content if isinstance(response.content, str) else str(response.content)
            
            logger.info("="*80)
            logger.info(f"[二选一-阶段一] 评委 {judge.name} 原始输出:")
            logger.info(f"{raw_content}")
            logger.info("="*80)
            
            # 解析二选一响应
            data = parse_binary_choice_response(raw_content)
            
            if data and data.get("choice") and data.get("reasoning"):
                # 确定选择的标签
                choice_label = option_a if data["choice"] == "A" else option_b
                
                # 构建输出数据
                output_data = {
                    "judge_id": judge.name,
                    "judge_display_name": judge_display_name,
                    "choice": data["choice"],
                    "choice_label": choice_label,
                    "reasoning": data["reasoning"],
                    "inner_monologue": data.get("inner_monologue"),
                    "raw_output": raw_content,
                }
                
                # 添加调试信息
                if judge.name in debug_contexts:
                    ctx = debug_contexts[judge.name]
                    output_data["system_message"] = ctx["system_message"]
                    output_data["user_instruction"] = user_instruction
                    output_data["model_name"] = ctx["model_name"]
                    output_data["debug_context"] = {
                        "persona": ctx["persona"],
                        "guide": ctx["guide"],
                    }
                
                judge_outputs.append(output_data)
                logger.success(f"评委 {judge.name} 选择成功: {data['choice']} ({choice_label})")
            else:
                logger.warning(f"评委 {judge.name} 返回的数据不完整")
                judge_outputs.append({
                    "judge_id": judge.name,
                    "judge_display_name": judge_display_name,
                    "error": "数据不完整",
                    "choice": None,
                    "reasoning": None,
                    "raw_output": raw_content,
                })
        
        except Exception as e:
            logger.error(f"解析评委 {judge.name} 响应失败: {e}")
            judge_outputs.append({
                "judge_id": judge.name,
                "judge_display_name": judge_display_name,
                "error": f"解析失败: {str(e)}",
                "choice": None,
                "reasoning": None,
            })
    
    # 5. 统计选择
    valid_results = [r for r in judge_outputs if r.get("choice")]
    choice_a_count = len([r for r in valid_results if r["choice"] == "A"])
    choice_b_count = len([r for r in valid_results if r["choice"] == "B"])
    
    logger.info(f"二选一阶段一完成: 共 {len(judge_outputs)} 个评委，有效 {len(valid_results)} 个")
    logger.info(f"选择 A ({option_a}): {choice_a_count} 票")
    logger.info(f"选择 B ({option_b}): {choice_b_count} 票")
    
    return {
        "entry_id": entry_id,
        "judge_results": judge_outputs,
        "choice_a_count": choice_a_count,
        "choice_b_count": choice_b_count,
    }
