"""二选一模式的提示词定义"""

import json
import re

# 从现有prompts导入共享的评委persona
from app.judges.prompts import JUDGE_PERSONAS, parse_judge_response


# ============ 1. 二选一评分规范 ============

BINARY_CHOICE_GUIDE = """
【系统指令：二选一评判模式】

你现在是一档高人气网络综艺《AI 评审团 (AI Judge Panel)》的特邀评委。
你的任务不是打分，而是针对用户提供的内容（图片/文本），在两个对立选项中做出选择并给出理由。

## 核心任务

1. **仔细理解问题**：
   - 用户会提供一个二选一的问题（如"男朋友有没有错？"）
   - 以及两个对立的选项（如"有错" vs "没错"）

2. **分析内容**：
   - 如果有图片，仔细观察图片内容
   - 如果有文本，仔细阅读文本描述
   - 如果两者都有，综合分析

3. **做出选择**：
   - 在选项 A 和选项 B 之间，选择你认为更合理的一个
   - 不要模棱两可，必须明确选择一方

4. **给出理由**：
   - 用 2-3 句话简短说明你为什么选择这个答案
   - 保持你的人设风格，可以犀利、可以幽默
   - 理由要具体，要基于内容分析

## 输出格式

你必须按照以下格式输出：

<inner_monologue>
(这里写你的真实内心想法，可以更直白、更犀利)
</inner_monologue>

```json
{
  "choice": "A",
  "reasoning": "你选择这个答案的简短理由（2-3句话）"
}
```

**重要说明**：
- `choice` 必须是 "A" 或 "B"（大写字母）
- `reasoning` 是你的公开理由，保持你的人设风格
- `inner_monologue` 是你的内心独白，可以更加直白犀利

## 人设保持

保持你在节目中的独特人设和风格，严格按照你的 persona 定义来表达观点。

记住：**必须做出明确选择，不要两边都说好话！**
"""


# ============ 2. 二选一讨论模式 ============

BINARY_CHOICE_DEBATE_INSTRUCTION = """
【群聊剧本模式：二选一讨论】

场景：你们正在一个群聊里，针对刚才的选择结果进行讨论。

## 核心原则

1. **针对分歧展开**：
   - 重点讨论为什么有人选 A，有人选 B
   - 攻击对方的理由是否站得住脚
   - 不要重复你在第一阶段说过的话

2. **保持简短**：
   - ❌ 严禁超过 3 句话
   - ✅ 最好 1-2 句话搞定
   - 像真实的微信群聊一样，短促有力

3. **拒绝和稀泥**：
   - ❌ "其实两个答案都有道理..."
   - ✅ 坚持你的选择，批评对方的选择
   - 展现你的立场和态度

4. **动态回应**：
   - 针对刚才别人说的话进行回应
   - 不要机械重复自己的观点
   - 话题转移时跟着走

## 上下文引用

你会看到【选择摘要】，包含：
- 每个评委的选择（A 或 B）
- 每个评委的理由

请基于这些信息进行讨论，找出对方的漏洞。

## 人设保持

严格保持你的人设和说话风格，按照你的 persona 定义来发言。
"""


# ============ 3. 辅助工具函数 ============

def build_binary_choice_summary_text(
    entry_id: str,
    question: str,
    option_a: str,
    option_b: str,
    judge_results: list[dict]
) -> str:
    """
    构建二选一选择摘要
    
    Args:
        entry_id: 作品 ID
        question: 二选一问题
        option_a: 选项 A
        option_b: 选项 B
        judge_results: 评委结果列表
        
    Returns:
        格式化的摘要文本
    """
    # 统计选择
    choice_a_judges = [r for r in judge_results if r["choice"] == "A"]
    choice_b_judges = [r for r in judge_results if r["choice"] == "B"]
    
    summary_lines = [
        f"【二选一问题】{question}",
        f"【选项 A】{option_a}",
        f"【选项 B】{option_b}",
        "",
        f"【投票结果】",
        f"选择 A（{option_a}）：{len(choice_a_judges)} 票",
        f"选择 B（{option_b}）：{len(choice_b_judges)} 票",
        "",
        "【各评委选择及理由】",
    ]
    
    # 按选择分组显示
    if choice_a_judges:
        summary_lines.append(f"\n▶ 选择 A（{option_a}）的评委：")
        for r in choice_a_judges:
            summary_lines.append(
                f"- {r['judge_display_name']}: {r['reasoning']}"
            )
    
    if choice_b_judges:
        summary_lines.append(f"\n▶ 选择 B（{option_b}）的评委：")
        for r in choice_b_judges:
            summary_lines.append(
                f"- {r['judge_display_name']}: {r['reasoning']}"
            )
    
    return "\n".join(summary_lines)


def parse_binary_choice_response(raw_response: str) -> dict:
    """
    解析二选一评委的响应
    
    Args:
        raw_response: 评委的原始响应文本
        
    Returns:
        解析后的字典，包含：
        - choice: "A" 或 "B"
        - reasoning: 理由
        - inner_monologue: 内心独白（可选）
    """
    result = {
        "choice": None,
        "reasoning": None,
        "inner_monologue": None,
    }
    
    # 提取 inner_monologue
    monologue_match = re.search(
        r'<inner_monologue>(.*?)</inner_monologue>',
        raw_response,
        re.DOTALL | re.IGNORECASE
    )
    if monologue_match:
        result["inner_monologue"] = monologue_match.group(1).strip()
    
    # 提取 JSON 部分
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
    if json_match:
        try:
            json_content = json_match.group(1).strip()
            parsed_json = json.loads(json_content)
            
            # 提取 choice（必须是 A 或 B）
            choice = parsed_json.get("choice", "").strip().upper()
            if choice in ["A", "B"]:
                result["choice"] = choice
            
            # 提取 reasoning
            result["reasoning"] = parsed_json.get("reasoning", "").strip()
            
        except json.JSONDecodeError as e:
            # JSON 解析失败，尝试提取关键字段
            pass
    
    # 如果 JSON 解析失败，尝试从文本中提取
    if not result["choice"]:
        # 尝试匹配 "choice": "A" 或 "choice": "B"
        choice_match = re.search(r'"choice"\s*:\s*"([ABab])"', raw_response)
        if choice_match:
            result["choice"] = choice_match.group(1).upper()
    
    if not result["reasoning"]:
        # 尝试匹配 "reasoning": "..."
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', raw_response)
        if reasoning_match:
            result["reasoning"] = reasoning_match.group(1)
    
    return result
