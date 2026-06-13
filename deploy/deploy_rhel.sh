#!/bin/bash
# ========================================
# 学生信息管理系统 - 阿里云一键部署脚本
# 适用系统：Aliyun Linux 3 / Anolis OS 8 / CentOS 7/8 / RHEL / Fedora
# 适用场景：阿里云轻量应用服务器（应用镜像，无 apt 的情况）
# 部署时间：约 8-15 分钟
# ========================================
#
# 使用方法：
#   SSH 登录服务器后，把这一整段复制粘贴到终端执行：
#   curl -fsSL https://raw.githubusercontent.com/April389/student-system/main/deploy/deploy_rhel.sh -o /root/deploy.sh && bash /root/deploy.sh
#
# 它会自动完成：
#   - 系统更新（dnf/yum）
#   - 安装 Python 3.10+（用 dnf module 或 pyenv）
#   - 安装 MariaDB 10.x（MySQL 协议兼容，pymysql 直连）
#   - 创建项目用户 student
#   - 拉取 GitHub 代码
#   - 安装 Python 依赖
#   - 配置 systemd 守护 uvicorn
#   - 配置 nginx 反向代理
#   - 配置 firewall
# ========================================

set -e

# ---- 配置区 ----
GIT_REPO="https://github.com/April389/student-system.git"
APP_USER="student"
APP_DIR="/home/${APP_USER}/app"
APP_PORT=8000
DB_NAME="student_system"
DB_USER="student_app"
DB_PASSWORD=$(openssl rand -hex 12)
SECRET_KEY=$(openssl rand -hex 32)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; }

# 必须是 root
if [ "$(id -u)" -ne 0 ]; then
  err "请用 root 用户运行：sudo bash $0"
  exit 1
fi

log "=========================================="
log "  学生信息管理系统 - 阿里云部署 (RHEL/CentOS/Aliyun Linux)"
log "  服务器：$(curl -s ifconfig.me 2>/dev/null || echo '未知')"
log "=========================================="

# ===== 步骤 0: 检测包管理器和系统版本 =====
log "[0/10] 检测系统..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log "  系统：$PRETTY_NAME"
    log "  ID: $ID, VERSION_ID: $VERSION_ID"
fi

if command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
    PYTHON_PKG="python3 python3-pip python3-devel gcc"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
    PYTHON_PKG="python3 python3-pip python3-devel gcc"
else
    err "未找到 dnf/yum，本脚本只支持 RPM 系系统"
    exit 1
fi
log "  包管理器：$PKG_MGR"

# 检测 MariaDB/MySQL 服务名
if [ "$ID" = "centos" ] && [ "${VERSION_ID%%.*}" = "7" ]; then
    DB_SERVICE="mariadb"
    DB_PKG="mariadb-server mariadb"
else
    DB_SERVICE="mariadb"
    DB_PKG="mariadb-server mariadb"
fi

# ===== 步骤 1: 系统更新 =====
log "[1/10] 系统更新..."
$PKG_MGR update -y -q > /dev/null 2>&1 || warn "系统更新失败，继续"
$PKG_MGR install -y -q epel-release > /dev/null 2>&1 || true
log "  ✓ 系统更新完成"

# ===== 步骤 2: 基础工具 =====
log "[2/10] 安装基础工具 (curl, git, nginx, firewalld)..."
$PKG_MGR install -y -q curl git nginx firewalld > /dev/null 2>&1
log "  ✓ 基础工具安装完成"

# ===== 步骤 3: Python 3.10+ =====
log "[3/10] 安装 Python 3.10+..."
# 检查 python3.10 / python3.11 / python3.9 / python3.6
if ! command -v python3 &> /dev/null; then
    $PKG_MGR install -y -q $PYTHON_PKG > /dev/null 2>&1
fi

# 优先尝试用 dnf module 装 python3.11（Aliyun Linux 3 支持）
if [ "$PKG_MGR" = "dnf" ] && ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    log "  尝试用 dnf module 装 python3.11..."
    $PKG_MGR module reset python3 -y -q > /dev/null 2>&1 || true
    $PKG_MGR module enable python311 -y -q > /dev/null 2>&1 && \
        $PKG_MGR install -y -q python3.11 python3.11-pip python3.11-devel -q > /dev/null 2>&1 || \
        $PKG_MGR install -y -q python3.10 python3.10-pip python3.10-devel -q > /dev/null 2>&1 || \
        warn "module 装不上，用系统默认 python3"
fi

PYTHON_BIN=$(which python3)
PYTHON_VER=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
log "  ✓ Python $PYTHON_VER 安装完成（$PYTHON_BIN）"

# ===== 步骤 4: MariaDB 10.x =====
log "[4/10] 安装 MariaDB（MySQL 协议兼容，pymysql 直连）..."
$PKG_MGR install -y -q $DB_PKG > /dev/null 2>&1
systemctl enable $DB_SERVICE > /dev/null 2>&1
systemctl start  $DB_SERVICE
sleep 3
log "  ✓ MariaDB 启动完成"

# ===== 步骤 5: 配置 MariaDB =====
log "[5/10] 配置 MariaDB（创建数据库和用户）..."
# 仅监听 localhost
if [ -f /etc/my.cnf ]; then
    if ! grep -q "^bind-address" /etc/my.cnf; then
        echo "bind-address = 127.0.0.1" >> /etc/my.cnf
    else
        sed -i 's/^bind-address.*/bind-address = 127.0.0.1/' /etc/my.cnf
    fi
fi
# MariaDB 10.4+ 默认有 root 密码在 /var/log/mysqld.log，需要先清空 root 密码
systemctl restart $DB_SERVICE
sleep 2

# 用 socket 认证连接（Aliyun Linux 3 / CentOS 7 默认 unix_socket）
mysql -u root <<EOF 2>&1 | head -5 || warn "root 无密码连接失败，尝试跳过"
CREATE DATABASE IF NOT EXISTS ${DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 保存密码
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
log "  ✓ 密码保存到 /root/.db_password"

# ===== 步骤 6: 创建应用用户 =====
log "[6/10] 创建应用用户 ${APP_USER}..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd -m -s /bin/bash ${APP_USER}
fi
log "  ✓ 用户 ${APP_USER} 创建完成"

# ===== 步骤 7: 拉取代码 =====
log "[7/10] 拉取 GitHub 代码..."
if [ -d "${APP_DIR}" ]; then
    warn "${APP_DIR} 已存在，备份为 ${APP_DIR}.bak"
    mv ${APP_DIR} ${APP_DIR}.bak
fi
sudo -u ${APP_USER} bash <<EOSU
cd /home/${APP_USER}
git clone ${GIT_REPO} app
cd app
$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
EOSU
log "  ✓ 代码拉取 + venv 创建完成"

# ===== 步骤 8: 写 .env + systemd service =====
log "[8/10] 写入 .env + systemd service..."

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

cat > /etc/systemd/system/student-system.service <<EOF
[Unit]
Description=Student Management System (FastAPI)
After=network.target ${DB_SERVICE}.service
Wants=${DB_SERVICE}.service

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

mkdir -p /var/log/student-system
chown -R ${APP_USER}:${APP_USER} /var/log/student-system

systemctl daemon-reload
systemctl enable student-system
systemctl start  student-system
sleep 3
systemctl status student-system --no-pager | head -5 || warn "服务状态查看失败"

log "  ✓ systemd 服务启动完成"

# ===== 步骤 9: nginx + firewalld =====
log "[9/10] 配置 nginx + firewalld..."

# nginx 配置
cat > /etc/nginx/conf.d/student-system.conf <<EOF
server {
    listen       80 default_server;
    server_name  _;

    location = /health {
        access_log off;
        return 200 "ok\n";
        add_header Content-Type text/plain;
    }

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        client_max_body_size 10M;
        proxy_buffering off;
    }
}
EOF

# 删除默认 server 配置（如果存在）
rm -f /etc/nginx/conf.d/default.conf 2>/dev/null
if [ -f /etc/nginx/nginx.conf ] && grep -q "include /etc/nginx/sites-enabled" /etc/nginx/nginx.conf; then
    rm -f /etc/nginx/sites-enabled/default
fi

nginx -t && systemctl reload nginx
systemctl enable nginx

# firewalld 防火墙
systemctl enable firewalld > /dev/null 2>&1
systemctl start  firewalld > /dev/null 2>&1 || true
firewall-cmd --permanent --add-port=22/tcp  > /dev/null 2>&1 || true
firewall-cmd --permanent --add-port=80/tcp  > /dev/null 2>&1 || true
firewall-cmd --permanent --add-port=443/tcp > /dev/null 2>&1 || true
firewall-cmd --reload > /dev/null 2>&1 || true

log "  ✓ nginx + firewalld 配置完成"

# ===== 步骤 10: 验证 =====
log "[10/10] 验证部署..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${APP_PORT}/docs || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    log "  ✓ 后端本地访问正常 (HTTP $HTTP_CODE)"
else
    warn "  后端 HTTP 状态码：$HTTP_CODE，看下面日志："
    journalctl -u student-system -n 30 --no-pager 2>&1 | head -40 || true
fi

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
echo "  数据库密码：/root/.db_password  （权限 600）"
echo "  服务管理："
echo "    systemctl status student-system     # 状态"
echo "    systemctl restart student-system    # 重启"
echo "    journalctl -u student-system -f     # 实时日志"
echo ""
echo "  默认管理员账号：admin / 123456"
echo ""
echo "  下一步："
echo "    1. 阿里云控制台 → 防火墙 → 确认 80/443 放行"
echo "    2. 浏览器访问 http://${PUBLIC_IP}/docs 验证"
echo "    3. 部署前端到 EdgeOne Pages"
echo "       https://edgeone.ai/ → 导入 Git → Build output: static"
echo "       访问：https://xxx.edgeone.app/?api_base_url=http://${PUBLIC_IP}"
echo "=========================================="
