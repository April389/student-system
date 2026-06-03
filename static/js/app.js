// ========================================
// 前端交互逻辑文件 app.js
// 作用：处理页面的交互和数据传递
// ========================================
//
// JavaScript 职责说明：
//   1. 负责页面的交互和数据传递
//      比如点击"查询"按钮后如何向后端 Python 发送请求
//   2. 表单提交前的数据校验
//   3. 动态更新页面上的学生列表
//
// 数据流向：
//   用户操作 HTML 页面  →  JavaScript 处理交互逻辑
//   →  调用 Axios（api.js）发送 HTTP 请求
//   →  HTTP 协议打包数据  →  TCP/IP 传输
//   →  到达 Python 后端（FastAPI）
//   →  返回 JSON 数据  →  JavaScript 更新 HTML 页面
// ========================================


// ========================================
// 第一部分：全局变量
// ========================================
let currentPage = 1;          // 当前学生列表页码
const pageSize = 10;          // 每页显示条数
let currentKeyword = '';      // 当前搜索关键词


// ========================================
// 第二部分：页面初始化
// ========================================
// DOMContentLoaded 事件：页面 HTML 加载完成后执行
// 检查用户是否已登录（本地是否有 Token）
document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (token) {
        // 有 Token，显示主界面
        showMainPage();
    } else {
        // 无 Token，显示登录页
        showLoginPage();
    }
});


// ========================================
// 第三部分：页面切换函数
// ========================================

/**
 * 显示登录页面
 * 隐藏主界面，显示登录表单
 */
function showLoginPage() {
    document.getElementById('login-page').classList.add('active');
    document.getElementById('main-page').classList.remove('active');
}

/**
 * 显示主界面
 * 隐藏登录页，显示系统主界面，并加载数据
 */
function showMainPage() {
    document.getElementById('login-page').classList.remove('active');
    document.getElementById('main-page').classList.add('active');

    // 显示当前用户名
    const userStr = localStorage.getItem('user');
    if (userStr) {
        try {
            const user = JSON.parse(userStr);
            document.getElementById('current-user-name').textContent = user.real_name || user.username;
        } catch (e) {
            // 解析失败忽略
        }
    }

    // 加载初始数据
    loadStudents();
    loadStatisticsOverview();
    loadUsers();
}

/**
 * 切换 Tab 页签
 * 点击左侧菜单时，切换右侧内容区域
 */
function switchTab(tabName, element) {
    // 移除所有菜单项的 active 状态
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
    });
    // 给当前点击的菜单项添加 active
    element.classList.add('active');

    // 隐藏所有 Tab 内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    // 显示目标 Tab
    const targetTab = document.getElementById('tab-' + tabName);
    if (targetTab) {
        targetTab.classList.add('active');
    }

    // 切换到对应页面时刷新数据
    if (tabName === 'statistics') {
        loadStatisticsOverview();
    } else if (tabName === 'user-manage') {
        loadUsers();
    } else if (tabName === 'student-list') {
        loadStudents();
    }
}


// ========================================
// 第四部分：登录与退出
// ========================================

/**
 * 处理登录操作
 *
 * 流程：
 *   1. 获取用户输入的用户名和密码
 *   2. 前端表单校验（非空检查）
 *   3. 调用 API.login() 发送 POST 请求到后端
 *   4. 登录成功：将 Token 存储到 localStorage
 *   5. 跳转到主界面
 *   6. 登录失败：显示错误提示
 */
async function handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();

    // 前端表单校验
    if (!username) {
        showToast('请输入用户名', 'error');
        return;
    }
    if (!password) {
        showToast('请输入密码', 'error');
        return;
    }

    try {
        // 调用 Axios 发送登录请求
        // POST /api/auth/login
        const response = await API.login(username, password);
        const data = response.data;

        // 登录成功：存储 Token 到 localStorage
        // Token 就是后端发的"电子通行证"
        // 后续每次请求都会通过 Axios 拦截器自动携带
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));

        showToast('登录成功！', 'success');

        // 清空登录表单
        document.getElementById('login-username').value = '';
        document.getElementById('login-password').value = '';

        // 显示主界面
        showMainPage();

    } catch (error) {
        // 登录失败
        const detail = error.response?.data?.detail || '登录失败';
        showToast(detail, 'error');
    }
}

/**
 * 处理退出登录
 * 清除本地存储的 Token 和用户信息，返回登录页
 */
function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showLoginPage();
    showToast('已退出登录', 'info');
}


// ========================================
// 第五部分：学生列表（CRUD - Read）
// ========================================

/**
 * 加载学生列表数据
 * 调用后端 GET /api/students 接口获取数据并渲染表格
 */
async function loadStudents(page) {
    if (page) currentPage = page;

    try {
        const response = await API.getStudents(currentPage, pageSize, currentKeyword);
        const data = response.data;

        renderStudentTable(data.data || []);
        renderPagination(data.total || 0, data.page || 1, data.page_size || pageSize);

    } catch (error) {
        // 请求失败时由 Axios 拦截器统一处理
    }
}

/**
 * 渲染学生表格
 * 将后端返回的数据填充到 HTML 表格中
 */
function renderStudentTable(students) {
    const tbody = document.getElementById('student-table-body');

    if (!students || students.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty-tip">暂无学生数据</td></tr>';
        return;
    }

    let html = '';
    students.forEach(s => {
        html += `
            <tr>
                <td>${s.student_no || '-'}</td>
                <td>${s.real_name || '-'}</td>
                <td>${s.gender || '-'}</td>
                <td>${s.age || '-'}</td>
                <td>${s.class_name || '-'}</td>
                <td>${s.major || '-'}</td>
                <td>${s.chinese_score != null ? s.chinese_score : '-'}</td>
                <td>${s.math_score != null ? s.math_score : '-'}</td>
                <td>${s.english_score != null ? s.english_score : '-'}</td>
                <td>
                    <button class="btn btn-edit" onclick="openEditModal(${s.id})">编辑</button>
                    <button class="btn btn-delete" onclick="handleDeleteStudent(${s.id}, '${s.real_name}')">删除</button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

/**
 * 渲染分页控件
 */
function renderPagination(total, page, pageSize) {
    const container = document.getElementById('student-pagination');
    const totalPages = Math.ceil(total / pageSize);

    if (totalPages <= 1) {
        container.innerHTML = `<span class="page-info">共 ${total} 条记录</span>`;
        return;
    }

    let html = '';
    html += `<button ${page <= 1 ? 'disabled' : ''} onclick="loadStudents(${page - 1})">上一页</button>`;

    for (let i = 1; i <= totalPages && i <= 7; i++) {
        html += `<button class="${i === page ? 'active' : ''}" onclick="loadStudents(${i})">${i}</button>`;
    }

    html += `<button ${page >= totalPages ? 'disabled' : ''} onclick="loadStudents(${page + 1})">下一页</button>`;
    html += `<span class="page-info">共 ${total} 条 / ${totalPages} 页</span>`;

    container.innerHTML = html;
}

/**
 * 搜索学生
 */
function searchStudents() {
    currentKeyword = document.getElementById('search-keyword').value.trim();
    currentPage = 1;
    loadStudents();
}

/**
 * 重置搜索
 */
function resetSearch() {
    document.getElementById('search-keyword').value = '';
    currentKeyword = '';
    currentPage = 1;
    loadStudents();
}


// ========================================
// 第六部分：添加学生（CRUD - Create）
// ========================================

/**
 * 处理添加学生
 *
 * 流程：
 *   1. 获取表单数据
 *   2. 前端数据校验
 *   3. 调用 API.addStudent() 发送 POST 请求
 *   4. 成功后刷新学生列表
 */
async function handleAddStudent() {
    // 收集表单数据
    const data = {
        username: document.getElementById('add-username').value.trim(),
        password: document.getElementById('add-password').value.trim(),
        real_name: document.getElementById('add-real-name').value.trim(),
        student_no: document.getElementById('add-student-no').value.trim(),
        gender: document.getElementById('add-gender').value,
        age: parseInt(document.getElementById('add-age').value) || null,
        class_name: document.getElementById('add-class-name').value.trim() || null,
        major: document.getElementById('add-major').value.trim() || null,
        grade: document.getElementById('add-grade').value.trim() || null,
        enrollment_date: document.getElementById('add-enrollment-date').value || null,
        chinese_score: parseInt(document.getElementById('add-chinese-score').value) || null,
        math_score: parseInt(document.getElementById('add-math-score').value) || null,
        english_score: parseInt(document.getElementById('add-english-score').value) || null,
    };

    // 前端校验：必填字段
    if (!data.username) { showToast('请输入用户名', 'error'); return; }
    if (!data.password) { showToast('请输入密码', 'error'); return; }
    if (!data.real_name) { showToast('请输入真实姓名', 'error'); return; }
    if (!data.student_no) { showToast('请输入学号', 'error'); return; }

    try {
        await API.addStudent(data);
        showToast('学生添加成功！', 'success');
        resetAddForm();
        loadStudents();  // 刷新列表
    } catch (error) {
        // 错误由 Axios 拦截器处理
    }
}

/**
 * 重置添加表单
 */
function resetAddForm() {
    document.getElementById('add-student-form').querySelectorAll('input, select').forEach(el => {
        el.value = '';
    });
}


// ========================================
// 第七部分：编辑学生（CRUD - Update）
// ========================================

/**
 * 打开编辑弹窗
 * 先获取学生详情，填充到编辑表单中
 */
async function openEditModal(studentId) {
    try {
        const response = await API.getStudentDetail(studentId);
        const s = response.data.data;

        // 填充表单数据
        document.getElementById('edit-student-id').value = s.id;
        document.getElementById('edit-real-name').value = s.real_name || '';
        document.getElementById('edit-gender').value = s.gender || '';
        document.getElementById('edit-age').value = s.age || '';
        document.getElementById('edit-class-name').value = s.class_name || '';
        document.getElementById('edit-major').value = s.major || '';
        document.getElementById('edit-grade').value = s.grade || '';
        document.getElementById('edit-chinese-score').value = s.chinese_score || '';
        document.getElementById('edit-math-score').value = s.math_score || '';
        document.getElementById('edit-english-score').value = s.english_score || '';

        // 显示弹窗
        document.getElementById('edit-modal').style.display = 'flex';

    } catch (error) {
        // 错误由拦截器处理
    }
}

/**
 * 关闭编辑弹窗
 */
function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
}

/**
 * 保存编辑
 * 只发送修改了的字段（PUT 请求）
 */
async function handleEditStudent() {
    const studentId = document.getElementById('edit-student-id').value;

    // 收集表单数据
    const data = {};
    const realName = document.getElementById('edit-real-name').value.trim();
    const gender = document.getElementById('edit-gender').value;
    const age = document.getElementById('edit-age').value;
    const className = document.getElementById('edit-class-name').value.trim();
    const major = document.getElementById('edit-major').value.trim();
    const grade = document.getElementById('edit-grade').value.trim();
    const chineseScore = document.getElementById('edit-chinese-score').value;
    const mathScore = document.getElementById('edit-math-score').value;
    const englishScore = document.getElementById('edit-english-score').value;

    if (realName) data.real_name = realName;
    if (gender !== '') data.gender = gender;
    if (age) data.age = parseInt(age);
    if (className) data.class_name = className;
    if (major) data.major = major;
    if (grade) data.grade = grade;
    if (chineseScore) data.chinese_score = parseInt(chineseScore);
    if (mathScore) data.math_score = parseInt(mathScore);
    if (englishScore) data.english_score = parseInt(englishScore);

    try {
        await API.updateStudent(studentId, data);
        showToast('修改成功！', 'success');
        closeEditModal();
        loadStudents();  // 刷新列表
    } catch (error) {
        // 错误由拦截器处理
    }
}


// ========================================
// 第八部分：删除学生（CRUD - Delete）
// ========================================

/**
 * 处理删除学生
 * 先确认，再调用 DELETE 接口
 */
async function handleDeleteStudent(studentId, studentName) {
    // 确认对话框
    if (!confirm(`确定要删除学生「${studentName}」吗？此操作不可恢复！`)) {
        return;
    }

    try {
        await API.deleteStudent(studentId);
        showToast('删除成功！', 'success');
        loadStudents();  // 刷新列表
    } catch (error) {
        // 错误由拦截器处理
    }
}


// ========================================
// 第九部分：数据统计（Pandas 统计结果展示）
// ========================================

/**
 * 加载成绩总览统计
 * 调用 GET /api/statistics/overview
 * 后端使用 Pandas 计算各科平均分、最高分等
 */
async function loadStatisticsOverview() {
    try {
        const response = await API.getStatisticsOverview();
        const data = response.data.data;

        if (!data) {
            document.getElementById('stats-overview').innerHTML = '<p class="empty-tip">暂无统计数据</p>';
            return;
        }

        let html = '';

        // 学生总人数卡片
        html += `
            <div class="stat-card">
                <div class="stat-label">学生总人数</div>
                <div class="stat-value">${data.total_students}</div>
            </div>
        `;

        // 各科平均分卡片
        if (data.averages) {
            for (const [subject, avg] of Object.entries(data.averages)) {
                const maxScore = data.max_scores?.[subject] || '-';
                const minScore = data.min_scores?.[subject] || '-';
                html += `
                    <div class="stat-card">
                        <div class="stat-label">${subject}平均分</div>
                        <div class="stat-value">${avg}</div>
                        <div class="stat-sub">最高 ${maxScore} / 最低 ${minScore}</div>
                    </div>
                `;
            }
        }

        // 班级人数统计
        if (data.class_counts && Object.keys(data.class_counts).length > 0) {
            html += `
                <div class="stat-card">
                    <div class="stat-label">班级数量</div>
                    <div class="stat-value">${Object.keys(data.class_counts).length}</div>
                    <div class="stat-sub">${Object.entries(data.class_counts).map(([k, v]) => k + ':' + v + '人').join(' ')}</div>
                </div>
            `;

            // 填充班级下拉框
            const select = document.getElementById('stats-class-select');
            select.innerHTML = '<option value="">选择班级查看统计</option>';
            for (const className of Object.keys(data.class_counts)) {
                select.innerHTML += `<option value="${className}">${className} (${data.class_counts[className]}人)</option>`;
            }
        }

        document.getElementById('stats-overview').innerHTML = html;

    } catch (error) {
        // 错误由拦截器处理
    }
}

/**
 * 加载班级详细统计
 * 选择班级后，调用 GET /api/statistics/class/{name}
 */
async function loadClassStatistics() {
    const className = document.getElementById('stats-class-select').value;

    if (!className) {
        document.getElementById('stats-class-detail').style.display = 'none';
        return;
    }

    try {
        const response = await API.getClassStatistics(className);
        const data = response.data.data;

        if (!data) return;

        document.getElementById('stats-class-detail').style.display = 'block';
        document.getElementById('stats-class-title').textContent = `${className} 成绩统计`;

        // 渲染各科统计
        let statsHtml = '';
        if (data.subject_stats) {
            for (const [subject, stats] of Object.entries(data.subject_stats)) {
                statsHtml += `
                    <div class="stat-card">
                        <div class="stat-label">${subject}</div>
                        <div class="stat-value">${stats.average}</div>
                        <div class="stat-sub">最高 ${stats.max} / 最低 ${stats.min} / 中位数 ${stats.median}</div>
                    </div>
                `;
            }
        }
        statsHtml += `
            <div class="stat-card">
                <div class="stat-label">班级人数</div>
                <div class="stat-value">${data.student_count}</div>
            </div>
        `;
        document.getElementById('stats-class-info').innerHTML = statsHtml;

        // 渲染排名表格
        let rankHtml = '';
        if (data.ranking) {
            data.ranking.forEach(r => {
                rankHtml += `
                    <tr>
                        <td>${r.rank}</td>
                        <td>${r.student_no || '-'}</td>
                        <td>${r.real_name || '-'}</td>
                        <td>${r.chinese_score != null ? r.chinese_score : '-'}</td>
                        <td>${r.math_score != null ? r.math_score : '-'}</td>
                        <td>${r.english_score != null ? r.english_score : '-'}</td>
                        <td>${r.total_score || '-'}</td>
                    </tr>
                `;
            });
        }
        document.getElementById('stats-ranking-body').innerHTML = rankHtml || '<tr><td colspan="7" class="empty-tip">暂无数据</td></tr>';

    } catch (error) {
        // 错误由拦截器处理
    }
}


// ========================================
// 第十部分：用户管理
// ========================================

/**
 * 加载用户列表
 */
async function loadUsers() {
    const keyword = document.getElementById('user-search-keyword')?.value.trim() || '';

    try {
        const response = await API.getUsers(1, 50, keyword);
        const data = response.data;

        const tbody = document.getElementById('user-table-body');

        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-tip">暂无用户数据</td></tr>';
            return;
        }

        let html = '';
        data.data.forEach(u => {
            const statusText = u.status === 1 ? '正常' : '已禁用';
            const statusClass = u.status === 1 ? 'style="color:#52c41a"' : 'style="color:#e74c3c"';
            const toggleText = u.status === 1 ? '禁用' : '启用';
            const roles = (u.roles || []).join(', ') || '未分配';

            html += `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td>${u.real_name || '-'}</td>
                    <td>${u.email || '-'}</td>
                    <td>${u.phone || '-'}</td>
                    <td>${roles}</td>
                    <td ${statusClass}>${statusText}</td>
                    <td>
                        <button class="btn btn-small btn-default" onclick="handleToggleUserStatus(${u.id}, ${u.status === 1 ? 0 : 1})">${toggleText}</button>
                        <button class="btn btn-small btn-danger" onclick="handleResetPassword(${u.id}, '${u.username}')">重置密码</button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

    } catch (error) {
        // 错误由拦截器处理
    }
}

/**
 * 搜索用户
 */
function searchUsers() {
    loadUsers();
}

/**
 * 切换用户状态（启用/禁用）
 */
async function handleToggleUserStatus(userId, newStatus) {
    const action = newStatus === 1 ? '启用' : '禁用';
    if (!confirm(`确定要${action}该用户吗？`)) return;

    try {
        await API.updateUserStatus(userId, newStatus);
        showToast(`${action}成功`, 'success');
        loadUsers();
    } catch (error) {
        // 错误由拦截器处理
    }
}

/**
 * 重置用户密码
 */
async function handleResetPassword(userId, username) {
    const newPassword = prompt(`请输入用户「${username}」的新密码（至少6位）：`);
    if (!newPassword) return;
    if (newPassword.length < 6) {
        showToast('密码至少6位', 'error');
        return;
    }

    try {
        await API.resetPassword(userId, newPassword);
        showToast('密码重置成功', 'success');
    } catch (error) {
        // 错误由拦截器处理
    }
}


// ========================================
// 第十一部分：工具函数
// ========================================

/**
 * 显示提示信息（Toast）
 * 在页面右上角弹出消息提示
 *
 * @param {string} message - 提示文字
 * @param {string} type - 类型：success/error/info
 */
function showToast(message, type) {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type || 'info'}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    // 3秒后自动消失
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
