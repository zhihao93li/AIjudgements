# API 文档

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`
- **响应格式**: JSON

## 接口列表

### 1. 健康检查

检查服务是否正常运行。

**请求**

```http
GET /api/health
```

**响应**

```json
{
  "status": "ok",
  "message": "AI Judge System is running"
}
```

---

### 2. 提交评分（完整流程）

提交参赛作品并触发完整的评分流程（阶段一 + 阶段二）。

**请求**

```http
POST /api/judge_entry
Content-Type: application/json

{
  "entry_id": "entry_001",
  "image_url": "https://example.com/image.jpg",
  "competition_type": "outfit",
  "extra_text": "日常通勤穿搭（可选）"
}
```

**参数说明**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| entry_id | string | 是 | 作品唯一 ID |
| image_url | string | 是 | 图片 URL（需公网可访问）|
| competition_type | string | 是 | 比赛类型：outfit（穿搭）/ funny（搞笑）|
| extra_text | string | 否 | 补充说明文本 |

**响应**

```json
{
  "entry_id": "entry_001",
  "competition_type": "outfit",
  "judge_results": [
    {
      "judge_id": "chatgpt5_judge",
      "judge_display_name": "ChatGPT-5 评委",
      "overall_score": 8.5,
      "dimension_scores": [
        {
          "name": "风格统一度",
          "score": 8.0,
          "comment": "整体搭配协调"
        },
        {
          "name": "创意与个性",
          "score": 9.0,
          "comment": "有独特的风格表达"
        }
      ],
      "strengths": [
        "色彩搭配有记忆点",
        "配饰选择恰当"
      ],
      "weaknesses": [
        "鞋子略显单调"
      ],
      "one_liner": "整体表现不错，有进一步提升空间",
      "comment_for_audience": "这是一套很适合日常通勤的搭配...",
      "safety_notes": []
    }
  ],
  "sorted_results": [
    // 按 overall_score 降序排列的评委评分
  ],
  "debate": {
    "debate_id": "entry_001_debate",
    "participants": [
      "chatgpt5_judge",
      "grok_judge",
      "gemini_judge",
      "doubao_judge",
      "qwen_judge"
    ],
    "messages": [
      {
        "sequence": 1,
        "speaker": "grok_judge",
        "content": "我觉得这个搭配挺有意思的..."
      },
      {
        "sequence": 2,
        "speaker": "chatgpt5_judge",
        "content": "我同意 Grok 的观点..."
      }
    ]
  }
}
```

**状态码**

- `200`: 成功
- `500`: 服务器错误（评分失败）

---

### 3. 查询作品结果

根据 `entry_id` 查询已评分作品的完整信息。

**请求**

```http
GET /api/judge_entry/{entry_id}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| entry_id | string | 作品 ID |

**响应**

```json
{
  "entry_id": "entry_001",
  "image_url": "https://example.com/image.jpg",
  "competition_type": "outfit",
  "extra_text": "日常通勤穿搭",
  "created_at": "2025-11-17T10:00:00",
  "judge_results": [
    // 评委评分列表
  ],
  "debate": {
    // 群聊讨论内容
  }
}
```

**状态码**

- `200`: 成功
- `404`: 作品不存在

---

## 数据模型

### JudgeResult（评委评分）

```typescript
{
  judge_id: string;              // 评委 ID
  judge_display_name: string;    // 评委显示名称
  overall_score: number;         // 总分（0-10）
  dimension_scores?: Array<{     // 维度评分
    name: string;
    score: number;
    comment?: string;
  }>;
  strengths?: string[];          // 优点列表
  weaknesses?: string[];         // 缺点列表
  one_liner?: string;           // 一句话点评
  comment_for_audience?: string; // 给观众的评语
  safety_notes?: string[];      // 安全提示
}
```

### DebateMessage（群聊消息）

```typescript
{
  sequence: number;   // 消息序号
  speaker: string;    // 发言者 ID
  content: string;    // 发言内容
}
```

---

## 使用示例

### cURL

```bash
# 提交评分
curl -X POST "http://localhost:8000/api/judge_entry" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_id": "entry_001",
    "image_url": "https://example.com/image.jpg",
    "competition_type": "outfit",
    "extra_text": "日常通勤穿搭"
  }'

# 查询结果
curl "http://localhost:8000/api/judge_entry/entry_001"
```

### Python

```python
import requests

# 提交评分
response = requests.post(
    "http://localhost:8000/api/judge_entry",
    json={
        "entry_id": "entry_001",
        "image_url": "https://example.com/image.jpg",
        "competition_type": "outfit",
        "extra_text": "日常通勤穿搭"
    }
)
result = response.json()

# 查询结果
response = requests.get("http://localhost:8000/api/judge_entry/entry_001")
entry = response.json()
```

### JavaScript

```javascript
// 提交评分
const response = await fetch('http://localhost:8000/api/judge_entry', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    entry_id: 'entry_001',
    image_url: 'https://example.com/image.jpg',
    competition_type: 'outfit',
    extra_text: '日常通勤穿搭'
  })
});
const result = await response.json();

// 查询结果
const entry = await fetch('http://localhost:8000/api/judge_entry/entry_001')
  .then(res => res.json());
```

---

## 错误处理

所有错误响应格式：

```json
{
  "detail": "错误信息描述"
}
```

常见错误：

- 图片 URL 无法访问
- 模型 API 调用失败
- 数据库操作失败

建议在客户端做好错误处理和重试机制。

