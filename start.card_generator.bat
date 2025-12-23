@echo off
chcp 65001 >nul
title 卡密生成器

:: 检测Python环境
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw card_generator.py
    exit
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    start "" python card_generator.py
    exit
)

py -3 card_generator.py
