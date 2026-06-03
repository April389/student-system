#!/bin/bash
# ========================================
# Render 构建脚本 build.sh
# 在部署时自动执行，安装依赖
# ========================================

echo "=== 安装 Python 依赖 ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 构建完成 ==="
