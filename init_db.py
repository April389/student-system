# ========================================
# 数据库初始化脚本 init_db.py
# 作用：创建数据库表并插入初始数据（管理员账号、角色、权限）
# ========================================
#
# 运行方式：
#   1. 先在 MySQL 中创建数据库：
#      CREATE DATABASE student_system DEFAULT CHARACTER SET utf8mb4;
#
#   2. 然后运行此脚本：
#      python init_db.py
#
# 脚本会自动：
#   - 创建所有数据表（5张基础表 + 学生信息表）
#   - 插入默认角色（超级管理员、老师、学生）
#   - 插入默认权限（菜单权限和按钮权限）
#   - 创建管理员账号（admin/123456）
#   - 为角色分配权限
# ========================================

from database import engine, Base, SessionLocal
from models import SysUser, SysRole, SysPermission, SysUserRole, SysRolePermission
from auth import hash_password


def init_database():
    """初始化数据库"""

    # ========================================
    # 第一步：创建所有数据表
    # ========================================
    print("正在创建数据表...")
    Base.metadata.create_all(bind=engine)
    print("数据表创建完成！")

    # ========================================
    # 第二步：插入初始数据
    # ========================================
    db = SessionLocal()

    try:
        # --- 检查是否已有数据（避免重复插入）---
        if db.query(SysUser).count() > 0:
            print("数据库已有数据，跳过初始化。")
            return

        # ========================================
        # 插入角色数据（sys_role 表）
        # ========================================
        print("正在插入角色数据...")
        roles = [
            SysRole(role_name="超级管理员", role_code="admin", description="系统最高权限管理员"),
            SysRole(role_name="老师", role_code="teacher", description="教师角色，可管理学生信息和查看成绩"),
            SysRole(role_name="学生", role_code="student", description="学生角色，可查看自己的信息和成绩"),
        ]
        for role in roles:
            db.add(role)
        db.flush()  # flush 后角色对象会获得自增的 id

        # ========================================
        # 插入权限数据（sys_permission 表）
        # ========================================
        print("正在插入权限数据...")
        permissions = [
            # --- 学生管理权限 ---
            SysPermission(permission_name="查看学生列表", permission_code="student:list", permission_type="menu", description="查看学生信息列表页面"),
            SysPermission(permission_name="查看学生详情", permission_code="student:detail", permission_type="menu", description="查看学生详细信息"),
            SysPermission(permission_name="添加学生", permission_code="student:create", permission_type="button", description="添加新学生按钮"),
            SysPermission(permission_name="修改学生", permission_code="student:update", permission_type="button", description="修改学生信息按钮"),
            SysPermission(permission_name="删除学生", permission_code="student:delete", permission_type="button", description="删除学生按钮"),

            # --- 用户管理权限 ---
            SysPermission(permission_name="查看用户列表", permission_code="user:list", permission_type="menu", description="查看用户管理页面"),
            SysPermission(permission_name="管理用户", permission_code="user:manage", permission_type="button", description="用户管理操作"),

            # --- 数据统计权限 ---
            SysPermission(permission_name="查看数据统计", permission_code="statistics:view", permission_type="menu", description="查看成绩统计页面"),
        ]
        for perm in permissions:
            db.add(perm)
        db.flush()

        # ========================================
        # 为角色分配权限（sys_role_permission 关联表）
        # ========================================
        print("正在分配角色权限...")

        # 超级管理员：所有权限
        admin_role = db.query(SysRole).filter(SysRole.role_code == "admin").first()
        for perm in permissions:
            db.add(SysRolePermission(role_id=admin_role.id, permission_id=perm.id))

        # 老师：查看学生列表、查看详情、添加/修改学生、查看统计
        teacher_role = db.query(SysRole).filter(SysRole.role_code == "teacher").first()
        teacher_perms = ["student:list", "student:detail", "student:create", "student:update", "statistics:view"]
        for perm_code in teacher_perms:
            perm = db.query(SysPermission).filter(SysPermission.permission_code == perm_code).first()
            if perm:
                db.add(SysRolePermission(role_id=teacher_role.id, permission_id=perm.id))

        # 学生：查看学生列表、查看详情、查看统计
        student_role = db.query(SysRole).filter(SysRole.role_code == "student").first()
        student_perms = ["student:list", "student:detail", "statistics:view"]
        for perm_code in student_perms:
            perm = db.query(SysPermission).filter(SysPermission.permission_code == perm_code).first()
            if perm:
                db.add(SysRolePermission(role_id=student_role.id, permission_id=perm.id))

        # ========================================
        # 创建管理员账号（sys_user 表）
        # ========================================
        print("正在创建管理员账号...")
        admin_user = SysUser(
            username="admin",
            password=hash_password("123456"),  # 默认密码：123456（bcrypt 加密存储）
            real_name="系统管理员",
            email="admin@school.edu",
            status=1,
        )
        db.add(admin_user)
        db.flush()

        # 为管理员分配"超级管理员"角色
        db.add(SysUserRole(user_id=admin_user.id, role_id=admin_role.id))

        # ========================================
        # 提交所有数据
        # ========================================
        db.commit()
        print("=" * 50)
        print("数据库初始化完成！")
        print("=" * 50)
        print()
        print("默认管理员账号：")
        print("  用户名: admin")
        print("  密码:   123456")
        print()
        print("默认角色：超级管理员、老师、学生")
        print("默认权限：已自动分配给对应角色")
        print("=" * 50)

    except Exception as e:
        db.rollback()  # 出错时回滚所有操作
        print(f"初始化失败: {e}")
        raise
    finally:
        db.close()


# 直接运行此脚本时执行初始化
if __name__ == "__main__":
    init_database()
