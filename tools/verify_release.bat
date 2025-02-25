@echo off
rem Scout Release Verification Wrapper for Windows
rem This script provides a simple way to run the release verification process

setlocal enabledelayedexpansion

rem Determine script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

rem Default values
set "VERSION=1.0.0"
set "OUTPUT_DIR=%PROJECT_ROOT%\verification_results"
set "SKIP_BUILD=0"
set "SKIP_TESTS=0"
set "SKIP_DOCS=0"
set "SKIP_CHECK=0"

rem Text colors (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "NC=[0m"

rem Check if help is requested
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help

rem Parse arguments
:parse_args
if "%1"=="" goto :end_parse_args

if "%1"=="--version" (
    set "VERSION=%2"
    shift
    shift
    goto :parse_args
)

if "%1"=="-v" (
    set "VERSION=%2"
    shift
    shift
    goto :parse_args
)

if "%1"=="--output-dir" (
    set "OUTPUT_DIR=%2"
    shift
    shift
    goto :parse_args
)

if "%1"=="-o" (
    set "OUTPUT_DIR=%2"
    shift
    shift
    goto :parse_args
)

if "%1"=="--skip-build" (
    set "SKIP_BUILD=1"
    shift
    goto :parse_args
)

if "%1"=="-b" (
    set "SKIP_BUILD=1"
    shift
    goto :parse_args
)

if "%1"=="--skip-tests" (
    set "SKIP_TESTS=1"
    shift
    goto :parse_args
)

if "%1"=="-t" (
    set "SKIP_TESTS=1"
    shift
    goto :parse_args
)

if "%1"=="--skip-docs" (
    set "SKIP_DOCS=1"
    shift
    goto :parse_args
)

if "%1"=="-d" (
    set "SKIP_DOCS=1"
    shift
    goto :parse_args
)

if "%1"=="--skip-check" (
    set "SKIP_CHECK=1"
    shift
    goto :parse_args
)

if "%1"=="-c" (
    set "SKIP_CHECK=1"
    shift
    goto :parse_args
)

if "%1"=="--skip-all" (
    set "SKIP_BUILD=1"
    set "SKIP_TESTS=1"
    set "SKIP_DOCS=1"
    set "SKIP_CHECK=1"
    shift
    goto :parse_args
)

if "%1"=="-a" (
    set "SKIP_BUILD=1"
    set "SKIP_TESTS=1"
    set "SKIP_DOCS=1"
    set "SKIP_CHECK=1"
    shift
    goto :parse_args
)

echo %RED%Error: Unknown option: %1%NC%
call :show_help
exit /b 1

:end_parse_args

rem Header
echo.
echo %PURPLE%=========================================================%NC%
echo %PURPLE%Scout %VERSION% Release Verification%NC%
echo %PURPLE%=========================================================%NC%
echo.

rem Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%Error: Python is not installed or not in PATH%NC%
    echo Please install Python 3.9 or higher
    exit /b 1
)

rem Check Python version
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%V"
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set "PYTHON_MAJOR=%%a"
    set "PYTHON_MINOR=%%b"
)

if !PYTHON_MAJOR! lss 3 (
    echo %YELLOW%Warning: Python 3.9 or higher is recommended (detected !PYTHON_VERSION!)%NC%
) else (
    if !PYTHON_MINOR! lss 9 (
        echo %YELLOW%Warning: Python 3.9 or higher is recommended (detected !PYTHON_VERSION!)%NC%
    )
)

rem Build command
set "CMD=python %SCRIPT_DIR%run_release_verification.py --version %VERSION% --output-dir %OUTPUT_DIR%"

if %SKIP_BUILD% equ 1 (
    set "CMD=!CMD! --skip-build"
    echo %YELLOW%Skipping build process%NC%
)

if %SKIP_TESTS% equ 1 (
    set "CMD=!CMD! --skip-tests"
    echo %YELLOW%Skipping tests%NC%
)

if %SKIP_DOCS% equ 1 (
    set "CMD=!CMD! --skip-docs"
    echo %YELLOW%Skipping documentation checks%NC%
)

if %SKIP_CHECK% equ 1 (
    set "CMD=!CMD! --skip-check"
    echo %YELLOW%Skipping version checks%NC%
)

rem Print command
echo %BLUE%Running command:%NC% !CMD!
echo.

rem Run verification
%CMD%
set RESULT=%ERRORLEVEL%

rem Print exit status
if %RESULT% equ 0 (
    echo.
    echo %GREEN%Verification completed successfully!%NC%
) else (
    echo.
    echo %RED%Verification completed with errors. Please check the report for details.%NC%
)

echo.
echo %BLUE%Next steps:%NC%
echo 1. Review the verification report in the output directory
echo 2. Complete any remaining items in the verification checklist
echo 3. Address any failed tests or checks
echo 4. Sign off on the release when all checks pass
echo.

exit /b %RESULT%

:show_help
echo %BLUE%Scout Release Verification Tool%NC%
echo.
echo This script helps verify that the Scout application is ready for release.
echo.
echo Usage: %0 [options]
echo.
echo Options:
echo   -v, --version VERSION    Version to verify (default: 1.0.0)
echo   -o, --output-dir DIR     Directory to store verification results
echo   -b, --skip-build         Skip building executables
echo   -t, --skip-tests         Skip running tests
echo   -d, --skip-docs          Skip documentation checks
echo   -c, --skip-check         Skip version checks
echo   -a, --skip-all           Skip all checks and only generate reports
echo   -h, --help               Show this help message
echo.
echo Example:
echo   %0 --version 1.0.0 --skip-tests
echo.
exit /b 0 