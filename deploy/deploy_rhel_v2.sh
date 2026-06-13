#!/bin/bash
# ========================================
# 学生信息管理系统 - 阿里云一键部署脚本 V2
# 适用：Aliyun Linux 3 / Anolis OS 8 / CentOS 7/8
# 跳过 dnf update（新机无需全量更新，省 30+ 分钟）
# ========================================

set -e

GIT_REPO="https://github.com/April389/student-system.git"
APP_USER="student"
APP_DIR="/home/${APP_USER}/app"
APP_PORT=8000
DB_NAME="student_system"
DB_USER="student_app"
DB_PASSWORD=$(openssl rand -hex 12)
SECRET_KEY=$(openssl rand -hex 32)

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN:${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; }

# 必须是 root
if [ "$(id -u)" -ne 0 ]; then
  err "请用 root 运行"
  exit 1
fi

log "=========================================="
log "  学生管理系统 - 阿里云部署 V2 (跳过 update)"
log "=========================================="

# ===== 步骤 0: 检测 =====
log "[0/9] 检测系统..."
. /etc/os-release 2>/dev/null || true
log "  系统：$PRETTY_NAME"

if command -v dnf &>/dev/null; then
    PKG_MGR="dnf"
else
    PKG_MGR="yum"
fi
log "  包管理器：$PKG_MGR"

# ===== 步骤 0.5: 清理 dnf 锁（重要）=====
log "[0/9] 清理可能残留的 dnf 锁..."
rm -f /var/run/dnf.pid /var/run/yum.pid 2>/dev/null
killall -9 dnf yum 2>/dev/null || true
dnf clean all -q 2>/dev/null || true
log "  ✓ 锁已清理"

# ===== 步骤 1: 基础工具 =====
log "[1/9] 安装基础工具 (curl, git, nginx, firewalld)..."
# 加超时 5 分钟，避免卡死
timeout 300 $PKG_MGR install -y -q --skip-broken curl git nginx firewalld openssl 2>&1 | tail -5
log "  ✓ 基础工具完成"

# ===== 步骤 2: Python 3 =====
log "[2/9] 安装 Python 3..."
# Aliyun Linux 3 默认有 python3 (3.6) 但 FastAPI 要 3.9+
# 优先用 dnf module 装 3.11
if [ "$PKG_MGR" = "dnf" ]; then
    timeout 300 $PKG_MGR install -y -q python3 python3-pip python3-devel gcc 2>&1 | tail -3
    PYTHON_BIN=$(which python3 2>/dev/null || echo /usr/bin/python3)
    PYTHON_VER=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
    log "  系统 Python: $PYTHON_VER"

    # 如果 < 3.9，尝试装 3.11
    if $PYTHON_BIN -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
        log "  ✓ Python 版本满足要求"
    else
        warn "Python 版本太老，尝试用 dnf module 装 python3.11..."
        timeout 300 $PKG_MGR module enable python311 -y -q 2>&1 | tail -3 || true
        timeout 300 $PKG_MGR install -y -q python3.11 python3.11-pip python3.11-devel 2>&1 | tail -3 || \
        timeout 300 $PKG_MGR install -y -q python3.10 python3.10-pip python3.10-devel 2>&1 | tail -3 || \
        warn "装 3.10/3.11 失败，将用系统 Python 3.6（可能不兼容 FastAPI）"
        # 重新检测
        PYTHON_BIN=$(which python3.11 2>/dev/null || which python3.10 2>/dev/null || which python3)
        PYTHON_VER=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
        log "  最终 Python: $PYTHON_VER"
    fi
else
    # CentOS 7
    timeout 300 yum install -y -q python3 python3-pip python3-devel gcc 2>&1 | tail -3
    PYTHON_BIN=$(which python3)
fi
log "  ✓ Python: $($PYTHON_BIN --version 2>&1)"

# ===== 步骤 3: MariaDB =====
log "[3/9] 安装 MariaDB..."
DB_SERVICE="mariadb"
timeout 300 $PKG_MGR install -y -q mariadb-server mariadb 2>&1 | tail -3
systemctl enable $DB_SERVICE
systemctl start  $DB_SERVICE
sleep 3
log "  ✓ MariaDB 启动完成"

# ===== 步骤 4: 配置 MariaDB =====
log "[4/9] 配置 MariaDB..."

# 监听 localhost
if [ -f /etc/my.cnf ]; then
    if ! grep -q "^bind-address" /etc/my.cnf; then
        echo "bind-address = 127.0.0.1" >> /etc/my.cnf
    else
        sed -i 's/^bind-address.*/bind-address = 127.0.0.1/' /etc/my.cnf
    fi
fi
systemctl restart $DB_SERVICE
sleep 2

# Aliyun Linux 3 默认 MariaDB 用 unix_socket 认证，root 无密码
mysql -u root 2>/dev/null <<EOF
CREATE DATABASE IF NOT EXISTS ${DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF
log "  ✓ 数据库和用户创建完成"

# 保存密码
cat > /root/.db_password <<EOF
DB_HOST: 127.0.0.1
DB_PORT: 3306
DB_USER: ${DB_USER}
DB_PASSWORD: ${DB_PASSWORD}
DB_NAME: ${DB_NAME}
EOF
chmod 600 /root/.db_password
log "  密码已保存到 /root/.db_password"

# ===== 步骤 5: 创建应用用户 =====
log "[5/9] 创建应用用户 ${APP_USER}..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd -m -s /bin/bash ${APP_USER}
fi
log "  ✓ 用户已存在或已创建"

# ===== 步骤 6: 拉取代码 + 装依赖 =====
log "[6/9] 拉取代码 + 装依赖..."
if [ -d "${APP_DIR}" ]; then
    rm -rf ${APP_DIR}.bak
    mv ${APP_DIR} ${APP_DIR}.bak
fi

# 关键：pip 要 --break-system-packages 或用 venv
sudo -u ${APP_USER} bash <<EOSU
set -e
cd /home/${APP_USER}
git clone ${GIT_REPO} app
cd app
$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
EOSU
log "  ✓ 代码 + 依赖完成"

# ===== 步骤 7: 写 .env + systemd =====
log "[7/9] 写 .env + systemd service..."

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
log "  ✓ systemd 启动完成"

# ===== 步骤 8: nginx + firewalld =====
log "[8/9] 配置 nginx + firewalld..."

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
# 删除可能冲突的默认配置
rm -f /etc/nginx/conf.d/default.conf

nginx -t && systemctl reload nginx
systemctl enable nginx
log "  ✓ nginx 配置完成"

# firewalld（不强制要求，nginx 已经能 80 端口）
systemctl enable firewalld 2>/dev/null || true
systemctl start  firewalld 2>/dev/null || true
firewall-cmd --permanent --add-port=22/tcp  2>/dev/null || true
firewall-cmd --permanent --add-port=80/tcp  2>/dev/null || true
firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true
log "  ✓ firewalld 配置完成"

# ===== 步骤 9: 验证 =====
log "[9/9] 验证..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${APP_PORT}/docs 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    log "  ✓ 后端本地 HTTP $HTTP_CODE 正常"
else
    warn "  后端 HTTP $HTTP_CODE，日志："
    journalctl -u student-system -n 30 --no-pager 2>&1 | head -50
fi

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "120.27.17.52")

echo ""
echo "=========================================="
echo "  🎉 部署完成！"
echo "=========================================="
echo ""
echo "  访问：http://${PUBLIC_IP}/docs"
echo "  数据库密码：/root/.db_password"
echo "  服务管理："
echo "    systemctl status student-system"
echo "    journalctl -u student-system -f"
echo "=========================================="
