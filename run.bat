@echo off
REM 手写数字视频识别 — 启动脚本
REM 自动定位 digit_recognition conda 环境

set ENV_NAME=digit_recognition

REM 尝试多个可能的路径
set PYTHON_EXE=D:\conda_envs\%ENV_NAME%\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=%USERPROFILE%\.conda\envs\%ENV_NAME%\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=%USERPROFILE%\anaconda3\envs\%ENV_NAME%\python.exe

if exist "%PYTHON_EXE%" (
    echo [INFO] 使用环境: %PYTHON_EXE%
    "%PYTHON_EXE%" "%~dp0src\main.py" %*
) else (
    echo [ERROR] 找不到 digit_recognition 环境
    echo 请先执行: conda activate digit_recognition
    pause
)
