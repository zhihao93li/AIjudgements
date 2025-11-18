# Python 3.11 安装指南

## 为什么需要 Python 3.11+

根据 [AutoGen 官方文档](https://microsoft.github.io/autogen/stable/)，最新版本的 **autogen-agentchat** 需要 **Python 3.10 或更高版本**。

我们推荐使用 Python 3.11，因为它：
- ✅ 完全兼容 AutoGen 最新版本
- ✅ 性能更好（比 3.10 快 10-60%）
- ✅ 更好的错误提示
- ✅ 长期支持版本

## macOS 安装步骤

### 方法 1：官方安装器（推荐，最简单）

1. **下载 Python 3.11 安装包**
   
   访问：https://www.python.org/downloads/macos/
   
   或直接下载：https://www.python.org/ftp/python/3.11.10/python-3.11.10-macos11.pkg

2. **运行安装器**
   
   双击下载的 `.pkg` 文件，按照向导完成安装

3. **验证安装**
   
   ```bash
   python3.11 --version
   # 应该显示: Python 3.11.10
   ```

4. **设置为默认 python3（可选）**
   
   ```bash
   # 添加到 ~/.zshrc
   echo 'alias python3=/usr/local/bin/python3.11' >> ~/.zshrc
   echo 'alias pip3=/usr/local/bin/pip3.11' >> ~/.zshrc
   source ~/.zshrc
   ```

### 方法 2：使用 Homebrew（如果已安装）

```bash
# 安装 Homebrew（如果还没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python 3.11
brew install python@3.11

# 验证
python3.11 --version
```

### 方法 3：使用 pyenv（推荐给开发者）

```bash
# 安装 pyenv
curl https://pyenv.run | bash

# 添加到 ~/.zshrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# 安装 Python 3.11
pyenv install 3.11.10
pyenv global 3.11.10

# 验证
python --version
```

## 安装完成后

### 1. 创建虚拟环境

```bash
cd /Users/zhihaoli/Documents/项目/show5

# 使用 Python 3.11 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证虚拟环境中的 Python 版本
python --version
# 应该显示: Python 3.11.x
```

### 2. 安装项目依赖

```bash
# 确保在虚拟环境中
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 3. 初始化数据库

```bash
python -m app.db.init_db
```

### 4. 启动服务

```bash
python app/main.py
```

## 验证 AutoGen 安装

```bash
python -c "import autogen_agentchat; print(f'AutoGen AgentChat version: {autogen_agentchat.__version__}')"
python -c "import autogen_ext; print('AutoGen Ext installed successfully')"
```

## 常见问题

### Q: 安装后找不到 python3.11 命令？

**A:** 检查安装路径：

```bash
ls -la /usr/local/bin/python3.11
# 或
ls -la /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11
```

如果存在，添加到 PATH：

```bash
export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"
```

### Q: pip install 失败，提示权限错误？

**A:** 使用虚拟环境（推荐）或添加 `--user` 标志：

```bash
# 推荐：使用虚拟环境
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 或者：用户级安装
python3.11 -m pip install --user -r requirements.txt
```

### Q: 多个 Python 版本如何管理？

**A:** 使用 `pyenv` 或明确指定版本：

```bash
# 使用完整路径
/usr/local/bin/python3.11 -m venv venv

# 或使用 pyenv
pyenv local 3.11.10
```

## 下一步

安装完成后，按照 [QUICK_START.md](QUICK_START.md) 继续配置和运行项目。


