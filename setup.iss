; DVPTest 泄气阀压力测试上位机 安装脚本
; 保存为 setup.iss，放在 D:\Python\DVPTest\ 目录下
; 使用 Inno Setup 6 编译

[Setup]
AppName=DVPTest
AppVersion=1.0.0
AppPublisher=刘欣
AppPublisherURL=https://github.com
AppSupportURL=https://github.com
AppUpdatesURL=https://github.com
DefaultDirName={autopf}\DVPTest
DefaultGroupName=DVPTest
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=D:\Python\DVPTest\installer
OutputBaseFilename=DVPTest_Setup
SetupIconFile=D:\Python\DVPTest\app.ico
UninstallDisplayIcon={app}\DVPTest.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce

[Files]
; 将打包后的所有文件复制到安装目录
Source: "D:\Python\DVPTest\dist\DVPTest\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DVPTest"; Filename: "{app}\DVPTest.exe"
Name: "{group}\卸载 DVPTest"; Filename: "{uninstallexe}"
Name: "{autodesktop}\DVPTest"; Filename: "{app}\DVPTest.exe"; Tasks: desktopicon

[Run]
; 安装完成后可选启动程序
Filename: "{app}\DVPTest.exe"; Description: "启动 DVPTest"; Flags: postinstall nowait skipifsilent

[Dirs]
; 安装时创建日志目录（程序运行时会自动创建，但提前创建可避免权限问题）
Name: "{app}\logs\debug"
Name: "{app}\logs\csv"
Name: "{app}\logs\data"

[UninstallDelete]
; 卸载时删除整个安装目录（包括日志文件，可选）
Type: filesandordirs; Name: "{app}"