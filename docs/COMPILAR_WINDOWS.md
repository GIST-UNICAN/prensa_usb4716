# Compilar para Windows

La distribución prevista es `onedir`: una carpeta `dist\PrensaMarshallUSB4716` que contiene el ejecutable, la DLL puente y los recursos. Es la opción recomendada para la USB-4716, porque DAQNavi aporta dependencias nativas y resulta más fácil diagnosticar una DLL ausente que en un ejecutable único.

## Equipo de compilación

Use **Windows 11 x64**. PyInstaller genera para el sistema donde se ejecuta, por lo que un macOS no genera un `.exe` de Windows válido. Instale:

1. Python x64, preferiblemente la misma versión que se vaya a mantener para el laboratorio.
2. DAQNavi/XNavi x64 y el SDK de Advantech; compruebe la USB-4716 en Navigator.
3. Visual Studio Build Tools x64 con C++, para `cl.exe`.

Desde *x64 Native Tools Command Prompt for VS 2022*, ejecute:

```bat
packaging\build_windows.bat
```

El script instala las dependencias, compila `bridge\usb4716_bridge.dll` si aún no existe y deja el programa en `dist\PrensaMarshallUSB4716\PrensaMarshallUSB4716.exe`.

## Recursos y datos persistentes

El empaquetado contiene el logotipo UC, la configuración inicial y los datos simulados. En el ejecutable, la configuración editable, el historial y las exportaciones se guardan en:

```text
%LOCALAPPDATA%\Universidad de Cantabria\Prensa Marshall USB-4716\
```

Así, una actualización de la carpeta `dist` no borra calibraciones, pinout ni ensayos. La configuración inicial se copia allí la primera vez que se abre el programa.

## Validación antes de entregar

1. Ejecute `PrensaMarshallUSB4716.exe --demo` y abra `sample_data\ensayo_marshall_simulado.json`.
2. Genere CSV, Excel, HTML, ZIP y PDF; confirme la identidad UC en el PDF.
3. En el equipo de prensa, compruebe DAQNavi Navigator, los AI0/AI1 y AI2/AI3, la tara y dos patrones por sensor antes de un ensayo real.

No se incluye DAQNavi en el paquete: debe instalarse mediante el instalador y licencia de Advantech en cada equipo.

## Instalador con icono y accesos directos

Para entregar la aplicación de forma instalable, instale primero [Inno Setup 6](https://jrsoftware.org/isdl.php):

```bat
winget install --id JRSoftware.InnoSetup -e -s winget -i
```

Después, desde la carpeta raíz del proyecto ejecute:

```bat
packaging\build_installer.bat
```

Se generará `release\Instalar_PrensaMarshallUSB4716.exe`. Al ejecutarlo, el instalador copia toda la carpeta necesaria, crea el icono en el Escritorio y añade **Prensa Marshall USB-4716** al menú Inicio, dentro de Aplicaciones. No requiere permisos de administrador y se instala para el usuario actual.
