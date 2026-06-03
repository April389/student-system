"""
API 实体测试脚本
逐步测试所有接口，传真实数据验证
"""
import requests
import json

BASE = "http://127.0.0.1:8000"

def pretty(title, resp):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"  状态码: {resp.status_code}")
    data = resp.json()
    print(f"  返回: {json.dumps(data, ensure_ascii=False, indent=2)}")
    print(f"{'='*60}")
    return data

# ========== 测试1: 登录 ==========
print("\n" + "█"*60)
print("  测试1: 管理员登录")
print("█"*60)
r = requests.post(f"{BASE}/api/auth/login", json={
    "username": "admin",
    "password": "123456"
})
login_data = pretty("POST /api/auth/login", r)
TOKEN = login_data["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print(f"\n>>> Token 获取成功: {TOKEN[:30]}...")

# ========== 测试2: 批量添加学生 ==========
print("\n" + "█"*60)
print("  测试2: 批量添加学生数据（5名学生）")
print("█"*60)

students = [
    {
        "username": "zhangsan", "password": "123456",
        "real_name": "张三", "student_no": "2023001",
        "gender": "男", "age": 20,
        "class_name": "计算机2301班", "major": "计算机科学与技术",
        "grade": "2023级", "enrollment_date": "2023-09-01",
        "chinese_score": 85, "math_score": 92, "english_score": 78
    },
    {
        "username": "lisi", "password": "123456",
        "real_name": "李四", "student_no": "2023002",
        "gender": "女", "age": 19,
        "class_name": "计算机2301班", "major": "计算机科学与技术",
        "grade": "2023级", "enrollment_date": "2023-09-01",
        "chinese_score": 91, "math_score": 88, "english_score": 95
    },
    {
        "username": "wangwu", "password": "123456",
        "real_name": "王五", "student_no": "2023003",
        "gender": "男", "age": 21,
        "class_name": "计算机2302班", "major": "软件工程",
        "grade": "2023级", "enrollment_date": "2023-09-01",
        "chinese_score": 76, "math_score": 95, "english_score": 70
    },
    {
        "username": "zhaoliu", "password": "123456",
        "real_name": "赵六", "student_no": "2023004",
        "gender": "女", "age": 20,
        "class_name": "计算机2302班", "major": "软件工程",
        "grade": "2023级", "enrollment_date": "2023-09-01",
        "chinese_score": 88, "math_score": 79, "english_score": 82
    },
    {
        "username": "sunqi", "password": "123456",
        "real_name": "孙七", "student_no": "2023005",
        "gender": "男", "age": 22,
        "class_name": "数据科学2301班", "major": "数据科学与大数据",
        "grade": "2023级", "enrollment_date": "2023-09-01",
        "chinese_score": 82, "math_score": 97, "english_score": 74
    }
]

created_ids = []
for i, s in enumerate(students, 1):
    r = requests.post(f"{BASE}/api/students", json=s, headers=HEADERS)
    data = pretty(f"[{i}/5] POST /api/students - 添加 {s['real_name']}", r)
    if r.status_code == 200 and data.get("code") == 200:
        sid = data["data"]["id"]
        created_ids.append(sid)
        print(f">>> 添加成功! ID={sid}")
    else:
        print(f">>> 添加失败: {data.get('message', '未知错误')}")

# ========== 测试3: 查询学生列表 ==========
print("\n" + "█"*60)
print("  测试3: 查询学生列表")
print("█"*60)

r = requests.get(f"{BASE}/api/students", headers=HEADERS)
pretty("GET /api/students - 查询全部学生", r)

# 按关键词搜索
r = requests.get(f"{BASE}/api/students", params={"keyword": "张三"}, headers=HEADERS)
pretty("GET /api/students?keyword=张三 - 搜索张三", r)

# 按班级筛选
r = requests.get(f"{BASE}/api/students", params={"class_name": "计算机2301班"}, headers=HEADERS)
pretty("GET /api/students?class_name=计算机2301班", r)

# ========== 测试4: 修改学生信息 ==========
print("\n" + "█"*60)
print("  测试4: 修改学生信息")
print("█"*60)

if created_ids:
    target_id = created_ids[0]
    r = requests.put(f"{BASE}/api/students/{target_id}", json={
        "age": 21,
        "chinese_score": 90,
        "math_score": 98,
        "english_score": 85
    }, headers=HEADERS)
    pretty(f"PUT /api/students/{target_id} - 修改张三的成绩和年龄", r)

# ========== 测试5: 删除学生 ==========
print("\n" + "█"*60)
print("  测试5: 删除学生")
print("█"*60)

if len(created_ids) >= 5:
    target_id = created_ids[4]
    r = requests.delete(f"{BASE}/api/students/{target_id}", headers=HEADERS)
    pretty(f"DELETE /api/students/{target_id} - 删除孙七", r)

# 删除后再查一次，确认删除成功
r = requests.get(f"{BASE}/api/students", headers=HEADERS)
pretty("GET /api/students - 删除后再次查询", r)

# ========== 测试6: 数据统计 ==========
print("\n" + "█"*60)
print("  测试6: 数据统计接口")
print("█"*60)

r = requests.get(f"{BASE}/api/statistics/overview", headers=HEADERS)
pretty("GET /api/statistics/overview - 总体统计", r)

r = requests.get(f"{BASE}/api/statistics/class", headers=HEADERS)
pretty("GET /api/statistics/class - 班级统计", r)

# ========== 测试7: 获取当前用户信息 ==========
print("\n" + "█"*60)
print("  测试7: 获取当前登录用户信息")
print("█"*60)

r = requests.get(f"{BASE}/api/auth/me", headers=HEADERS)
pretty("GET /api/auth/me - 当前用户", r)

print("\n" + "="*60)
print("  所有测试完成！")
print("="*60)
