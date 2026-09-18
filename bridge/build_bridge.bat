@echo off
setlocal
pushd "%~dp0"
REM Ajuste esta ruta si DAQNavi se instala en otro directorio.
set DAQNAVI=C:\Advantech\DAQNavi

if not exist "%DAQNAVI%\Inc\bdaqctrl.h" (
  echo ERROR: no se encuentra %DAQNAVI%\Inc\bdaqctrl.h
  echo Instale DAQNavi SDK/XNavi o edite la variable DAQNAVI de este BAT.
  pause
  exit /b 1
)

where cl >nul 2>nul
if errorlevel 1 (
  echo ERROR: cl.exe no esta disponible.
  echo Abra "x64 Native Tools Command Prompt for VS 2022" y ejecute este BAT desde ahi.
  pause
  exit /b 1
)

cl /nologo /EHsc /LD /O2 /std:c++17 /I"%DAQNAVI%\Inc" usb4716_bridge.cpp /Fe:usb4716_bridge.dll
if errorlevel 1 exit /b 1

echo.
echo DLL creada correctamente: usb4716_bridge.dll
pause
