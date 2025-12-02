"""二选一模式阶段二：评委群聊讨论"""

from typing import Optional
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import TextMessage
from loguru import logger

from app.judges.binary_choice_prompts import (
    JUDGE_PERSONAS,
    BINARY_CHOICE_DEBATE_INSTRUCTION,
    build_binary_choice_summary_text,
)
from app.judges.prompts import SELECTOR_PROMPT_TEMPLATE
from app.judges.utils import make_text_client, get_model_for_judge
from app.config import get_settings

settings = get_settings()


def build_binary_choice_debate_judges(
    judge_results: Optional[list[dict]] = None,
) -> tuple[list[AssistantAgent], dict]:
    """
    构建所有评委 Agent（二选一讨论模式）
    
    Args:
        judge_results: 阶段一的评委选择结果
    
    Returns:
        (评委 Agent 列表, 调试上下文字典)
    """
    judges = []
    debug_contexts = {}
    
    # 建立 judge_id 到 result 的映射
    judge_result_map = {}
    if judge_results:
        for res in judge_results:
            if "judge_id" in res:
                judge_result_map[res["judge_id"]] = res
    
    for judge_id, persona_info in JUDGE_PERSONAS.items():
        model_name = get_model_for_judge(judge_id)
        display_name = persona_info.get("display_name", judge_id)
        persona = persona_info.get("persona", "")
        
        # 构建自我选择上下文
        self_context = ""
        if judge_id in judge_result_map:
            my_res = judge_result_map[judge_id]
            my_choice = my_res.get("choice", "")
            my_choice_label = my_res.get("choice_label", "")
            my_reasoning = my_res.get("reasoning", "")
            my_inner_monologue = my_res.get("inner_monologue", "")
            
            self_context = f"""
            
=== 背景：你在第一阶段的选择 ===
你选择了：{my_choice} ({my_choice_label})
你的理由是："{my_reasoning}"
{f'你的内心独白："{my_inner_monologue}"' if my_inner_monologue else ''}

这只是一个参考背景。在接下来的讨论中，你应该：
- 优先回应其他评委最新的发言
- 可以坚持你的选择，也可以被说服改变立场
- 避免重复已经说过的内容
- 针对对方的理由进行攻击或辩论

注意：在【选择摘要】中你会看到所有评委的选择，其中标记为 {display_name} 的就是你的选择。
"""
        
        # 讨论模式的 system message
        system_message = persona + BINARY_CHOICE_DEBATE_INSTRUCTION + self_context
        
        # 保存调试上下文
        debug_contexts[judge_id] = {
            "judge_id": judge_id,
            "display_name": display_name,
            "model_name": model_name,
            "system_message": system_message,
            "persona": persona,
            "debate_instruction": BINARY_CHOICE_DEBATE_INSTRUCTION,
            "self_context": self_context,
        }
        
        try:
            model_client = make_text_client(model=model_name, family="openai")
            
            judge = AssistantAgent(
                name=judge_id,
                model_client=model_client,
                system_message=system_message,
            )
            
            judges.append(judge)
            logger.info(f"[二选一-阶段二] 创建讨论评委成功: {judge_id} ({display_name})")
            
        except Exception as e:
            logger.error(f"创建讨论评委失败: {judge_id} - {e}")
            continue
    
    return judges, debug_contexts


def build_selector_prompt(judges: list[AssistantAgent]) -> str:
    """
    构建选择器的 prompt（复用现有逻辑）
    
    Args:
        judges: 评委列表
    
    Returns:
        完整的选择器 prompt
    """
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
                core_trait = persona_text.strip()[:50] + "..."
        except Exception:
            core_trait = "性格鲜明"
            
        roles_list.append(f"- {judge.name}: {display_name} - {core_trait}")

    roles = "\n".join(roles_list)
    participants = ", ".join([judge.name for judge in judges])
    
    return SELECTOR_PROMPT_TEMPLATE.format(
        roles=roles,
        history="{history}",
        participants=participants,
    )


async def run_binary_choice_debate(
    entry_id: str,
    question: str,
    option_a: str,
    option_b: str,
    judge_results: list[dict],
    max_messages: Optional[int] = None,
) -> dict:
    """
    二选一阶段二主函数：评委群聊讨论
    
    Args:
        entry_id: 作品 ID
        question: 二选一问题
        option_a: 选项 A
        option_b: 选项 B
        judge_results: 阶段一的评委选择结果
        max_messages: 最大消息数
    
    Returns:
        包含讨论消息的字典
    """
    logger.info(f"开始二选一阶段二群聊讨论: entry_id={entry_id}")
    
    if not judge_results:
        logger.warning("没有评委选择结果，跳过讨论")
        return {
            "entry_id": entry_id,
            "messages": [],
            "error": "没有评委选择结果",
        }
    
    # 1. 生成选择摘要上下文
    summary_text = build_binary_choice_summary_text(
        entry_id=entry_id,
        question=question,
        option_a=option_a,
        option_b=option_b,
        judge_results=judge_results,
    )
    
    logger.debug(f"选择摘要:\n{summary_text}")
    
    # 2. 构建讨论模式的评委
    judges, debug_contexts = build_binary_choice_debate_judges(
        judge_results=judge_results,
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
    logger.info(f"[二选一-阶段二] 配置最大消息数: {max_msgs}")
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
    all_messages_history = []
    
    try:
        logger.info("开始运行二选一讨论群聊...")
        
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
        logger.info("[二选一-阶段二] 群聊开始")
        logger.info(f"初始上下文:\n{summary_text}")
        logger.info("=" * 80)
        
        # 运行 stream
        result_stream = team.run_stream(task=initial_message)
        
        # 收集消息
        message_count = 0
        async for event in result_stream:
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
                    
                    # 清洗逻辑（复用现有的清洗逻辑）
                    import re
                    
                    # 去除 <thinking> 标签内容
                    content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
                    
                    def extract_final_response(text: str) -> str:
                        """提取最终回复"""
                        final_markers = [
                            r"所以最终发言应该是[：:]\\s*",
                            r"所以组合起来[：:]\\s*",
                            r"最终发言[：:]\\s*",
                            r"最终[：:]\\s*",
                        ]
                        
                        for marker in final_markers:
                            matches = list(re.finditer(marker, text))
                            if matches:
                                last_match = matches[-1]
                                return text[last_match.end():].strip()
                        
                        draft_markers = [
                            r"比如[：:]\\s*",
                            r"或者[：:]\\s*",
                            r"或者更符合人设[：:]\\s*",
                        ]
                        
                        last_draft_pos = -1
                        for marker in draft_markers:
                            matches = list(re.finditer(marker, text))
                            if matches:
                                pos = matches[-1].end()
                                if pos > last_draft_pos:
                                    last_draft_pos = pos
                        
                        if last_draft_pos != -1:
                            return text[last_draft_pos:].strip()
                            
                        return text
                    
                    extracted_content = extract_final_response(content)
                    
                    def is_thinking_block(text_block: str) -> bool:
                        keywords = ["人设", "扮演", "口头禅", "首先", "然后", "用户", "需要我", "对话", "观点", "反驳", "支持", "要注意", "比如", "或者"]
                        hit_count = sum(1 for kw in keywords if kw in text_block)
                        
                        if (text_block.startswith("我") or text_block.startswith("用户")) and ("扮演" in text_block or "人设" in text_block):
                            return True
                        if hit_count >= 3:
                            return True
                        return False
                    
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
                    
                    # 如果清洗后内容为空，跳过
                    if not content:
                        logger.warning(f"跳过纯思维链消息: {event.source}")
                        continue
                    
                    message_count += 1
                    
                    # 获取该评委的模型名称
                    model_name = get_model_for_judge(event.source)
                    
                    # 保存当前发言时的上下文历史
                    context_at_this_time = list(all_messages_history)
                    
                    # 保存消息
                    debate_messages.append({
                        "speaker": event.source,
                        "content": content,
                        "context_history": context_at_this_time,
                        "raw_response": content,
                        "model_name": model_name,
                    })
                    
                    # 添加到历史记录
                    all_messages_history.append({
                        "source": event.source,
                        "content": content,
                    })
                    
                    logger.info("="*80)
                    logger.info(f"[二选一-第 {message_count} 轮] 发言者: {event.source} (模型: {model_name})")
                    logger.info(f"上下文消息数: {len(context_at_this_time)}")
                    logger.info(f"完整回复:\n{content}")
                    logger.info("="*80)
        
        logger.success(f"二选一群聊讨论完成，共 {len(debate_messages)} 条消息")
        
    except Exception as e:
        logger.error(f"运行群聊失败: {e}")
        return {
            "entry_id": entry_id,
            "messages": debate_messages,
            "error": f"群聊运行异常: {str(e)}",
        }
    
    # 8. 返回结果
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
