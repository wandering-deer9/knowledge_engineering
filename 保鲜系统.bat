@echo off
chcp 65001 >nul
title 一键启动全宇宙保鲜系统 - 专为 knowledge_engineering 定制
color 0A

echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║      全宇宙最强保鲜系统 启动中...        ║
echo  ║   扔CSV到 import 文件夹 → 10秒自动更新    ║
echo  ║        git push 也行，全都能吃！         ║
echo  ╚═══════════════════════════════════════════╝
echo.

:: 1. 启动 Neo4j 服务
echo [1/3] 正在后台启动 Neo4j 服务...
start "" neo4j start
timeout /t 12 >nul

:: 2. 启动 Webhook 服务器（接收 GitHub push）
echo [2/3] 启动 Webhook 监听服务器...
cd /d "%~dp0scripts"
start "" /min python webhook_server.py

:: 3. 启动 ngrok 公网隧道
echo [3/3] 启动 ngrok 公网隧道...
start "" /min "%~dp0ngrok.exe" http 5000

echo.
echo  ██████████████████████████ 全部启动成功！██████████████████████████
echo.
echo     知识图谱实时地址（点一下就到）：
echo     http://localhost:7474/browser/
echo.
echo     使用方法：
echo     1. 把新 CSV 扔进 import 文件夹 → 10秒自动保鲜
echo     2. 或者在 GitHub 改文件 → git push → 自动保鲜
echo     两种方式都行，飞书都会精准提醒！
echo.
echo     你已达成：扔文件即更新，push即取经！
echo.
echo  按任意