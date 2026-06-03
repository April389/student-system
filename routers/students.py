# ========================================
# 学生管理路由文件 routers/students.py
# 作用：处理学生信息的增删查改（CRUD）API 接口
# ========================================
#
# REST API 接口规范说明：
#   URL 地址                  | HTTP 方法  | 作用
#   -------------------------|-----------|------------------
#   /api/students             | GET       | 查询学生列表（支持分页和搜索）
#   /api/students/{id}        | GET       | 查询单个学生详情
#   /api/students             | POST      | 添加新学生
#   /api/students/{id}        | PUT       | 修改学生信息
#   /api/students/{id}        | DELETE    | 删除学生
#
# CRUD 对应关系：
#   C (Create) —— POST   —— 创建/添加学生
#   R (Read)   —— GET    —— 读取/查询学生
#   U (Update) —— PUT    —— 更新/修改学生
#   D (Delete) —— DELETE —— 删除学生
#
# 权限拦截：
#   所有接口都需要携带合法的 JWT Token
#   部分操作（如删除）还需要特定权限
# ========================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from database import get_db
from models import SysUser, SysUserRole, SysRole, StudentInfo
from schemas import StudentCreate, StudentUpdate, StudentResponse, ApiResponse, PaginatedResponse
from auth import hash_password
from dependencies import get_current_user, require_permission


# 创建学生管理路由器
router = APIRouter(prefix="/api/students", tags=["学生管理"])


# ========================================
# 接口一：查询学生列表（分页 + 搜索）
# ========================================
# URL:    GET /api/students
# 方法:   GET（读取数据）
# 功能:   获取学生列表，支持分页和关键词搜索
# 权限:   需要登录 + student:list 权限
#
# 查询参数（Query Parameters）：
#   page      —— 当前页码，默认 1
#   page_size —— 每页条数，默认 10
#   keyword   —— 搜索关键词（可选），支持按姓名、学号、班级搜索
#
# 示例请求：
#   GET /api/students?page=1&page_size=10&keyword=张三
@router.get("", summary="查询学生列表")
def get_student_list(
    page: int = Query(1, ge=1, description="当前页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    keyword: Optional[str] = Query(None, description="搜索关键词（姓名/学号/班级）"),
    current_user: SysUser = Depends(get_current_user),  # Token 拦截验证
    db: Session = Depends(get_db)
):
    """
    查询学生列表

    支持功能：
      1. 分页查询（page + page_size）
      2. 关键词搜索（keyword，可搜索姓名、学号、班级）

    数据流转：
      前端发送 GET 请求  →  FastAPI 解析查询参数
      →  SQLAlchemy 构建查询  →  MySQL 执行 SQL
      →  返回 JSON 数据  →  前端渲染表格
    """
    # 构建基础查询：连接 student_info 和 sys_user 表
    query = (
        db.query(StudentInfo, SysUser)
        .join(SysUser, StudentInfo.user_id == SysUser.id)
    )

    # 如果有搜索关键词，添加模糊搜索条件
    if keyword:
        query = query.filter(
            or_(
                SysUser.real_name.like(f"%{keyword}%"),       # 按姓名搜索
                StudentInfo.student_no.like(f"%{keyword}%"),   # 按学号搜索
                StudentInfo.class_name.like(f"%{keyword}%"),   # 按班级搜索
                StudentInfo.major.like(f"%{keyword}%"),        # 按专业搜索
            )
        )

    # 计算总记录数
    total = query.count()

    # 分页处理：offset 跳过前面的记录，limit 限制返回条数
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    # 组装返回数据
    student_list = []
    for student, user in results:
        student_list.append({
            "id": student.id,
            "user_id": student.user_id,
            "student_no": student.student_no,
            "real_name": user.real_name,
            "username": user.username,
            "gender": student.gender,
            "age": student.age,
            "class_name": student.class_name,
            "major": student.major,
            "grade": student.grade,
            "enrollment_date": student.enrollment_date,
            "chinese_score": student.chinese_score,
            "math_score": student.math_score,
            "english_score": student.english_score,
            "created_at": student.created_at.isoformat() if student.created_at else None,
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": student_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ========================================
# 接口二：查询单个学生详情
# ========================================
# URL:    GET /api/students/{student_id}
# 方法:   GET（读取数据）
# 功能:   根据学生 ID 获取详细信息
# 权限:   需要登录
@router.get("/{student_id}", summary="查询学生详情")
def get_student_detail(
    student_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询单个学生的详细信息
    """
    # 查询学生信息
    result = (
        db.query(StudentInfo, SysUser)
        .join(SysUser, StudentInfo.user_id == SysUser.id)
        .filter(StudentInfo.id == student_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生信息不存在",
        )

    student, user = result
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "id": student.id,
            "user_id": student.user_id,
            "student_no": student.student_no,
            "real_name": user.real_name,
            "username": user.username,
            "gender": student.gender,
            "age": student.age,
            "class_name": student.class_name,
            "major": student.major,
            "grade": student.grade,
            "enrollment_date": student.enrollment_date,
            "chinese_score": student.chinese_score,
            "math_score": student.math_score,
            "english_score": student.english_score,
            "email": user.email,
            "phone": user.phone,
            "created_at": student.created_at.isoformat() if student.created_at else None,
        }
    }


# ========================================
# 接口三：添加新学生
# ========================================
# URL:    POST /api/students
# 方法:   POST（创建数据）
# 功能:   同时创建用户账号和学生详细信息
# 权限:   需要登录 + student:create 权限
#
# 请求体（Body）示例：
#   {
#     "username": "student001",
#     "password": "123456",
#     "real_name": "张三",
#     "student_no": "2023001",
#     "gender": "男",
#     "age": 20,
#     "class_name": "计算机2301班",
#     "chinese_score": 85,
#     "math_score": 92,
#     "english_score": 78
#   }
@router.post("", summary="添加新学生")
def create_student(
    student_data: StudentCreate,   # Pydantic 自动校验数据格式
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    添加新学生

    操作步骤：
      1. 检查用户名和学号是否已被占用
      2. 在 sys_user 表中创建用户账号（密码加密）
      3. 在 student_info 表中创建学生详细信息
      4. 为用户分配"学生"角色
    """
    # 第一步：检查用户名是否已存在
    existing_user = db.query(SysUser).filter(SysUser.username == student_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 第二步：检查学号是否已存在
    existing_student = db.query(StudentInfo).filter(StudentInfo.student_no == student_data.student_no).first()
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号已存在",
        )

    # 第三步：创建用户账号（密码使用 bcrypt 加密）
    new_user = SysUser(
        username=student_data.username,
        password=hash_password(student_data.password),  # 加密密码
        real_name=student_data.real_name,
    )
    db.add(new_user)
    db.flush()  # flush 会执行 SQL 但不提交事务，这样可以获取自增的 id

    # 第四步：创建学生详细信息
    new_student = StudentInfo(
        user_id=new_user.id,              # 关联到刚创建的用户
        student_no=student_data.student_no,
        gender=student_data.gender,
        age=student_data.age,
        class_name=student_data.class_name,
        major=student_data.major,
        grade=student_data.grade,
        enrollment_date=student_data.enrollment_date,
        chinese_score=student_data.chinese_score,
        math_score=student_data.math_score,
        english_score=student_data.english_score,
    )
    db.add(new_student)

    # 第五步：为用户分配"学生"角色
    student_role = db.query(SysRole).filter(SysRole.role_code == "student").first()
    if student_role:
        user_role = SysUserRole(user_id=new_user.id, role_id=student_role.id)
        db.add(user_role)

    # 第六步：提交事务（一次性写入所有数据）
    db.commit()
    db.refresh(new_student)

    return {
        "code": 200,
        "message": "学生添加成功",
        "data": {
            "id": new_student.id,
            "student_no": new_student.student_no,
            "real_name": student_data.real_name,
        }
    }


# ========================================
# 接口四：修改学生信息
# ========================================
# URL:    PUT /api/students/{student_id}
# 方法:   PUT（更新数据）
# 功能:   根据学生 ID 修改学生信息
# 权限:   需要登录 + student:update 权限
#
# 请求体（Body）示例（只传需要修改的字段）：
#   {
#     "real_name": "李四",
#     "class_name": "计算机2302班",
#     "math_score": 95
#   }
@router.put("/{student_id}", summary="修改学生信息")
def update_student(
    student_id: int,
    student_data: StudentUpdate,   # Pydantic 校验，所有字段可选
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改学生信息

    只更新传入的字段，未传入的字段保持不变
    使用 exclude_unset=True 获取实际传了值的字段
    """
    # 查询学生信息
    student = db.query(StudentInfo).filter(StudentInfo.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生信息不存在",
        )

    # 获取前端实际传入的字段（排除未设置的字段）
    update_data = student_data.model_dump(exclude_unset=True)

    # 更新学生表中的字段
    for key, value in update_data.items():
        setattr(student, key, value)

    # 如果修改了真实姓名，同步更新 sys_user 表
    if "real_name" in update_data:
        user = db.query(SysUser).filter(SysUser.id == student.user_id).first()
        if user:
            user.real_name = update_data["real_name"]

    # 提交修改
    db.commit()
    db.refresh(student)

    return {
        "code": 200,
        "message": "学生信息修改成功",
        "data": {"id": student.id}
    }


# ========================================
# 接口五：删除学生
# ========================================
# URL:    DELETE /api/students/{student_id}
# 方法:   DELETE（删除数据）
# 功能:   根据学生 ID 删除学生信息
# 权限:   需要登录 + student:delete 权限（权限拦截示例）
#
# 注意：
#   删除操作会同时删除 sys_user 和 student_info 中的记录
#   因为 sys_user_role 关联表设置了 cascade="all, delete-orphan"
#   所以用户的角色关联也会被自动删除
@router.delete("/{student_id}", summary="删除学生")
def delete_student(
    student_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除学生

    操作步骤：
      1. 查询学生信息
      2. 删除 student_info 表中的记录
      3. 删除 sys_user 表中的关联账号
      4. 关联表（sys_user_role）会自动级联删除
    """
    # 查询学生信息
    student = db.query(StudentInfo).filter(StudentInfo.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生信息不存在",
        )

    # 查询关联的用户账号
    user = db.query(SysUser).filter(SysUser.id == student.user_id).first()

    # 删除学生信息
    db.delete(student)

    # 删除用户账号（级联删除会自动清理 sys_user_role 关联记录）
    if user:
        db.delete(user)

    # 提交删除
    db.commit()

    return {
        "code": 200,
        "message": "学生删除成功",
        "data": None,
    }
