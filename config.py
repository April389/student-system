# ========================================
# 后端配置文件 config.py
# 作用：集中管理整个系统的全局配置参数
# ========================================
#
# 环境变量支持说明：
#   本地运行时使用默认值
#   云端部署时通过环境变量覆盖（Render 等平台可设置环境变量）
#   优先级：环境变量 > 默认值
# ========================================

import os  # 用于读取环境变量


# ========================================
# 第一部分：MySQL 数据库配置
# ========================================
# 说明：
#   - PyMySQL 作为数据库驱动器，负责连接 Python 与 MySQL
#   - SQLAlchemy 作为 ORM 库，后续用 Python 对象操作数据库
#   - 连接字符串格式：mysql+pymysql://用户名:密码@主机:端口/数据库名

# 数据库连接信息（支持环境变量覆盖，方便云端部署）
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")          # 数据库服务器地址
DB_PORT = int(os.getenv("DB_PORT", "3306"))           # MySQL 默认端口
DB_USER = os.getenv("DB_USER", "root")                # MySQL 用户名
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")      # MySQL 密码（分享时修改）
DB_NAME = os.getenv("DB_NAME", "student_system")      # 数据库名称

# SQLAlchemy 连接字符串
# 格式说明：
#   mysql+pymysql  ——  表示使用 PyMySQL 驱动连接 MySQL
#   root:123456    ——  用户名:密码
#   @127.0.0.1:3306 ——  服务器地址:端口
#   /student_system ——  数据库名
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


# ========================================
# 第二部分：JWT Token 配置（登录认证）
# ========================================
# 说明：
#   - PyJWT 用于生成和验证 JWT Token
#   - 用户登录成功后，后端生成一个 Token 发给前端
#   - 前端每次请求都带上这个 Token，后端验证后才允许操作

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-2024")  # JWT 签名密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")            # JWT 加密算法（HS256 是对称加密）
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # Token 过期时间（分钟）


# ========================================
# 第三部分：服务器配置
# ========================================
# APP_PORT 优先使用 Render 的 PORT 环境变量（Render 自动分配端口）
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")   # 后端服务监听地址
APP_PORT = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))  # 端口（优先用 Render 的 PORT）
