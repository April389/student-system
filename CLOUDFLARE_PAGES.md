# Cloudflare Pages - 学生管理系统前端部署说明
#
# 部署步骤（GitHub 关联后全自动）：
#   1. 登录 https://dash.cloudflare.com/
#   2. Workers & Pages → Create application → Pages → Connect to Git
#   3. 选择 April389/student-system 仓库
#   4. Build settings:
#        Production branch:   main
#        Build command:       （留空，纯静态文件）
#        Build output:        /static
#   5. 环境变量（可选，更灵活用 URL 参数 ?api_base_url=）：
#        API_BASE_URL  =  https://student-system-backend.fly.dev
#   6. Save and Deploy
#
# 部署完成后访问：
#   https://student-system-frontend.pages.dev/
#   https://student-system.pages.dev/  （可能名字冲突，要改）
#
# 如需绑定自定义域名：
#   Pages 项目 → Custom domains → Set up a custom domain
#
# 注意：
#   - 纯静态文件部署，不需要 build 步骤
#   - 唯一要求是后端 CORS 允许 *.pages.dev 域名（main.py 已经 allow_origins=["*"]，无需改）
