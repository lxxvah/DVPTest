@echo off
:: 切换到脚本所在目录
cd /d %~dp0

echo ==========================================
echo 正在自动推送到 GitHub...
echo ==========================================

:: 添加所有修改
git add .

:: 提交修改（如果无修改则忽略报错）
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo 没有需要提交的更改。
) else (
    git commit -m "Auto commit: %date% %time%"
)

:: 推送到远程仓库
git push

if %errorlevel% neq 0 (
    echo GitHub 推送失败，请检查网络或 Git 配置。
    exit /b %errorlevel%
)

echo GitHub 推送成功！
exit