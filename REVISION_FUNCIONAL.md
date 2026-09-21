# Revisión de compatibilidad

Se han comparado `AD_SOFT/FRMSTART.FRM`, `FRMRUN.FRM`, `Form2.frm` y `FILTRAR/FILTRAR.FRM` con la aplicación Python. Los ejecutables de las distintas versiones no se han ejecutado; no se puede certificar que coincidan con el código fuente conservado.

| Función del código antiguo | Aplicación actual |
| --- | --- |
| Lectura de carga y deformación, conversión de voltaje | Conservada con USB-4716 y modo simulado |
| Tara de ambos canales | Conservada; ahora también anula el offset calibrado |
| Lecturas actuales y máximos | Conservada; máximos limitados al ensayo |
| Iniciar, parar, reiniciar | Conservada; confirmación al descartar datos sin guardar |
| Referencia de probeta y nombre de fichero | Conservada; añade operador y notas |
| Guardar TXT con separadores `*` | Añadida exportación compatible: centésimas de mm, kp, segundos relativos |
| Abrir datos antiguos para dibujar | Añadida importación TXT con coma decimal y cambio de medianoche |
| Dibujo mediante plantilla Excel externa | Sustituido por gráficas integradas, zoom y exportación PNG |
| Promedio de 10 lecturas y truncamiento a enteros | Promedio configurable de indicadores; el archivo nuevo conserva cada muestra sin truncar |
| Aviso al salir sin guardar | Añadido también al iniciar, reiniciar y abrir otro ensayo |
| Selección de dispositivos Advantech antiguos | Adaptada a nombre DAQNavi y canales; sin enumeración automática de tarjetas antiguas |
| Campo velocidad en FILTRAR | Añadida velocidad media medida en mm/min; no impone velocidad a la prensa |

El código FILTRAR calcula umbrales del 5 % y 95 %, pero la rutina inspeccionada no los aplica al exportar. La nueva aplicación presenta ese tramo como filtro explícito **Ascenso 5–95 %**, limitado al ascenso hasta el primer pico, y permite exportarlo como CSV de análisis. También incluye media móvil y mediana. Ninguno modifica las muestras originales ni replica `100 * Int(deformacion)`, que pierde precisión y contradice las unidades almacenadas por adquisición.

## Funciones añadidas

- Laboratorio de calibración multipunto: patrones manuales o captura del último segundo, recta, residuos, R², error máximo e historial en `config.json`.
- Captura de calibración independiente de la tara; al aplicar se reinicia la tara del sensor. Dos puntos no permiten evaluar la linealidad: su ajuste es exacto por definición.
- Resumen: número de puntos, duración, carga máxima en kp/kgf/N/kN, deformación al pico y velocidad media entre extremos; la presión se habilita con el área de probeta.
- Marcador del pico en la curva.
- CSV más archivo `.metadata.json` con configuración y tara del ensayo. Mantenga ambos juntos para volver a generar informes con su calibración original.
- Validación y escritura atómica de configuración. Los datos de un ensayo conservan su calibración aunque posteriormente cambie la activa.
- Voltajes originales por lectura; el TXT antiguo carece de voltajes y se representa con `nan`, sin inventarlos.

## Límites de verificación

Las pruebas automáticas cubren calibración, formato antiguo real, unidades, medianoche, tara con offset, máximos, persistencia, configuración inválida y adquisición simulada. La adquisición real, el cableado diferencial y la DLL requieren comprobación en Windows con DAQNavi y la USB-4716 conectada. No se certifica equivalencia de todos los ejecutables históricos ni cumplimiento de una norma de ensayo. La velocidad y la deformación al pico son estadísticas descriptivas.

## Ampliación: biblioteca y análisis

Se incorpora un historial SQLite transaccional con guardado al detener, búsqueda, recuperación y comparación de 2–6 ensayos. El formato JSON versionado permite transportar datos y metadatos sin depender de la base de datos. Se añaden Excel con gráficas editables, HTML autónomo, ZIP individual y ZIP de selección. Las vistas de análisis incorporan deformación, voltajes y velocidad frente al tiempo, unidades de fuerza o presión, filtros y exportación del análisis.

Las pruebas adicionales verifican persistencia tras reabrir, actualización sin duplicados, errores de guardado sin pérdida del estado pendiente, restauración de metadatos, selección comparativa, exportación por lotes, archivos Excel con gráficas, integridad del ZIP, voltajes ausentes y rechazo de datos inválidos. El guardado al detener no equivale a recuperación de un ensayo interrumpido por un cierre inesperado.

## Revisión eléctrica y marca institucional

Se han contrastado los manuales oficiales PCL-816 y USB-4716 y todas las llamadas de adquisición del proyecto VB6. La tabla de conexiones, inventario completo CN3 y parámetros recuperados están en `docs/MIGRACION_TARJETA.md`. Se validan los pares y su coherencia con la configuración antes de conectar. La DLL verifica por lectura posterior el modo diferencial y rango ±5 V. Se corrigió la convención de carga de la DLL a `ctypes.CDLL`, coherente con sus exportaciones `__cdecl`, y el BAT compila desde su propio directorio.

La interfaz admite logotipo institucional y el PDF lo incorpora en cada página. Se ha renderizado y revisado un informe de ejemplo con datos simulados, además de probar automáticamente la presencia de imágenes y pies de página. La suite suma 23 pruebas en el entorno de desarrollo; `requirements-dev.txt` incluye el lector PDF de las pruebas. La DLL todavía requiere compilación con SDK y verificación física en Windows.
