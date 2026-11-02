@echo off
REM ============================================================================
REM  一条龙打包：安装 Python 依赖 -> 编译原生库 -> PyInstaller 生成可执行文件
REM
REM  产物：
REM    dist\MotionGlove3DViewer\MotionGlove3DViewer.exe
REM
REM  用法（在本目录直接运行）：
REM    [Windows]build.cmd                默认：隐藏控制台窗口
REM    [Windows]build.cmd --console      保留控制台窗口（便于查看报错）
REM    [Windows]build.cmd --force        强制重装依赖并重新编译原生库
REM    [Windows]build.cmd --skip-deps    跳过依赖安装（libs\ 已就绪时更快）
REM    [Windows]build.cmd --skip-native  跳过原生库编译（已编译过时更快）
REM    [Windows]build.cmd --help         显示本帮助
REM ============================================================================
setlocal EnableExtensions
chcp 65001 >nul

REM 注意：变量名不要用 ROOT_DIR —— scripts 下的 helper 脚本会覆盖同名变量
set "PROJECT_ROOT=%~dp0"
pushd "%PROJECT_ROOT%" >nul 2>&1
if errorlevel 1 (
    echo [error] 无法进入工程目录："%PROJECT_ROOT%"
    exit /b 1
)

set "DO_CONSOLE=0"
set "FORCE=0"
set "SKIP_DEPS=0"
set "SKIP_NATIVE=0"

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--console" (set "DO_CONSOLE=1" & shift & goto parse_args)
if /i "%~1"=="--force" (set "FORCE=1" & shift & goto parse_args)
if /i "%~1"=="--skip-deps" (set "SKIP_DEPS=1" & shift & goto parse_args)
if /i "%~1"=="--skip-native" (set "SKIP_NATIVE=1" & shift & goto parse_args)
if /i "%~1"=="--help" goto usage
if /i "%~1"=="-h" goto usage
echo [warn] 忽略未知参数：%~1
shift
goto parse_args

:args_done
echo ============================================================
echo  MotionGlove3DViewer 一条龙打包
echo  工程目录：%PROJECT_ROOT%
echo ============================================================

where python >nul 2>nul
if errorlevel 1 (
    echo [error] 未找到 python，请先安装 Python 3.10+ 并加入 PATH
    goto fail
)
for /f "delims=" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
echo [info] %PY_VERSION%

REM ---------------------------------------------------------------- 依赖
echo.
echo === [1/3] Python 运行时依赖（libs\） ===
if "%SKIP_DEPS%"=="1" (
    echo [skip] 已指定 --skip-deps
    goto deps_done
)

set "DEPS_READY=1"
for %%M in (vtk numpy PySide6) do (
    if not exist "%PROJECT_ROOT%libs\%%M" set "DEPS_READY=0"
)

if "%FORCE%"=="1" (
    echo [run ] --force：重新安装依赖
    goto deps_install
)
if "%DEPS_READY%"=="1" (
    echo [skip] libs\ 已包含 vtk / numpy / PySide6（--force 可强制重装）
    goto deps_done
)

:deps_install
set "DEPS_SCRIPT=%PROJECT_ROOT%scripts\[Windows]setup_python_libs.cmd"
if not exist "%DEPS_SCRIPT%" (
    echo [error] 未找到 %DEPS_SCRIPT%
    goto fail
)
call "%DEPS_SCRIPT%"
set "DEPS_RC=%errorlevel%"
if not "%DEPS_RC%"=="0" (
    echo [error] 依赖安装失败，退出码 %DEPS_RC%
    goto fail
)
:deps_done

REM ---------------------------------------------------------------- 原生库
echo.
echo === [2/3] 编译原生库（third_party\MotionGloveSDK_cpp） ===
set "NATIVE_DLL=%PROJECT_ROOT%build\mgsdk_cpp\install\bin\MotionGloveSDK.dll"
if "%SKIP_NATIVE%"=="1" (
    echo [skip] 已指定 --skip-native
    goto native_done
)
if "%FORCE%"=="1" goto native_build
if exist "%NATIVE_DLL%" (
    echo [skip] 已存在 %NATIVE_DLL%（--force 可重新编译）
    goto native_done
)

:native_build
set "NATIVE_SCRIPT=%PROJECT_ROOT%scripts\[Windows]build_mgsdk_cpp.cmd"
if not exist "%NATIVE_SCRIPT%" (
    echo [error] 未找到 %NATIVE_SCRIPT%
    goto fail
)
call "%NATIVE_SCRIPT%"
set "NATIVE_RC=%errorlevel%"
if not "%NATIVE_RC%"=="0" (
    echo [error] 原生库编译失败，退出码 %NATIVE_RC%
    goto fail
)
if not exist "%NATIVE_DLL%" (
    echo [error] 编译完成但未找到 %NATIVE_DLL%
    goto fail
)
:native_done

REM ---------------------------------------------------------------- PyInstaller
echo.
echo === [3/3] PyInstaller 生成可执行文件 ===
set "PYTHONPATH=%PROJECT_ROOT%libs;%PROJECT_ROOT%src;%PYTHONPATH%"
set "MG_DIST_CONSOLE=%DO_CONSOLE%"
if "%DO_CONSOLE%"=="1" (
    echo [info] 保留控制台窗口
) else (
    echo [info] 隐藏控制台窗口
)

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo [warn] 未检测到 PyInstaller，正在安装 pyinstaller==6.19.0 ...
    python -m pip install pyinstaller==6.19.0
    if errorlevel 1 (
        echo [error] PyInstaller 安装失败
        goto fail
    )
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --distpath "%PROJECT_ROOT%dist" ^
    --workpath "%PROJECT_ROOT%build\pyinstaller" ^
    "%PROJECT_ROOT%MotionGlove3DViewer.spec"
set "PYI_RC=%errorlevel%"
if not "%PYI_RC%"=="0" (
    echo [error] PyInstaller 打包失败，退出码 %PYI_RC%
    goto fail
)

set "EXE_PATH=%PROJECT_ROOT%dist\MotionGlove3DViewer\MotionGlove3DViewer.exe"
if not exist "%EXE_PATH%" (
    echo [error] 未生成 %EXE_PATH%
    goto fail
)

REM PyInstaller 运行后可能改掉控制台代码页，重新设置以免中文乱码
chcp 65001 >nul

echo.
echo ============================================================
echo  [done] 打包完成
echo  主程序：%EXE_PATH%
for %%F in ("%EXE_PATH%") do echo  大小：%%~zF 字节
echo  输出目录：%PROJECT_ROOT%dist\MotionGlove3DViewer\
echo ============================================================
popd
exit /b 0

:usage
echo 用法：[Windows]build.cmd [--console] [--force] [--skip-deps] [--skip-native]
echo.
echo   --console      保留控制台窗口（默认隐藏）
echo   --force        强制重装 Python 依赖并重新编译原生库
echo   --skip-deps    跳过依赖安装
echo   --skip-native  跳过原生库编译
echo   --help, -h     显示本帮助
popd
exit /b 0

:fail
echo.
echo [failed] 打包中止，请检查上面的报错信息
popd
exit /b 1
