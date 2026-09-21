# Prensa Marshall - USB-4716 (Tkinter)

Aplicacion Windows 11 para adquisicion de fuerza y deformacion mediante Advantech USB-4716 y DAQNavi.

## Funciones principales

- Interfaz Tkinter con pestañas de ensayo, datos, configuracion e instrucciones.
- Conexion desacoplada mediante `daq_api.py` y `bridge/usb4716_bridge.dll`.
- Pinout configurable para el DB37 antiguo y para los pares diferenciales de la USB-4716.
- Calibracion configurable por factor/offset o mediante dos puntos conocidos.
- Tara configurable.
- Graficas en tiempo real: fuerza-deformacion y fuerza-tiempo.
- Exportacion de cada grafica a PNG.
- Tabla completa de datos.
- Exportacion CSV con voltajes brutos y magnitudes calculadas.
- Generacion de informe PDF con resumen, configuracion, pinout, calibracion, graficas y tabla de datos.
- Botones de informacion contextual en la interfaz.
- Modo simulacion sin hardware.

## Instalacion

1. Instalar Python 3 x64 con Tkinter.
2. Instalar dependencias:

```bat
py -m pip install -r requirements.txt
```

3. Para probar sin tarjeta:

```bat
py app.py --demo
```

4. Para hardware real, instalar Advantech DAQNavi/XNavi y el SDK, comprobar el nombre del dispositivo en Navigator y compilar:

```bat
bridge\build_bridge.bat
```

5. Ejecutar:

```bat
py app.py
```

## Ejecutable Windows

La compilación se realiza en Windows x64 con PyInstaller y se distribuye como carpeta `onedir`, junto a la DLL puente. Consulte [docs/COMPILAR_WINDOWS.md](docs/COMPILAR_WINDOWS.md); el script reproducible es `packaging/build_windows.bat`.

## Datos de prueba

`sample_data/ensayo_marshall_simulado.json` es un ensayo sintético de 20 segundos y 401 muestras, con un pico próximo a 1.275 kp, deformación y ruido de adquisición. Ábralo desde **Historial > Importar ensayo JSON**; quedará archivado como simulación y puede compararse, filtrarse y exportarse. El CSV equivalente está en la misma carpeta. Para regenerarlos de forma determinista: `python tools/generate_demo_data.py`.

## Pinout PCL-816 → USB-4716 (contrastado con manuales)

- Fuerza: DB37 pin 1 (H/+) y pin 20 (L/-) -> USB AI0 (+) / AI1 (-)
- Deformacion: DB37 pin 2 (H/+) y pin 21 (L/-) -> USB AI2 (+) / AI3 (-)
- Entradas diferenciales, rango +/-5 V.

La guía completa con masas, todos los contactos DB37 y parámetros recuperados está en [docs/MIGRACION_TARJETA.md](docs/MIGRACION_TARJETA.md). El pinout puede cambiarse desde `Configuracion > Pinout`. Los pares USB diferenciales deben ser consecutivos y comenzar en canal par: 0/1, 2/3, 4/5, etc.

## Calibracion inicial recuperada del sistema antiguo

- Fuerza: `-1970.57 kp/V`
- Deformacion: `2.643095 mm/V`

La aplicacion utiliza:

`magnitud = factor * (voltaje - tara) + offset`

Los coeficientes pueden editarse desde la propia interfaz o calcularse con dos puntos conocidos.

## Observacion

El software realiza adquisicion y registro. No controla el movimiento ni la seguridad de la prensa.

## Laboratorio de calibración y revisión de ensayos

La pestaña **Calibración · laboratorio** permite elegir fuerza (kp) o deformación (mm), introducir patrones y ajustar una recta con dos o más puntos. Con la DAQ conectada y el ensayo detenido, **Capturar 1 s** toma la media de los voltajes brutos recientes y muestra su variación. Espere a que el patrón se estabilice antes de capturar. Revise la gráfica y los residuos y pulse **Aplicar y guardar calibración**. Los patrones, fecha, errores y condición de simulación quedan en `config.json`. La tara del sensor se reinicia al aplicar; realice una nueva tara sin carga antes del ensayo.

**Datos / Exportación** abre CSV nuevos y TXT antiguos, exporta TXT y muestra pico de carga, deformación al pico, duración y velocidad media. El CSV guarda cada lectura sin suavizado, voltajes y fuerza en kp, kgf, N y kN; cuando se indica el área, añade Pa, kPa, MPa y kgf/cm². Conserva el archivo `.metadata.json` junto al CSV. Los TXT antiguos expresan deformación en centésimas de mm, que se convierten automáticamente a mm, y no incluyen voltajes.

La comparación detallada con el código antiguo y los límites de verificación están en [REVISION_FUNCIONAL.md](REVISION_FUNCIONAL.md).

Pruebas (requieren Tkinter y un entorno gráfico):

```sh
python -m unittest discover -s tests -v
```

## Historial de ensayos

La pestaña **Historial** conserva cada ensayo automáticamente al pulsar **Parar**. El archivo local está en `ensayos/historial.sqlite3` (o en `output_directory` si se cambia la configuración). Incluye lecturas, identificación, fecha, origen, calibración y tara. Los datos importados de CSV/TXT se incorporan con **Guardar en historial**; los JSON se archivan al importarlos.

- Busque por referencia, probeta, operador o notas, y filtre por modo real, simulado o desconocido.
- Haga doble clic para recuperar un ensayo; editar su identificación y guardarlo actualiza ese registro sin duplicarlo.
- Seleccione entre dos y seis registros con Ctrl/Cmd + clic y pulse **Comparar selección**.
- **Exportar selección a ZIP** crea una copia portátil con un JSON y un CSV por ensayo, más un índice. Extraiga el ZIP y abra cada `ensayo.json` para recuperarlo en otra instalación.
- Para respaldar toda la base de datos, cierre la aplicación y copie `historial.sqlite3`.

El guardado automático se realiza al detener el ensayo, no durante cada lectura. Una interrupción del proceso antes de detenerlo puede perder las lecturas de la sesión en curso. Si falla el guardado, los datos permanecen en memoria y se muestra un aviso para exportarlos.

## Análisis y gráficas

**Análisis / gráficas** incorpora cinco vistas: fuerza–deformación, fuerza–tiempo, deformación–tiempo, voltajes–tiempo y velocidad–tiempo. Permite trabajar en kp, kgf, N y kN; al indicar el área de probeta en Configuración, habilita Pa, kPa, MPa y kgf/cm². Incluye señal sin filtrar, media móvil, mediana y los tramos “Desde 5 %” y “Ascenso 5–95 %”. El último reproduce de forma explícita los umbrales que el formulario `FILTRAR` antiguo calculaba sin llegar a aplicar. Los filtros sólo afectan a la vista o al CSV de análisis; el archivo bruto, las estadísticas y la calibración no se alteran.

La velocidad se estima con diferencias de deformación sobre ventanas de al menos 0,5 segundos. En registros más cortos no se muestra una velocidad. Los archivos antiguos sin voltajes indican que no hay datos para esa vista. Para mantener la fluidez, las gráficas grandes reducen los puntos dibujados; los datos exportados se conservan completos. Durante la adquisición, las gráficas de **Ensayo** son las vistas en directo; pulse **Ver ensayo actual** para actualizar el análisis ampliado.

## Exportaciones ampliadas

Desde **Datos / Exportación**, con el ensayo detenido:

| Formato | Contenido |
| --- | --- |
| Excel (`.xlsx`) | Resumen, datos completos, calibración y tres gráficas editables |
| JSON (`.json`) | Ensayo completo versionado, recuperable en la aplicación |
| HTML (`.html`) | Informe autónomo con resumen y cinco gráficas SVG; funciona sin Internet y se puede imprimir |
| ZIP (`.zip`) | JSON, CSV completo, informe HTML y cinco imágenes PNG |
| PNG / SVG | Vista de análisis actual, incluidas comparaciones, unidad, filtro y tramo seleccionados |
| CSV de vista filtrada | Puntos y valores exactamente visibles en el análisis, con el filtro seleccionado |

Se mantienen las exportaciones CSV, TXT antiguo y PDF existentes. Excel requiere `openpyxl`, ya incluido en `requirements.txt`. Los informes HTML y el paquete ZIP usan datos sin suavizar; para exportar exactamente la vista suavizada o comparativa use el botón PNG/SVG de **Análisis / gráficas**. Los voltajes inexistentes se guardan como `null` en JSON y celdas vacías en Excel/CSV ampliado.

## Logotipo UC en aplicación e informes

Se incluye el logotipo oficial UC (2024), horizontal en color, de la Universidad de Cantabria. **Configuración > Identidad / PDF** permite elegir otro PNG/JPG institucional o restaurar el original. El PDF muestra el logotipo en todas sus páginas, con numeración y espacio reservado en cabecera. La página institucional que publica los formatos oficiales es [Imagen Corporativa IFCA](https://ifca.unican.es/es-es/acerca-del-ifca/imagen-corporativa).

**Configuración > Migración PCL-816** resume el cableado. El puente verifica el modo diferencial y ±5 V después de configurarlos. Debe recompilarse `bridge/build_bridge.bat` en Windows con el SDK DAQNavi; la comprobación física de señales y la calibración con patrones siguen pendientes en el equipo real.
