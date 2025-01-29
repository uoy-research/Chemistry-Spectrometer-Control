@echo off
echo Starting build process...

REM Check if icon exists
if not exist chem.ico (
    echo Error: chem.ico not found!
    pause
    exit /b 1
)

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

if errorlevel 1 (
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
pause 