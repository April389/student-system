# 阿里云轻量服务器部署指南
**目标服务器：120.27.17.52**（华北 1 青岛）

## 步骤 0：服务器初始化（控制台操作）

1. **重置密码**：阿里云控制台 → 轻量应用服务器 → 实例 → 重置密码
   - 用户名：`root`
   - 密码：自定义（**记住它**）
2. **配置防火墙**：实例 → 防火墙 → 添加规则
   - 端口 22（SSH）— 默认就有
   - 端口 80（HTTP）— 手动加
   - 端口 443（HTTPS）— 手动加
3. **绑定公网 IP**：确认实例有公网 IP（已提供：120.27.17.52）

## 步骤 1：本地 SSH 连接（PowerShell）

打开 PowerShell：
```powershell
ssh root@120.27.17.52
# 第一次连接会问 yes/no，输入 yes
# 然后输入密码（输入时不会显示）
```

**成功标志**：看到 `root@xxx:~#` 提示符

**如果 SSH 连不上**：
- 检查阿里云安全组是否放行 22 端口
- 检查轻量服务器防火墙是否放行 22
- 确认密码正确（重新重置一次）

## 步骤 2：上传部署脚本

**方式 A（推荐）：用 scp 从本地上传**
```powershell
# 在本地 PowerShell（不是 SSH 后的）
cd d:\19027\Documents\学生管理系统后端开发
scp deploy\deploy_aliyun.sh root@120.27.17.52:/root/
```

**方式 B：在服务器上直接下载**
```bash
# SSH 进服务器后
curl -fsSL -o /root/deploy_aliyun.sh https://raw.githubusercontent.com/April389/student-system/main/deploy/deploy_aliyun.sh
# ⚠️ 这一步需要你先把代码 push 到 GitHub（见步骤 3）
```

## 步骤 3：把代码 push 到 GitHub

**先在你本地 PowerShell**（不是 SSH 后的）：

```powershell
cd d:\19027\Documents\学生管理系统后端开发
git add -A
git status              # 看改了什么
git commit -m "feat: 阿里云部署脚本（deploy_aliyun.sh + systemd + nginx）"
git push origin main
```

**如果 push 失败**：参考之前 GitHub 网络问题，可能需要 VPN 或换网络。

## 步骤 4：执行部署（SSH 进去后）

```bash
# 1. 给脚本加执行权限
chmod +x /root/deploy_aliyun.sh

# 2. 执行部署（耗时 8-15 分钟）
bash /root/deploy_aliyun.sh
```

**部署过程会看到**：
```
[1/9] 更新系统...
[2/9] 安装基础工具...
[3/9] 安装 Python 3.10...
[4/9] 安装 MySQL 8...
[5/9] 配置 MySQL...
[6/9] 创建应用用户...
[7/9] 拉取 GitHub 代码...
[8/9] 启动 systemd 服务...
[9/9] 配置 nginx...
🎉 部署完成！
```

**关键保存**：部署完成后立刻查看数据库密码
```bash
cat /root/.db_password
```

## 步骤 5：验证后端

部署完成后在本地浏览器打开：
```
http://120.27.17.52/docs
```

**应该看到**：FastAPI Swagger UI 文档页面

**测试登录**（在 Swagger 页 `/api/auth/login` 接口）：
- 用户名：`admin`
- 密码：`123456`

## 步骤 6：部署前端（EdgeOne Pages）

参考 `deploy/EDGEONE_PAGES.md` 文件，**简版**：
1. 打开 https://edgeone.ai/ 注册
2. Pages → 导入 Git → 选 student-system
3. Build output 填 `static`
4. 部署
5. 访问：`https://xxx.edgeone.app/?api_base_url=http://120.27.17.52`

## 部署后管理命令速查（SSH 进去后用）

```bash
# 服务管理
systemctl status student-system     # 看状态
systemctl restart student-system    # 重启
systemctl stop student-system       # 停止
journalctl -u student-system -f     # 实时日志
journalctl -u student-system -n 100 # 最近 100 条日志

# 数据库
mysql -u student_app -p student_system
# 输入 /root/.db_password 里的密码

# 文件位置
/home/student/app/          # 项目代码
/home/student/app/.env      # 环境变量（含密钥）
/var/log/student-system/    # 日志
/root/.db_password          # 数据库密码

# 更新代码（你 push 到 GitHub 后）
cd /home/student/app && sudo -u student git pull
systemctl restart student-system

# 看 nginx 错误
tail -f /var/log/nginx/error.log
```

## 故障排查

### 后端启动失败
```bash
journalctl -u student-system -n 50 --no-pager
```
最常见原因：
- 数据库密码错（重新跑 deploy_aliyun.sh 即可）
- 端口 8000 被占：`lsof -i :8000` 看谁在用

### 前端访问后端超时
- 浏览器直接访问 `http://120.27.17.52/docs` 验证后端 OK
- 检查阿里云防火墙 80 端口是否放行
- 检查 nginx 状态：`systemctl status nginx`

### 数据库连不上
```bash
sudo -u student_app mysql -h 127.0.0.1 -u student_app -p student_system
# 输 /root/.db_password 里的密码
```

## 完整时间预估

| 步骤 | 时间 | 难度 |
|------|------|------|
| 注册阿里云 + 学生认证 | 5 分钟 | ⭐ |
| 买 0 元服务器 | 3 分钟 | ⭐ |
| 改 root 密码 + 配防火墙 | 3 分钟 | ⭐ |
| SSH 连接 | 1 分钟 | ⭐ |
| Git push | 1 分钟 | ⭐ |
| 跑部署脚本 | 15 分钟 | ⭐⭐ |
| EdgeOne Pages 部署前端 | 5 分钟 | ⭐ |
| **总计** | **~35 分钟** | — |
