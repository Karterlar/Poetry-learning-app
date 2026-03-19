@echo off
chcp 65001 >nul
title 诗词学习助手 - 一键启动

echo ==========================================
echo        诗词学习助手（Poetry Expert System）
echo ==========================================
echo.

cd /d %~dp0

echo [1/5] 检查 Python 是否已安装...
python --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Python！
    echo 请先安装 Python 3.10 或 3.11，并勾选 "Add Python to PATH"
    echo 官网：https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo [2/5] 检查虚拟环境...
if not exist venv (
    echo 未检测到虚拟环境，正在创建 venv...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo [错误] 虚拟环境创建失败！
        echo 请确认 Python 安装正常。
        echo.
        pause
        exit /b
    )
)

echo [3/5] 激活虚拟环境...
call venv\Scripts\activate
if errorlevel 1 (
    echo.
    echo [错误] 虚拟环境激活失败！
    echo.
    pause
    exit /b
)

echo [4/5] 安装/检查依赖...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [警告] requirements.txt 安装失败，尝试使用备用方式安装依赖...
    pip install streamlit==1.50.0 gTTS==2.5.4 audio-recorder-streamlit==0.0.10 SpeechRecognition==3.15.1 typing_extensions==4.15.0
)

echo [5/5] 启动项目...
echo.
echo 启动成功后，请在浏览器打开：
echo http://localhost:8501
echo.
echo 如果浏览器没有自动打开，请手动复制上方地址访问。
echo.

python -m streamlit run poem_app_v3.py

echo.
echo 程序已退出。
pause

Ensure start.bat uses CRLF
