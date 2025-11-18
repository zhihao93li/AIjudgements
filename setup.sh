#!/bin/bash

# AI Judge System - 自动化设置脚本
# 用于 Python 3.11 + AutoGen 最新版本

set -e  # 遇到错误立即退出

echo "======================================================"
echo "  AI Judge System - 自动化设置"
echo "======================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检测 Python 3.11
echo "📌 步骤 1/5: 检查 Python 版本..."
if command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ 找到 Python 3.11: $PYTHON_VERSION${NC}"
    PYTHON_CMD="python3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_VERSION=$(python3.12 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ 找到 Python 3.12: $PYTHON_VERSION${NC}"
    PYTHON_CMD="python3.12"
elif command -v python3.10 &> /dev/null; then
    PYTHON_VERSION=$(python3.10 --version 2>&1 | awk '{print $2}')
    echo -e "${YELLOW}⚠ 找到 Python 3.10: $PYTHON_VERSION (建议使用 3.11+)${NC}"
    PYTHON_CMD="python3.10"
else
    echo -e "${RED}✗ 未找到 Python 3.10+ 版本！${NC}"
    echo ""
    echo "请先安装 Python 3.11："
    echo "1. 访问: https://www.python.org/downloads/macos/"
    echo "2. 下载并安装 Python 3.11"
    echo "3. 重新运行此脚本"
    echo ""
    echo "或使用 Homebrew: brew install python@3.11"
    exit 1
fi

# 创建虚拟环境
echo ""
echo "📌 步骤 2/5: 创建虚拟环境..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠ 虚拟环境已存在，跳过创建${NC}"
else
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo ""
echo "📌 步骤 3/5: 激活虚拟环境..."
source venv/bin/activate
echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
echo "   Python: $(python --version)"
echo "   位置: $(which python)"

# 升级 pip
echo ""
echo "📌 步骤 4/5: 升级 pip..."
python -m pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip 已升级到最新版本${NC}"

# 安装依赖
echo ""
echo "📌 步骤 5/5: 安装项目依赖..."
echo "   这可能需要几分钟时间..."
pip install -r requirements.txt

echo ""
echo -e "${GREEN}✓ 依赖安装完成！${NC}"

# 验证 AutoGen 安装
echo ""
echo "📌 验证 AutoGen 安装..."
python -c "import autogen_agentchat; print(f'  ✓ autogen-agentchat: {autogen_agentchat.__version__}')" 2>/dev/null || echo -e "${YELLOW}  ⚠ autogen-agentchat 导入失败${NC}"
python -c "import autogen_ext; print('  ✓ autogen-ext: 已安装')" 2>/dev/null || echo -e "${YELLOW}  ⚠ autogen-ext 导入失败${NC}"
python -c "import autogen_core; print(f'  ✓ autogen-core: {autogen_core.__version__}')" 2>/dev/null || echo -e "${YELLOW}  ⚠ autogen-core 导入失败${NC}"

# 检查配置文件
echo ""
echo "📌 检查配置文件..."
if [ -f ".env" ]; then
    if grep -q "your-api-key-here" .env; then
        echo -e "${YELLOW}⚠ 请编辑 .env 文件，填入你的 API Key${NC}"
    else
        echo -e "${GREEN}✓ .env 文件已配置${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env 文件不存在，请复制 .env.example 并配置${NC}"
fi

# 初始化数据库
echo ""
echo "📌 初始化数据库..."
python -m app.db.init_db || echo -e "${YELLOW}⚠ 数据库初始化可能失败，请检查日志${NC}"

echo ""
echo "======================================================"
echo -e "${GREEN}✅ 安装完成！${NC}"
echo "======================================================"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，填入你的 LLM API Key"
echo "2. 启动服务: python app/main.py"
echo "3. 访问 API 文档: http://localhost:8000/docs"
echo ""
echo "快速测试："
echo "  python examples/quick_start.py"
echo ""
echo "查看完整文档："
echo "  - 快速开始: QUICK_START.md"
echo "  - API 文档: docs/API.md"
echo "  - 部署指南: docs/DEPLOYMENT.md"
echo ""


