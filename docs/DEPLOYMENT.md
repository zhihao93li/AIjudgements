# 部署指南

## 环境要求

- Python 3.10+
- 8GB+ RAM（推荐）
- 稳定的网络连接（访问 LLM API）

## 部署步骤

### 1. 克隆项目（或下载）

```bash
cd /your/project/path
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```env
# LLM Gateway Configuration
LLM_GATEWAY_BASE_URL=https://api.openai.com/v1
LLM_GATEWAY_API_KEY=your-api-key-here

# Model Names (根据你的网关调整)
MODEL_CHATGPT5=gpt-4o
MODEL_GROK=grok-beta
MODEL_GEMINI=gemini-2.0-flash-exp
MODEL_DOUBAO=doubao-pro-32k
MODEL_QWEN=qwen-max
MODEL_SELECTOR=gpt-4o-mini

# Database
DATABASE_URL=sqlite+aiosqlite:///./ai_judge.db

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Debate Configuration
MAX_DEBATE_MESSAGES=12
```

### 5. 初始化数据库

```bash
python -m app.db.init_db
```

### 6. 启动服务

#### 开发模式

```bash
python app/main.py
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 生产模式

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. 验证部署

访问：

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

## 生产环境建议

### 使用 Gunicorn + Uvicorn

```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### 使用 Systemd（Linux）

创建 `/etc/systemd/system/ai-judge.service`：

```ini
[Unit]
Description=AI Judge System
After=network.target

[Service]
Type=notify
User=your-user
WorkingDirectory=/path/to/show5
Environment="PATH=/path/to/show5/venv/bin"
ExecStart=/path/to/show5/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-judge
sudo systemctl start ai-judge
sudo systemctl status ai-judge
```

### 使用 Docker

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建和运行：

```bash
docker build -t ai-judge-system .
docker run -d -p 8000:8000 --env-file .env ai-judge-system
```

### 使用 Docker Compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./ai_judge.db:/app/ai_judge.db
    restart: unless-stopped
```

运行：

```bash
docker-compose up -d
```

## 反向代理配置

### Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超时时间（评分可能需要较长时间）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### Caddy

```caddy
yourdomain.com {
    reverse_proxy localhost:8000 {
        timeout 300s
    }
}
```

## 监控和维护

### 日志位置

- 应用日志：`logs/ai_judge_YYYY-MM-DD.log`
- 错误日志：`logs/ai_judge_error_YYYY-MM-DD.log`

### 查看日志

```bash
# 实时查看日志
tail -f logs/ai_judge_$(date +%Y-%m-%d).log

# 查看错误日志
tail -f logs/ai_judge_error_$(date +%Y-%m-%d).log
```

### 数据库备份

```bash
# 备份 SQLite 数据库
cp ai_judge.db ai_judge_backup_$(date +%Y%m%d_%H%M%S).db
```

### 性能优化建议

1. **增加 Worker 数量**：根据 CPU 核心数调整
2. **使用缓存**：对频繁查询的作品结果进行缓存
3. **异步任务队列**：使用 Celery 处理耗时的评分任务
4. **数据库优化**：生产环境建议使用 PostgreSQL 替代 SQLite

## 故障排查

### 常见问题

1. **模型 API 调用失败**
   - 检查 API Key 是否正确
   - 检查网络连接
   - 查看模型名称配置是否正确

2. **图片下载失败**
   - 确保图片 URL 公网可访问
   - 检查服务器网络出站规则

3. **数据库锁定（SQLite）**
   - 生产环境建议使用 PostgreSQL
   - 或增加 SQLite 超时时间

4. **内存不足**
   - 减少 Worker 数量
   - 限制并发请求数

## 安全建议

1. **API Key 保护**：不要将 `.env` 文件提交到版本控制
2. **CORS 配置**：生产环境限制允许的域名
3. **速率限制**：使用 slowapi 等库限制请求频率
4. **HTTPS**：使用 SSL/TLS 加密传输
5. **日志脱敏**：避免在日志中记录敏感信息

## 扩展阅读

- [FastAPI 部署文档](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn 部署指南](https://www.uvicorn.org/deployment/)
- [AutoGen 文档](https://microsoft.github.io/autogen/)

