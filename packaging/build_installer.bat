@echo off
setlocal EnableExtensions
pushd "%~dp0\.."

REM Primero se crea la distribucion de la aplicacion.
call packaging\build_windows.bat
if errorlevel 1 exit /b 1

REM Inno Setup suele quedar disponible en PATH. Se contempla tambien su ruta habitual.
set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
  echo.
  echo ERROR: No se encontro Inno Setup 6.
  echo Instalelo con: winget install --id JRSoftware.InnoSetup -e -s winget -i
  echo Despues vuelva a ejecutar packaging\build_installer.bat.
  exit /b 1
)

"%ISCC%" "packaging\PrensaMarshallUSB4716.iss"
if errorlevel 1 exit /b 1

echo.
echo Generado: release\Instalar_PrensaMarshallUSB4716.exe
popd
