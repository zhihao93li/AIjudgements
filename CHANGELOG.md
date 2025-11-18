# 更新日志

## [1.0.0] - 2025-11-17

### ✨ 新功能

- 🎭 实现多评委并发看图评分系统（阶段一）
  - 支持 5 个评委：ChatGPT-5、Grok、Gemini 2.5、豆包、千问
  - 多模态支持，评委直接观看图片评分
  - 结构化 JSON 输出，包含总分、维度分、优缺点等

- 💬 实现评委群聊讨论系统（阶段二）
  - 基于 AutoGen SelectorGroupChat
  - 智能选择下一位发言者
  - 自动生成综艺感对话内容

- 🚀 FastAPI REST API
  - POST /api/judge_entry - 提交评分请求
  - GET /api/judge_entry/{id} - 查询评分结果
  - GET /api/health - 健康检查

- 💾 数据库系统
  - SQLAlchemy ORM
  - 支持 SQLite（开发）/ PostgreSQL（生产）
  - 完整的 CRUD 操作

- 📊 日志系统
  - 基于 Loguru
  - 彩色控制台输出
  - 按日期轮转的文件日志
  - 独立的错误日志

### 📚 文档

- README.md - 项目介绍和快速开始
- docs/API.md - API 接口文档
- docs/DEPLOYMENT.md - 部署指南
- docs/ARCHITECTURE.md - 系统架构文档

### 🧪 测试

- tests/test_example.py - 单元测试示例
- tests/test_api.sh - API 测试脚本
- examples/quick_start.py - 快速开始示例

### 🎯 支持的比赛类型

- outfit - 穿搭大赛
- funny - 搞笑图片大赛

### 📦 依赖

- autogen-agentchat 0.4.0.dev8
- autogen-ext[openai] 0.4.0.dev8
- FastAPI 0.115.0
- SQLAlchemy 2.0.35
- Pydantic 2.9.2
- Loguru 0.7.2

---

## 未来计划

### v1.1（即将发布）

- [ ] 添加更多评委模型支持
- [ ] 优化 JSON 解析容错性
- [ ] 添加请求缓存机制
- [ ] 完善错误处理

### v2.0

- [ ] 支持多图评分
- [ ] 添加主持人角色
- [ ] 实时流式输出
- [ ] 异步任务队列（Celery）
- [ ] 更多比赛类型模板

### v3.0

- [ ] 用户交互支持（追问）
- [ ] 评论系统
- [ ] 排行榜功能
- [ ] 数据分析看板
- [ ] Web 前端界面

