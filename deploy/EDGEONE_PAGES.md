# EdgeOne Pages 部署说明 - 学生管理系统前端

## 部署步骤

### 第 1 步：注册 EdgeOne
1. 打开 https://edgeone.ai/
2. 右上角 "免费开始" → 用微信/QQ/手机号扫码注册
3. **不需要绑信用卡**

### 第 2 步：创建 Pages 项目
1. 登录后进入控制台
2. 左侧菜单选 "Pages" → "创建项目"
3. 选 "导入 Git 仓库" → 授权 GitHub
4. 选 `April389/student-system` 仓库
5. 配置：
   - 项目名称：`student-system-frontend`
   - 框架预设：**无（Other）** 或 **Static Site**
   - 根目录：留空
   - **构建命令**：留空（纯静态文件，无需 build）
   - **构建输出目录**：`static` ⬅️ 关键！
   - 分支：`main`

### 第 3 步：环境变量（可选）
在 "环境变量" 标签添加：
- 变量名：`API_BASE_URL`
- 值：`http://120.27.17.52`

> 这只是兜底，**实际生效靠 URL 参数**，因为 index.html 里的脚本会优先读 `?api_base_url=`

### 第 4 步：部署
- 点 "开始部署"
- 等 1-3 分钟，看到 ✅ "部署成功" 即可

### 第 5 步：访问

部署成功后访问（实际域名以控制台显示为准）：
- `https://student-system-frontend.edgeone.app/`
- `https://student-system-frontend-xxxx.edgeone.app/`

**带后端地址的访问方式**（推荐）：
```
https://your-domain.edgeone.app/?api_base_url=http://120.27.17.52
```
这一访问后，URL 参数会被存到 localStorage，后续访问都不需要再加。

## CORS 注意事项
- EdgeOne Pages 默认 `*.edgeone.app` 域名
- 后端 CORS 配置 `allow_origins=["*"]` 已经允许跨域，无需改

## 验证清单
- [ ] 打开前端 URL 能看到登录页
- [ ] 输入 admin / 123456 能登录
- [ ] 能看到学生列表
- [ ] 浏览器 F12 → Network → 看请求是不是发到 120.27.17.52

## 常见问题

### Q1: 部署后打开是空白页？
- 检查 Build output 是不是 `static`（不是 `/static`）
- 检查仓库 `static` 目录里有没有 `index.html`

### Q2: 登录提示 "网络错误"？
- 浏览器直接访问 `http://120.27.17.52/docs` 验证后端能不能开
- 检查后端 uvicorn 进程：`systemctl status student-system`
- 检查防火墙：阿里云安全组是否放行 80/443 端口（**这个必须配置**）

### Q3: 登录提示 CORS 错误？
- main.py 第 91 行已经是 `allow_origins=["*"]`，不应该出错
- 如果出错，把后端 CORS 改成 `allow_origins=["https://your-domain.edgeone.app"]`

## 阿里云安全组放行（必须）
阿里云轻量应用服务器默认只放行 22/80/443，但 80/443 可能要手动加：
1. 阿里云控制台 → 轻量应用服务器 → 实例 → 防火墙
2. 添加规则：
   - 端口 80，协议 TCP，源 0.0.0.0/0
   - 端口 443，协议 TCP，源 0.0.0.0/0
3. 保存
