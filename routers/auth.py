# ========================================
# 认证路由文件 routers/auth.py
# 作用：处理用户登录、注册相关的 API 接口
# ========================================
#
# REST API 接口规范说明：
#   URL 地址         | HTTP 方法  | 作用
#   ----------------|-----------|------------------
#   /api/auth/login  | POST      | 用户登录，获取 Token
#   /api/auth/register | POST    | 用户注册（管理员操作）
#   /api/auth/me     | GET       | 获取当前登录用户信息
#
# HTTP 方法说明：
#   GET    —— 读取数据（查询）
#   POST   —— 创建数据（新增）
#   PUT    —— 更新数据（修改）
#   DELETE —— 删除数据
#
# 数据流向：
#   前端 HTML  →  Axios 发送 HTTP 请求  →  FastAPI 接收并校验
#   →  执行业务逻辑  →  返回 JSON 数据  →  前端展示
# ========================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import SysUser, SysUserRole, SysRole
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse, ApiResponse
from auth import hash_password, verify_password, create_access_token
from dependencies import get_current_user, get_user_roles, get_user_permissions


# 创建认证路由器
# prefix="/api/auth"  —— 所有接口的 URL 前缀
# tags=["认证管理"]   —— 在 FastAPI 自动文档中的分组名称
router = APIRouter(prefix="/api/auth", tags=["认证管理"])


# ========================================
# 接口一：用户登录
# ========================================
# URL:    POST /api/auth/login
# 方法:   POST（创建 Token）
# 功能:   验证用户名密码，成功后返回 JWT Token
# 权限:   无需登录（公开接口）
#
# 请求体（Body）示例：
#   {
#     "username": "admin",
#     "password": "123456"
#   }
#
# 返回示例：
#   {
#     "access_token": "eyJhbGciOi...",
#     "token_type": "bearer",
#     "user": { ... }
#   }
@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录接口

    流程：
      1. 前端发送用户名和密码
      2. 查询数据库中是否存在该用户
      3. 使用 passlib 验证密码（明文 vs 密文）
      4. 验证通过后，使用 PyJWT 生成 Token
      5. 将 Token 和用户信息一起返回给前端
    """
    # 第一步：根据用户名查询用户
    user = db.query(SysUser).filter(SysUser.username == user_data.username).first()

    # 第二步：检查用户是否存在
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 第三步：检查账户是否被禁用
    if user.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用，请联系管理员",
        )

    # 第四步：验证密码
    # verify_password 会将明文密码与数据库中的密文进行比对
    if not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 第五步：生成 JWT Token
    # 将用户名编码到 Token 中，作为用户身份标识
    access_token = create_access_token(data={"sub": user.username})

    # 第六步：获取用户角色信息
    roles = get_user_roles(user.id, db)

    # 第七步：返回 Token 和用户信息
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            email=user.email,
            phone=user.phone,
            status=user.status,
            created_at=user.created_at,
            roles=roles,
        )
    )


# ========================================
# 接口二：用户注册
# ========================================
# URL:    POST /api/auth/register
# 方法:   POST（创建新用户）
# 功能:   创建新用户并加密密码
# 权限:   需要登录（管理员操作）
@router.post("/register", response_model=ApiResponse, summary="用户注册")
def register(
    user_data: UserCreate,
    current_user: SysUser = Depends(get_current_user),  # 需要登录才能注册
    db: Session = Depends(get_db)
):
    """
    用户注册接口（由管理员创建新账户）

    流程：
      1. 检查用户名是否已被占用
      2. 使用 passlib + bcrypt 加密密码
      3. 将用户信息存入 sys_user 表
      4. 返回创建结果
    """
    # 检查用户名是否已存在
    existing_user = db.query(SysUser).filter(SysUser.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 创建新用户（密码使用 bcrypt 加密存储）
    new_user = SysUser(
        username=user_data.username,
        password=hash_password(user_data.password),  # 明文密码 → 加密密文
        real_name=user_data.real_name,
        email=user_data.email,
        phone=user_data.phone,
    )

    # 写入数据库
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return ApiResponse(
        code=200,
        message="用户注册成功",
        data={"id": new_user.id, "username": new_user.username}
    )


# ========================================
# 接口三：获取当前登录用户信息
# ========================================
# URL:    GET /api/auth/me
# 方法:   GET（读取用户信息）
# 功能:   获取当前 Token 对应的用户详细信息
# 权限:   需要登录（Token 验证）
@router.get("/me", response_model=ApiResponse, summary="获取当前用户信息")
def get_me(
    current_user: SysUser = Depends(get_current_user),  # Token 拦截验证
    db: Session = Depends(get_db)
):
    """
    获取当前登录用户信息

    前端通过请求头携带 Token：
      Authorization: Bearer eyJhbGciOi...

    get_current_user 会自动验证 Token 并返回用户对象
    """
    roles = get_user_roles(current_user.id, db)
    permissions = get_user_permissions(current_user.id, db)

    return ApiResponse(
        code=200,
        message="获取成功",
        data={
            "id": current_user.id,
            "username": current_user.username,
            "real_name": current_user.real_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "status": current_user.status,
            "roles": roles,
            "permissions": permissions,
        }
    )
