# 系统架构文档

## 系统概览

AI Judge System 是一个基于多模态 AI 的娱乐评分系统，采用两阶段评分流程：

1. **阶段一**：多个 AI 评委并发观看图片并独立打分
2. **阶段二**：评委基于评分结果进行群聊讨论

## 技术架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         客户端层                              │
│  (Web / 小程序 / 移动端 / API Client)                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTP/HTTPS
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                      FastAPI 应用层                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API 路由层 (routes.py)                               │   │
│  │  - POST /api/judge_entry  (评分)                      │   │
│  │  - GET  /api/judge_entry/{id}  (查询)                 │   │
│  │  - GET  /api/health  (健康检查)                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
┌──────────┐ ┌─────────┐ ┌──────────────┐
│  评委系统 │ │ 数据库层 │ │  配置 & 日志  │
│          │ │         │ │              │
│ Stage 1  │ │ SQLite/ │ │  Config      │
│ (评分)   │ │ Postgres│ │  Loguru      │
│          │ │         │ │              │
│ Stage 2  │ │ CRUD    │ │  Settings    │
│ (讨论)   │ │ ORM     │ │              │
└────┬─────┘ └─────────┘ └──────────────┘
     │
     │ OpenAI Compatible API
     │
     ▼
┌─────────────────────────────────────────┐
│         LLM Gateway / API                │
│  ┌──────────────────────────────────┐   │
│  │  ChatGPT-5 / GPT-4o              │   │
│  │  Grok                            │   │
│  │  Gemini 2.5                      │   │
│  │  豆包 (Doubao)                   │   │
│  │  千问 (Qwen)                     │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 核心模块

### 1. 评委系统 (app/judges/)

#### stage_one.py - 阶段一评分

```python
功能：
- 构建多模态评委 Agent
- 下载并处理图片
- 并发调用所有评委
- 解析和验证 JSON 响应
- 排序评分结果

流程：
1. build_vision_judges() -> 创建 5 个 AssistantAgent
2. build_multimodal_message() -> 构建图片+文本消息
3. asyncio.gather() -> 并发执行
4. parse_json_from_response() -> 提取 JSON
5. 排序并返回结果
```

#### stage_two.py - 阶段二讨论

```python
功能：
- 构建讨论模式的评委 Agent
- 生成初评摘要上下文
- 配置 SelectorGroupChat
- 运行群聊并收集消息

流程：
1. build_debate_judges() -> 创建讨论模式 Agent
2. build_judge_summary_text() -> 生成上下文
3. SelectorGroupChat() -> 配置群聊
4. team.run_stream() -> 运行讨论
5. 收集并返回消息
```

#### prompts.py - Prompt 管理

```python
包含：
- COMMON_SCORING_GUIDE: 通用评分规范
- JUDGE_PERSONAS: 5 个评委的人设
- DEBATE_MODE_INSTRUCTION: 讨论模式说明
- SELECTOR_PROMPT_TEMPLATE: 选择器提示词
- build_judge_summary_text(): 摘要生成函数
```

#### utils.py - 工具函数

```python
功能：
- make_vision_client(): 创建多模态客户端
- make_text_client(): 创建文本客户端
- get_model_for_judge(): 获取评委模型名
- parse_json_from_response(): JSON 提取
```

### 2. 数据层 (app/models/)

#### database.py - ORM 模型

```python
表结构：
- Entry: 参赛作品
- JudgeResult: 评委评分
- DebateSession: 讨论会话
- DebateMessage: 讨论消息

关系：
Entry 1:N JudgeResult
Entry 1:N DebateSession
DebateSession 1:N DebateMessage
```

#### schemas.py - Pydantic 模型

```python
用途：
- API 请求验证
- API 响应序列化
- 数据类型约束

主要模型：
- JudgeEntryRequest: 评分请求
- JudgeEntryResponse: 评分响应
- EntryResponse: 作品查询响应
```

### 3. 数据库操作 (app/db/)

#### crud.py - CRUD 函数

```python
异步操作：
- save_entry(): 保存作品
- save_judge_results(): 保存评分
- save_debate_session(): 保存讨论
- get_entry_by_id(): 查询作品
- get_judge_results_by_entry(): 查询评分
- get_debate_by_entry(): 查询讨论
```

### 4. API 层 (app/api/)

#### routes.py - 路由定义

```python
端点：
- POST /api/judge_entry: 完整评分流程
- GET /api/judge_entry/{id}: 查询结果
- GET /api/health: 健康检查

特点：
- 依赖注入 (Depends)
- 异常处理
- 日志记录
```

### 5. 配置管理 (app/config.py)

```python
使用 pydantic-settings 管理配置：
- 环境变量读取
- 类型验证
- 默认值设置
- 配置单例 (@lru_cache)
```

### 6. 日志系统 (app/logger.py)

```python
使用 loguru 提供：
- 彩色控制台输出
- 文件日志（按日期轮转）
- 错误日志单独记录
- 自动压缩归档
```

## 数据流程

### 完整评分流程

```
1. 客户端提交请求
   ↓
2. API 层接收并验证
   ↓
3. 保存作品信息到数据库
   ↓
4. 阶段一：并发评分
   ├─ 下载图片
   ├─ 构建多模态消息
   ├─ 5 个评委并发调用
   ├─ 解析 JSON 响应
   └─ 排序结果
   ↓
5. 保存评分结果
   ↓
6. 阶段二：群聊讨论
   ├─ 生成初评摘要
   ├─ 创建 SelectorGroupChat
   ├─ 运行群聊（8-12 轮）
   └─ 收集消息
   ↓
7. 保存讨论记录
   ↓
8. 返回完整结果给客户端
```

## 关键技术选型

### AutoGen Framework

- **用途**：多 Agent 协作框架
- **优势**：
  - 原生支持多模态
  - 内置 GroupChat 机制
  - 灵活的 Agent 配置
  - 良好的异步支持

### FastAPI

- **用途**：Web 框架
- **优势**：
  - 高性能（基于 Starlette）
  - 自动 API 文档
  - 类型安全
  - 异步原生支持

### SQLAlchemy

- **用途**：ORM 数据库操作
- **优势**：
  - 强大的查询能力
  - 异步支持
  - 多数据库兼容
  - 关系映射清晰

### Loguru

- **用途**：日志管理
- **优势**：
  - 简单易用
  - 彩色输出
  - 自动轮转
  - 结构化日志

## 扩展性设计

### 1. 新增评委

```python
# 在 prompts.py 中添加人设
JUDGE_PERSONAS["new_judge"] = {
    "display_name": "新评委",
    "persona": "人设描述..."
}

# 在 config.py 中添加模型配置
model_new_judge: str = "model-name"

# 在 utils.py 中添加映射
model_mapping["new_judge"] = settings.model_new_judge
```

### 2. 新增比赛类型

```python
# 在 prompts.py 中添加维度定义
# 示例：添加"舞蹈大赛"
"""
### dance（舞蹈大赛）
维度：
- 技术难度
- 表现力
- 创意编排
- 整体协调性
"""
```

### 3. 自定义评分维度

修改 `COMMON_SCORING_GUIDE` 中的维度定义，评委会自动适配。

### 4. 异步任务化

```python
# 引入 Celery
@celery.app.task
async def async_judge_entry(entry_id, image_url, ...):
    # 执行评分逻辑
    pass

# API 返回任务 ID，前端轮询结果
```

## 性能优化

### 并发优化

- 阶段一使用 `asyncio.gather()` 并发调用
- 数据库使用异步 Session
- 图片下载可使用 aiohttp

### 缓存策略

```python
# 对频繁查询的作品结果缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_entry(entry_id):
    pass
```

### 数据库优化

- 添加索引：entry_id, competition_type
- 使用连接池
- 批量插入优化

## 安全考虑

1. **API Key 保护**：环境变量存储，不提交代码库
2. **输入验证**：Pydantic 模型自动验证
3. **SQL 注入防护**：使用 ORM 参数化查询
4. **速率限制**：可集成 slowapi
5. **CORS 配置**：生产环境限制域名

## 监控指标

建议监控：

- API 响应时间
- 评委调用成功率
- 数据库连接池状态
- 内存使用情况
- 并发请求数
- 错误率

## 未来规划

### v2 功能

- 多图支持
- 主持人角色
- 实时流式输出
- 异步任务队列
- 评委投票机制

### v3 功能

- 用户交互（追问、补充）
- 评论系统
- 排行榜系统
- 数据分析看板

