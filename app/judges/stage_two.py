"""阶段二：评委群聊讨论（SelectorGroupChat）"""

from typing import Optional
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import TextMessage
from loguru import logger

from app.judges.prompts import (
    COMMON_SCORING_GUIDE,
    JUDGE_PERSONAS,
    DEBATE_MODE_INSTRUCTION,
    SELECTOR_PROMPT_TEMPLATE,
    build_judge_summary_text,
)
from app.judges.utils import make_text_client, get_model_for_judge
from app.config import get_settings

settings = get_settings()


def build_debate_judges() -> list[AssistantAgent]:
    """
    构建所有评委 Agent（阶段二：讨论模式）
    
    Returns:
        评委 Agent 列表
    """
    judges = []
    
    for judge_id, persona_info in JUDGE_PERSONAS.items():
        model_name = get_model_for_judge(judge_id)
        display_name = persona_info["display_name"]
        persona = persona_info["persona"]
        
        # 讨论模式的 system message：评分规范 + 人设 + 讨论模式说明
        system_message = COMMON_SCORING_GUIDE + persona + DEBATE_MODE_INSTRUCTION
        
        try:
            # 讨论阶段不需要 vision，使用文本模型即可
            model_client = make_text_client(model=model_name, family="openai")
            
            judge = AssistantAgent(
                name=judge_id,
                model_client=model_client,
                system_message=system_message,
            )
            
            judges.append(judge)
            logger.info(f"创建讨论评委成功: {judge_id} ({display_name})")
            
        except Exception as e:
            logger.error(f"创建讨论评委失败: {judge_id} - {e}")
            continue
    
    return judges


def build_selector_prompt(judges: list[AssistantAgent]) -> str:
    """
    构建选择器的 prompt
    
    Args:
        judges: 评委列表
    
    Returns:
        完整的选择器 prompt
    """
    # 构建评委角色说明
    roles = "\n".join([
        f"- {judge.name}: {JUDGE_PERSONAS[judge.name]['display_name']} - {JUDGE_PERSONAS[judge.name]['persona'].split('特点：')[1].split('评分特点')[0].strip()}"
        for judge in judges
        if judge.name in JUDGE_PERSONAS
    ])
    
    # 候选评委列表
    participants = ", ".join([judge.name for judge in judges])
    
    # 填充模板
    return SELECTOR_PROMPT_TEMPLATE.format(
        roles=roles,
        history="{history}",  # 这个会由 AutoGen 自动填充
        participants=participants,
    )


async def run_debate_for_entry(
    entry_id: str,
    competition_type: str,
    judge_results: list[dict],
    max_messages: Optional[int] = None,
) -> dict:
    """
    阶段二主函数：评委群聊讨论
    
    Args:
        entry_id: 作品 ID
        competition_type: 比赛类型
        judge_results: 阶段一的评委评分结果
        max_messages: 最大消息数（None 则使用配置默认值）
    
    Returns:
        包含讨论消息的字典
    """
    logger.info(f"开始阶段二群聊讨论: entry_id={entry_id}")
    
    if not judge_results:
        logger.warning("没有评委评分结果，跳过讨论")
        return {
            "entry_id": entry_id,
            "messages": [],
            "error": "没有评委评分结果",
        }
    
    # 1. 生成初评摘要上下文
    summary_text = build_judge_summary_text(
        entry_id=entry_id,
        competition_type=competition_type,
        judge_results=judge_results,
    )
    
    logger.debug(f"初评摘要:\n{summary_text}")
    
    # 2. 构建讨论模式的评委
    judges = build_debate_judges()
    
    if not judges:
        logger.error("没有可用的讨论评委")
        return {
            "entry_id": entry_id,
            "messages": [],
            "error": "没有可用的讨论评委",
        }
    
    # 3. 创建选择器模型客户端
    selector_client = make_text_client(
        model=settings.model_selector,
        family="openai"
    )
    
    # 4. 构建选择器 prompt
    selector_prompt = build_selector_prompt(judges)
    
    # 5. 配置终止条件
    max_msgs = max_messages or settings.max_debate_messages
    termination = MaxMessageTermination(max_messages=max_msgs)
    
    # 6. 创建 SelectorGroupChat
    try:
        team = SelectorGroupChat(
            participants=judges,
            model_client=selector_client,
            termination_condition=termination,
            selector_prompt=selector_prompt,
        )
        
        logger.info(f"创建 SelectorGroupChat 成功，参与评委: {[j.name for j in judges]}")
        
    except Exception as e:
        logger.error(f"创建 SelectorGroupChat 失败: {e}")
        return {
            "entry_id": entry_id,
            "messages": [],
            "error": f"创建群聊失败: {str(e)}",
        }
    
    # 7. 运行群聊
    debate_messages = []
    
    try:
        logger.info("开始运行群聊...")
        
        # 创建初始消息
        initial_message = TextMessage(
            content=summary_text,
            source="user",
        )
        
        # 运行 stream
        result_stream = team.run_stream(task=initial_message)
        
        # 收集消息
        async for event in result_stream:
            # 检查是否是 Agent 消息
            if hasattr(event, 'source') and hasattr(event, 'content'):
                # 过滤掉 user 和 system 消息，只保留评委发言
                if event.source not in ["user", "system"] and event.source in [j.name for j in judges]:
                    content = event.content if isinstance(event.content, str) else str(event.content)
                    
                    debate_messages.append({
                        "speaker": event.source,
                        "content": content,
                    })
                    
                    logger.info(f"[{event.source}]: {content[:100]}...")
        
        logger.success(f"群聊讨论完成，共 {len(debate_messages)} 条消息")
        
    except Exception as e:
        logger.error(f"运行群聊失败: {e}")
        return {
            "entry_id": entry_id,
            "messages": debate_messages,  # 返回已收集的消息
            "error": f"群聊运行异常: {str(e)}",
        }
    
    # 8. 返回结果
    return {
        "entry_id": entry_id,
        "messages": debate_messages,
        "participants": [j.name for j in judges],
    }

