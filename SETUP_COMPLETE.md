# 🎉 AI Judge System - 安装指南

## 📋 当前状态

✅ 项目代码已完成（基于 AutoGen 最新版本）  
⏳ 需要安装 Python 3.11 和依赖包

## 🚀 完整安装流程

### 第一步：安装 Python 3.11

你的系统当前是 **Python 3.9.6**，但 AutoGen 最新版本需要 **Python 3.10+**（推荐 3.11）。

#### 选项 A：官方安装器（最简单，推荐）

1. **下载 Python 3.11**
   
   访问：https://www.python.org/ftp/python/3.11.10/python-3.11.10-macos11.pkg
   
   或：https://www.python.org/downloads/macos/

2. **安装**
   
   双击下载的 `.pkg` 文件，按照向导安装

3. **验证**
   
   ```bash
   python3.11 --version
   # 应该显示: Python 3.11.10
   ```

#### 选项 B：使用 Homebrew

```bash
# 如果没有 Homebrew，先安装（需要管理员权限）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python 3.11
brew install python@3.11

# 验证
python3.11 --version
```

### 第二步：运行自动化安装脚本

安装完 Python 3.11 后，在项目目录运行：

```bash
cd /Users/zhihaoli/Documents/项目/show5
./setup.sh
```

这个脚本会自动完成：
- ✅ 检测 Python 3.11
- ✅ 创建虚拟环境
- ✅ 安装最新版 AutoGen（autogen-agentchat, autogen-ext, autogen-core）
- ✅ 安装所有依赖
- ✅ 初始化数据库
- ✅ 验证安装

### 第三步：配置 API Key

编辑 `.env` 文件：

```bash
nano .env
```

修改以下配置：

```env
# 必须修改
LLM_GATEWAY_API_KEY=sk-your-actual-api-key-here

# 如果使用 OpenAI 官方 API，保持默认即可
LLM_GATEWAY_BASE_URL=https://api.openai.com/v1

# 如果使用其他网关（如 one-api），修改为你的网关地址
# LLM_GATEWAY_BASE_URL=https://your-gateway.com/v1
```

### 第四步：启动服务

```bash
# 激活虚拟环境（如果还没激活）
source venv/bin/activate

# 启动服务
python app/main.py
```

看到以下输出说明启动成功：

```
============================================================
AI Judge System 正在启动...
============================================================
数据库初始化完成
系统启动完成！
API 文档地址: http://0.0.0.0:8000/docs
```

### 第五步：测试系统

#### 方式 1：使用 Swagger UI（推荐）

打开浏览器访问：http://localhost:8000/docs

#### 方式 2：使用 Python 示例

```bash
python examples/quick_start.py
```

#### 方式 3：使用 cURL

```bash
curl -X POST "http://localhost:8000/api/judge_entry" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_id": "test_001",
    "image_url": "https://picsum.photos/800/600",
    "competition_type": "outfit",
    "extra_text": "测试穿搭图片"
  }'
```

## 📚 技术栈

- **AutoGen**: 最新版本 (autogen-agentchat >= 0.4.0)
  - 参考文档：https://microsoft.github.io/autogen/stable/
  - 需要 Python 3.10+
  - 支持多模态 AI Agent
  - 内置 GroupChat 和 SelectorGroupChat

- **FastAPI**: 现代 Python Web 框架
- **SQLAlchemy**: 异步 ORM
- **Loguru**: 优雅的日志管理

## ❓ 常见问题

### Q1: 为什么必须使用 Python 3.11？

**A:** 根据 [AutoGen 官方文档](https://microsoft.github.io/autogen/stable/)，最新版本的 `autogen-agentchat` 需要 Python 3.10 或更高版本。我们推荐 3.11 因为：
- 性能更好（比 3.10 快 10-60%）
- 更好的错误提示
- 长期支持

### Q2: 能否使用旧版本的 AutoGen？

**A:** 可以，但不推荐。旧版本（pyautogen 0.2.x）的 API 完全不同，需要重写大量代码。使用最新版本可以获得：
- 更好的多模态支持
- 更强大的 GroupChat 功能
- 更好的异步支持
- 更活跃的社区支持

### Q3: setup.sh 脚本失败怎么办？

**A:** 手动执行以下步骤：

```bash
# 1. 创建虚拟环境
python3.11 -m venv venv

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 升级 pip
pip install --upgrade pip

# 4. 安装依赖
pip install -r requirements.txt

# 5. 初始化数据库
python -m app.db.init_db
```

### Q4: 找不到 python3.11 命令？

**A:** 检查安装路径：

```bash
# 查找 Python 3.11
which python3.11
ls -la /usr/local/bin/python3.11
ls -la /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11

# 添加到 PATH（临时）
export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"

# 永久添加（添加到 ~/.zshrc）
echo 'export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Q5: API 调用失败？

**A:** 检查：
1. `.env` 文件中的 API Key 是否正确
2. 模型名称是否正确（如 `gpt-4o`）
3. API 额度是否充足
4. 网络连接是否正常
5. 查看日志：`tail -f logs/ai_judge_*.log`

## 🔗 相关文档

- [INSTALL_PYTHON.md](INSTALL_PYTHON.md) - Python 3.11 详细安装指南
- [QUICK_START.md](QUICK_START.md) - 5 分钟快速入门
- [README.md](README.md) - 项目介绍
- [docs/API.md](docs/API.md) - API 接口文档
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - 系统架构
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - 生产环境部署

## 🎯 下一步

1. ✅ **现在**：安装 Python 3.11
2. ✅ **然后**：运行 `./setup.sh`
3. ✅ **配置**：编辑 `.env` 文件
4. ✅ **启动**：`python app/main.py`
5. ✅ **测试**：访问 http://localhost:8000/docs

---

**准备好了吗？** 🚀

1. 先下载并安装 Python 3.11：https://www.python.org/downloads/macos/
2. 然后运行：`./setup.sh`


