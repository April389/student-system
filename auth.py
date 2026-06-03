# ========================================
# 认证模块 auth.py
# 作用：处理用户密码加密 和 JWT Token 的生成与验证
# ========================================
#
# 技术栈说明：
#   1. passlib[bcrypt] —— 密码加密工具
#      将用户输入的明文密码加密成乱码（密文）存储到数据库
#      即使数据库泄露，也无法还原出原始密码，保障安全
#
#   2. PyJWT —— JWT Token 处理工具
#      用户登录成功后，生成一个 JWT Token（电子通行证）发给前端
#      前端后续每次请求都携带这个 Token
#      后端通过验证 Token 来确认用户身份
#
# JWT 工作流程：
#   登录成功  →  生成 Token（包含用户信息 + 过期时间 + 签名）
#             →  发送给前端
#   前端请求  →  在请求头（Header）中携带 Token
#             →  后端验证 Token 的签名和有效期
#             →  验证通过则允许操作，否则拒绝
# ========================================

import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


# ========================================
# 第一部分：密码加密（passlib + bcrypt）
# ========================================
# CryptContext 是 passlib 提供的密码加密上下文管理器
# schemes=["bcrypt"]  —— 使用 bcrypt 算法进行加密
#   bcrypt 的特点：
#   - 每次加密同一个密码，得到的密文都不同（加盐机制）
#   - 无法从密文反推出明文
#   - 加密速度故意设计得慢，防止暴力破解
# deprecated="auto"  —— 自动标记过时的加密算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    将明文密码加密为密文

    参数：
        password: 用户输入的原始密码（明文）

    返回：
        加密后的密码（密文/乱码），存储到数据库中

    示例：
        输入："123456"
        输出："$2b$12$LJ3m4ys3G..." （每次都不同的乱码）
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与加密后的密文是否匹配

    参数：
        plain_password:  用户输入的原始密码（明文）
        hashed_password: 数据库中存储的加密密码（密文）

    返回：
        True  —— 密码正确
        False —— 密码错误

    原理：
        passlib 会从密文中提取"盐值"，
        然后用同样的盐值对明文密码加密，比较结果是否一致
    """
    return pwd_context.verify(plain_password, hashed_password)


# ========================================
# 第二部分：JWT Token 生成（PyJWT）
# ========================================
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    生成 JWT Token（用户的电子通行证）

    参数：
        data: 需要编码到 Token 中的数据
              通常包含 {"sub": "用户名"}
        expires_delta: Token 的过期时间（可选，默认使用配置文件中的时间）

    返回：
        JWT Token 字符串

    JWT 结构说明（三段式，用 . 分隔）：
        第一段：Header   —— 声明加密算法（HS256）
        第二段：Payload  —— 携带的数据（用户名、过期时间等）
        第三段：Signature —— 数字签名，防止数据被篡改

    示例：
        输入：data={"sub": "admin"}
        输出："eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIs..."
    """
    # 复制一份数据，避免修改原始字典
    to_encode = data.copy()

    # 计算过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 将过期时间加入 Token 的 Payload 中
    # "exp" 是 JWT 标准字段名，表示过期时间戳
    to_encode.update({"exp": expire})

    # 使用 SECRET_KEY 对数据进行签名，生成 JWT Token
    # jwt.encode() 会自动完成：Header编码 + Payload编码 + 签名
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


# ========================================
# 第三部分：JWT Token 验证（PyJWT）
# ========================================
def decode_access_token(token: str) -> dict:
    """
    验证并解码 JWT Token

    参数：
        token: 前端传过来的 JWT Token 字符串

    返回：
        解码后的数据字典（包含用户名等信息）
        例如：{"sub": "admin", "exp": 1234567890}

    异常：
        jwt.ExpiredSignatureError  —— Token 已过期
        jwt.InvalidTokenError      —— Token 无效（被篡改或格式错误）

    验证过程：
        1. 检查 Token 格式是否正确
        2. 用 SECRET_KEY 验证签名是否被篡改
        3. 检查 Token 是否已过期
        4. 全部通过后，解码返回 Payload 数据
    """
    try:
        # jwt.decode() 会自动完成：签名验证 + 过期检查 + 解码
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token 已超过有效期
        raise ValueError("Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        # Token 被篡改或格式错误
        raise ValueError("无效的 Token")
