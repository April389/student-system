# ========================================
# 主入口文件 main.py
# 作用：FastAPI 应用的启动入口和全局配置
# ========================================
#
# FastAPI 框架说明：
#   FastAPI 是一个现代的 Python Web 框架
#   它可以自动生成可视化交互式文档（Swagger UI）
#   以 REST API 的规范为标准来建造接口
#
# 自动文档地址（启动后访问）：
#   Swagger UI:  http://127.0.0.1:8000/docs
#   ReDoc:       http://127.0.0.1:8000/redoc
#
# 大致数据流向：
#   前端 HTML  →  通过 RESTful 风格设计接口
#   →  使用 HTTP 协议打包数据  →  依靠 TCP/IP 协议在网络中传输
#   →  到达 Python 后端（FastAPI）
#
# 网络协议说明：
#   TCP/IP 传输协议：
#     为前后端传输确定"目标地点"
#     IP 保证找到目标服务器，TCP 将数据打包运输
#     负责重发保证数据完整不丢失
#     不需要特意编写，电脑能上网就能直接用
#
#   HTTP 传输协议：
#     相当于将数据打包并贴上标签
#     告诉服务器数据包的作用，是读还是存
#     可获得数据传输结果（例如是否成功）
# ========================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import pymysql
import os
from config import APP_HOST, APP_PORT, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
from database import engine, Base, SessionLocal
from models import SysUser, SysRole, SysPermission, SysUserRole, SysRolePermission
from auth import hash_password
from routers import auth, students, users, statistics

# 项目根目录（静态文件和前端页面的基准路径）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ========================================
# 第一部分：创建 FastAPI 应用实例
# ========================================
# FastAPI() 创建一个 Web 应用对象
# title   —— 应用名称（显示在自动文档中）
# description —— 应用描述
# version —— 版本号
app = FastAPI(
    title="学生信息管理系统 API",
    description="""
    ## 系统简介
    学生信息管理系统后端 API 接口文档

    ## 技术栈
    - **FastAPI** —— Web 框架
    - **PyJWT** —— JWT Token 认证
    - **passlib[bcrypt]** —— 密码加密
    - **SQLAlchemy** —— ORM 数据库操作
    - **PyMySQL** —— MySQL 驱动器
    - **Pandas** —— 数据统计分析

    ## 接口分组
    - 认证管理：登录、注册、获取用户信息
    - 学生管理：增删查改学生信息
    - 用户管理：用户列表、角色分配、密码重置
    - 数据统计：成绩总览、班级统计、排名查询
    """,
    version="1.0.0",
)


# ========================================
# 第二部分：配置 CORS 跨域支持
# ========================================
# CORS（跨源资源共享）说明：
#   前端页面运行在 http://127.0.0.1:5500（或其他端口）
#   后端 API 运行在 http://127.0.0.1:8000
#   浏览器默认禁止不同端口之间的请求（同源策略）
#   CORSMiddleware 允许前端跨域访问后端接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 允许所有来源（生产环境建议限制具体域名）
    allow_credentials=True,       # 允许携带 Cookie
    allow_methods=["*"],          # 允许所有 HTTP 方法（GET、POST、PUT、DELETE）
    allow_headers=["*"],          # 允许所有请求头（包括 Authorization: Bearer Token）
)


# ========================================
# 第三部分：挂载静态文件目录
# ========================================
# 将 static 目录挂载为静态文件服务
# 前端 HTML、CSS、JS 文件放在 static 目录下
# 访问 http://127.0.0.1:8000/static/index.html 即可看到前端页面
try:
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
except Exception:
    pass  # 如果 static 目录不存在，跳过


# ========================================
# 第四部分：注册路由（接口模块）
# ========================================
# 将各个功能模块的路由注册到 FastAPI 应用中
# 注册后，FastAPI 会根据 URL 和方法自动匹配到对应的处理函数
#
# REST API 接口总览：
#   认证管理 /api/auth/*
#     POST /api/auth/login      —— 用户登录
#     POST /api/auth/register   —— 用户注册
#     GET  /api/auth/me         —— 获取当前用户
#
#   学生管理 /api/students/*
#     GET    /api/students          —— 查询学生列表
#     GET    /api/students/{id}     —— 查询学生详情
#     POST   /api/students          —— 添加学生
#     PUT    /api/students/{id}     —— 修改学生
#     DELETE /api/students/{id}     —— 删除学生
#
#   用户管理 /api/users/*
#     GET  /api/users               —— 查询用户列表
#     GET  /api/users/{id}          —— 查询用户详情
#     PUT  /api/users/{id}/status   —— 启用/禁用用户
#     PUT  /api/users/{id}/password —— 重置密码
#     GET  /api/users/roles/list    —— 获取角色列表
#     PUT  /api/users/{id}/roles    —— 分配角色
#
#   数据统计 /api/statistics/*
#     GET /api/statistics/overview         —— 成绩总览
#     GET /api/statistics/class/{name}     —— 班级统计
#     GET /api/statistics/ranking          —— 成绩排名

app.include_router(auth.router)         # 注册认证路由
app.include_router(students.router)     # 注册学生管理路由
app.include_router(users.router)        # 注册用户管理路由
app.include_router(statistics.router)   # 注册数据统计路由


# ========================================
# 第五部分：首页路由（前端页面入口）
# ========================================
@app.get("/", tags=["首页"])
def root():
    """
    首页接口

    直接返回前端页面（index.html）
    访问 http://127.0.0.1:8000/ 即可看到系统界面
    """
    try:
        return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
    except Exception:
        return {
            "system": "学生信息管理系统",
            "version": "1.0.0",
            "docs": "/docs",
            "message": "欢迎访问学生信息管理系统 API（前端页面未找到，请访问 /docs 查看接口文档）",
        }


@app.get("/docs-page", tags=["首页"])
def docs_page():
    """API 文档页面入口"""
    return {"swagger_ui": "/docs", "redoc": "/redoc"}


# ========================================
# 第六部分：应用启动事件（自动建库 + 建表 + 初始化数据）
# ========================================
def _auto_create_database():
    """
    自动创建数据库（如果不存在）
    使用 PyMySQL 直连 MySQL 服务器，检查数据库是否存在
    不存在则自动创建，解决分享项目后需要手动建库的问题
    """
    try:
        # 先不指定数据库名，连接 MySQL 服务器
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        # 检查数据库是否存在
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall()]

        if DB_NAME not in databases:
            # 数据库不存在，自动创建
            cursor.execute(
                f"CREATE DATABASE `{DB_NAME}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.commit()
            print(f"  数据库 '{DB_NAME}' 已自动创建")
        else:
            print(f"  数据库 '{DB_NAME}' 已存在")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  [警告] 自动创建数据库失败: {e}")
        print(f"  请手动执行: CREATE DATABASE {DB_NAME} DEFAULT CHARACTER SET utf8mb4;")


def _auto_init_seed_data():
    """
    自动初始化种子数据（角色、权限、管理员账号）
    仅在数据库为空时执行，已有数据则跳过
    """
    db = SessionLocal()
    try:
        # 检查是否已有用户数据（有数据说明已初始化过）
        if db.query(SysUser).count() > 0:
            print("  数据库已有数据，跳过初始化")
            return

        # --- 插入角色 ---
        roles = [
            SysRole(role_name="超级管理员", role_code="admin", description="系统最高权限管理员"),
            SysRole(role_name="老师", role_code="teacher", description="教师角色，可管理学生信息和查看成绩"),
            SysRole(role_name="学生", role_code="student", description="学生角色，可查看自己的信息和成绩"),
        ]
        for role in roles:
            db.add(role)
        db.flush()

        # --- 插入权限 ---
        permissions = [
            SysPermission(permission_name="查看学生列表", permission_code="student:list", permission_type="menu", description="查看学生信息列表页面"),
            SysPermission(permission_name="查看学生详情", permission_code="student:detail", permission_type="menu", description="查看学生详细信息"),
            SysPermission(permission_name="添加学生", permission_code="student:create", permission_type="button", description="添加新学生按钮"),
            SysPermission(permission_name="修改学生", permission_code="student:update", permission_type="button", description="修改学生信息按钮"),
            SysPermission(permission_name="删除学生", permission_code="student:delete", permission_type="button", description="删除学生按钮"),
            SysPermission(permission_name="查看用户列表", permission_code="user:list", permission_type="menu", description="查看用户管理页面"),
            SysPermission(permission_name="管理用户", permission_code="user:manage", permission_type="button", description="用户管理操作"),
            SysPermission(permission_name="查看数据统计", permission_code="statistics:view", permission_type="menu", description="查看成绩统计页面"),
        ]
        for perm in permissions:
            db.add(perm)
        db.flush()

        # --- 为角色分配权限 ---
        admin_role = db.query(SysRole).filter(SysRole.role_code == "admin").first()
        for perm in permissions:
            db.add(SysRolePermission(role_id=admin_role.id, permission_id=perm.id))

        teacher_role = db.query(SysRole).filter(SysRole.role_code == "teacher").first()
        for code in ["student:list", "student:detail", "student:create", "student:update", "statistics:view"]:
            p = db.query(SysPermission).filter(SysPermission.permission_code == code).first()
            if p:
                db.add(SysRolePermission(role_id=teacher_role.id, permission_id=p.id))

        student_role = db.query(SysRole).filter(SysRole.role_code == "student").first()
        for code in ["student:list", "student:detail", "statistics:view"]:
            p = db.query(SysPermission).filter(SysPermission.permission_code == code).first()
            if p:
                db.add(SysRolePermission(role_id=student_role.id, permission_id=p.id))

        # --- 创建管理员账号 ---
        admin_user = SysUser(
            username="admin",
            password=hash_password("123456"),
            real_name="系统管理员",
            email="admin@school.edu",
            status=1,
        )
        db.add(admin_user)
        db.flush()
        db.add(SysUserRole(user_id=admin_user.id, role_id=admin_role.id))

        db.commit()
        print("  初始数据插入完成（3个角色、8个权限、管理员账号 admin/123456）")

    except Exception as e:
        db.rollback()
        print(f"  [警告] 初始化数据失败: {e}")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    """
    应用启动时自动执行全部初始化：
      1. 自动创建数据库（如果不存在）—— 解决分享后需手动建库的问题
      2. 自动创建数据表（ORM 根据 models.py 建表）
      3. 自动插入种子数据（角色、权限、管理员账号）

    这样别人拿到项目后，只需修改 config.py 中的数据库密码，
    然后运行 python main.py 即可全自动启动！
    """
    print("=" * 55)
    print("  学生信息管理系统启动中...")
    print(f"  API 文档: http://{APP_HOST}:{APP_PORT}/docs")
    print(f"  前端页面: http://{APP_HOST}:{APP_PORT}/")
    print("=" * 55)

    # 第一步：自动创建数据库
    print("[1/3] 检查数据库...")
    _auto_create_database()

    # 第二步：自动创建数据表
    print("[2/3] 检查数据表...")
    Base.metadata.create_all(bind=engine)
    print("  数据表检查/创建完成")

    # 第三步：自动插入种子数据
    print("[3/3] 检查初始数据...")
    _auto_init_seed_data()

    print("=" * 55)
    print("  启动完成！")
    print("  默认管理员账号: admin / 123456")
    print("=" * 55)


# ========================================
# 第七部分：启动服务器
# ========================================
# uvicorn 是 ASGI 服务器，用于运行 FastAPI 应用
# 直接运行此文件时启动服务器
#
# 启动命令（二选一）：
#   python main.py
#   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
#
# --reload 参数表示代码修改后自动重启（开发模式）
if __name__ == "__main__":
    uvicorn.run(
        "main:app",           # 模块名:应用变量名
        host=APP_HOST,        # 监听地址
        port=APP_PORT,        # 监听端口
        reload=True,          # 开发模式：代码修改后自动重启
    )
