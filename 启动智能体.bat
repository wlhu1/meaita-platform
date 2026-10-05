@echo off
chcp 65001 >nul
title ME-AITA 教师成长智能体
cd /d "%~dp0"

echo ============================================
echo   ME-AITA 教师成长智能体 - 一键启动
echo   河南大学 · 本地部署版
echo ============================================
echo.

REM 1. 检查并创建虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [1/3] 首次运行，正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请确认已安装 Python 3.9+
        pause
        exit /b 1
    )
)

REM 2. 安装依赖
echo [2/3] 检查并安装依赖...
"venv\Scripts\python.exe" -m pip install -r requirements.txt -q

REM 3. 启动后端并在浏览器打开
echo [3/3] 启动后端服务...
start "" "http://127.0.0.1:8000"
"venv\Scripts\python.exe" backend\main.py

pause
