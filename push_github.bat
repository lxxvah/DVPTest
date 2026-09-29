@echo off
:: 强制控制台使用 UTF-8 编码，解决乱码
chcp 65001 >nul
cd /d %~dp0

echo ==========================================
echo 正在自动分析变更并推送到 GitHub...
echo ==========================================

git add .

:: 检查是否有实际变更
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo.
    echo 没有需要提交的更改，脚本退出。
    pause
    exit /b 0
)

set "MSG=Auto: "
set "HAS_PY=0"
set "HAS_ISS=0"
set "HAS_BAT=0"

:: 使用 findstr 替代 for 循环，避免解析中文文件名时乱码
git diff --cached --name-only | findstr /i "\.py$" >nul && set "HAS_PY=1"
git diff --cached --name-only | findstr /i "\.iss$" >nul && set "HAS_ISS=1"
git diff --cached --name-only | findstr /i "\.bat$" >nul && set "HAS_BAT=1"

:: 使用英文拼接，彻底避开 CMD 传递中文给 Git 的乱码问题
if %HAS_PY% equ 1 set "MSG=%MSG%Update Python code "
if %HAS_ISS% equ 1 set "MSG=%MSG%Update Installer "
if %HAS_BAT% equ 1 set "MSG=%MSG%Update Bat scripts "

:: 如果什么都没匹配到
if "%MSG%"=="Auto: " set "MSG=Auto: Update project files"

:: 加上时间戳（去掉 %time% 在 10 点前的空格）
set "T=%time: =0%"
set "MSG=%MSG% [%date:~0,10% %T:~0,8%]"

echo.
echo 分析完成，自动生成提交信息: %MSG%
git commit -m "%MSG%"

if %errorlevel% neq 0 (
    echo.
    echo Git 提交失败，请检查 Git 配置或是否有冲突。
    pause
    exit /b %errorlevel%
)

:: 推送到远程仓库
git push

if %errorlevel% neq 0 (
    echo.
    echo GitHub 推送失败，请检查网络或 Git 配置。
    pause
    exit /b %errorlevel%
)

echo.
echo GitHub 推送成功！
pause
exit /b 0