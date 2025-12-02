# 二选一模式架构文档

## 概述

本文档描述二选一模式的实现架构。二选一模式与现有的评分模式**完全解耦**，两者互不影响。

## 设计原则

### 1. 完全解耦
- **独立的数据模型**：使用独立的数据库表
- **独立的业务逻辑**：独立的stage_one和stage_two实现
- **独立的API路由**：使用`/api/binary_choice`前缀
- **独立的Schema**：请求和响应模型完全独立

### 2. 共享评委Persona
- **唯一的耦合点**：两个模式共享`JUDGE_PERSONAS`定义
- 位置：`app/judges/prompts.py`
- 这保证了评委的人设在两个模式中保持一致

## 架构组成

### 数据层

#### 数据库模型 (`app/models/binary_choice_database.py`)
```
BinaryChoiceEntry          # 二选一作品表
├── entry_id              # 作品ID
├── question              # 二选一问题
├── option_a              # 选项A
├── option_b              # 选项B
├── image_url             # 图片URL（可选）
├── text_content          # 文本内容（可选）
└── extra_context         # 补充说明

BinaryChoiceResult        # 评委选择结果表
├── judge_id              # 评委ID
├── choice                # 选择：'A' 或 'B'
├── choice_label          # 选项标签
├── reasoning             # 选择理由
└── inner_monologue       # 内心独白

BinaryChoiceDebateSession # 讨论会话表
└── messages              # 讨论消息

BinaryChoiceMessage       # 讨论消息表
├── speaker               # 发言者
└── content               # 发言内容
```

#### Schema定义 (`app/models/binary_choice_schemas.py`)
- `BinaryChoiceRequest`：请求模型
- `BinaryChoiceResponse`：响应模型
- `BinaryChoiceJudgeResult`：单个评委结果
- `BinaryChoiceDebateResponse`：讨论结果

#### CRUD操作 (`app/db/binary_choice_crud.py`)
- `save_binary_choice_entry`：保存作品
- `save_binary_choice_results`：保存评委结果
- `save_binary_choice_debate`：保存讨论记录
- `get_binary_choice_entry_by_id`：查询作品

### 业务逻辑层

#### Prompts (`app/judges/binary_choice_prompts.py`)
- `BINARY_CHOICE_GUIDE`：二选一评判指南
- `BINARY_CHOICE_DEBATE_INSTRUCTION`：讨论指南
- `build_binary_choice_summary_text`：构建选择摘要
- `parse_binary_choice_response`：解析评委响应
- **共享**：`JUDGE_PERSONAS`（从`app/judges/prompts.py`导入）

#### 阶段一 (`app/judges/binary_choice_stage_one.py`)
主函数：`binary_choice_with_all_judges`
1. 构建评委Agent（使用二选一指南）
2. 构建消息（支持图片/文本/两者）
3. 并发调用所有评委
4. 解析选择和理由
5. 统计投票结果

#### 阶段二 (`app/judges/binary_choice_stage_two.py`)
主函数：`run_binary_choice_debate`
1. 构建讨论评委（注入各自的选择）
2. 生成选择摘要
3. 创建SelectorGroupChat
4. 运行讨论
5. 清洗和保存消息

### API层

#### 路由 (`app/api/binary_choice_routes.py`)
- **POST** `/api/binary_choice/judge`：完整评判流程
- **GET** `/api/binary_choice/entry/{entry_id}`：查询结果

路由已在`app/main.py`中注册：
```python
app.include_router(binary_choice_router, prefix="/api/binary_choice", tags=["二选一模式"])
```

## 使用示例

### 请求示例

```json
{
  "question": "男朋友有没有错？",
  "option_a": "有错",
  "option_b": "没错",
  "image_url": "https://example.com/image.jpg",
  "extra_context": "情侣吵架场景"
}
```

或使用文本：

```json
{
  "question": "这个产品设计是否合理？",
  "option_a": "合理",
  "option_b": "不合理",
  "text_content": "产品采用了极简设计理念，去掉了所有实体按钮..."
}
```

### 响应示例

```json
{
  "entry_id": "binary_abc123",
  "question": "男朋友有没有错？",
  "option_a": "有错",
  "option_b": "没错",
  "choice_a_count": 3,
  "choice_b_count": 2,
  "judge_results": [
    {
      "judge_id": "ChatGPT",
      "judge_display_name": "ChatGPT",
      "choice": "A",
      "choice_label": "有错",
      "reasoning": "从沟通角度来看，他应该主动道歉",
      "inner_monologue": "（内心独白内容）"
    }
  ],
  "debate": {
    "debate_id": "binary_abc123_debate",
    "participants": ["ChatGPT", "Grok", "Gemini"],
    "messages": [...]
  }
}
```

## 工作流程

### 完整流程

1. **接收请求** → `POST /api/binary_choice/judge`
2. **保存作品** → `save_binary_choice_entry()`
3. **阶段一：评委选择**
   - `binary_choice_with_all_judges()`
   - 每个评委看到问题、选项和内容
   - 选择A或B，并给出理由
4. **保存选择结果** → `save_binary_choice_results()`
5. **阶段二：讨论**
   - `run_binary_choice_debate()`
   - 看到所有评委的选择和理由
   - 针对分歧进行讨论
6. **保存讨论记录** → `save_binary_choice_debate()`
7. **返回完整结果**

## 与现有评分模式的对比

| 特性 | 评分模式 | 二选一模式 |
|------|----------|-----------|
| **数据模型** | Entry, JudgeResult, DebateSession | BinaryChoiceEntry, BinaryChoiceResult, BinaryChoiceDebateSession |
| **输入** | 图片 + 可选文本 | 图片/文本/两者 + 问题 + 两个选项 |
| **阶段一输出** | 分数 + 评语 | 选择（A/B）+ 理由 |
| **API前缀** | `/api` | `/api/binary_choice` |
| **提示词** | COMMON_SCORING_GUIDE | BINARY_CHOICE_GUIDE |
| **共享** | 无 | JUDGE_PERSONAS |

## 数据库表结构

数据库初始化时会自动创建以下表：

```sql
-- 现有表（不变）
entries
judge_results
debate_sessions
debate_messages

-- 新增表（二选一模式）
binary_choice_entries
binary_choice_results
binary_choice_debate_sessions
binary_choice_messages
```

## 文件清单

### 新增文件
1. `app/models/binary_choice_database.py` - 数据库模型
2. `app/models/binary_choice_schemas.py` - Pydantic模型
3. `app/db/binary_choice_crud.py` - CRUD操作
4. `app/judges/binary_choice_prompts.py` - 提示词定义
5. `app/judges/binary_choice_stage_one.py` - 阶段一逻辑
6. `app/judges/binary_choice_stage_two.py` - 阶段二逻辑
7. `app/api/binary_choice_routes.py` - API路由

### 修改文件
1. `app/models/__init__.py` - 添加二选一模型导出
2. `app/main.py` - 注册二选一路由

### 不影响的文件（现有路径）
- `app/api/routes.py` - 无修改
- `app/judges/stage_one.py` - 无修改
- `app/judges/stage_two.py` - 无修改
- `app/db/crud.py` - 无修改
- 所有前端文件 - 无修改

## 注意事项

1. **数据库迁移**：首次运行需要初始化数据库以创建新表
2. **评委Persona**：修改`JUDGE_PERSONAS`会同时影响两个模式
3. **完全独立**：除了共享persona外，两个模式没有任何交互
4. **前端开发**：需要为二选一模式开发独立的前端页面

## 下一步

### 后端（已完成）
- ✅ 数据模型
- ✅ 业务逻辑
- ✅ API路由
- ✅ 数据库集成

### 前端（待开发）
- ⏳ 二选一提交页面
- ⏳ 二选一结果展示页面
- ⏳ 投票结果可视化
- ⏳ 讨论展示界面
