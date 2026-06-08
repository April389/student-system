"""清理测试数据（按依赖顺序）"""
import pymysql

c = pymysql.connect(host='127.0.0.1', user='root', password='123456', database='student_system')
cur = c.cursor()

# 第一步：找出所有测试用户
cur.execute("SELECT id FROM sys_user WHERE username NOT IN ('admin', 'zhangsan', 'lisi', 'wangwu', 'zhaoliu', 'sunqi')")
test_user_ids = [row[0] for row in cur.fetchall()]
print(f"找到 {len(test_user_ids)} 个测试用户")

# 第二步：删除关联表数据
if test_user_ids:
    placeholders = ','.join(['%s'] * len(test_user_ids))
    cur.execute(f"DELETE FROM sys_user_role WHERE user_id IN ({placeholders})", test_user_ids)
    cur.execute(f"DELETE FROM student_info WHERE user_id IN ({placeholders})", test_user_ids)
    cur.execute(f"DELETE FROM sys_user WHERE id IN ({placeholders})", test_user_ids)

# 第三步：清理异常学生（学号是测试数据的）
cur.execute("DELETE FROM student_info WHERE student_no REGEXP '^[a-z]{1,2}[0-9]+$'")
print("已清理 test_* 学号的学生")

c.commit()
cur.execute("SELECT COUNT(*) FROM sys_user")
print(f"剩余用户: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM student_info")
print(f"剩余学生: {cur.fetchone()[0]}")
cur.close()
c.close()
print("清理完成")
