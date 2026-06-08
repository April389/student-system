# ========================================
# 数据模型文件 models.py
# 作用：定义数据库表结构（ORM 映射）
# ========================================
#
# 数据库设计说明：
#   共 5 张表，3 张基础表 + 2 张关联表
#
#   基础表：
#     1. sys_user       —— 用户表，存储学生、老师、管理员的账号信息
#     2. sys_role       —— 角色表，存储"超级管理员"、"老师"、"学生"等角色
#     3. sys_permission —— 权限表，存储具体的菜单或按钮权限
#
#   关联表：
#     4. sys_user_role         —— 用户-角色关联表，记录哪个用户属于哪个角色
#     5. sys_role_permission   —— 角色-权限关联表，记录哪个角色拥有哪些权限
#
#   关联表的作用：
#     关联表虽然繁琐，但主要用于权限管理部分
#     判断账户归属与所握权限
#     实现"一个用户可以有多个角色，一个角色可以有多个权限"的多对多关系
#
# ORM 映射关系：
#   Python 类  →  MySQL 数据表
#   类的属性   →  表的字段（列）
#   类的实例   →  表中的一行数据
# ========================================

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ========================================
# 第一张表：sys_user（用户表）
# ========================================
# 存储所有用户（学生、老师、管理员）的账号信息
# 每个用户有唯一的用户名，密码使用 bcrypt 加密存储
class SysUser(Base):
    __tablename__ = "sys_user"  # 对应 MySQL 中的表名

    # --- 字段定义 ---
    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID，自增主键")
    username = Column(String(50), unique=True, nullable=False, comment="用户名，唯一，不能为空")
    password = Column(String(255), nullable=False, comment="密码（bcrypt加密后的密文）")
    real_name = Column(String(50), nullable=True, comment="真实姓名")
    email = Column(String(100), nullable=True, comment="邮箱地址")
    phone = Column(String(20), nullable=True, comment="手机号码")
    status = Column(Integer, default=1, comment="账户状态：1=正常，0=禁用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # --- 关联关系 ---
    # 一个用户可以拥有多个角色（通过 sys_user_role 关联表）
    roles = relationship("SysUserRole", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SysUser(id={self.id}, username='{self.username}', real_name='{self.real_name}')>"


# ========================================
# 第二张表：sys_role（角色表）
# ========================================
# 存储系统中定义的角色
# 例如：超级管理员、老师、学生
class SysRole(Base):
    __tablename__ = "sys_role"

    # --- 字段定义 ---
    id = Column(Integer, primary_key=True, autoincrement=True, comment="角色ID，自增主键")
    role_name = Column(String(50), unique=True, nullable=False, comment="角色名称，如：超级管理员、老师、学生")
    role_code = Column(String(50), unique=True, nullable=False, comment="角色编码，如：admin、teacher、student")
    description = Column(String(200), nullable=True, comment="角色描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # --- 关联关系 ---
    # 一个角色可以分配给多个用户（通过 sys_user_role 关联表）
    users = relationship("SysUserRole", back_populates="role")
    # 一个角色可以拥有多个权限（通过 sys_role_permission 关联表）
    permissions = relationship("SysRolePermission", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SysRole(id={self.id}, role_name='{self.role_name}')>"


# ========================================
# 第三张表：sys_permission（权限表）
# ========================================
# 存储具体的菜单权限或按钮权限
# 例如：查看学生列表、添加学生、删除学生、查看成绩统计
class SysPermission(Base):
    __tablename__ = "sys_permission"

    # --- 字段定义 ---
    id = Column(Integer, primary_key=True, autoincrement=True, comment="权限ID，自增主键")
    permission_name = Column(String(50), nullable=False, comment="权限名称，如：查看学生列表")
    permission_code = Column(String(100), unique=True, nullable=False, comment="权限编码，如：student:list")
    permission_type = Column(String(20), nullable=False, comment="权限类型：menu=菜单权限，button=按钮权限")
    description = Column(String(200), nullable=True, comment="权限描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # --- 关联关系 ---
    # 一个权限可以被分配给多个角色（通过 sys_role_permission 关联表）
    roles = relationship("SysRolePermission", back_populates="permission")

    def __repr__(self):
        return f"<SysPermission(id={self.id}, permission_name='{self.permission_name}')>"


# ========================================
# 第四张表：sys_user_role（用户-角色关联表）
# ========================================
# 记录哪个用户属于哪个角色（多对多关系的中间表）
# 例如：用户"张三"同时拥有"学生"和"班干部"两个角色
class SysUserRole(Base):
    __tablename__ = "sys_user_role"

    # --- 字段定义 ---
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID，自增主键")
    user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False, comment="用户ID，关联 sys_user 表")
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=False, comment="角色ID，关联 sys_role 表")
    created_at = Column(DateTime, default=datetime.now, comment="分配时间")

    # --- 关联关系 ---
    # 反向关联到用户表
    user = relationship("SysUser", back_populates="roles")
    # 反向关联到角色表
    role = relationship("SysRole", back_populates="users")

    def __repr__(self):
        return f"<SysUserRole(user_id={self.user_id}, role_id={self.role_id})>"


# ========================================
# 第五张表：sys_role_permission（角色-权限关联表）
# ========================================
# 记录哪个角色拥有哪些权限（多对多关系的中间表）
# 例如："管理员"角色拥有"查看学生列表"、"添加学生"、"删除学生"等权限
class SysRolePermission(Base):
    __tablename__ = "sys_role_permission"

    # --- 字段定义 ---
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID，自增主键")
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=False, comment="角色ID，关联 sys_role 表")
    permission_id = Column(Integer, ForeignKey("sys_permission.id"), nullable=False, comment="权限ID，关联 sys_permission 表")
    created_at = Column(DateTime, default=datetime.now, comment="分配时间")

    # --- 关联关系 ---
    # 反向关联到角色表
    role = relationship("SysRole", back_populates="permissions")
    # 反向关联到权限表
    permission = relationship("SysPermission", back_populates="roles")

    def __repr__(self):
        return f"<SysRolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


# ========================================
# 扩展表：student_info（学生详细信息表）
# ========================================
# 存储学生的详细学籍信息
# 与 sys_user 通过 user_id 关联
class StudentInfo(Base):
    __tablename__ = "student_info"

    # --- 字段定义 ---
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID，自增主键")
    user_id = Column(Integer, ForeignKey("sys_user.id"), unique=True, nullable=False, comment="关联用户ID")
    student_no = Column(String(30), unique=True, nullable=False, comment="学号，唯一")
    gender = Column(String(10), nullable=True, comment="性别：男/女")
    age = Column(Integer, nullable=True, comment="年龄")
    class_name = Column(String(50), nullable=True, comment="班级名称，如：计算机2301班")
    major = Column(String(100), nullable=True, comment="专业名称")
    grade = Column(String(20), nullable=True, comment="年级，如：2023级")
    enrollment_date = Column(String(20), nullable=True, comment="入学日期")
    chinese_score = Column(Integer, nullable=True, comment="语文成绩")
    math_score = Column(Integer, nullable=True, comment="数学成绩")
    english_score = Column(Integer, nullable=True, comment="英语成绩")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # --- 关联关系 ---
    user = relationship("SysUser")

    def __repr__(self):
        return f"<StudentInfo(student_no='{self.student_no}', class_name='{self.class_name}')>"
