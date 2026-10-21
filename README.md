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

La compilación se realiza en Windows x64 con PyInstaller y se distribuye como carpeta `onedir`, junto a la DLL puente. El ejecutable y la ventana usan el icono de prensa en la paleta UC. Consulte [docs/COMPILAR_WINDOWS.md](docs/COMPILAR_WINDOWS.md); el script reproducible es `packaging/build_windows.bat`.

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

La pestaña **Configuración → Calibración → Patrones / anillo / versiones** permite elegir fuerza (kp) o deformación (mm), introducir patrones y ajustar una recta con dos o más puntos. Con la DAQ conectada y el ensayo detenido, **Capturar 1 s** toma la media de los voltajes brutos recientes y muestra su variación. Espere a que el patrón se estabilice antes de capturar. Revise la gráfica y los residuos y pulse **Aplicar y guardar calibración**. Los patrones, fecha, errores y condición de simulación quedan en `config.json`. La tara del sensor se reinicia al aplicar; realice una nueva tara sin carga antes del ensayo.

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


## Indicadores y depuración

En Ensayo, seleccione **Directa** para ver la última muestra o **Suavizada** para ver el promedio de las muestras de cada ventana seleccionada (0,25 / 0,5 / 1 / 2 s; por defecto 1 s). El registro y los máximos conservan los datos originales. Las cajas mantienen su tamaño y ajustan la fuente al espacio disponible.

La pestaña **Depuración / Voltajes** muestra ambos pares configurados antes de tara/calibración, la frecuencia observada y el umbral de saturación. Se actualiza cada 100 ms y grafica hasta los últimos 10 segundos (máximo 2000 muestras). Requiere conectar la tarjeta o la simulación.

Diagnóstico desde CMD, con la aplicación desconectada:

```bat
py tools/diagnose_daq.py --seconds 5
py tools/diagnose_daq.py --demo --seconds 5
powershell -NoProfile -Command "Get-PnpDevice -PresentOnly | Where-Object { $_.FriendlyName -match '4716|Advantech|DAQ' } | Format-List Status,Class,FriendlyName,InstanceId"
```

El diagnóstico usa el nombre de dispositivo y los canales de la configuración; imprime voltajes originales o el código de error de DAQNavi.


### Medir la fluctuación con la máquina estable

Conecte la tarjeta y, sin ensayo ni tara en curso, abra **Depuración / Voltajes > Medir fluctuación (10 s)**. Mantenga la carga estable. La captura utiliza las mismas lecturas de la adquisición y calcula media, desviación estándar muestral, pico a pico, pendiente lineal, saturaciones, frecuencia observada y separación máxima entre muestras. Compara la desviación entre promedios de bloques completos de 0,25, 0,5, 1 y 2 segundos; los bloques parciales se excluyen.

**Guardar captura CSV + resumen** exporta todos los voltajes con sus tiempos y un `.metadata.json` con configuración, fecha, indicador de simulación y estadísticas. No altera la tara, calibración, máximos ni ensayos. Desconectar, tarar o iniciar un ensayo cancela una captura incompleta. El promedio reduce fluctuaciones de visualización, pero también oculta cambios rápidos: conserve siempre el registro bruto. Una pendiente en 10 s no identifica por sí sola el origen del ruido ni demuestra deriva del sensor.


### Limpieza de ruido: Kalman

En **Ensayo > Indicadores > Kalman** (o **Depuración / Voltajes > ▶ Kalman / Captura**) se activa un filtro escalar independiente para fuerza y deformación. Estima cada muestra usando solo el pasado y presenta el resultado cada 0,1 s, sin esperar bloques de un segundo. La opción de ventana se aplica únicamente a **Suavizada**. Puede volver a **Directa** en cualquier momento. En **Depuración / Voltajes**, cuatro casillas independientes permiten mostrar u ocultar fuerza original, fuerza corregida, deformación original y deformación corregida. La comparación funciona también cuando los indicadores están en Directa o Suavizada. «Corregida» significa filtrada con Kalman; no modifica la calibración.

El modelo es un paseo aleatorio con ruido de medida, implementado sin dependencias nuevas en `denoising.py`. La varianza de observación se estimó en los primeros cinco segundos de `output/noise/captura_20261008_132520.csv`, quitando una tendencia lineal: fuerza 0,000309184 V²; deformación 0,00000666608 V². La varianza de proceso se eligió para una respuesta nominal de 0,15 s a 100 Hz; se escala con el tiempo real entre lecturas. Con esta elección, ambos canales tienen la misma respuesta nominal, aunque sus varianzas estén en escalas distintas. Es un ajuste inicial para este equipo, no entrenamiento supervisado ni calibración física. Referencia del modelo de estimación: https://pykalman.readthedocs.io/en/latest/class_docs.html

Los estados se reinician al cambiar el modo, reconectar, tarar o iniciar un ensayo, así como tras una pausa mayor de un segundo o un reinicio del reloj. Los máximos, alarmas, tara, capturas de fluctuación y CSV completo siguen utilizando los datos originales. Kalman cambia la lectura actual, las curvas visibles de Ensayo y la comparación de depuración. Las curvas indican el nivel activo y su anotación «Pico visible» corresponde a la curva filtrada. Puede atenuar picos cortos y retrasar cambios rápidos.

Comprobación reproducible:

```bat
.venv\Scripts\python tools\evaluate_denoising.py output\noise\captura_20261008_132520.csv
```

El programa exporta CSV comparativo, JSON de métricas y PNG. En los últimos cinco segundos de esa captura, la desviación de fuerza pasa de 9,511 a 0,939 mV y la de deformación de 2,856 a 0,474 mV. Son reducciones de fluctuación en un tramo declarado estable; sin una referencia limpia no demuestran exactitud ni generalización a ensayos dinámicos. En un escalón sintético a 100 Hz, el filtro alcanza el 90 % del cambio a los 0,34 s. El parámetro de respuesta se fijó por compromiso de retardo, no se optimizó sobre el tramo de evaluación.


### Entrenar Kalman con medidas estables

En **Depuración / Voltajes**, abra el panel ocultable **▶ Kalman / Captura**. Con la tarjeta conectada, sin ensayo ni tara, mantenga la carga estable, elija entre **10 y 120 segundos** (30 por defecto) y pulse **Entrenar**. El progreso aparece en una línea de estado; las estadísticas completas se conservan en el archivo exportado y el perfil, sin cuadro de resultados en pantalla. El botón **Cancelar** interrumpe el entrenamiento sin sustituir el perfil anterior. Ocultar el panel no interrumpe el entrenamiento ni desactiva el filtro.

Se estima una varianza de observación independiente por canal en el primer 70 % de las muestras, tras quitar tendencia lineal. El 30 % final se reserva para una comparación descriptiva de desviaciones bruto/filtrado. El parámetro de proceso Q se mantiene fijo respecto al ajuste inicial: entrenar con más ruido modifica realmente la ganancia y el retardo. No se puede inferir la dinámica bajo carga a partir de medidas estables; el resultado muestra el tiempo nominal hasta el 90 % de un escalón a 100 Hz.

Se rechazan capturas con saturación, menos de 200 muestras, frecuencia observada inferior a 20 Hz o pausas mayores que el máximo de 250 ms y cinco intervalos medianos. La comprobación de estabilidad exige que tanto la deriva total estimada como el recorrido entre medias de diez bloques no superen dos desviaciones estándar de la señal original. Son comprobaciones heurísticas: mantener físicamente la carga estable sigue siendo necesario. Una señal constante usa un suelo de varianza basado en la cuantización de 16 bits y ±5 V.

Si se acepta, el perfil se guarda de forma atómica y se activa Kalman. `kalman_profile.json`, junto a la configuración, conserva parámetros, estadísticas, fecha, identificación de la adquisición y muestras originales de entrenamiento. Se carga al iniciar y al guardar configuración únicamente si coinciden dispositivo, canales, modo, rango y frecuencia. Un perfil incompatible o inválido deja activo el ajuste inicial e indica el motivo. La simulación usa un archivo separado, `kalman_profile.demo.json`, y nunca sustituye el perfil real. Un rechazo, cancelación o fallo al guardar conserva el perfil anterior. Para volver a ver lecturas directas, desactive Kalman o seleccione Directa en Ensayo.


### Diagnóstico de oscilaciones grandes

La adquisición avisa de saltos repetidos cuando, en el tramo reciente, al menos el 20 % de los intervalos de hasta 50 ms cambian 0,25 V o más y la excursión alcanza 0,5 V. Es un aviso descriptivo, no un diagnóstico de cableado: los originales se conservan, incluidos los negativos. Una tensión negativa estable o un único escalón no activan este aviso.

El entrenamiento también rechaza desviación estándar mayor de 0,1 V o recorrido pico a pico mayor de 0,5 V, aunque no haya saturación. Estos umbrales conservadores impiden aprender grandes interferencias como ruido normal. El rechazo conserva el filtro anterior; no corrige ni recorta la señal.

El 08/10/2026 se reprodujeron tensiones de deformación entre −4,353 y +0,030 V en `output/noise/diagnostico_20261008_133719.csv`. Capturas independientes a 137 y 250 Hz mostraron una componente dominante de 50 Hz (ajuste senoidal: 96,1 % y 87,5 % de la variación respectivamente). Es compatible con interferencia de red, pero no identifica por sí solo si el origen está en el sensor, acondicionador, referencia o cableado. Los voltajes provienen directamente de DAQNavi antes del filtro y la calibración. El manual describe el par diferencial consecutivo y los efectos de tensiones de modo común: https://advdownload.advantech.com/productfile/Downloadfile3/1-26D8IVA/USB-4716_User_Manual_Ed.3-FINAL.pdf


Comprobación independiente adicional: `tools/diagnose_single_input.cpp` lee exclusivamente AI2 (o AI0 con argumento `0`) desde el SDK C++, sin GUI, puente Python ni filtro. Verifica diferencial y ±5 V, y escribe unos tres segundos de CSV a 137 Hz. No utiliza salidas. Ejecutar con la aplicación desconectada. Compilación desde un entorno MSVC x64 con el SDK instalado:

```bat
cl /nologo /EHsc /O2 /std:c++17 /I"C:\Advantech\DAQNavi\Inc" tools\diagnose_single_input.cpp /Fe:tmp\diagnose_single_input.exe /Fo:tmp\diagnose_single_input.obj
tmp\diagnose_single_input.exe 2 > output\noise\solo_AI2.csv
```

En la comprobación de AI2 aislada se obtuvo −4,406 a +0,030 V; un seno de 50 Hz explica el 96,7 % de la variación. Invertir el orden de AI0/AI2 mantuvo la anomalía. Estos resultados excluyen la interfaz, Kalman y el cambio entre ambos canales como origen; no permiten distinguir por software entre sensor, acondicionador, cableado/referencia o entrada de la DAQ. Resultados guardados en `output/noise/diagnostico_independiente.json`.


### Distribución visual y suavizado fuerte

Depuración reserva el espacio central a la gráfica. Los paneles **Kalman / Captura** y **Conexión** se pueden plegar; el cuadro grande de resultados se ha eliminado. Las cuatro casillas de curvas permanecen accesibles y el progreso ocupa una línea de estado.

En Ensayo se puede seleccionar **Kalman** y elegir **Normal**, **Alto** (nivel inicial) o **Muy alto**. El nivel escala la varianza de proceso por 1, 0,09 o 0,01 respectivamente, manteniendo el ruido de observación aprendido. Más suavizado atenúa más las oscilaciones pero sigue más lentamente los cambios reales. El selector de ventana de media solo afecta al modo Suavizada. Estos controles están sincronizados con Depuración.

La lectura actual y las curvas de Ensayo se filtran para visualización; los máximos y el CSV y las métricas conservan la adquisición original; PNG y las curvas del PDF muestran la vista seleccionada. La curva visible se recalcula al cambiar el modo o nivel. El suavizado no corrige el desplazamiento de tensión ni sustituye la revisión de la interferencia eléctrica observada.


### Tramo útil y elección de gráficas

En Ensayo, las casillas permiten mostrar cualquier combinación de fuerza–deformación, fuerza–tiempo, deformación–tiempo, voltajes y velocidad. La distribución se adapta al número de gráficas elegidas. **Solo ensayo detectado** está activado inicialmente: busca el episodio dominante de carga tras al menos un segundo de reposo inicial, usando medias de bloques de 0,25 s. El umbral combina el ruido inicial y el 5 % de la excursión máxima; el final requiere retorno bajo el umbral de descarga durante 0,5 s. Los límites son estimados y pueden variar mientras llega información; no paran la adquisición ni recortan el archivo. Sin detección clara la vista queda vacía: desmarque para inspeccionar el registro completo. Análisis ofrece el mismo tramo en su selector.

**Ocultar negativos (vista)** oculta puntos negativos en fuerza/deformación mediante huecos, sin llevarlos artificialmente a cero. No oculta tensiones negativas en Voltajes ni velocidades negativas. Fuerza–deformación muestra puntos sin unir; **Unir puntos F-d** permite volver a la línea. El modo Suavizada también aplica la media a las curvas, no solo a los indicadores. El filtro se calcula antes de recortar para evitar transitorios artificiales al comienzo del tramo visible.

PNG y las curvas del PDF de Ensayo siguen el modo, recorte y ocultación seleccionados. El informe HTML usa una media móvil de aproximadamente un segundo, recorte automático y puntos F-d sin unir; lo declara expresamente. Las métricas y los CSV completos conservan todos los datos originales. El CSV de análisis conserva los valores filtrados del tramo elegido, incluidos negativos: la casilla de ocultación es solo gráfica.

Revisión del programa anterior: `version vieja/AD_SOFT/FRMSTART.FRM` inicializa `numero_lecturas=10` (línea 722), promedia voltajes antes de convertir (líneas 1119–1127 y 1157–1165) y acumula diez valores al escribir el archivo (1075–1085), truncándolos con `Int`. `version vieja/FILTRAR/FILTRAR.FRM` calcula 5 % y 95 % (167–168), pero la rutina inspeccionada exporta todos los registros (173–176); no aplica esos límites. El programa actual conserva precisión y datos brutos, y hace explícitos los filtros de visualización.

### Calibración conjunta con el anillo a 1 mm

En **Configuración → Calibración → Patrones / anillo / versiones**, introduzca la fuerza conocida del certificado del anillo a 1 mm, expresada en **kp**. Sin carga y en la referencia de cero pulse **1. Capturar cero**. Mantenga el anillo en 1 mm y pulse **2. Capturar a 1 mm**: guarda simultáneamente las últimas lecturas originales de ambos canales, con fecha y variación reciente. Pulse **3. Guardar ambas** para ajustar y guardar dos rectas: cero→0 kp/0 mm y punto conocido→fuerza indicada/1 mm.

La calibración exige conexión, lecturas recientes, ausencia de ensayo/tara, voltajes válidos y separación entre puntos suficiente frente al ruido. Usa el voltaje de la última lectura recibida al pulsar (no un valor suavizado ni la media de un segundo). Fuerza y deformación se guardan juntas de forma atómica, con historial; sus taras se reinician. Desconectar invalida las capturas pendientes y cambiar la configuración exige repetirlas. Los ensayos archivados conservan sus coeficientes originales. No introduzca 1 como fuerza: 1 mm es la referencia de desplazamiento; la fuerza debe proceder del certificado.

### Calibración de recorrido 0–1 mm

En Configuración → Calibración → Patrones / anillo / versiones, seleccione **Solo deformación** (predeterminado), capture el cero y después el punto estable de 1 mm, y pulse **3. Aplicar y guardar**. Capturar no aplica el ajuste: el estado indica que está pendiente. Se promedian las lecturas recientes de cada captura. Este modo conserva el factor, offset y tara de fuerza y no exige introducir una fuerza. **Ambas** permite ajustar también fuerza con el valor certificado del anillo.

La pestaña muestra las ecuaciones activas, la fecha y la ruta absoluta de `config.json`. El guardado es atómico e incluye los puntos, estadísticas y coeficientes anteriores; al iniciar se recuperan los coeficientes guardados. La tara del canal recalibrado se reinicia. Los ensayos ya archivados conservan su calibración original.

### Tara y detección de rotura

Tarar recoge exactamente 100 lecturas y calcula su media aritmética, igual que el programa antiguo. Rechaza voltajes no finitos o saturados conservando el cero anterior; si se acepta reinicia los filtros e indicadores a cero. La advertencia de oscilación permanece independiente de la tara. No congela artificialmente la lectura posterior. La saturación eléctrica sigue siendo un aviso de error.

Suavizada utiliza una ventana temporal real; Análisis e informes ofrecen Media temporal 1 s. El cuadro PICO BRUTO identifica expresamente el máximo sin filtrar. El banner PROBETA ROTA muestra una estimación independiente sobre una media de 1 s: exige una caída de al menos el 10 % del incremento de carga, 10 kp y seis desviaciones robustas del nivel inicial, sostenida 0,5 s. Registre un segundo inicial sin carga. El tramo desde el pico estimado aparece rojo en directo y en gráficas exportadas. Una descarga manual puede parecer una rotura; el aviso no controla la máquina ni detiene la adquisición.

### Modo antiguo predeterminado

**Antiguo (10 lecturas)** actualiza los indicadores al completar cada bloque de diez voltajes y aplica la calibración después de restar la tara. Para la curva fuerza–deformación y el TXT acumula diez valores de la lectura mantenida entre actualizaciones, como el bucle VB: aplica `floor` (VB `Int`) a kp y centésimas de mm. No equivale a promediar cien lecturas independientes. La curva une esos mismos puntos en orden temporal; no se ordena por deformación ni se elimina selectivamente el ruido. Los bloques incompletos no se exportan. Los tiempos son los de la adquisición nueva, no se simula el reloj del PC antiguo. CSV bruto e historial conservan las lecturas individuales. Los otros modos siguen disponibles.

Toda la calibración está exclusivamente en Configuración → Calibración, con subpestañas para coeficientes/dos puntos y patrones/anillo/versiones. El laboratorio tiene desplazamiento vertical.

### Rechazo de retrocesos transitorios

Antes del promedio se comprueban caídas breves de fuerza y deformación: cinco muestras previas crecientes, caída superior a seis incrementos habituales (mínimo 10 kp y 15 % para fuerza; 0,02 mm para deformación), recuperación en un máximo de 0,12 s y dos muestras confirmando el retorno. Solo esos tramos se interpolan entre los extremos; una caída pendiente o sostenida se conserva. No se impone monotonía a todo el ensayo. La corrección afecta curvas y TXT procesado; el historial y CSV bruto conservan los originales. Esta comprobación es una extensión del algoritmo antiguo.

La tara conserva la media aritmética de cien lecturas, pero ahora valida dispersión, deriva y saturación antes de aceptar el cero. Si falla, mantiene la tara anterior. No se confunde corregir el cero con eliminar una interferencia sostenida.

### Mediana y recorrido de compresión (predeterminado)

El filtro predeterminado es Mediana de 10 lecturas, tanto en Ensayo como en Análisis e informes. Durante la adquisición, los indicadores se actualizan con el último punto procesado de la curva. La deformación mostrada se estima como recorrido unidireccional: se mantiene el máximo de la señal filtrada, con banda de 0,02 mm respecto al cero fijo de tara. No se ordenan las muestras ni se cambia la fuerza para obligarla a subir. Este supuesto solo corresponde a una prensa que continúa comprimiendo: una descarga o retracción real no se representa en el recorrido estimado. Los voltajes y magnitudes brutas se conservan en historial/CSV, y el método queda en los metadatos de nuevos ensayos. El modo antiguo sigue disponible; su TXT conserva su cálculo histórico.

### Kalman con cero estable

En Ensayo, la casilla **Kalman con cero estable tras tarar** activa Kalman y una retención de valores mostrados. Tras una tara aceptada, cada canal permanece en cero mientras no supere cinco veces la desviación de voltaje medida en la tara, convertida con su factor de calibración (mínimos: 1 kp y 0,02 mm). Exige 0,3 s continuados fuera de banda en la misma dirección. Tras activarse, mantiene el último valor dentro de esa banda para estabilizar las mesetas; permite también descensos de fuerza. La tara no se desplaza. Sin estadísticas de una tara válida, Kalman funciona pero no se aplica un cero artificial. La opción afecta a indicadores, curvas de Ensayo y su exportación PNG; los datos brutos y las herramientas independientes de Análisis se conservan. La retención puede ocultar cambios pequeños dentro de la banda y añade 0,3 s de confirmación al retardo del filtro.

### Fuerza no negativa y precisión de indicadores

Las fuerzas negativas calculadas con la tara se excluyen del denominador y de las muestras de medias, medianas y actualizaciones Kalman. No se sustituyen por ceros antes de promediar. Si una ventana no tiene fuerza válida, muestra cero; Kalman conserva su última estimación válida sin incorporar la lectura negativa. Voltajes de diagnóstico e historial/CSV bruto se mantienen. Los indicadores muestran kp/kgf sin decimales y kN con un decimal; los cálculos conservan precisión interna.

### Resultados Marshall y Excel calculado

La segunda pestaña, Datos / Exportación, abre Resultados calculados con estabilidad máxima, 95 % de carga, deformaciones interpoladas a 50 kp y al 95 %, diferencia Marshall, tangente y deformación corregida. La subpestaña Lecturas brutas mantiene la tabla original. Excel + gráficas exporta Resultados Marshall y Gráfico Marshall, con números ya calculados y gráfica XY editable, además del registro bruto, configuración y resumen existentes; no necesita macros. El cálculo reproduce el VBA de rota 1.xls y rota 2.xls: máxima media de cinco diferencias en la rama ascendente, pendiente entre i−2 e i+2, corte de tangente y truncado a centésimas donde corresponde. Si no hay cruce de umbral o pendiente válida muestra No disponible. Para adquisiciones DAQ usa mediana de 10 y recorrido de compresión; los TXT importados ya procesados no se vuelven a filtrar. La tangente de máxima subida no es el máximo de rotura.

El banner de rotura muestra el pico de fuerza estimado, tiempo relativo al inicio detectado y deformación procesada en ese instante. Si no se detecta inicio, lo indica en lugar de inventar el origen temporal.

### Presentación y exportación de resultados calculados

Datos / Exportación (segunda pestaña) presenta tarjetas de resultados y la curva con tangente. Para adquisiciones DAQ usa una media por bloques de diez lecturas; el último bloque parcial se incluye y se identifica por el número de lecturas. Pantalla y Excel consumen exactamente la misma lista de puntos. El libro tiene Resultados Marshall (puntos y resultados), Gráfico Marshall (resumen y gráfica editable) y Configuración; no añade las muestras brutas al Excel. El historial y el CSV bruto siguen disponibles por separado. Esto actualiza el criterio anterior de mediana en esta pestaña; Ensayo y Análisis conservan sus selectores.

El tramo rojo empieza en la carga máxima de la curva procesada que se dibuja. En directo la caída posterior confirma la detección y se marca retroactivamente ese máximo; al revisar un ensayo terminado se usa su máximo. El banner incluye ese pico, deformación y tiempo desde el inicio detectado. EN 12697-34:2020, apartados 3.1/3.2 y 7.2, toma la carga máxima y la tangente como referencias de estabilidad/flujo; el rojo es una convención visual de esta aplicación. Los cálculos históricos de d50/d95 se mantienen identificados como resultados del VBA antiguo, sin declarar que por sí solos certifiquen cumplimiento normativo.

La comparación de calibraciones conserva el mismo cero físico archivado, elimina la contribución offset/factor de la tara antes de aplicar los factores nuevos y trabaja sobre copias. El ajuste obtenido de la flexión de 1 mm del anillo no valida automáticamente el recorrido de la prensa ni la deformación de la probeta.


### Interfaz y criterio de resultados vigentes

La interfaz tiene tres pestañas: **Directo**, **Exportar** y **Configuración**. Esta sección sustituye las descripciones anteriores de organización y formatos.

Directo muestra Conectar (solo sin conexión), Tarar, Iniciar/Finalizar ensayo, Reiniciar, nombre y Guardar nombre. Al abrir se intenta conectar automáticamente con la USB-4716, sin diálogo modal si no está disponible. La tara valida y promedia 100 lecturas; Iniciar reutiliza una tara manual válida o realiza una nueva si falta. El procesamiento predeterminado usa una media por bloques de diez para indicadores y gráficas; durante la adquisición se muestran bloques completos. Los filtros y gráficas se seleccionan y guardan desde Configuración > Vista.

Altura (mm) y volumen (mm³) son opcionales y editables en Directo y Exportar. Se archivan con el ensayo. Exportar permite cargar con doble clic, identifica el último por fecha de adquisición y ofrece Excel por defecto. Clic derecho > Borrar ensayo abre un diálogo con Confirmar borrado; elimina solo ese registro del historial, sin borrar archivos exportados. Los formatos adicionales se habilitan en Configuración > Archivos y usan los mismos puntos procesados.

Resultados y Excel utilizan bloques de diez, incluyendo el último parcial; los TXT ya procesados no se vuelven a promediar. La curva queda a la izquierda y los valores a la derecha. El Excel incluye gráfica XY con valores en ambos ejes, hojas Resultados Marshall, Gráfico Marshall, Referencia UNE y Configuración, sin añadir muestras brutas. El historial conserva los originales.

Referencia: **UNE-EN 12697-34:2022**, equivalente a EN 12697-34:2020, apartados 3 y 7 y anexo A. F es la deformación en el máximo menos el origen de la tangente A; Ft es carga máxima dividida por pendiente; FT es deformación total en el máximo. La estabilidad corregida es carga máxima en kN multiplicada por c, con c = 5,2 exp(−0,0259 h) o 5,2 exp(−3,2·10⁻⁶ v); el cociente es S/F. Se redondean al final a las precisiones normativas. Los d50/d95 antiguos se identifican solo como información histórica, no como F normativa.

Las celdas amarillas R20/R21 de Gráfico Marshall permiten introducir o cambiar altura/volumen; si ambas están informadas se usa altura. Sin ninguna dimensión, c, S corregida y S/F quedan pendientes. Excel recalcula mediante sus fórmulas al abrir o editar. La tangente numérica de cinco puntos es una estimación de la aplicación que debe revisarse visualmente; también deben comprobarse por separado las condiciones del ensayo y los requisitos del grupo de probetas.
