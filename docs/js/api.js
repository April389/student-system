// ========================================
// API 请求封装文件 api.js
// 作用：使用 Axios 连接前后端，发送 HTTP 请求
// ========================================
//
// Axios 说明：
//   Axios 是一个基于 Promise 的 HTTP 请求库
//   用于在前端发送请求到后端 Python（FastAPI）
//
//   工作流程：
//     用户操作页面  →  JavaScript 调用 Axios 发送 HTTP 请求
//     →  HTTP 协议打包数据（贴标签：读还是存）
//     →  TCP/IP 协议传输到后端
//     →  FastAPI 接收并处理
//     →  返回 JSON 数据
//     →  Axios 接收响应并更新页面
//
// 请求拦截器说明：
//   配置请求拦截器，在每次发请求时
//   自动把后端发的 Token 塞进 HTTP 请求头（Header）里
//   格式：Authorization: Bearer eyJhbGciOi...
//   这样后端就能通过 Token 识别用户身份
// ========================================


// ========================================
// 第一部分：创建 Axios 实例并配置基础参数
// ========================================
// axios.create() 创建一个自定义的 Axios 实例
// 可以设置统一的配置（如基础 URL、超时时间等）

// 后端地址优先级（由高到低）：
//   1. window.API_BASE_URL    —— 运行时注入（Cloudflare Pages 可在 index.html 里动态设）
//   2. localStorage('api_base_url')  —— 用户在浏览器里手改
//   3. 相对路径 ''     —— 同域部署（后端和前端一个域名）
const _apiBaseURL = (function () {
    if (typeof window !== 'undefined' && window.API_BASE_URL) {
        return window.API_BASE_URL.replace(/\/+$/, '');  // 去掉末尾斜杠
    }
    try {
        const stored = localStorage.getItem('api_base_url');
        if (stored) return stored.replace(/\/+$/, '');
    } catch (e) { /* localStorage 不可用时忽略 */ }
    return '';  // 默认同域部署
})();

const api = axios.create({
    // baseURL: 后端 API 的根地址
    //   本地同域：http://127.0.0.1:8000
    //   独立部署：window.API_BASE_URL = "https://student-system.fly.dev"
    //   Cloudflare Pages + fly.io 独立部署场景下，通过 index.html 里的 <script> 注入
    baseURL: _apiBaseURL,

    // timeout: 请求超时时间（毫秒）
    // 超过 10 秒没响应就视为请求失败
    timeout: 10000,

    // headers: 默认请求头
    // Content-Type 告诉后端发送的数据格式是 JSON
    headers: {
        'Content-Type': 'application/json'
    }
});


// ========================================
// 第二部分：请求拦截器（自动携带 Token）
// ========================================
// 请求拦截器会在每次发送请求之前自动执行
// 主要作用：从本地存储中取出 Token，塞进请求头
//
// 原理：
//   用户登录成功后，后端返回 JWT Token
//   前端将 Token 存储在 localStorage 中
//   每次发送请求时，拦截器自动从 localStorage 取出 Token
//   放入请求头的 Authorization 字段
//   格式：Authorization: Bearer <token>
api.interceptors.request.use(
    function (config) {
        // 从 localStorage 中获取 Token
        const token = localStorage.getItem('token');

        // 如果 Token 存在，就添加到请求头中
        if (token) {
            // Bearer 是 HTTP 认证方案的标准前缀
            // 后端 FastAPI 的 HTTPBearer 会自动解析这个值
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        return config;  // 返回修改后的配置，继续发送请求
    },
    function (error) {
        // 请求配置出错时的处理
        return Promise.reject(error);
    }
);


// ========================================
// 第三部分：响应拦截器（统一处理错误）
// ========================================
// 响应拦截器会在收到后端响应后自动执行
// 主要作用：统一处理 HTTP 错误（如 401 未登录、403 无权限等）
api.interceptors.response.use(
    function (response) {
        // 请求成功（HTTP 状态码 2xx）
        return response;
    },
    function (error) {
        // 请求失败时的处理
        if (error.response) {
            const status = error.response.status;

            switch (status) {
                case 401:
                    // 401 未授权：Token 过期或无效
                    // 清除本地 Token，跳转到登录页
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    showLoginPage();
                    showToast('登录已过期，请重新登录', 'error');
                    break;

                case 403:
                    // 403 禁止访问：权限不足
                    showToast('权限不足，无法执行此操作', 'error');
                    break;

                case 404:
                    // 404 未找到：请求的资源不存在
                    showToast('请求的资源不存在', 'error');
                    break;

                case 422:
                    // 422 数据校验失败：Pydantic 校验不通过
                    const detail = error.response.data?.detail;
                    if (Array.isArray(detail)) {
                        // Pydantic 返回的校验错误列表
                        const msg = detail.map(d => d.msg).join(', ');
                        showToast(`数据格式错误: ${msg}`, 'error');
                    } else {
                        showToast(detail || '数据校验失败', 'error');
                    }
                    break;

                case 500:
                    // 500 服务器内部错误
                    showToast('服务器内部错误', 'error');
                    break;

                default:
                    showToast(`请求失败 (${status})`, 'error');
            }
        } else {
            // 网络错误（后端未启动或网络断开）
            showToast('网络错误，请检查后端服务是否启动', 'error');
        }

        return Promise.reject(error);
    }
);


// ========================================
// 第四部分：封装具体的 API 请求函数
// ========================================
// 将每个后端接口封装成一个函数，方便在 app.js 中调用
// 每个函数对应一个 REST API 接口

const API = {

    // --- 认证相关接口 ---

    // 用户登录
    // POST /api/auth/login
    // 发送用户名和密码，返回 JWT Token
    login: function(username, password) {
        return api.post('/api/auth/login', {
            username: username,
            password: password
        });
    },

    // 获取当前登录用户信息
    // GET /api/auth/me
    getMe: function() {
        return api.get('/api/auth/me');
    },

    // --- 学生管理接口 ---

    // 查询学生列表（分页 + 搜索）
    // GET /api/students?page=1&page_size=10&keyword=xxx
    getStudents: function(page, pageSize, keyword) {
        const params = { page: page, page_size: pageSize };
        if (keyword) params.keyword = keyword;
        return api.get('/api/students', { params: params });
    },

    // 查询单个学生详情
    // GET /api/students/{id}
    getStudentDetail: function(id) {
        return api.get(`/api/students/${id}`);
    },

    // 添加新学生
    // POST /api/students
    // 请求体为 JSON 格式的学生数据
    addStudent: function(data) {
        return api.post('/api/students', data);
    },

    // 修改学生信息
    // PUT /api/students/{id}
    updateStudent: function(id, data) {
        return api.put(`/api/students/${id}`, data);
    },

    // 删除学生
    // DELETE /api/students/{id}
    deleteStudent: function(id) {
        return api.delete(`/api/students/${id}`);
    },

    // --- 数据统计接口 ---

    // 获取成绩总览统计
    // GET /api/statistics/overview
    getStatisticsOverview: function() {
        return api.get('/api/statistics/overview');
    },

    // 获取指定班级的成绩统计
    // GET /api/statistics/class/{class_name}
    getClassStatistics: function(className) {
        return api.get(`/api/statistics/class/${encodeURIComponent(className)}`);
    },

    // 获取成绩排名
    // GET /api/statistics/ranking
    getRanking: function(sortBy, order, limit) {
        return api.get('/api/statistics/ranking', {
            params: { sort_by: sortBy, order: order, limit: limit }
        });
    },

    // --- 用户管理接口 ---

    // 获取用户列表
    // GET /api/users
    getUsers: function(page, pageSize, keyword) {
        const params = { page: page, page_size: pageSize };
        if (keyword) params.keyword = keyword;
        return api.get('/api/users', { params: params });
    },

    // 启用/禁用用户
    // PUT /api/users/{id}/status
    updateUserStatus: function(id, status) {
        return api.put(`/api/users/${id}/status`, { status: status });
    },

    // 重置用户密码
    // PUT /api/users/{id}/password
    resetPassword: function(id, newPassword) {
        return api.put(`/api/users/${id}/password`, { new_password: newPassword });
    },
};
