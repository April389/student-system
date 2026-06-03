# ========================================
# 数据校验文件 schemas.py
# 作用：定义前端传入数据的格式校验规则
# ========================================
#
# 技术说明：
#   Pydantic 是 FastAPI 的标配数据校验库
#   使用类型提示语法（Type Hints）定义字段类型
#   例如：name: str  表示 name 必须是字符串
#         age: int   表示 age 必须是整数
#
#   它能自动检查前端传过来的数据格式对不对
#   如果格式不对，FastAPI 会自动返回 422 错误（数据校验失败）
#
# 工作原理：
#   前端发送 JSON 数据  →  Pydantic 模型校验  →  校验通过则转为 Python 对象
#                                              →  校验不通过则返回错误信息
# ========================================

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========================================
# 第一部分：用户相关的数据校验模型
# ========================================

# --- 用户注册时的数据校验 ---
class UserCreate(BaseModel):
    """
    用户注册时，前端需要传过来的数据格式
    Field(...) 中的 ... 表示必填字段
    """
    username: str = Field(..., min_length=3, max_length=50, description="用户名，3-50个字符")
    password: str = Field(..., min_length=6, max_length=50, description="密码，至少6个字符")
    real_name: Optional[str] = Field(None, max_length=50, description="真实姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "password": "123456",
                "real_name": "张三",
                "email": "zhangsan@example.com",
                "phone": "13800138000"
            }
        }


# --- 用户登录时的数据校验 ---
class UserLogin(BaseModel):
    """
    用户登录时，前端需要传过来的数据格式
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "123456"
            }
        }


# --- 用户信息返回格式（不包含密码） ---
class UserResponse(BaseModel):
    """
    返回给前端的用户信息格式
    注意：绝对不能返回密码字段！
    """
    id: int
    username: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None
    roles: Optional[List[str]] = None  # 用户拥有的角色名称列表

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 模型对象直接转换


# ========================================
# 第二部分：学生信息相关的数据校验模型
# ========================================

# --- 创建学生时的数据校验 ---
class StudentCreate(BaseModel):
    """
    添加学生信息时，前端需要传过来的数据格式
    """
    username: str = Field(..., description="登录用户名")
    password: str = Field(..., min_length=6, description="登录密码")
    real_name: str = Field(..., description="学生真实姓名")
    student_no: str = Field(..., description="学号")
    gender: Optional[str] = Field(None, description="性别")
    age: Optional[int] = Field(None, ge=1, le=150, description="年龄")
    class_name: Optional[str] = Field(None, description="班级")
    major: Optional[str] = Field(None, description="专业")
    grade: Optional[str] = Field(None, description="年级")
    enrollment_date: Optional[str] = Field(None, description="入学日期")
    chinese_score: Optional[int] = Field(None, ge=0, le=100, description="语文成绩")
    math_score: Optional[int] = Field(None, ge=0, le=100, description="数学成绩")
    english_score: Optional[int] = Field(None, ge=0, le=100, description="英语成绩")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "student001",
                "password": "123456",
                "real_name": "张三",
                "student_no": "2023001",
                "gender": "男",
                "age": 20,
                "class_name": "计算机2301班",
                "major": "计算机科学与技术",
                "grade": "2023级",
                "enrollment_date": "2023-09-01",
                "chinese_score": 85,
                "math_score": 92,
                "english_score": 78
            }
        }


# --- 更新学生信息时的数据校验 ---
class StudentUpdate(BaseModel):
    """
    更新学生信息时，前端需要传过来的数据格式
    所有字段都是可选的（只传需要修改的字段）
    """
    real_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=150)
    class_name: Optional[str] = None
    major: Optional[str] = None
    grade: Optional[str] = None
    enrollment_date: Optional[str] = None
    chinese_score: Optional[int] = Field(None, ge=0, le=100)
    math_score: Optional[int] = Field(None, ge=0, le=100)
    english_score: Optional[int] = Field(None, ge=0, le=100)


# --- 学生信息返回格式 ---
class StudentResponse(BaseModel):
    """
    返回给前端的学生信息格式
    """
    id: int
    student_no: str
    real_name: str
    username: str
    gender: Optional[str] = None
    age: Optional[int] = None
    class_name: Optional[str] = None
    major: Optional[str] = None
    grade: Optional[str] = None
    enrollment_date: Optional[str] = None
    chinese_score: Optional[int] = None
    math_score: Optional[int] = None
    english_score: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========================================
# 第三部分：通用响应模型
# ========================================

# --- 统一返回格式 ---
class ApiResponse(BaseModel):
    """
    所有接口的统一返回格式
    前端可以根据 code 判断请求是否成功
    """
    code: int = 200           # 状态码：200=成功，其他=失败
    message: str = "操作成功"  # 提示信息
    data: Optional[dict] = None  # 返回的数据（可选）


# --- 分页列表返回格式 ---
class PaginatedResponse(BaseModel):
    """
    分页查询的返回格式
    """
    code: int = 200
    message: str = "查询成功"
    data: Optional[List[dict]] = None  # 数据列表
    total: int = 0             # 总记录数
    page: int = 1              # 当前页码
    page_size: int = 10        # 每页条数


# ========================================
# 第四部分：Token 返回模型
# ========================================
class TokenResponse(BaseModel):
    """
    登录成功后返回的 Token 信息
    """
    access_token: str    # JWT Token（电子通行证）
    token_type: str = "bearer"  # Token 类型
    user: UserResponse   # 用户信息
