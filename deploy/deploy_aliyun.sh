#!/bin/bash
# ========================================
# 学生信息管理系统 - 阿里云一键部署脚本
# 适用系统：Ubuntu 22.04 LTS
# 适用场景：轻量应用服务器 2C2G
# 部署时间：约 8-15 分钟
# ========================================
#
# 使用方法：
#   1. SSH 登录服务器：ssh root@120.27.17.52
#   2. 上传此脚本：scp deploy_aliyun.sh root@120.27.17.52:/root/
#      或者：直接在服务器上用 curl 下载
#   3. 执行：bash deploy_aliyun.sh
#
# 它会自动完成：
#   - 系统更新
#   - 安装 Python 3.10 + pip + 虚拟环境
#   - 安装 MySQL 8（端口只监听 localhost）
#   - 创建项目用户 student
#   - 拉取 GitHub 代码
#   - 安装 Python 依赖
#   - 启动 MySQL + 创建数据库
#   - 配置 systemd 守护 uvicorn
#   - 配置 nginx 反向代理（HTTP 80）
#   - 配置防火墙（ufw）
# ========================================

set -e  # 任何一步失败立即退出

# ---- 配置区（部署前可改） ----
GIT_REPO="https://github.com/April389/student-system.git"
APP_USER="student"
APP_DIR="/home/${APP_USER}/app"
APP_PORT=8000
DB_NAME="student_system"
DB_USER="student_app"
# MySQL 密码：自动生成 24 位强密码并保存到 /root/.db_password
DB_PASSWORD=$(openssl rand -hex 12)
SECRET_KEY=$(openssl rand -hex 32)
PYTHON_VERSION="3.10"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: ${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: ${NC} $1"; }

# 必须是 root 运行
if [ "$(id -u)" -ne 0 ]; then
  err "请用 root 用户运行：sudo bash deploy_aliyun.sh"
  exit 1
fi

log "=========================================="
log "  学生信息管理系统 - 阿里云部署"
log "  服务器：$(curl -s ifconfig.me 2>/dev/null || echo '未知')"
log "=========================================="

# ===== 步骤 1: 系统更新 =====
log "[1/9] 更新系统..."
export DEBIAN_FRONTEND=noninteractive
apt update -y > /dev/null
apt upgrade -y > /dev/null
log "  ✓ 系统更新完成"

# ===== 步骤 2: 安装基础工具 =====
log "[2/9] 安装基础工具 (curl, git, nginx, mysql)..."
apt install -y software-properties-common curl git nginx ufw > /dev/null
log "  ✓ 基础工具安装完成"

# ===== 步骤 3: 安装 Python 3.10 =====
log "[3/9] 安装 Python ${PYTHON_VERSION}..."
if ! command -v python${PYTHON_VERSION} &> /dev/null; then
    add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1 || warn "PPA 添加失败，使用系统 Python"
    apt update -y > /dev/null
    apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev > /dev/null
fi
log "  ✓ Python $(python${PYTHON_VERSION} --version) 安装完成"

# ===== 步骤 4: 安装 MySQL 8 =====
log "[4/9] 安装 MySQL 8..."
if ! command -v mysql &> /dev/null; then
    # 阿里云轻量默认不带 MySQL server，手动装
    apt install -y mysql-server-8.0 mysql-client-8.0 > /dev/null 2>&1 || \
    apt install -y mysql-server mysql-client > /dev/null 2>&1
fi
# 启动 MySQL
systemctl enable mysql
systemctl start mysql
log "  ✓ MySQL $(mysql --version) 启动完成"

# ===== 步骤 5: MySQL 安全配置 =====
log "[5/9] 配置 MySQL（创建数据库和用户）..."
# 仅监听 localhost（关键安全设置）
sed -i 's/^bind-address.*/bind-address = 127.0.0.1/' /etc/mysql/mysql.conf.d/mysqld.cnf
sed -i 's/^mysqlx-bind-address.*/mysqlx-bind-address = 127.0.0.1/' /etc/mysql/mysql.conf.d/mysqld.cnf
systemctl restart mysql

# 创建数据库和应用用户
mysql <<EOF
CREATE DATABASE IF NOT EXISTS ${DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 保存密码到文件（部署完成后立即查看）
cat > /root/.db_password <<EOF
数据库连接信息（请妥善保存）
============================
DB_HOST: 127.0.0.1
DB_PORT: 3306
DB_USER: ${DB_USER}
DB_PASSWORD: ${DB_PASSWORD}
DB_NAME: ${DB_NAME}
EOF
chmod 600 /root/.db_password

log "  ✓ 数据库 '${DB_NAME}' 创建完成"
log "  ✓ 用户 '${DB_USER}' 创建完成，密码已保存到 /root/.db_password"

# ===== 步骤 6: 创建应用用户 =====
log "[6/9] 创建应用用户 ${APP_USER}..."
if ! id "${APP_USER}" &>/dev/null; then
    adduser --disabled-password --gecos "" ${APP_USER}
fi
log "  ✓ 用户 ${APP_USER} 创建完成"

# ===== 步骤 7: 拉取代码 + 安装依赖 =====
log "[7/9] 拉取 GitHub 代码并安装 Python 依赖..."
if [ -d "${APP_DIR}" ]; then
    warn "目录 ${APP_DIR} 已存在，备份为 ${APP_DIR}.bak"
    mv ${APP_DIR} ${APP_DIR}.bak
fi

sudo -u ${APP_USER} bash <<EOSU
cd /home/${APP_USER}
git clone ${GIT_REPO} app
cd ${APP_DIR}
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
EOSU

log "  ✓ 代码拉取 + 依赖安装完成"

# ===== 步骤 8: 写入配置 + 启动 =====
log "[8/9] 写入 .env 配置 + 启动 systemd 服务..."

# 生成 .env（不修改 config.py，避免污染代码）
cat > ${APP_DIR}/.env <<EOF
APP_HOST=0.0.0.0
APP_PORT=${APP_PORT}
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}
SECRET_KEY=${SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256
EOF
chown ${APP_USER}:${APP_USER} ${APP_DIR}/.env
chmod 600 ${APP_DIR}/.env

# 写入 systemd service 文件（注入环境变量，避免修改 config.py）
cat > /etc/systemd/system/student-system.service <<EOF
[Unit]
Description=Student Management System (FastAPI)
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin:/usr/bin"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn main:app --host 0.0.0.0 --port ${APP_PORT} --workers 1
Restart=always
RestartSec=5
StandardOutput=append:/var/log/student-system/access.log
StandardError=append:/var/log/student-system/error.log

[Install]
WantedBy=multi-user.target
EOF

# 创建日志目录
mkdir -p /var/log/student-system
chown -R ${APP_USER}:${APP_USER} /var/log/student-system

# 启动服务
systemctl daemon-reload
systemctl enable student-system
systemctl start student-system
sleep 3
systemctl status student-system --no-pager

log "  ✓ systemd 服务已启动"

# ===== 步骤 9: 配置 nginx =====
log "[9/9] 配置 nginx 反向代理..."
cat > /etc/nginx/sites-available/student-system <<EOF
server {
    listen 80 default_server;
    server_name _;

    # 安全：禁止访问敏感文件
    location ~ /\.(?!well-known) { deny all; }

    # 后端 API 反向代理
    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        client_max_body_size 10M;
    }
}
EOF
ln -sf /etc/nginx/sites-available/student-system /etc/nginx/sites-enabled/student-system
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 防火墙
ufw allow 22/tcp > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null
ufw --force enable > /dev/null

log "  ✓ nginx + 防火墙 配置完成"

# ===== 收尾 =====
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "120.27.17.52")

echo ""
echo "=========================================="
echo "  🎉 部署完成！"
echo "=========================================="
echo ""
echo "  访问地址："
echo "    API 文档:    http://${PUBLIC_IP}/docs"
echo "    主页:        http://${PUBLIC_IP}/"
echo ""
echo "  数据库密码：/root/.db_password  （已设权限 600）"
echo "  服务管理："
echo "    systemctl status student-system    # 查看状态"
echo "    systemctl restart student-system   # 重启"
echo "    journalctl -u student-system -f    # 看日志"
echo ""
echo "  默认管理员账号：admin / 123456"
echo ""
echo "  下一步：部署前端"
echo "    1. 打开 https://edgeone.ai/ 注册"
echo "    2. Pages → 导入 Git → 选 student-system"
echo "    3. Build output: static"
echo "    4. 访问时加 ?api_base_url=http://${PUBLIC_IP}"
echo "=========================================="
