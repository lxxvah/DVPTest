@echo off
cd /d %~dp0

echo ==========================================
echo 开始清理旧文件...
echo ==========================================
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

echo ==========================================
echo 正在打包单文件版本 (Onefile)...
echo ==========================================
:: -F 表示单文件，-w 表示隐藏控制台窗口，-i 指定图标
pyinstaller --noconfirm --clean -F -w -i app.ico -n DVPTest_Single main.py

if %errorlevel% neq 0 (
    echo 单文件打包失败！
    exit /b %errorlevel%
)

echo ==========================================
echo 正在打包多文件版本 (Onedir)...
echo ==========================================
:: -D 表示多文件（默认也是多文件，这里显式声明）
pyinstaller --noconfirm --clean -D -w -i app.ico -n DVPTest_Multi main.py

if %errorlevel% neq 0 (
    echo 多文件打包失败！
    exit /b %errorlevel%
)

echo ==========================================
echo 开始执行 Inno Setup 脚本...
echo ==========================================
:: 设置 Inno Setup 编译器的默认路径（如果不在这个路径请修改）
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist "%ISCC_PATH%" (
    "%ISCC_PATH%" DVPTest.iss
) else (
    :: 尝试直接从环境变量中调用
    ISCC.exe DVPTest.iss
)

if %errorlevel% neq 0 (
    echo Inno Setup 执行失败，请检查 ISCC 路径或 .iss 脚本内容。
    exit /b %errorlevel%
)

echo ==========================================
echo 所有任务执行成功！即将自动退出。
echo ==========================================
exit