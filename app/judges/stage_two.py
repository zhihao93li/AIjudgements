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


def build_debate_judges(
    custom_scoring_guide: Optional[str] = None,
    custom_personas: Optional[dict] = None,
    custom_debate_instruction: Optional[str] = None
) -> tuple[list[AssistantAgent], dict]:
    """
    构建所有评委 Agent（阶段二：讨论模式）
    
    Args:
        custom_scoring_guide: 自定义评分规范
        custom_personas: 自定义评委人设
        custom_debate_instruction: 自定义讨论模式说明
    
    Returns:
        (评委 Agent 列表, 调试上下文字典)
    """
    judges = []
    debug_contexts = {}  # 保存每个评委的调试信息
    
    # 使用自定义或默认的配置
    scoring_guide = custom_scoring_guide or COMMON_SCORING_GUIDE
    personas = custom_personas or JUDGE_PERSONAS
    debate_instruction = custom_debate_instruction or DEBATE_MODE_INSTRUCTION
    
    for judge_id, persona_info in personas.items():
        model_name = get_model_for_judge(judge_id)
        display_name = persona_info.get("display_name", judge_id)
        persona = persona_info.get("persona", "")
        
        
        # 讨论模式的 system message：只需要人设 + 讨论模式说明
        # 不要包含 scoring_guide，因为那是为阶段一评分设计的（包含 inner_monologue 和 JSON 输出指令）
        system_message = persona + debate_instruction
        
        # 保存调试上下文
        debug_contexts[judge_id] = {
            "judge_id": judge_id,
            "display_name": display_name,
            "model_name": model_name,
            "system_message": system_message,
            "persona": persona,
            "debate_instruction": debate_instruction,
        }
        
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
    
    return judges, debug_contexts


def build_selector_prompt(judges: list[AssistantAgent]) -> str:
    """
    构建选择器的 prompt
    
    Args:
        judges: 评委列表
    
    Returns:
        完整的选择器 prompt
    """
    # 构建评委角色说明
    roles_list = []
    
    for judge in judges:
        if judge.name not in JUDGE_PERSONAS:
            continue
            
        persona_text = JUDGE_PERSONAS[judge.name]['persona']
        display_name = JUDGE_PERSONAS[judge.name]['display_name']
        
        # 尝试提取核心性格
        try:
            if "核心性格**：" in persona_text:
                core_trait = persona_text.split("核心性格**：")[1].split("\n")[0].strip()
            elif "核心特质：" in persona_text:
                core_trait = persona_text.split("核心特质：")[1].split("\n")[0].strip()
            else:
                # Fallback: 取前 50 个字符
                core_trait = persona_text.strip()[:50] + "..."
        except Exception:
            core_trait = "性格鲜明"
            
        roles_list.append(f"- {judge.name}: {display_name} - {core_trait}")

    roles = "\n".join(roles_list)
    
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
    custom_scoring_guide: Optional[str] = None,
    custom_personas: Optional[dict] = None,
    custom_debate_instruction: Optional[str] = None,
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
    judges, debug_contexts = build_debate_judges(
        custom_scoring_guide=custom_scoring_guide,
        custom_personas=custom_personas,
        custom_debate_instruction=custom_debate_instruction
    )
    
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
    logger.info(f"[阶段二] 配置最大消息数: {max_msgs}")
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
    all_messages_history = []  # 完整的消息历史（包括 user 消息）
    
    try:
        logger.info("开始运行群聊...")
        
        # 创建初始消息
        initial_message = TextMessage(
            content=summary_text,
            source="user",
        )
        
        # 记录初始消息到历史
        all_messages_history.append({
            "source": "user",
            "content": summary_text,
        })
        
        logger.info("=" * 80)
        logger.info("[阶段二] 群聊开始")
        logger.info(f"初始上下文:\n{summary_text}")
        logger.info("=" * 80)
        
        # 运行 stream
        result_stream = team.run_stream(task=initial_message)
        
        # 收集消息
        message_count = 0
        async for event in result_stream:
            # 只处理真正的消息事件，过滤其他event类型（如TaskResult等）
            # 检查event的类名，autogen的消息类通常包含'Message'
            event_type = event.__class__.__name__
            
            # 只处理消息类型的event
            if 'Message' not in event_type:
                logger.debug(f"跳过非消息事件: {event_type}")
                continue
            
            # 检查是否是 Agent 消息
            if hasattr(event, 'source') and hasattr(event, 'content'):
                # 过滤掉 user 和 system 消息，只保留评委发言
                if event.source not in ["user", "system"] and event.source in [j.name for j in judges]:
                    content = event.content if isinstance(event.content, str) else str(event.content)
                    # --- 清洗逻辑开始 ---
                    import re
                    
                    # 1. 去除 <thinking> 标签内容
                    content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
                    
                    def extract_final_response(text: str) -> str:
                        """
                        尝试从思维链中提取最终回复
                        """
                        # 策略 A: 寻找明确的"最终发言"标记
                        # 匹配模式： "所以最终发言应该是："、"所以组合起来："、"最终："
                        final_markers = [
                            r"所以最终发言应该是[：:]\s*",
                            r"所以组合起来[：:]\s*",
                            r"最终发言[：:]\s*",
                            r"最终[：:]\s*",
                        ]
                        
                        for marker in final_markers:
                            # 查找最后一个匹配项（防止中间有类似的引用）
                            matches = list(re.finditer(marker, text))
                            if matches:
                                last_match = matches[-1]
                                return text[last_match.end():].strip()
                        
                        # 策略 B: 寻找最后一个"草稿"标记
                        # 模型经常说 "比如：..." "或者：..."
                        draft_markers = [
                            r"比如[：:]\s*",
                            r"或者[：:]\s*",
                            r"或者更符合人设[：:]\s*",
                        ]
                        
                        last_draft_pos = -1
                        for marker in draft_markers:
                            matches = list(re.finditer(marker, text))
                            if matches:
                                pos = matches[-1].end()
                                if pos > last_draft_pos:
                                    last_draft_pos = pos
                        
                        if last_draft_pos != -1:
                            # 提取最后一个草稿之后的内容
                            return text[last_draft_pos:].strip()
                            
                        return text

                    # 2. 执行提取策略
                    extracted_content = extract_final_response(content)
                    
                    # 3. 最后的安全网：如果提取后的内容仍然包含大量思维链关键词，则进一步清洗
                    def is_thinking_block(text_block: str) -> bool:
                        keywords = ["人设", "扮演", "口头禅", "首先", "然后", "用户", "需要我", "对话", "观点", "反驳", "支持", "要注意", "比如", "或者"]
                        hit_count = 0
                        for kw in keywords:
                            if kw in text_block:
                                hit_count += 1
                        
                        if (text_block.startswith("我") or text_block.startswith("用户")) and ("扮演" in text_block or "人设" in text_block):
                            return True
                        if hit_count >= 3:
                            return True
                        return False

                    # 如果提取并没有显著改变长度（说明没找到标记），或者提取后的内容看起来还是像思维链
                    # 则应用逐行清洗
                    lines = extracted_content.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if not is_thinking_block(line):
                            cleaned_lines.append(line)
                        else:
                            logger.debug(f"检测到思维链并移除: {line[:50]}...")
                    
                    content = '\n'.join(cleaned_lines).strip()
                    
                    # 如果清洗后内容为空，说明这条消息纯粹是思维链，跳过
                    if not content:
                        logger.warning(f"跳过纯思维链消息: {event.source}")
                        continue
                    # --- 清洗逻辑结束 ---
                    message_count += 1
                    
                    # 获取该评委的模型名称
                    model_name = get_model_for_judge(event.source)
                    
                    # 保存当前发言时的上下文历史（深拷贝）
                    context_at_this_time = list(all_messages_history)
                    
                    # 保存消息（包含调试信息）
                    debate_messages.append({
                        "speaker": event.source,
                        "content": content,
                        "context_history": context_at_this_time,  # 发言时看到的所有历史
                        "raw_response": content,  # 原始响应（暂时和 content 相同）
                        "model_name": model_name,
                    })
                    
                    # 添加到历史记录
                    all_messages_history.append({
                        "source": event.source,
                        "content": content,
                    })
                    
                    logger.info("="*80)
                    logger.info(f"[第 {message_count} 轮] 发言者: {event.source} (模型: {model_name})")
                    logger.info(f"上下文消息数: {len(context_at_this_time)}")
                    logger.info(f"完整回复:\n{content}")
                    logger.info("="*80)
        
        logger.success(f"群聊讨论完成，共 {len(debate_messages)} 条消息")
        
    except Exception as e:
        logger.error(f"运行群聊失败: {e}")
        return {
            "entry_id": entry_id,
            "messages": debate_messages,  # 返回已收集的消息
            "error": f"群聊运行异常: {str(e)}",
        }
    
    # 8. 返回结果（包含调试信息）
    return {
        "entry_id": entry_id,
        "messages": debate_messages,
        "participants": [j.name for j in judges],
        # 调试信息
        "debug_info": {
            "judge_contexts": debug_contexts,
            "selector_prompt": selector_prompt,
            "initial_message": summary_text,
        }
    }

