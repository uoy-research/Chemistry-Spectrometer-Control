@echo off
echo Starting build process with virtual environment...

REM Check if python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found in PATH
    pause
    exit /b 1
)

REM Check if icon exists
if not exist chem.ico (
    echo Error: chem.ico not found!
    pause
    exit /b 1
)

REM Create and activate virtual environment
echo Creating build virtual environment...
if exist venv rmdir /s /q venv
python -m venv venv
call venv\Scripts\activate

REM Install required packages in virtual environment
echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pyinstaller

echo Checking C:\ssbubble directory...
if not exist C:\ssbubble (
    echo Creating C:\ssbubble directory...
    mkdir C:\ssbubble
)

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Creating necessary directories...
mkdir dist\SSBubble\config 2>nul
mkdir dist\SSBubble\data 2>nul

echo Building SSBubble...
pyinstaller --clean SSBubble.spec --log-level DEBUG

set BUILD_STATUS=%errorlevel%

REM Deactivate virtual environment
call deactivate

if %BUILD_STATUS% neq 0 (
    echo Build failed! Check the error messages above.
    pause
    exit /b 1
)

echo Copying configuration files...
xcopy /y /i config\*.json dist\SSBubble\config\ 2>nul

REM Copy macro files to C:\ssbubble if they don't exist there
if exist valve_macro_data.json (
    if not exist C:\ssbubble\valve_macro_data.json (
        copy valve_macro_data.json C:\ssbubble\
    )
)
if exist motor_macro_data.json (
    if not exist C:\ssbubble\motor_macro_data.json (
        copy motor_macro_data.json C:\ssbubble\
    )
)

if not exist dist\SSBubble\SSBubble.exe (
    echo Error: Executable was not created!
    echo Checking for common issues...
    
    if not exist src\main.py (
        echo Error: src\main.py not found!
    )
    
    echo Please check the build output above for errors.
    pause
    exit /b 1
)

echo Build successful! Testing executable...
cd dist\SSBubble
SSBubble.exe
cd ..\..

echo Build process complete.
echo You can remove the venv directory if you don't need it anymore.
pause 