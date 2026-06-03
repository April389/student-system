# ========================================
# 数据库连接文件 database.py
# 作用：建立 Python 与 MySQL 的连接通道
# ========================================
#
# 技术栈说明：
#   1. PyMySQL —— 数据库驱动器，类似于 MySQL 与 Python 的"翻译官"
#      负责底层的数据传输，让 Python 能够与 MySQL 通信
#
#   2. SQLAlchemy —— ORM（对象关系映射）库
#      以 Python 类定义表结构，用 Python 对象代替行数据
#      让 Python 语法代替 MySQL 语句完成增删查改
#
#   3. ORM 映射原理：
#      Python 类      →  MySQL 数据表
#      类的属性        →  表的字段（列）
#      类的实例（对象）→  表中的一行数据
#      类的关联关系    →  表之间的外键关系
#
# 数据流转过程：
#   Python 对象  →  SQLAlchemy ORM 转换  →  MySQL SQL 语句  →  数据库执行
# ========================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL


# ========================================
# 第一步：创建数据库引擎（Engine）
# ========================================
# engine 是 SQLAlchemy 与数据库通信的核心对象
# 它内部使用 PyMySQL 驱动器来连接 MySQL
# echo=True 会在控制台打印每次执行的 SQL 语句（方便调试）
engine = create_engine(
    DATABASE_URL,
    echo=True,               # 开启 SQL 语句日志输出
    pool_pre_ping=True,      # 连接池健康检查，防止使用已断开的连接
    pool_recycle=3600,       # 连接回收时间（秒），防止 MySQL 超时断开
)


# ========================================
# 第二步：创建数据库会话工厂（SessionLocal）
# ========================================
# SessionLocal 是一个工厂函数，每次调用都会创建一个新的数据库会话
# 数据库会话相当于一次"对话"，用于执行 SQL 操作
# autocommit=False  —— 不自动提交，需要手动 commit
# autoflush=False   —— 不自动刷新，避免意外的数据库写入
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ========================================
# 第三步：创建 ORM 基类（Base）
# ========================================
# 所有数据模型（表）都需要继承这个 Base 类
# Base 会自动收集所有子类的表定义信息
Base = declarative_base()


# ========================================
# 第四步：定义获取数据库会话的依赖函数
# ========================================
# 这是一个生成器函数，FastAPI 的 Depends() 会自动调用它
# 每次请求时：
#   1. 创建一个新的数据库会话（db）
#   2. 将 db 传给接口函数使用
#   3. 请求结束后，自动关闭会话（释放资源）
def get_db():
    """
    获取数据库会话的依赖函数
    用于 FastAPI 的 Depends() 注入
    """
    db = SessionLocal()       # 创建新的数据库会话
    try:
        yield db              # 将会话交给接口使用
    finally:
        db.close()            # 请求结束后关闭会话，释放数据库连接
