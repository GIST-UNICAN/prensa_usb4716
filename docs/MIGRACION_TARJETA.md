# Migración del sistema Marshall: PCL-816 → USB-4716

## Conclusión y alcance

La tarjeta antigua identificada en el proyecto VB6 es la **Advantech PCL-816**, con dirección ISA `200H`. La nueva es **Advantech USB-4716**, confirmada por el usuario. El programa principal lee solamente dos señales de tensión: carga en el canal diferencial 0 y deformación en el 1. La USB puede sustituir esas dos entradas conservando los acondicionadores, sus alimentaciones, polaridad, rango y factores iniciales.

La PCL-816 tiene 16 entradas diferenciales de 16 bits, hasta 100 kS/s; la USB-4716 tiene 8 diferenciales / 16 simples de 16 bits, hasta 200 kS/s agregadas. No son tarjetas idénticas, ni estas cifras representan la tasa del programa. La aplicación usa lecturas instantáneas por software, no adquisición temporizada por hardware.

La equivalencia del cableado se ha contrastado con los manuales, pero no se ha probado físicamente la tarjeta, los sensores ni los ejecutables históricos. Los colores y empalmes reales no pueden identificarse desde el código. La tabla siguiente supone continuidad directa hasta el conector **CN3 de la PCL-816**, sin adaptadores que cambien la numeración.

## Cable a cable: las cuatro señales utilizadas

Con los equipos sin alimentación, identifique cada conductor por continuidad y por el número grabado en el conector DB37. No cuente contactos mirando una fotografía: la cara de soldadura y la cara de conexión se ven invertidas.

| Conductor que se retira de CN3 / DB37 antiguo | Función | Conectar al borne USB-4716 | Canal que lee la aplicación |
| --- | --- | --- | --- |
| Pin **1**, A/D H0 | Carga, señal positiva | **AI0** | **0**, diferencial |
| Pin **20**, A/D L0 | Carga, retorno negativo | **AI1** | Retorno del canal 0; no se lee como canal separado |
| Pin **2**, A/D H1 | Deformación, señal positiva | **AI2** | **2**, diferencial |
| Pin **21**, A/D L1 | Deformación, retorno negativo | **AI3** | Retorno del canal 2; no se lee como canal separado |

Localización USB: use el bloque serigrafiado de **entradas AI**. La figura 3.1 del manual muestra `AI0, AI1, AI2, AI3, AGND` juntos, junto al extremo donde está USB. Los destinos anteriores son etiquetas de bornes, no números DB37 ni nombres de las salidas AO. Siga la serigrafía de su unidad.

**No conecte la deformación a AI1 por llamarse “canal 1” en la tarjeta antigua:** en este perfil AI1 es el retorno de carga. La lectura nueva de deformación se configura en AI2.

## Referencia, pantalla y alimentación

- CN3 tiene AGND en los pines **9, 10, 19, 28 y 29**. Si un conductor existente está identificado como referencia analógica, su función corresponde a **AGND del bloque de entradas** de la USB. Antes de trasladarlo, confirme que es una referencia y no una pantalla conectada en otro punto.
- H0/L0 y H1/L1 siguen siendo pares diferenciales. **No añada puentes AI1–AGND o AI3–AGND indiscriminadamente.** El esquema de referencia depende de si el acondicionador entrega una señal referenciada o flotante. La USB necesita respetar también su límite de modo común, no solo la diferencia ±5 V. El apéndice A del manual indica 11 V para modo común; no es el rango útil de medición.
- Mantenga la pantalla y puesta a tierra del acondicionador conforme a su esquema. El manual USB recomienda pares trenzados apantallados y conectar la pantalla en un único punto en el origen. No use la pantalla como retorno de señal por suposición.
- **AGND y DGND no se deben puentear**: el manual USB los separa por función.
- Conserve las fuentes y acondicionadores originales de la célula de carga y del transductor. La USB adquiere tensión; no sustituye la excitación de un puente extensométrico ni la electrónica de un LVDT. No conecte cables de excitación, +12 V o +24 V a AI.
- El CN3 analógico de la PCL-816 no proporciona alimentación. CN1/CN2 y módulos auxiliares sí pueden tener otras funciones; cualquier cable conectado a ellos necesita identificación aparte. El código de este proyecto no permite justificar su traslado a un borne de la USB.

## Parámetros recuperados del programa y equivalentes

| Parámetro | Código anterior | Aplicación nueva / equivalencia |
| --- | --- | --- |
| Tarjeta | `PCL-816 I/O=200H` | `USB-4716,BID#0`, sustituir por el nombre exacto de Navigator |
| Dirección ISA | 0x200 | No aplicable a USB; no se copia a BID |
| Entradas utilizadas | Diferenciales 0 y 1 | Positivos físicos 0 y 2; retornos AI1 y AI3 |
| Rango | Texto ±5 V, índice de ganancia 1 de la lista del driver y alarma ±4,95 V | `Differential` + `V_Neg5To5`, impuestos por la DLL y comprobados tras configurar |
| Ganancia | La ganancia depende de la tarjeta y de su tabla de driver | Se selecciona el mismo rango en voltios, **no se copia el código numérico de ganancia** |
| Método de lectura | `DRV_AIVoltageIn`, `TrigMode=0`, dos llamadas secuenciales | Dos lecturas `InstantAiCtrl::Read`, sin trigger externo |
| Temporización | `Timer1.Interval=1` ms solicitado por VB6 | 100 Hz solicitados por defecto, configurable; no equivale a 1 kHz garantizado del programa antiguo |
| Suavizado | Media de bloques de 10 lecturas; el registro vuelve a acumular valores mantenidos y trunca a enteros | Media móvil de 10 en indicadores; se conserva cada muestra sin truncar. El análisis añade media móvil y mediana sin modificar el registro |
| Tara | Pasa a 100 lecturas y toma los ceros de ambos canales | Promedia 100 muestras; compensa también offsets de calibración |
| Conversión fuerza | `(V - cero) × -1970,57` kp | Factor inicial **-1970,57 kp/V**, offset 0 |
| Conversión deformación | `(V - cero) × 2,643095` mm | Factor inicial **2,643095 mm/V**, offset 0 |
| Saturación | Fuera de ±4,95 V | Aviso desde ±4,95 V |
| DI / DO / AO / contador | Sin llamadas de uso en el programa del proyecto | No se utilizan; no trasladar conexiones adicionales por suposición |
| IRQ / DMA / pacer ISA | No usados por la ruta de lectura de la aplicación | No se configuran ni necesitan cableado en esta ruta USB |
| Salida TXT | Centésimas de mm, kp y segundos del día | Exportación compatible con esos campos; tiempo relativo y sin truncamiento destructivo |

No se debe copiar la ganancia interna “×2” de una tarjeta a otra: el rango ±5 V es lo que debe coincidir. Los factores físicos deben comprobarse con patrones después de migrar; no calibran por sí mismos errores del acondicionador o del cableado.

Evidencias locales: `version vieja/AD_SOFT/Adsoft.vbp` incluye `FRMSTART.FRM` como formulario principal. `FRMRUN.FRM` es un ejemplo adicional y no está incluido en ese proyecto. En FRMSTART: constantes y número de lecturas, líneas 718–722; tarjeta/rango, 1028–1036; canales, 1042 y 1060; registro, 1075–1087; lectura y trigger, 1101–1108; promedios, 1119–1127 y 1157–1165; tara, 1188–1212. Los ficheros DRIVER.BAS contienen declaraciones genéricas de funciones, que no significan que el programa las utilice.

## Resto del DB37 antiguo (CN3): inventario

| Canal PCL-816 | H (+) | L (-) | Uso en este proyecto |
| --- | --- | --- | --- |
| 0 | 1 | 20 | Carga |
| 1 | 2 | 21 | Deformación |
| 2 | 3 | 22 | No leído |
| 3 | 4 | 23 | No leído |
| 4 | 5 | 24 | No leído |
| 5 | 6 | 25 | No leído |
| 6 | 7 | 26 | No leído |
| 7 | 8 | 27 | No leído |
| 8 | 11 | 30 | No leído |
| 9 | 12 | 31 | No leído |
| 10 | 13 | 32 | No leído |
| 11 | 14 | 33 | No leído |
| 12 | 15 | 34 | No leído |
| 13 | 16 | 35 | No leído |
| 14 | 17 | 36 | No leído |
| 15 | 18 | 37 | No leído |

Los cinco contactos restantes son AGND: 9, 10, 19, 28 y 29. Esta tabla corresponde a PCL-816, no a PCL-818, cuyo DB37 tiene otras funciones en varios contactos.

## Puesta en marcha y equivalencia práctica

1. Identifique CN3, los cuatro conductores y cualquier masa/pantalla antes de desmontar. Mantenga los acondicionadores y las fuentes existentes.
2. Instale DAQNavi/XNavi en Windows y compruebe la USB-4716 en Navigator. Use Python y SDK de la misma arquitectura x64. Compile `bridge/build_bridge.bat` con las herramientas x64 de Visual Studio.
3. En Navigator, compruebe AI0 diferencial ±5 V y AI2 diferencial ±5 V. Aplique por separado una tensión conocida al par de carga y al de deformación y verifique que solo cambia su canal. El programa vuelve a imponer estos ajustes al conectar.
4. Conecte la salida acondicionada de los sensores según la tabla y compruebe los voltajes antes de tarar. Una carga positiva debe producir fuerza positiva con la calibración elegida; si no ocurre, revise polaridad y acondicionador.
5. Haga tara sin carga y sin desplazamiento de referencia. Compruebe dos o más patrones de fuerza y desplazamiento; registre los resultados en el laboratorio de calibración.
6. Compare una prueba conocida con la antigua instalación: cero, sensibilidad, sentido de variación y pico, teniendo en cuenta el distinto filtrado y la frecuencia efectiva. No hay prueba real de esta migración en este equipo de desarrollo.

## Fuentes del fabricante

- [Manual PCL-816/814B, figuras 1.2 y 3.2, páginas impresas 2 y 16](https://downloadt.advantech.com/download/downloadsr.aspx?File_Id=1-11PRKHJ). Copia local: `docs/hardware/PCL-816_manual.pdf`.
- [Manual USB-4716, edición 3, figuras 3.1 y 3.3 y apéndice A](https://advdownload.advantech.com/productfile/Downloadfile3/1-26D8IVA/USB-4716_User_Manual_Ed.3-FINAL.pdf). Copia local: `docs/hardware/USB-4716_manual.pdf`.
- [Ficha PCL-816 del fabricante](https://advdownload.advantech.com/productfile/PIS/PCL-816/Product%20-%20Datasheet/PCL-816_816-DA_DS20101026174709.pdf).

## Identidad UC

La aplicación incluye el logotipo UC (2024), versión horizontal en color, publicado por la [Universidad de Cantabria](https://ifca.unican.es/es-es/acerca-del-ifca/imagen-corporativa). Puede cambiarlo desde **Configuración > Identidad / PDF**. Aparece en la cabecera de la aplicación y de **cada página del PDF**, conservando su proporción. La identidad se toma de la configuración actual de la aplicación; los datos de calibración del informe siguen siendo los originales del ensayo.
