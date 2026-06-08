"""
学生管理系统 - 综合测试套件
========================================

测试策略：
  1. 黑盒功能测试（等价类划分 + 边界值法）—— 测试各个菜单的正常和异常输入
  2. 权限和安全测试 —— 验证是否存在越权漏洞
  3. 白盒单元测试 —— 验证核心算法（密码加密、JWT、统计逻辑）
  4. 并发测试（本地）—— 模拟多用户同时操作，验证基础并发能力

测试运行前需要：
  - 后端服务运行在 http://127.0.0.1:8000
  - 至少存在 admin 账号（密码 123456）

执行方式：
  python test_comprehensive.py
"""

import requests
import json
import threading
import time
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from datetime import datetime

# ========================================
# 全局配置
# ========================================
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USER = ("admin", "123456")
STUDENT_USER = ("zhangsan", "123456")  # 用已存在的学生账号测试权限

# 测试结果统计
STATS = {"pass": 0, "fail": 0, "error": 0, "total": 0}
LOCK = threading.Lock()  # 用于并发测试时安全计数


# ========================================
# 工具函数
# ========================================
def print_header(title: str):
    """打印测试段标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """打印小节标题"""
    print(f"\n  ── {title} " + "─" * (60 - len(title)))


def print_test(name: str, passed: bool, detail: str = ""):
    """
    打印单条测试结果
    passed: True=通过, False=失败
    """
    STATS["total"] += 1
    if passed:
        STATS["pass"] += 1
        icon = "[通过]"
    else:
        STATS["fail"] += 1
        icon = "[失败]"

    print(f"  {icon} {name}")
    if detail:
        for line in detail.split("\n"):
            print(f"        {line}")


def safe_request(method: str, url: str, **kwargs) -> Tuple[int, dict]:
    """
    安全地发送 HTTP 请求
    返回: (状态码, 响应JSON)
    """
    try:
        r = requests.request(method, url, timeout=5, **kwargs)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        return r.status_code, data
    except Exception as e:
        return -1, {"error": str(e)}


def login(username: str, password: str) -> str:
    """登录获取 token，失败返回空串"""
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": username, "password": password})
    if code == 200 and "access_token" in data:
        return data["access_token"]
    return ""


# ========================================
# 第一部分：黑盒功能测试
# ========================================
def test_blackbox_login():
    """
    黑盒测试 - 登录模块
    方法：等价类划分 + 边界值
    """
    print_header("第一部分：黑盒功能测试 - 登录模块")
    print_section("等价类划分：有效 / 无效输入")

    # ───── 等价类1：有效登录 ─────
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": "admin", "password": "123456"})
    print_test("有效：admin/123456", code == 200 and "access_token" in data,
               f"状态码={code}, 返回={data.get('user', {}).get('username', '无')}")

    # ───── 等价类2：错误密码 ─────
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": "admin", "password": "wrong_pwd"})
    print_test("无效：密码错误", code == 401, f"状态码={code}, 提示={data.get('detail', '')}")

    # ───── 等价类3：不存在的用户 ─────
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": "no_such_user_xxx", "password": "123456"})
    print_test("无效：用户不存在", code == 401, f"状态码={code}, 提示={data.get('detail', '')}")

    # ───── 等价类4：空用户名 ─────
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": "", "password": "123456"})
    print_test("无效：用户名为空", code == 422, f"状态码={code}")

    # ───── 等价类5：空密码 ─────
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": "admin", "password": ""})
    print_test("无效：密码为空", code == 422, f"状态码={code}")

    # ───── 边界值：超长密码 ─────
    code, data = safe_request("POST", f"{BASE_URL}/api/auth/login",
                              json={"username": "admin", "password": "x" * 1000})
    print_test("边界：超长密码(1000字符)", code in (401, 422), f"状态码={code}")


def test_blackbox_student():
    """
    黑盒测试 - 学生管理模块
    方法：等价类划分 + 边界值
    """
    print_header("第二部分：黑盒功能测试 - 学生管理模块")
    print_section("等价类划分 + 边界值测试")

    admin_token = login(*ADMIN_USER)
    if not admin_token:
        print("  [错误] 管理员登录失败，跳过学生测试")
        STATS["error"] += 1
        return
    headers = {"Authorization": f"Bearer {admin_token}"}

    # ───── 1. 必填项缺失 ─────
    print_section("必填项缺失（等价类：必填字段为空）")
    code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=headers,
                              json={"username": "test1", "password": "123456"})  # 缺 real_name, student_no
    print_test("缺真实姓名", code == 422, f"状态码={code}")

    code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=headers,
                              json={"password": "123456", "real_name": "x", "student_no": "x"})
    print_test("缺用户名", code == 422, f"状态码={code}")

    # ───── 2. 成绩边界值（0-100） ─────
    print_section("成绩边界值（合法范围 0-100）")
    # 生成唯一用户名
    ts = int(time.time() * 1000)
    base_stu = {"username": f"test_{ts}", "password": "123456", "real_name": "测试", "student_no": f"ts{ts}"}

    boundary_scores = [
        ("成绩 = -1（越界）", -1, 422),
        ("成绩 = 0（下边界合法）", 0, 200),
        ("成绩 = 1（越界下边界）", 1, 200),
        ("成绩 = 50（中间值）", 50, 200),
        ("成绩 = 99（越界上边界）", 99, 200),
        ("成绩 = 100（上边界合法）", 100, 200),
        ("成绩 = 101（越界）", 101, 422),
    ]

    for desc, score, expected in boundary_scores:
        s = dict(base_stu)
        s["username"] = f"t_{ts}_{score}"
        s["student_no"] = f"ts_{score}_{ts}"
        s["chinese_score"] = score
        code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
        passed = (code == expected) or (code == 200 and expected == 200) or (code == 422 and expected == 422)
        print_test(f"{desc}, 期望={expected}", code == expected, f"实际={code}, 提示={data.get('message', data.get('detail', '')[:50])}")

    # ───── 3. 年龄边界值（1-150） ─────
    print_section("年龄边界值（合法范围 1-150）")
    age_cases = [
        ("年龄 = 0（越界）", 0, 422),
        ("年龄 = 1（下边界合法）", 1, 200),
        ("年龄 = 150（上边界合法）", 150, 200),
        ("年龄 = 151（越界）", 151, 422),
    ]
    for desc, age, expected in age_cases:
        s = dict(base_stu)
        s["username"] = f"t_age_{age}_{ts}"
        s["student_no"] = f"ts_age_{age}_{ts}"
        s["age"] = age
        code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
        print_test(f"{desc}, 期望={expected}", code == expected, f"实际={code}")

    # ───── 4. 字符串长度边界 ─────
    print_section("字符串长度边界")
    # 用户名长度（schema 要求 3-50）
    s = dict(base_stu)
    s["username"] = "ab"  # 2字符，越界
    s["student_no"] = f"too_short_user_{ts}"
    code, _ = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
    print_test("用户名2字符（应小于3）", code == 422, f"实际={code}")

    s = dict(base_stu)
    s["username"] = "a" * 60  # 60字符，越界
    s["student_no"] = f"too_long_user_{ts}"
    code, _ = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
    print_test("用户名60字符（应超过50）", code == 422, f"实际={code}")

    # ───── 5. 重复值检测 ─────
    print_section("业务约束：唯一性")
    s = dict(base_stu)
    s["username"] = "zhangsan"  # 已存在
    s["student_no"] = f"dup_{ts}"
    code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
    print_test("重复用户名(zhangsan)", code == 400, f"实际={code}, 提示={data.get('message', '')}")

    s = dict(base_stu)
    s["username"] = f"unique_{ts}"
    s["student_no"] = "2023001"  # 已存在
    code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
    print_test("重复学号(2023001)", code == 400, f"实际={code}, 提示={data.get('message', '')}")

    # ───── 6. 异常类型输入 ─────
    print_section("异常类型输入")
    s = dict(base_stu)
    s["username"] = f"typetest_{ts}"
    s["student_no"] = f"type_{ts}"
    s["age"] = "not_a_number"
    code, _ = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
    print_test("年龄传入字符串", code == 422, f"实际={code}")

    s = dict(base_stu)
    s["username"] = f"typetest2_{ts}"
    s["student_no"] = f"type2_{ts}"
    s["chinese_score"] = None
    code, _ = safe_request("POST", f"{BASE_URL}/api/students", headers=headers, json=s)
    print_test("成绩传null（应允许）", code == 200, f"实际={code}")


def test_blackbox_query():
    """
    黑盒测试 - 查询模块
    """
    print_header("第三部分：黑盒功能测试 - 查询与统计")
    admin_token = login(*ADMIN_USER)
    if not admin_token:
        return
    headers = {"Authorization": f"Bearer {admin_token}"}

    print_section("列表查询")
    # 正常查询
    code, data = safe_request("GET", f"{BASE_URL}/api/students", headers=headers)
    print_test("查询全部学生", code == 200, f"总数={data.get('total', '?')}")

    # 分页
    code, data = safe_request("GET", f"{BASE_URL}/api/students",
                              params={"page": 1, "page_size": 2}, headers=headers)
    print_test("分页(page=1, size=2)", code == 200 and len(data.get("data", [])) <= 2,
               f"返回条数={len(data.get('data', []))}")

    # 搜索
    code, data = safe_request("GET", f"{BASE_URL}/api/students",
                              params={"keyword": "张三"}, headers=headers)
    print_test("关键词搜索'张三'", code == 200, f"命中数={data.get('total', '?')}")

    # 边界：超长关键词
    code, data = safe_request("GET", f"{BASE_URL}/api/students",
                              params={"keyword": "x" * 1000}, headers=headers)
    print_test("超长关键词(1000字符)", code == 200, f"实际={code}")

    # 边界：超小页码
    code, data = safe_request("GET", f"{BASE_URL}/api/students",
                              params={"page": 0}, headers=headers)
    print_test("页码=0（应≥1）", code in (200, 422), f"实际={code}")

    # 边界：超长 page_size
    code, data = safe_request("GET", f"{BASE_URL}/api/students",
                              params={"page_size": 99999}, headers=headers)
    print_test("page_size=99999（应≤100）", code in (200, 422), f"实际={code}")

    print_section("统计接口")
    code, data = safe_request("GET", f"{BASE_URL}/api/statistics/overview", headers=headers)
    print_test("成绩总览统计", code == 200, f"学生数={data.get('data', {}).get('total_students', '?')}")

    code, data = safe_request("GET", f"{BASE_URL}/api/statistics/ranking", headers=headers)
    # 接口在 data 字段可能返回 None（暂无数据）或 list（有数据）两种情况
    ranking_data = data.get("data") or []
    print_test("成绩排名", code == 200, f"返回条数={len(ranking_data)}")

    # 异常班级名
    code, data = safe_request("GET", f"{BASE_URL}/api/statistics/class/不存在的班级xyz",
                              headers=headers)
    print_test("不存在的班级", code == 200, f"提示={data.get('message', '')}")


# ========================================
# 第二部分：权限和安全测试
# ========================================
def test_security():
    """
    权限和安全测试
    目标：确保没有越权漏洞
    """
    print_header("第四部分：权限和安全测试")
    admin_token = login(*ADMIN_USER)
    student_token = login(*STUDENT_USER)
    if not admin_token or not student_token:
        print("  [错误] 登录失败，跳过安全测试")
        return

    admin_h = {"Authorization": f"Bearer {admin_token}"}
    stu_h = {"Authorization": f"Bearer {student_token}"}

    print_section("未登录访问保护")
    # 不带 token 访问受保护接口
    # 说明：HTTPBearer(auto_error=True) 在缺少 Authorization header 时返回 401
    #      401 = 未认证（未提供 Token 或 Token 无效）
    #      403 = 已认证但权限不足
    # 这两个状态码在 Web 安全中都是合法响应
    for url in [f"{BASE_URL}/api/students", f"{BASE_URL}/api/users", f"{BASE_URL}/api/auth/me"]:
        code, _ = safe_request("GET", url)
        # 接受 401 或 403 都算未授权保护正常
        print_test(f"未登录访问 {url.split('/')[-1]}", code in (401, 403),
                   f"实际={code}（401=未认证，403=无权限，均为正常的未授权保护）")

    print_section("伪造/无效Token")
    fake_h = {"Authorization": "Bearer fake.invalid.token"}
    code, _ = safe_request("GET", f"{BASE_URL}/api/students", headers=fake_h)
    print_test("伪造的token", code == 401, f"实际={code}")

    code, _ = safe_request("GET", f"{BASE_URL}/api/students",
                           headers={"Authorization": "Bearer " + "x" * 200})
    print_test("超长无效token", code == 401, f"实际={code}")

    print_section("学生越权测试（应全部 403）")
    # 学生尝试访问用户管理
    code, data = safe_request("GET", f"{BASE_URL}/api/users", headers=stu_h)
    print_test("学生访问用户列表", code == 403, f"实际={code}, 提示={data.get('detail', '')[:40]}")

    # 学生尝试添加/修改/删除学生
    ts = int(time.time() * 1000)
    new_stu = {"username": f"hacker_{ts}", "password": "123456",
               "real_name": "hacker", "student_no": f"h{ts}"}
    code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=stu_h, json=new_stu)
    print_test("学生尝试添加其他学生", code == 403, f"实际={code}")

    code, data = safe_request("PUT", f"{BASE_URL}/api/students/1", headers=stu_h, json={"age": 99})
    print_test("学生尝试修改其他学生", code == 403, f"实际={code}")

    code, data = safe_request("DELETE", f"{BASE_URL}/api/students/1", headers=stu_h)
    print_test("学生尝试删除其他学生", code == 403, f"实际={code}")

    # 学生尝试禁用其他用户
    code, data = safe_request("PUT", f"{BASE_URL}/api/users/2/status",
                              headers=stu_h, json={"status": 0})
    print_test("学生尝试禁用其他用户", code == 403, f"实际={code}")

    print_section("管理员自保护")
    code, data = safe_request("PUT", f"{BASE_URL}/api/users/1/status",
                              headers=admin_h, json={"status": 0})
    print_test("管理员禁用自己（应400）", code == 400, f"实际={code}, 提示={data.get('detail', '')}")

    print_section("SQL注入检测")
    # 登录接口 SQL 注入
    inj_payloads = [
        {"username": "admin' OR '1'='1", "password": "x"},
        {"username": "admin' -- ", "password": "x"},
        {"username": "' OR 1=1 -- ", "password": "x"},
    ]
    for payload in inj_payloads:
        code, _ = safe_request("POST", f"{BASE_URL}/api/auth/login", json=payload)
        print_test(f"注入: {payload['username'][:30]}", code == 401, f"实际={code}")

    # 查询参数注入
    code, _ = safe_request("GET", f"{BASE_URL}/api/students",
                           params={"keyword": "'; DROP TABLE users; --"}, headers=admin_h)
    print_test("查询参数SQL注入", code == 200, f"实际={code}（应正常返回，不应崩）")

    # 检查数据表是否还存在（间接验证）
    code, _ = safe_request("GET", f"{BASE_URL}/api/auth/me", headers=admin_h)
    print_test("注入后系统仍正常（表未丢）", code == 200, f"实际={code}")

    print_section("XSS注入检测")
    xss_payload = "<script>alert('xss')</script>"
    new_stu = {"username": f"xss_{ts}", "password": "123456",
               "real_name": xss_payload, "student_no": f"xs{ts}"}
    code, data = safe_request("POST", f"{BASE_URL}/api/students", headers=admin_h, json=new_stu)
    print_test("提交XSS载荷", code in (200, 400), f"实际={code}")
    # 查询应能正确返回（数据原样保存，前端应做转义）
    code, data = safe_request("GET", f"{BASE_URL}/api/students",
                              params={"keyword": xss_payload}, headers=admin_h)
    print_test("XSS内容查询不执行", code == 200, f"实际={code}")


# ========================================
# 第三部分：白盒单元测试
# ========================================
def test_whitebox_core():
    """
    白盒测试 - 核心算法
    测试 auth.py 中的密码加密/验证、token 解析
    """
    print_header("第五部分：白盒单元测试 - 核心算法")

    print_section("密码加密")
    try:
        # 动态导入 auth 模块
        sys.path.insert(0, "d:/19027/Documents/学生管理系统后端开发")
        from auth import hash_password, verify_password, create_access_token, decode_access_token
        from config import SECRET_KEY, ALGORITHM

        # 测试1: 密码hash不应返回原密码
        pwd = "MySecret123"
        hashed = hash_password(pwd)
        print_test("hash不返回原密码", hashed != pwd, f"hash长度={len(hashed)}")

        # 测试2: 相同密码每次hash应不同（bcrypt salt）
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        print_test("相同密码每次hash不同（bcrypt加盐）", h1 != h2, "两次hash不一致")

        # 测试3: verify应能正确验证
        print_test("正确密码验证通过", verify_password(pwd, hashed))
        print_test("错误密码验证失败", not verify_password("wrong_pwd", hashed))
        print_test("空字符串密码验证失败", not verify_password("", hashed))

    except Exception as e:
        STATS["error"] += 1
        print_test("密码模块加载", False, f"异常: {e}")

    print_section("JWT Token")
    try:
        # 测试4: Token生成与解析
        token = create_access_token({"sub": "admin"})
        print_test("token生成非空", bool(token) and len(token) > 50, f"长度={len(token)}")

        # 测试5: 解析应能拿到用户名
        payload = decode_access_token(token)
        print_test("token能解析出sub", payload and payload.get("sub") == "admin", f"sub={payload.get('sub') if payload else 'None'}")

        # 测试6: 篡改token应失败
        # 说明：auth.decode_access_token 遇到非法 token 会抛 ValueError（被 dependencies.py 捕获转为 401）
        fake_token = token[:-5] + "AAAAA"
        try:
            result = decode_access_token(fake_token)
            print_test("篡改token应失败", result is None, f"解析返回={result}（未拒绝）")
        except ValueError as e:
            print_test("篡改token应失败", True, f"解析抛异常（依赖 dependencies.py 转 401）：{e}")

        # 测试7: 无效的token格式应失败
        try:
            result = decode_access_token("not.a.valid.token")
            print_test("无效token格式应失败", result is None, f"解析返回={result}（未拒绝）")
        except ValueError as e:
            print_test("无效token格式应失败", True, f"解析抛异常（依赖 dependencies.py 转 401）：{e}")

    except Exception as e:
        STATS["error"] += 1
        print_test("JWT模块测试", False, f"异常: {e}")

    print_section("统计逻辑（白盒）")
    try:
        import pandas as pd
        # 模拟数据
        df = pd.DataFrame({
            "chinese_score": [80, 90, 100, 0],
            "math_score": [70, 80, 90, 100],
            "english_score": [60, 75, 85, 95]
        })
        # 验证平均分
        avg = df["chinese_score"].mean()
        print_test("语文平均分计算", avg == 67.5, f"实际={avg}")

        # 边界：空DataFrame
        empty = pd.DataFrame()
        try:
            empty["x"].mean()
            print_test("空DataFrame统计", False, "未抛异常（应保护）")
        except Exception:
            print_test("空DataFrame统计", True, "抛异常，符合预期")

    except Exception as e:
        STATS["error"] += 1
        print_test("Pandas测试", False, f"异常: {e}")


# ========================================
# 第四部分：并发测试（本地）
# ========================================
def _concurrent_login(idx: int) -> bool:
    """单次登录（用于并发测试）"""
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": "admin", "password": "123456"},
                          timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def _concurrent_query(token: str) -> bool:
    """单次查询（用于并发测试）"""
    try:
        r = requests.get(f"{BASE_URL}/api/students",
                         headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def _concurrent_add(token: str, idx: int) -> bool:
    """单次添加学生（用于并发测试，验证数据一致性）"""
    try:
        ts = int(time.time() * 1000) + idx
        r = requests.post(f"{BASE_URL}/api/students",
                          headers={"Authorization": f"Bearer {token}"},
                          json={
                              "username": f"conc_{ts}",
                              "password": "123456",
                              "real_name": f"并发学生{idx}",
                              "student_no": f"c{ts}"
                          },
                          timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def test_concurrency():
    """
    并发测试
    说明：
      - 本地模拟多线程访问，验证：连接池、JWT校验、权限检查在并发下不崩溃
      - 验证：并发添加时数据库唯一约束能正常拦截
      - 局限：无法测试真实云端的网络延迟、CDN、容器自动休眠等场景
      - 部署后可使用 Locust/JMeter 等工具做完整压测
    """
    print_header("第六部分：并发测试（本地模拟）")
    admin_token = login(*ADMIN_USER)
    if not admin_token:
        print("  [错误] 登录失败，跳过并发测试")
        return

    print_section("并发登录测试（20个线程）")
    N = 20
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=N) as executor:
        futures = [executor.submit(_concurrent_login, i) for i in range(N)]
        results = [f.result() for f in as_completed(futures)]
    elapsed = time.time() - t0
    success = sum(1 for r in results if r)
    print_test(f"{N}个线程同时登录",
               success == N,
               f"成功={success}/{N}, 耗时={elapsed:.2f}s, QPS={N/elapsed:.1f}")

    print_section("并发查询测试（50个线程 × 10次）")
    M, K = 10, 50
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=M) as executor:
        futures = [executor.submit(_concurrent_query, admin_token) for _ in range(K)]
        results = [f.result() for f in as_completed(futures)]
    elapsed = time.time() - t0
    success = sum(1 for r in results if r)
    print_test(f"{K}次查询 / {M}线程",
               success == K,
               f"成功={success}/{K}, 耗时={elapsed:.2f}s, QPS={K/elapsed:.1f}")

    print_section("并发添加测试（验证唯一约束能正常拦截）")
    P = 10
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=P) as executor:
        futures = [executor.submit(_concurrent_add, admin_token, i) for i in range(P)]
        results = [f.result() for f in as_completed(futures)]
    elapsed = time.time() - t0
    success = sum(1 for r in results if r)
    print_test(f"{P}个线程同时添加不同学生",
               success == P,
               f"成功={success}/{P}, 耗时={elapsed:.2f}s")

    print_section("并发安全测试（同一学号/用户名 5个线程抢着加）")
    ts = int(time.time() * 1000)
    duplicate_payload = {
        "username": f"dup_concurrent_{ts}",
        "password": "123456",
        "real_name": "重名学生",
        "student_no": f"dup_no_{ts}"
    }

    def add_dup(idx):
        r = requests.post(f"{BASE_URL}/api/students",
                          headers={"Authorization": f"Bearer {admin_token}"},
                          json=duplicate_payload, timeout=10)
        return r.status_code

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(add_dup, i) for i in range(5)]
        codes = [f.result() for f in as_completed(futures)]
    success = sum(1 for c in codes if c == 200)
    failed = sum(1 for c in codes if c == 400)
    print_test("唯一性约束生效（5个并发只允许1个成功）",
               success == 1 and failed == 4,
               f"成功={success}, 失败={failed}, 状态码分布={dict((c, codes.count(c)) for c in set(codes))}")


# ========================================
# 主程序
# ========================================
def main():
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█  学生管理系统 - 综合测试套件" + " " * 33 + "█")
    print("█  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " * (60 - len(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    t_start = time.time()

    # 1. 登录黑盒
    test_blackbox_login()
    # 2. 学生黑盒
    test_blackbox_student()
    # 3. 查询黑盒
    test_blackbox_query()
    # 4. 权限安全
    test_security()
    # 5. 白盒核心
    test_whitebox_core()
    # 6. 并发
    test_concurrency()

    # 汇总
    elapsed = time.time() - t_start
    print("\n" + "=" * 70)
    print("  测试汇总")
    print("=" * 70)
    print(f"  总用例数: {STATS['total']}")
    print(f"  通过:   {STATS['pass']}  [OK]")
    print(f"  失败:   {STATS['fail']}  [X]")
    print(f"  异常:   {STATS['error']}  [!]")
    print(f"  通过率: {STATS['pass'] / max(STATS['total'], 1) * 100:.1f}%")
    print(f"  总耗时: {elapsed:.2f} 秒")
    print("=" * 70)

    if STATS["fail"] == 0 and STATS["error"] == 0:
        print("  [OK] 全部通过！")
        return 0
    else:
        print("  [!] 存在失败用例，请检查上方详情")
        return 1


if __name__ == "__main__":
    sys.exit(main())
