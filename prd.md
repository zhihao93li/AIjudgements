1. 背景与目标
1.1 背景

我们想做一个「AI 评委」的娱乐型 & 可扩展系统，用于：

穿搭大赛、选美大赛

搞笑图片/表情包大赛

其他基于图片的创意大赛

核心玩法：

用户上传自己的图片参赛；

多个大模型（ChatGPT-5、Grok、Gemini 2.5、豆包、千问等）扮演不同人设的“评委”；

每个评委自己看图给出评分与评价；

之后评委们在“评委群聊”里基于各自的评分和观点互相吐槽/讨论；

讨论过程和最终评分一起，用于对外展示和内容二次创作。

1.2 目标

实现一套通用的评委评分系统，支持接多个模型、多个比赛类型（穿搭、搞笑等）。

所有评委可以直接接收图片输入（多模态），而不是依赖中间的文字描述。

提供两阶段结果：

阶段一：每个评委的独立评分（结构化 JSON）。

阶段二：基于评分结果的多评委群聊讨论记录（文本对话）。

对上层产品暴露简单的 API，便于之后对接 Web 页面 / 小程序 / 自建后台。

2. 范围
2.1 本期范围（v1）

支持单张图片作为一个参赛作品（Entry）。

支持一个评委 panel：
ChatGPT-5 / Grok / Gemini 2.5 / 豆包 / 千问（具体模型可以替换）。

阶段一：每个评委直接看图打分：

使用 OpenAI 兼容多模态接口（通过 DMX 或其他聚合网关）。

输出统一 JSON 结构。

阶段二：评委群聊讨论：

使用 AutoGen 的 SelectorGroupChat 或类似实现；

以阶段一的评分结果作为输入上下文；

产出一段可对外展示的群聊对话（带说话人）。

提供基础的后端接口：

提交参赛作品并触发评分；

查询某个作品的评委评分与群聊记录。

2.2 不在本期范围

多轮用户交互（例如参赛者补充说明之后重新评分）。

多张图/图文组合的复杂作品结构。

复杂的账号体系和权限管理。

复杂的计费/额度控制（先假设系统内部使用）。

3. 用户与场景
3.1 角色

参赛用户（Player）：上传图片参与活动。

运营/活动策划（Ops）：配置比赛类型、评委人设、评分维度，查看结果。

开发/平台方（Dev）：负责实现后端的评委系统与集成。

3.2 典型使用场景

运营配置好「穿搭大赛」：

维度：风格统一度、创意与个性、实用性、场景适配度。

启用评委：5 个（ChatGPT-5 / Grok / Gemini / 豆包 / 千问）。

用户上传照片参赛。

后端触发：

阶段一：5 个评委各自看图打分；

阶段二：评委根据初始评分开启群聊讨论 8～12 轮。

前端展示：

各评委的独立评分卡片；

综合排序（总榜单）；

评委聊天内容截图/文本，用于营造综艺感。

4. 核心流程设计
4.1 总体流程

接收作品（Entry）：

入参至少包含：entry_id、image_url、competition_type、extra_text（可选）。

阶段一：多评委评分

对所有评委并发执行「看图 + 评分输出」。

落库 JudgeResult。

阶段二：群聊讨论

将各评委的 JudgeResult 汇总成“初评摘要上下文”；

构建群聊团队（同一批评委 Agent，但系统提示切换为“讨论模式”）；

使用 SelectorGroupChat 进行 N 轮对话；

落库 DebateSession 与 DebateMessage。

对外查询：

根据 entry_id 查询：

所有评委评分 JSON；

评委排名；

群聊讨论记录。

5. 数据结构（建议）
5.1 Entry（作品）

entry_id：string

image_url：string

competition_type：string（例如 outfit / funny）

extra_text：string（可选，用户自述或运营补充说明）

created_at / updated_at

5.2 JudgeResult（评委评分）

结构尽量贴近模型输出 JSON：

entry_id

judge_id：和 Agent name 一致（如 chatgpt5_judge）

judge_display_name

competition_type

overall_score：float

dimension_scores：JSON 数组

strengths：JSON 数组

weaknesses：JSON 数组

one_liner：string

comment_for_audience：string

safety_notes：JSON 数组

raw_output：string（模型原始返回，方便 debug）

created_at

5.3 DebateSession（群聊会话）

debate_id：string（如 entry_id + "_debate"）

entry_id

participants：数组，列表内是评委 id/name

config：JSON（记录 selector 参数、轮数上限等）

created_at

5.4 DebateMessage（群聊消息）

debate_id

sequence：int（轮次顺序）

speaker：string（评委 id）

content：string（自然语言内容）

created_at

6. 阶段一技术方案：多评委直接看图评分
6.1 模型客户端

使用 autogen-ext.models.openai.OpenAIChatCompletionClient 封装 OpenAI 兼容接口。

每个评委有独立的 model_client，指定对应的模型名与 family。

def make_vision_client(model: str, family: str) -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=model,
        api_key=LLM_GATEWAY_API_KEY,
        base_url=LLM_GATEWAY_BASE_URL,
        model_info={
            "vision": True,          # 关键：告诉 AutoGen 这是一种多模态模型
            "function_calling": False,
            "json_output": True,
            "family": family,
        },
    )


注意：
各模型名（ChatGPT-5 / Grok / Gemini / 豆包 / 千问）由配置文件决定；
要确保选用的都是网关支持的 vision 型号。

6.2 通用评分规范（system_message 公共部分）

见前面的 JSON Schema & 规范说明，这里不再重复。
实现上建议用一个长字符串 COMMON_SCORING_GUIDE，在各评委的 system_message 中引用，并在其后追加人设描述。

6.3 评委 Agent 定义

每个评委一个 AssistantAgent，示例：

from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import UnboundedChatCompletionContext

def build_vision_judges() -> list[AssistantAgent]:
    judges = []

    judges.append(
        AssistantAgent(
            name="chatgpt5_judge",
            model_client=make_vision_client("gpt-4o", family="openai-gpt4"),
            model_context=UnboundedChatCompletionContext(),
            system_message=COMMON_SCORING_GUIDE + """
【本评委人设】
- 名字：「ChatGPT-5 评委」。
- 风格中立、理性，擅长做均衡的综合判断和总结。
""",
        )
    )

    # 其他评委类似：Grok / Gemini / 豆包 / 千问
    return judges

6.4 多模态消息构造（图片 + 文本）

使用 MultiModalMessage 和 AGImage：

from autogen_agentchat.messages import MultiModalMessage
from autogen_core import Image as AGImage
from PIL import Image as PILImage
import requests
from io import BytesIO

def build_multimodal_message(image_url: str,
                             entry_id: str,
                             competition_type: str,
                             extra_text: str | None = None) -> MultiModalMessage:
    resp = requests.get(image_url)
    resp.raise_for_status()
    pil_image = PILImage.open(BytesIO(resp.content))
    ag_image = AGImage(pil_image)

    instruction = f"""
这是参赛作品 {entry_id} 的图片，比赛类型为 {competition_type}。

请你直接观察图片，根据系统提示中的评分规范，对作品进行打分和点评，并输出约定好的 JSON 结构。
"""

    if extra_text:
        instruction += f"\n\n补充说明：{extra_text}"

    return MultiModalMessage(
        content=[instruction, ag_image],
        source="user",
    )

6.5 阶段一评分执行流程
import asyncio
import json

async def score_image_with_all_judges(image_url: str,
                                      entry_id: str,
                                      competition_type: str = "outfit",
                                      extra_text: str | None = None) -> dict:
    mm_msg = build_multimodal_message(
        image_url=image_url,
        entry_id=entry_id,
        competition_type=competition_type,
        extra_text=extra_text,
    )

    judges = build_vision_judges()

    tasks = [j.on_messages([mm_msg]) for j in judges]
    results = await asyncio.gather(*tasks)

    judge_outputs = []
    for judge, res in zip(judges, results):
        msg = res.messages[-1]
        raw = msg.content
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {
                "judge_id": judge.name,
                "error": "invalid_json",
                "raw_output": raw,
            }
        judge_outputs.append(data)

    # 排序
    valid = [r for r in judge_outputs if "overall_score" in r]
    sorted_results = sorted(valid, key=lambda r: r["overall_score"], reverse=True)

    return {
        "entry_id": entry_id,
        "competition_type": competition_type,
        "judge_results": judge_outputs,
        "sorted_results": sorted_results,
    }


阶段一结束后需要：

将 judge_results 落库为 JudgeResult；

为阶段二准备一个结构化的 summary。

7. 阶段二技术方案：评委群聊讨论（SelectorGroupChat）
7.1 阶段二目标

在所有评委独立打分后：

让评委们基于各自的评分、优缺点和观点开展一段“群聊讨论”；

讨论中可以：

引用自己的打分；

反驳/补充其他评委；

在接近结束时由某一位评委（如 ChatGPT-5）给出一个简短的“综合评论”。

输出用于：

对外展示（综艺感的内容）；

二次内容创作（剪辑、配字幕等）。

7.2 群聊参与者

参与者：和阶段一同一批评委（5 个 AssistantAgent），但 system_message 需要增加“讨论模式说明”。

额外增加一个“导演/选择器模型”（轻量模型，例如 gpt-4o-mini）负责决定下一位发言的评委 —— 通过 SelectorGroupChat 实现。

7.3 讨论输入（上下文）

群聊不会直接再看图，而是基于「阶段一结果摘要」。
建议由后端生成一段结构化文字上下文，例如：

比赛类型：outfit
作品ID：entry_001

各评委初始评分如下：

- ChatGPT-5 评委：overall_score = 8.5
  优点：色彩搭配有记忆点；整体风格统一。
  缺点：配饰略简单。

- Grok 评委：overall_score = 7.2
  优点：街头感还不错。
  缺点：鞋子和上半身风格有点分裂。

- Gemini 2.5 评委：overall_score = 8.0
  维度评分：
    - 风格统一度：8
    - 创意与个性：8
    - 实用性：7
    - 场景适配度：9

- 豆包评委：overall_score = 7.8
  评价更偏向“日常可穿”。

- 千问评委：overall_score = 8.3
  更关注氛围感和故事感，认为整体调性偏复古通勤。

请在后续群聊中，围绕这些初始评分和观点展开讨论。


这段上下文会作为群聊的第一条 User 消息输入。

7.4 讨论模式下的评委 system_message

在原有评分规范基础上，为群聊阶段追加规则（也可以为群聊新建一套更轻量的 system_message）：

【群聊讨论模式说明】

现在进入“评委群聊讨论”阶段：

- 你已经完成了对作品的独立打分和点评。
- 当前阶段不需要重新打分，而是：
  1）解释你当时打分背后的理由；
  2）认可或反驳其他评委的观点；
  3）在合适的时候，补充你认为被忽略的点。

讨论规则：
- 保持语气有个性，但不要攻击参赛者本人，只围绕作品。
- 可以直接点名其他评委，例如“我同意 Grok 评委说的鞋子有点突兀”。
- 每次发言建议 2~5 句，避免长篇大论。
- 如果已经接近结尾，你可以尝试做一个简短的总结观点。


可以选择：

重用阶段一的 AssistantAgent，在讨论阶段动态覆盖/追加 system_message；

或者为讨论阶段单独实例化一批“讨论用评委 Agent”（推荐做成两套配置，方便分别调试）。

7.5 SelectorGroupChat 配置（核心）

使用 AutoGen 的 SelectorGroupChat：

participants: 5 个评委 Agent

model_client: 一个轻量模型（用于选择下一位发言者），比如 gpt-4o-mini

selector_prompt: 决策谁说话的提示词

termination_condition: 最大消息数，或由某位评委触发“结束”

selector_prompt 示例：

你是一个“评委群聊”的导演，只负责根据对话内容选择下一位发言的评委。

候选评委及其角色：
{roles}

当前对话记录：
{history}

候选评委列表：{participants}

选择规则：
1. 尽量保证每位评委至少发言一轮。
2. 如果上一条发言点名或提到了某位评委（例如提到其名字），优先选择被点名的评委回应。
3. 如果出现明显分歧或相反观点，优先选择立场不同的评委发言。
4. 临近结束时，更倾向选择 chatgpt5_judge 来帮助收束观点。

只输出一个名字，必须是 {participants} 中的一个，例如 "chatgpt5_judge"。
不要输出任何其他内容。


终止条件示例：

使用 MaxMessageTermination：

配置 max_messages = 10～15；

即最多对话轮数，防止对话过长。

7.6 群聊执行流程

伪代码结构：

from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import UserMessage

async def run_debate_for_entry(entry_id: str,
                               judge_results: list[dict]) -> dict:
    # 1. 生成“初评摘要上下文”
    summary_text = build_judge_summary_text(entry_id, judge_results)

    # 2. 构造群聊首条消息
    first_msg = UserMessage(
        content=summary_text,
        source="user",
    )

    # 3. 构建评委 Agent（讨论模式的 system_message，可重用函数）
    judges_for_debate = build_vision_judges_for_debate()

    # 4. SelectorGroupChat 配置
    selector_model_client = make_vision_client(
        model="gpt-4o-mini",  # 或任一轻量文本模型即可
        family="openai-gpt4"
    )

    team = SelectorGroupChat(
        participants=judges_for_debate,
        model_client=selector_model_client,
        selector_prompt=SELECTOR_PROMPT,  # 上面示例
        allow_repeated_speaker=False,
        termination_condition=MaxMessageTermination(max_messages=12),
    )

    # 5. 运行群聊
    result_stream = team.run_stream(
        task=first_msg,
    )
    # 这里按 autogen-agentchat 的实际 async 接口实现，
    # 需要遍历 stream 获取 message 序列。

    debate_messages = []  # [{speaker, content, sequence}, ...]

    async for event in result_stream:
        if event.message:
            debate_messages.append({
                "speaker": event.message.source,  # 评委 name
                "content": event.message.content,
            })

    # 6. 返回结果，便于落库
    return {
        "entry_id": entry_id,
        "messages": debate_messages,
    }


（具体 async 接口写法开发可按实际版本调整，这里是逻辑结构说明。）

8. API 设计（对上层）
8.1 提交评分 & 讨论（同步版）

后期可以拆成异步任务，这里先假设作品量不大，用同步接口单次跑完阶段一+二。

POST /api/judge_entry

请求体：

{
  "entry_id": "entry_001",
  "image_url": "https://xxx/your-image.jpg",
  "competition_type": "outfit",
  "extra_text": "日常通勤穿搭，身高体型信息省略。"
}


返回体：

{
  "entry_id": "entry_001",
  "competition_type": "outfit",
  "judge_results": [ /* 各评委 JSON */ ],
  "sorted_results": [ /* 按 overall_score 排序后的列表 */ ],
  "debate": {
    "messages": [
      {
        "speaker": "grok_judge",
        "content": "第一轮吐槽……"
      },
      {
        "speaker": "chatgpt5_judge",
        "content": "总结一下上一位说的……"
      }
    ]
  }
}


实现上建议：

接口内部串行执行：阶段一 → 阶段二；

阶段一/二中的异常要有日志，并在返回中标记某些评委失败而不是整体崩掉。

8.2 查询结果接口

GET /api/judge_entry/{entry_id}

返回：

从数据库读取 JudgeResult + DebateSession + DebateMessage。

用于前端渲染评委评分与群聊内容。

9. 日志与监控

记录以下关键日志：

每次评委调用的模型名、耗时、是否成功解析 JSON。

阶段二群聊的消息条数、是否触发终止条件。

指标建议：

单次 judge_entry 总耗时；

各模型平均响应时长；

JSON 解析失败率。

10. 版本规划
v1（当前 PRD）

单图、多评委直接看图评分；

单轮群聊讨论（SelectorGroupChat）；

基本 API 接入完成。

v2（后续可选）

支持多图/多视角；

支持更多比赛类型（搞笑、文案大赛等） + 不同维度模板；

引入“主持人”角色，对群聊过程进行引导和最终总结；

支持异步任务和队列，适配大规模参赛作品。