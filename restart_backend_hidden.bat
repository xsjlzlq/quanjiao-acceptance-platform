@echo off
chcp 65001 >nul
echo =========================================
echo       正在重启后端服务 (全椒县验收)
echo =========================================

echo.
echo [1/3] 正在清理旧的后端进程...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul

echo.
echo [2/3] 正在后台启动 FastAPI 服务...
cd /d "%~dp0backend"
powershell -Command "Start-Process -FilePath 'uvicorn.exe' -ArgumentList 'main:app, --host, 0.0.0.0, --port, 8081, --reload' -WindowStyle Hidden"

echo.
echo [3/3] 服务启动指令已发送！
echo -----------------------------------------
echo 后端地址: http://0.0.0.0:8081
echo 服务在后台静默运行中，此窗口可安全关闭。
echo =========================================
pause
