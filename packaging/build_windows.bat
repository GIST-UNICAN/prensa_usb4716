@echo off
setlocal EnableExtensions
pushd "%~dp0\.."

REM Ejecute en Windows x64, tras instalar DAQNavi/XNavi y Visual Studio Build Tools x64.
REM La USB-4716 y DAQNavi no se pueden validar ni empaquetar desde macOS.
py -3 -m pip install -r requirements.txt -r requirements-dev.txt
if errorlevel 1 exit /b 1

if not exist "bridge\usb4716_bridge.dll" (
  echo Compilando la DLL puente DAQNavi...
  set NO_PAUSE=1
  call bridge\build_bridge.bat
  if errorlevel 1 exit /b 1
)

REM onedir deja DLL y recursos visibles junto al EXE, apropiado para soporte de DAQNavi.
py -3 -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name "PrensaMarshallUSB4716" ^
  --add-data "assets;assets" ^
  --add-data "config.json;." ^
  --add-data "sample_data;sample_data" ^
  --add-binary "bridge\usb4716_bridge.dll;bridge" ^
  --collect-all matplotlib ^
  --hidden-import PIL.ImageTk ^
  app.py
if errorlevel 1 exit /b 1

echo.
echo Generado: dist\PrensaMarshallUSB4716\PrensaMarshallUSB4716.exe
echo Pruebe primero: dist\PrensaMarshallUSB4716\PrensaMarshallUSB4716.exe --demo
popd
