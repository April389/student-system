# ========================================
# 学生信息管理系统后端 Dockerfile
# 用于 fly.io 部署
# ========================================
# 基础镜像：Python 3.11 官方 slim 版本（体积小、兼容性好）
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
#   PYTHONDONTWRITEBYTECODE  禁止生成 .pyc 文件（节省空间）
#   PYTHONUNBUFFERED        禁止 stdout/stderr 缓冲（日志实时输出）
#   PIP_NO_CACHE_DIR        禁用 pip 缓存（减小镜像体积）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 先只复制 requirements.txt 装依赖（利用 Docker 缓存，代码改动不用重装依赖）
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 再复制全部项目文件
COPY . .

# fly.io 默认监听 8080 端口（fly.toml 里 $PORT 环境变量会覆盖）
EXPOSE 8080

# 启动命令
#   --host 0.0.0.0   监听所有网络接口
#   --port $PORT     fly.io 自动注入 PORT 环境变量
#   --workers 1      单 worker（免费层 256MB 内存，多 worker 会被 OOM）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
