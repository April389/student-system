# ========================================
# 权限依赖文件 dependencies.py
# 作用：权限拦截器，检查前端请求是否携带合法 Token
# ========================================
#
# 技术栈说明：
#   使用 FastAPI 自带的 Depends 和 HTTPBearer
#
#   1. Depends（依赖注入）
#      FastAPI 的核心机制，用于在接口执行前自动运行某些逻辑
#      例如：在执行"查询成绩"之前，先检查用户是否登录
#
#   2. HTTPBearer（HTTP Bearer Token 认证方案）
#      一种标准的 Token 传递方式
#      前端在 HTTP 请求头（Header）中这样传递 Token：
#      Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
#
#   3. 权限拦截器工作流程：
#      前端发起请求  →  拦截器检查请求头中的 Token
#                   →  Token 合法  →  放行，继续执行业务逻辑
#                   →  Token 无效  →  拦截，返回 401（未授权）
#                   →  无权限     →  拦截，返回 403（禁止访问）
# ========================================

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from auth import decode_access_token
from database import get_db
from models import SysUser, SysUserRole, SysRole, SysRolePermission, SysPermission


# ========================================
# 第一部分：HTTPBearer Token 提取器
# ========================================
# HTTPBearer 会自动从请求头中提取 Bearer Token
# 请求头格式：Authorization: Bearer <token>
# auto_error=True  —— 如果没有 Token，自动返回 401 错误
security = HTTPBearer(auto_error=True)


# ========================================
# 第二部分：获取当前登录用户（Token 验证）
# ========================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> SysUser:
    """
    权限拦截器：验证 Token 并获取当前登录用户

    工作流程：
      1. HTTPBearer 自动从请求头中提取 Token
      2. 调用 decode_access_token 验证 Token 的合法性
      3. 从 Token 中解析出用户名
      4. 查询数据库，获取用户对象
      5. 检查用户状态是否正常

    参数：
      credentials: HTTPBearer 自动提取的 Token 凭证
      db: 数据库会话（通过 Depends(get_db) 自动注入）

    返回：
      SysUser 对象（当前登录的用户）

    异常：
      401: Token 无效或已过期
      401: 用户不存在
      403: 用户已被禁用

    使用方式（在接口中添加这一行即可拦截）：
      @app.get("/api/students")
      def get_students(current_user: SysUser = Depends(get_current_user)):
          # 走到这里说明用户已登录，Token 合法
          pass
    """
    # 第一步：提取 Token 字符串
    token = credentials.credentials

    # 第二步：验证并解码 Token
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 第三步：从 Token 的 Payload 中提取用户名
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户信息",
        )

    # 第四步：查询数据库，获取用户对象
    user = db.query(SysUser).filter(SysUser.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 第五步：检查用户状态
    if user.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用，请联系管理员",
        )

    return user


# ========================================
# 第三部分：权限检查器（基于角色的权限控制 RBAC）
# ========================================
def require_permission(required_permission: str):
    """
    权限检查器工厂函数：检查当前用户是否拥有指定权限

    参数：
      required_permission: 需要的权限编码
                           例如："student:list"（查看学生列表）
                                 "student:delete"（删除学生）

    返回：
      一个依赖函数，可以在接口中使用 Depends() 调用

    权限判断流程：
      1. 获取当前用户的所有角色（通过 sys_user_role 关联表）
      2. 获取这些角色拥有的所有权限（通过 sys_role_permission 关联表）
      3. 检查所需权限是否在用户的权限列表中
      4. 有权限  →  放行
      5. 无权限  →  返回 403（禁止访问）

    使用方式：
      @app.delete("/api/students/{student_id}")
      def delete_student(
          current_user: SysUser = Depends(get_current_user),
          _: bool = Depends(require_permission("student:delete"))
      ):
          # 走到这里说明用户既登录了，又拥有"student:delete"权限
          pass
    """

    def permission_checker(
        current_user: SysUser = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        """
        实际的权限检查逻辑
        """
        # 第一步：查询用户的所有角色ID
        user_role_ids = [
            ur.role_id for ur in
            db.query(SysUserRole).filter(SysUserRole.user_id == current_user.id).all()
        ]

        if not user_role_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="该用户未分配任何角色",
            )

        # 第二步：查询这些角色拥有的所有权限编码
        permission_codes = (
            db.query(SysPermission.permission_code)
            .join(SysRolePermission, SysPermission.id == SysRolePermission.permission_id)
            .filter(SysRolePermission.role_id.in_(user_role_ids))
            .all()
        )

        # 提取权限编码列表
        user_permissions = [p[0] for p in permission_codes]

        # 第三步：检查用户是否拥有所需权限
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要权限：{required_permission}",
            )

        return True

    return permission_checker


# ========================================
# 第四部分：获取用户权限列表的工具函数
# ========================================
def get_user_permissions(user_id: int, db: Session) -> list:
    """
    获取指定用户的所有权限编码列表

    用于：登录时返回用户权限信息，前端根据权限控制页面显示

    查询路径：
      sys_user → sys_user_role → sys_role_permission → sys_permission
      用户    →  用户的角色    →  角色的权限           →  权限编码
    """
    # 查询用户的所有角色ID
    user_role_ids = [
        ur.role_id for ur in
        db.query(SysUserRole).filter(SysUserRole.user_id == user_id).all()
    ]

    if not user_role_ids:
        return []

    # 查询这些角色拥有的所有权限
    permissions = (
        db.query(SysPermission)
        .join(SysRolePermission, SysPermission.id == SysRolePermission.permission_id)
        .filter(SysRolePermission.role_id.in_(user_role_ids))
        .all()
    )

    return [{"code": p.permission_code, "name": p.permission_name, "type": p.permission_type}
            for p in permissions]


def get_user_roles(user_id: int, db: Session) -> list:
    """
    获取指定用户的所有角色名称列表
    """
    roles = (
        db.query(SysRole.role_name)
        .join(SysUserRole, SysRole.id == SysUserRole.role_id)
        .filter(SysUserRole.user_id == user_id)
        .all()
    )
    return [r[0] for r in roles]
