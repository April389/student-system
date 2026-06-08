# ========================================
# 数据统计路由文件 routers/statistics.py
# 作用：使用 Pandas 进行成绩数据统计分析
# ========================================
#
# 技术栈说明：
#   Pandas 是 Python 的数据统计分析库
#   核心语法围绕二维表格数据结构（DataFrame）展开
#
#   DataFrame 就像一个 Excel 表格：
#     - 每一列（Column）代表一个字段（如：语文成绩、数学成绩）
#     - 每一行（Row）代表一条记录（如：一个学生的数据）
#
#   常用统计操作：
#     df.groupby()   —— 分组（如按班级分组）
#     df.mean()      —— 计算平均值
#     df.max()       —— 计算最大值
#     df.min()       —— 计算最小值
#     df.sum()       —— 计算总和
#     df.count()     —— 计算数量
#     df.describe()  —— 一次性输出所有统计指标
#
# REST API 接口规范：
#   URL 地址                        | HTTP 方法 | 作用
#   -------------------------------|----------|------------------
#   /api/statistics/overview        | GET      | 成绩总览统计
#   /api/statistics/class/{name}    | GET      | 按班级统计成绩
#   /api/statistics/ranking         | GET      | 成绩排名
# ========================================

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import SysUser, StudentInfo
from dependencies import get_current_user


# 创建统计路由器
router = APIRouter(prefix="/api/statistics", tags=["数据统计"])


# ========================================
# 工具函数：从数据库查询数据并转为 Pandas DataFrame
# ========================================
def get_students_dataframe(db: Session, class_name: Optional[str] = None) -> pd.DataFrame:
    """
    从数据库查询学生数据，转换为 Pandas 二维表格（DataFrame）

    参数：
        db: 数据库会话
        class_name: 可选，指定班级名称进行筛选

    返回：
        DataFrame 对象（二维表格数据结构）

    转换过程：
        MySQL 查询结果  →  Python 列表  →  Pandas DataFrame
        此时 DataFrame 就像一张 Excel 表格，可以用各种方法统计分析
    """
    # 构建查询
    query = (
        db.query(StudentInfo, SysUser)
        .join(SysUser, StudentInfo.user_id == SysUser.id)
    )

    # 如果指定了班级，添加筛选条件
    if class_name:
        query = query.filter(StudentInfo.class_name == class_name)

    results = query.all()

    if not results:
        return pd.DataFrame()

    # 将查询结果转为字典列表
    data = []
    for student, user in results:
        data.append({
            "student_no": student.student_no,       # 学号
            "real_name": user.real_name,             # 姓名
            "gender": student.gender,                # 性别
            "age": student.age,                      # 年龄
            "class_name": student.class_name,        # 班级
            "major": student.major,                  # 专业
            "chinese_score": student.chinese_score,  # 语文成绩
            "math_score": student.math_score,        # 数学成绩
            "english_score": student.english_score,  # 英语成绩
        })

    # 转换为 Pandas DataFrame（二维表格）
    df = pd.DataFrame(data)

    # 删除全为 NaN（空值）的成绩列，避免统计出错
    score_columns = ["chinese_score", "math_score", "english_score"]
    for col in score_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ========================================
# 接口一：成绩总览统计
# ========================================
# URL:    GET /api/statistics/overview
# 方法:   GET（读取数据）
# 功能:   使用 Pandas 对所有学生的成绩进行统计分析
# 权限:   需要登录
#
# 返回的统计指标：
#   - 各科平均分（df.mean()）
#   - 各科最高分（df.max()）
#   - 各科最低分（df.min()）
#   - 学生总人数（df.count()）
#   - 各班人数统计（df.groupby()）
@router.get("/overview", summary="成绩总览统计")
def get_statistics_overview(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    成绩总览统计

    使用 Pandas 进行以下统计分析：
      1. df.mean()     —— 计算各科平均分
      2. df.max()      —— 计算各科最高分
      3. df.min()      —— 计算各科最低分
      4. df.count()    —— 统计学生总人数
      5. df.groupby()  —— 按班级分组统计人数
    """
    # 获取所有学生数据的 DataFrame
    df = get_students_dataframe(db)

    if df.empty:
        return {"code": 200, "message": "暂无数据", "data": None}

    # --- 统计指标一：各科平均分 ---
    # df.mean(numeric_only=True) 会自动计算所有数值列的平均值
    score_cols = ["chinese_score", "math_score", "english_score"]
    available_cols = [c for c in score_cols if c in df.columns]

    averages = {}
    max_scores = {}
    min_scores = {}

    for col in available_cols:
        col_data = df[col].dropna()  # 去除空值
        if not col_data.empty:
            col_name_map = {
                "chinese_score": "语文",
                "math_score": "数学",
                "english_score": "英语"
            }
            cn_name = col_name_map.get(col, col)
            averages[cn_name] = round(float(col_data.mean()), 2)    # 平均分（保留2位小数）
            max_scores[cn_name] = int(col_data.max())               # 最高分
            min_scores[cn_name] = int(col_data.min())               # 最低分

    # --- 统计指标二：学生总人数 ---
    total_students = int(df.shape[0])  # df.shape[0] 是行数

    # --- 统计指标三：按班级分组统计人数 ---
    # df.groupby("class_name") 将数据按班级分组
    # .size() 计算每组有多少条记录
    # 关键修复：groupby 遇到 NaN 班级名会归到 "nan" 组，统计时过滤掉
    class_counts = {}
    if "class_name" in df.columns:
        grouped = df.groupby("class_name", dropna=True).size()
        class_counts = {str(k): int(v) for k, v in grouped.to_dict().items()}

    # --- 统计指标四：按性别分组统计 ---
    gender_counts = {}
    if "gender" in df.columns:
        grouped = df.groupby("gender", dropna=True).size()
        gender_counts = {str(k): int(v) for k, v in grouped.to_dict().items()}

    return {
        "code": 200,
        "message": "统计成功",
        "data": {
            "total_students": total_students,        # 学生总人数
            "averages": averages,                     # 各科平均分
            "max_scores": max_scores,                 # 各科最高分
            "min_scores": min_scores,                 # 各科最低分
            "class_counts": class_counts,             # 各班人数
            "gender_counts": gender_counts,           # 男女比例
        }
    }


# ========================================
# 接口二：按班级统计成绩
# ========================================
# URL:    GET /api/statistics/class/{class_name}
# 方法:   GET（读取数据）
# 功能:   对指定班级的成绩进行详细统计
# 权限:   需要登录
@router.get("/class/{class_name}", summary="按班级统计成绩")
def get_class_statistics(
    class_name: str,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    按班级统计成绩

    使用 Pandas 进行班级级别的统计分析：
      1. df.groupby("class_name")  —— 按班级分组
      2. df.describe()            —— 输出详细统计描述
      3. df.sort_values()         —— 成绩排序
    """
    df = get_students_dataframe(db, class_name=class_name)

    if df.empty:
        return {"code": 200, "message": "该班级暂无数据", "data": None}

    # 各科统计
    score_cols = ["chinese_score", "math_score", "english_score"]
    available_cols = [c for c in score_cols if c in df.columns]

    subject_stats = {}
    col_name_map = {
        "chinese_score": "语文",
        "math_score": "数学",
        "english_score": "英语"
    }

    for col in available_cols:
        col_data = df[col].dropna()
        if not col_data.empty:
            cn_name = col_name_map.get(col, col)
            subject_stats[cn_name] = {
                "average": round(float(col_data.mean()), 2),   # 平均分
                "max": int(col_data.max()),                     # 最高分
                "min": int(col_data.min()),                     # 最低分
                "count": int(col_data.count()),                 # 有成绩的人数
                "median": round(float(col_data.median()), 2),  # 中位数
            }

    # 计算每个学生的总分并排名
    # df.sum(axis=1) 对每一行的所有成绩列求和
    if available_cols:
        df["total_score"] = df[available_cols].sum(axis=1)
        # df.sort_values() 按总分从高到低排序
        df_sorted = df.sort_values("total_score", ascending=False)

        ranking = []
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            ranking.append({
                "rank": i,
                "student_no": row.get("student_no", ""),
                "real_name": row.get("real_name", ""),
                "chinese_score": int(row.get("chinese_score", 0)) if pd.notna(row.get("chinese_score")) else None,
                "math_score": int(row.get("math_score", 0)) if pd.notna(row.get("math_score")) else None,
                "english_score": int(row.get("english_score", 0)) if pd.notna(row.get("english_score")) else None,
                "total_score": int(row.get("total_score", 0)),
            })
    else:
        ranking = []

    return {
        "code": 200,
        "message": "统计成功",
        "data": {
            "class_name": class_name,
            "student_count": int(df.shape[0]),
            "subject_stats": subject_stats,
            "ranking": ranking,
        }
    }


# ========================================
# 接口三：成绩排名
# ========================================
# URL:    GET /api/statistics/ranking
# 方法:   GET（读取数据）
# 功能:   获取学生成绩排名
# 权限:   需要登录
@router.get("/ranking", summary="成绩排名")
def get_score_ranking(
    sort_by: str = Query("total", description="排序依据：total/math/chinese/english"),
    order: str = Query("desc", description="排序方式：desc=降序，asc=升序"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    成绩排名

    使用 Pandas 的排序功能：
      df.sort_values() —— 按指定列排序
    """
    df = get_students_dataframe(db)

    if df.empty:
        return {"code": 200, "message": "暂无数据", "data": None}

    score_cols = ["chinese_score", "math_score", "english_score"]
    available_cols = [c for c in score_cols if c in df.columns]

    # 计算总分
    # 关键修复：sum(axis=1) 在全 NaN 行会返回 NaN，JSON 无法序列化
    # 所以使用 skipna=True 跳 NaN，并用 min_count=1 要求至少有 1 个有效值才求和
    # 这样全 NaN 的行 total_score 仍是 NaN，后续逻辑可以过滤
    if available_cols:
        df["total_score"] = df[available_cols].sum(axis=1, skipna=True, min_count=1)

    # 确定排序列
    sort_col_map = {
        "total": "total_score",
        "math": "math_score",
        "chinese": "chinese_score",
        "english": "english_score",
    }
    sort_col = sort_col_map.get(sort_by, "total_score")

    if sort_col not in df.columns:
        sort_col = "total_score"

    # 过滤掉 total_score 为 NaN 的行（全空成绩的不能参与排名）
    if sort_col == "total_score":
        df = df.dropna(subset=["total_score"])
    else:
        # 单科排名时也要过滤该科为 NaN 的行
        df = df.dropna(subset=[sort_col])

    if df.empty:
        return {"code": 200, "message": "暂无有效数据", "data": []}

    # df.sort_values() 按指定列排序
    # ascending=False 表示降序（从大到小）
    ascending = (order == "asc")
    df_sorted = df.sort_values(sort_col, ascending=ascending).head(limit)

    # 关键修复：iterrows() 会保留 NaN 为 numpy.nan(float)，json.dumps 不接受 NaN
    # 在转 dict 前将所有 NaN 统一转为 None
    df_sorted = df_sorted.astype(object).where(pd.notnull(df_sorted), None)

    # 组装排名数据
    ranking = []
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        ranking.append({
            "rank": i,
            "student_no": row.get("student_no", ""),
            "real_name": row.get("real_name", ""),
            "class_name": row.get("class_name", "") or "",
            "chinese_score": int(row.get("chinese_score", 0)) if row.get("chinese_score") is not None else None,
            "math_score": int(row.get("math_score", 0)) if row.get("math_score") is not None else None,
            "english_score": int(row.get("english_score", 0)) if row.get("english_score") is not None else None,
            "total_score": int(row.get("total_score", 0)) if row.get("total_score") is not None else None,
        })

    return {
        "code": 200,
        "message": "排名查询成功",
        "data": ranking,
    }
