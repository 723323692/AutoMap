@echo off
chcp 65001 >nul
title 卡密验证服务

:: 设置API密钥
set AUTH_API_SECRET=BabyBus2024SecretKey

echo 正在启动卡密验证服务...
echo API密钥: %AUTH_API_SECRET%
echo.

python auth_server.py

pause
