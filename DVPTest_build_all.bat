@echo off
chcp 65001 >nul
cd /d %~dp0

echo ==========================================
echo 开始清理旧文件...
echo ==========================================
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "installer" rd /s /q "installer"

echo ==========================================
echo 正在打包单文件版本 (Onefile)...
echo ==========================================
:: -F 单文件，-w 隐藏控制台，-i 图标
pyinstaller --noconfirm --clean -F -w -i app.ico -n DVPTest_Single main.py
if %errorlevel% neq 0 (
    echo 单文件打包失败！
    pause
    exit /b %errorlevel%
)

echo ==========================================
echo 正在打包多文件版本 (Onedir)...
echo ==========================================
:: -D 多文件，-w 隐藏控制台，-i 图标
pyinstaller --noconfirm --clean -D -w -i app.ico -n DVPTest_Multi main.py
if %errorlevel% neq 0 (
    echo 多文件打包失败！
    pause
    exit /b %errorlevel%
)

echo ==========================================
echo 校验打包产物...
echo ==========================================
if not exist "dist\DVPTest_Multi\DVPTest_Multi.exe" (
    echo 未找到 dist\DVPTest_Multi\DVPTest_Multi.exe，无法继续打安装包。
    pause
    exit /b 1
)

echo ==========================================
echo 开始执行 Inno Setup 脚本...
echo ==========================================
:: Inno Setup 编译器路径（若不在这个路径请修改）
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist "%ISCC_PATH%" (
    "%ISCC_PATH%" DVPTest.iss
) else (
    where ISCC.exe >nul 2>nul
    if %errorlevel% neq 0 (
        echo 未找到 ISCC.exe，请安装 Inno Setup 6 或修改 ISCC_PATH。
        pause
        exit /b 1
    )
    ISCC.exe DVPTest.iss
)

if %errorlevel% neq 0 (
    echo Inno Setup 执行失败，请检查 ISCC 路径或 .iss 脚本内容。
    pause
    exit /b %errorlevel%
)

echo ==========================================
echo 所有任务执行成功！
echo 单文件:  dist\DVPTest_Single\DVPTest_Single.exe
echo 多文件:  dist\DVPTest_Multi\DVPTest_Multi.exe
echo 安装包:  installer\DVPTest_Setup_v1.1.0.exe
echo ==========================================
pause
exit /b 0