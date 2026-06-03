# ========================================
# 用户管理路由文件 routers/users.py
# 作用：处理用户管理相关的 API 接口（管理员功能）
# ========================================
#
# REST API 接口规范：
#   URL 地址                  | HTTP 方法  | 作用
#   -------------------------|-----------|------------------
#   /api/users                | GET       | 查询用户列表
#   /api/users/{id}           | GET       | 查询用户详情
#   /api/users/{id}/status    | PUT       | 启用/禁用用户
#   /api/users/{id}/password  | PUT       | 重置用户密码
#   /api/users/roles          | GET       | 获取所有角色列表
#   /api/users/{id}/roles     | PUT       | 分配用户角色
# ========================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from database import get_db
from models import SysUser, SysUserRole, SysRole
from schemas import ApiResponse
from auth import hash_password
from dependencies import get_current_user, require_permission


# 创建用户管理路由器
router = APIRouter(prefix="/api/users", tags=["用户管理"])


# ========================================
# Pydantic 数据校验模型（本文件专用）
# ========================================
class StatusUpdate(BaseModel):
    """用户状态更新"""
    status: int = Field(..., description="状态：1=正常，0=禁用")

class PasswordReset(BaseModel):
    """密码重置"""
    new_password: str = Field(..., min_length=6, description="新密码，至少6个字符")

class RoleAssign(BaseModel):
    """角色分配"""
    role_ids: List[int] = Field(..., description="角色ID列表")


# ========================================
# 接口一：查询用户列表
# ========================================
# URL:    GET /api/users
# 方法:   GET（读取数据）
# 功能:   获取所有用户列表（管理员专用）
# 权限:   需要登录
@router.get("", summary="查询用户列表")
def get_user_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    current_user: SysUser = Depends(get_current_user),
    _: bool = Depends(require_permission("user:list")),
    db: Session = Depends(get_db)
):
    """查询用户列表，支持按用户名、姓名搜索"""
    query = db.query(SysUser)

    if keyword:
        query = query.filter(
            (SysUser.username.like(f"%{keyword}%")) |
            (SysUser.real_name.like(f"%{keyword}%"))
        )

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    user_list = []
    for user in users:
        # 查询用户角色
        roles = (
            db.query(SysRole.role_name)
            .join(SysUserRole, SysRole.id == SysUserRole.role_id)
            .filter(SysUserRole.user_id == user.id)
            .all()
        )
        user_list.append({
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status,
            "roles": [r[0] for r in roles],
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": user_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ========================================
# 接口二：查询用户详情
# ========================================
# URL:    GET /api/users/{user_id}
# 方法:   GET（读取数据）
@router.get("/{user_id}", summary="查询用户详情")
def get_user_detail(
    user_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询单个用户的详细信息"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    roles = (
        db.query(SysRole)
        .join(SysUserRole, SysRole.id == SysUserRole.role_id)
        .filter(SysUserRole.user_id == user.id)
        .all()
    )

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status,
            "roles": [{"id": r.id, "name": r.role_name, "code": r.role_code} for r in roles],
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    }


# ========================================
# 接口三：启用/禁用用户
# ========================================
# URL:    PUT /api/users/{user_id}/status
# 方法:   PUT（更新数据）
# 功能:   修改用户状态（正常/禁用）
@router.put("/{user_id}/status", summary="启用/禁用用户")
def update_user_status(
    user_id: int,
    data: StatusUpdate,
    current_user: SysUser = Depends(get_current_user),
    _: bool = Depends(require_permission("user:manage")),
    db: Session = Depends(get_db)
):
    """修改用户的启用/禁用状态（需要 user:manage 权限）"""
    # 禁止禁用自己
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")

    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.status = data.status
    db.commit()

    status_text = "启用" if data.status == 1 else "禁用"
    return ApiResponse(code=200, message=f"用户已{status_text}")


# ========================================
# 接口四：重置用户密码
# ========================================
# URL:    PUT /api/users/{user_id}/password
# 方法:   PUT（更新数据）
# 功能:   管理员重置用户密码
@router.put("/{user_id}/password", summary="重置用户密码")
def reset_user_password(
    user_id: int,
    data: PasswordReset,
    current_user: SysUser = Depends(get_current_user),
    _: bool = Depends(require_permission("user:manage")),
    db: Session = Depends(get_db)
):
    """重置用户密码（新密码使用 bcrypt 加密存储）"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 加密新密码
    user.password = hash_password(data.new_password)
    db.commit()

    return ApiResponse(code=200, message="密码重置成功")


# ========================================
# 接口五：获取所有角色列表
# ========================================
# URL:    GET /api/users/roles
# 方法:   GET（读取数据）
@router.get("/roles/list", summary="获取所有角色")
def get_all_roles(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统中所有角色列表"""
    roles = db.query(SysRole).all()
    return {
        "code": 200,
        "message": "查询成功",
        "data": [{"id": r.id, "name": r.role_name, "code": r.role_code, "description": r.description} for r in roles],
    }


# ========================================
# 接口六：分配用户角色
# ========================================
# URL:    PUT /api/users/{user_id}/roles
# 方法:   PUT（更新数据）
# 功能:   为指定用户分配角色
@router.put("/{user_id}/roles", summary="分配用户角色")
def assign_user_roles(
    user_id: int,
    data: RoleAssign,
    current_user: SysUser = Depends(get_current_user),
    _: bool = Depends(require_permission("user:manage")),
    db: Session = Depends(get_db)
):
    """
    为用户分配角色

    操作步骤：
      1. 删除该用户的所有现有角色
      2. 根据传入的 role_ids 重新分配角色
    """
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 删除现有角色关联
    db.query(SysUserRole).filter(SysUserRole.user_id == user_id).delete()

    # 添加新的角色关联
    for role_id in data.role_ids:
        role = db.query(SysRole).filter(SysRole.id == role_id).first()
        if role:
            user_role = SysUserRole(user_id=user_id, role_id=role_id)
            db.add(user_role)

    db.commit()
    return ApiResponse(code=200, message="角色分配成功")
