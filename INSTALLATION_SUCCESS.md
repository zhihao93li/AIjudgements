# 🎉 安装成功！

## ✅ 已完成的步骤

1. ✅ **Python 3.14.0** 已安装
2. ✅ **虚拟环境** 已创建（`venv/`）
3. ✅ **所有依赖** 已安装：
   - autogen-agentchat 0.7.5（最新版本！）
   - autogen-core 0.7.5
   - autogen-ext 0.7.5
   - FastAPI, SQLAlchemy, Pillow 等
4. ✅ **数据库** 已初始化（`ai_judge.db`）

## 🚀 下一步：配置和启动

### 步骤 1：配置 API Key（必须）

编辑 `.env` 文件：

```bash
nano .env
# 或使用你喜欢的编辑器
```

**必须修改的配置**：

```env
# 修改这行，填入你的 API Key
LLM_GATEWAY_API_KEY=sk-your-actual-api-key-here

# 如果使用 OpenAI 官方 API，保持默认：
LLM_GATEWAY_BASE_URL=https://api.openai.com/v1

# 如果使用其他网关（如 one-api、dmx 等），修改为：
# LLM_GATEWAY_BASE_URL=https://your-gateway.com/v1
```

**可选配置**（根据需要修改）：

```env
# 模型名称配置
MODEL_CHATGPT5=gpt-4o              # ChatGPT-5 评委使用的模型
MODEL_GROK=grok-beta               # Grok 评委（如果有）
MODEL_GEMINI=gemini-2.0-flash-exp  # Gemini 评委（如果有）
MODEL_DOUBAO=doubao-pro-32k        # 豆包评委（如果有）
MODEL_QWEN=qwen-max                # 千问评委（如果有）
MODEL_SELECTOR=gpt-4o-mini         # 选择器模型（用于群聊）

# 讨论配置
MAX_DEBATE_MESSAGES=12             # 群聊最大轮数
```

### 步骤 2：启动服务

```bash
# 确保在项目目录
cd /Users/zhihaoli/Documents/项目/show5

# 激活虚拟环境
source venv/bin/activate

# 启动服务
python app/main.py
```

**成功启动后会看到**：

```
============================================================
AI Judge System 正在启动...
============================================================
数据库初始化完成
系统启动完成！
API 文档地址: http://0.0.0.0:8000/docs
```

### 步骤 3：测试系统

#### 方式 1：使用 Swagger UI（推荐，最简单）

1. 打开浏览器访问：http://localhost:8000/docs
2. 找到 `POST /api/judge_entry` 接口
3. 点击 "Try it out"
4. 填入测试数据：

```json
{
  "entry_id": "test_001",
  "image_url": "https://picsum.photos/800/600",
  "competition_type": "outfit",
  "extra_text": "测试穿搭图片"
}
```

5. 点击 "Execute"
6. 等待 1-2 分钟（评委评分 + 群聊讨论）
7. 查看返回结果！

#### 方式 2：使用 Python 示例脚本

```bash
# 在另一个终端窗口
cd /Users/zhihaoli/Documents/项目/show5
source venv/bin/activate
python examples/quick_start.py
```

#### 方式 3：使用 cURL

```bash
curl -X POST "http://localhost:8000/api/judge_entry" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_id": "test_002",
    "image_url": "https://picsum.photos/800/600",
    "competition_type": "outfit",
    "extra_text": "日常通勤穿搭"
  }'
```

## 📊 系统功能

### 🎭 五个评委

1. **ChatGPT-5 评委** - 中立、理性、专业
2. **Grok 评委** - 幽默、犀利、直率
3. **Gemini 2.5 评委** - 细致、分析型、学院派
4. **豆包评委** - 亲切、生活化、接地气
5. **千问评委** - 文艺、感性、有情怀

### 📈 评分流程

**阶段一：独立评分（20-40秒）**
- 5 个评委并发看图
- 每个评委输出结构化评分
- 自动排序生成排行榜

**阶段二：群聊讨论（30-60秒）**
- 基于评分结果开启群聊
- 评委互动讨论、互相吐槽
- 产出综艺感对话内容

### 🎯 支持的比赛类型

- `outfit` - 穿搭大赛
  - 维度：风格统一度、创意与个性、实用性、场景适配度

- `funny` - 搞笑图片大赛
  - 维度：创意程度、笑点密度、传播潜力、执行质量

## 📖 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目介绍和快速开始 |
| [QUICK_START.md](QUICK_START.md) | 5 分钟快速入门 |
| [docs/API.md](docs/API.md) | API 接口详细文档 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构说明 |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 生产环境部署指南 |

## 🔧 常用命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动服务
python app/main.py

# 查看日志（实时）
tail -f logs/ai_judge_$(date +%Y-%m-%d).log

# 查看错误日志
tail -f logs/ai_judge_error_$(date +%Y-%m-%d).log

# 重新初始化数据库
python -m app.db.init_db

# 运行测试示例
python examples/quick_start.py

# 停止服务
# 在运行服务的终端按 Ctrl+C
```

## ❓ 常见问题

### Q: API 调用失败，提示 401 Unauthorized？

**A:** 检查 `.env` 文件中的 `LLM_GATEWAY_API_KEY` 是否正确。

### Q: 某个评委评分失败？

**A:** 可能原因：
1. 该模型在你的 API Key 中不可用
2. 模型名称配置错误
3. 临时网络问题

系统会继续执行其他评委，不会中断整个流程。

### Q: 响应时间太长？

**A:** 正常情况：
- 阶段一（评分）：20-40 秒
- 阶段二（讨论）：30-60 秒
- 总计：50-100 秒

如需加速：
- 减少评委数量
- 使用更快的模型（如 gpt-4o-mini）
- 减少讨论轮数（修改 `MAX_DEBATE_MESSAGES`）

### Q: 如何修改评委人设？

**A:** 编辑 `app/judges/prompts.py` 中的 `JUDGE_PERSONAS`。

### Q: 如何添加新的比赛类型？

**A:** 在 `app/judges/prompts.py` 的 `COMMON_SCORING_GUIDE` 中添加新类型的维度定义。

## 🎉 开始使用！

1. **配置 API Key**：编辑 `.env` 文件
2. **启动服务**：`python app/main.py`
3. **访问文档**：http://localhost:8000/docs
4. **测试评分**：上传图片，看评委打分和讨论！

---

**祝你使用愉快！** 🚀

如有问题，请查看日志文件：`logs/ai_judge_*.log`

