"""Perfil de cableado PCL-816 -> USB-4716, contrastado con sus manuales."""
INPUT_MODE='Differential'
INPUT_RANGE='V_Neg5To5'
LEGACY_AGND=(9,10,19,28,29)


def validate_channels(force,deformation):
    if any(type(ch) is not int or ch not in range(0,16,2) for ch in (force,deformation)):
        raise ValueError('USB-4716: los canales diferenciales positivos son AI0, AI2, … AI14.')
    if force==deformation: raise ValueError('Fuerza y deformación requieren pares distintos.')


def validate_hardware(config):
    validate_channels(config['force_channel'],config['deformation_channel'])
    if config.get('input_mode',INPUT_MODE)!=INPUT_MODE or config.get('input_range',INPUT_RANGE)!=INPUT_RANGE:
        raise ValueError('El puente de esta aplicación requiere modo diferencial y rango ±5 V.')
    p=config['pinout']
    for sensor,channel in [('force',config['force_channel']),('deformation',config['deformation_channel'])]:
        if p[f'usb_{sensor}_plus']!=channel or p[f'usb_{sensor}_minus']!=channel+1:
            raise ValueError('El pinout y los canales de adquisición no coinciden.')
        high=p[f'legacy_{sensor}_high']; low=p[f'legacy_{sensor}_low']
        if high not in (*range(1,9),*range(11,19)) or low!=high+19:
            raise ValueError('PCL-816: seleccione un par H/L válido; no utilice AGND como señal.')
    if p['legacy_force_high']==p['legacy_deformation_high']:
        raise ValueError('Los dos sensores no pueden compartir el mismo par antiguo.')


WIRING_HELP='''Perfil de migración: PCL-816 (CN3 DB37) → USB-4716
Fuerza: pin 1 (H0) → AI0 (+); pin 20 (L0) → AI1 (-).
Deformación: pin 2 (H1) → AI2 (+); pin 21 (L1) → AI3 (-).
Masas analógicas antiguas: CN3 9, 10, 19, 28 y 29. Si existe un conductor de referencia analógica identificado, corresponde al borne AGND del bloque de entradas, no a DGND.
No una automáticamente los retornos AI1/AI3 con AGND; conserve el esquema del acondicionador. No conecte excitación de sensores ni alimentación a las entradas AI.
El programa antiguo no utiliza DI, DO, AO, contador ni disparo externo. Otros cables existentes requieren identificación física: el software no permite deducir su función ni su color.
Rango fijo ±5 V, entradas diferenciales; se leen AI0 y AI2 por software. AI1 y AI3 son los retornos de esos pares, no canales independientes.
Ver docs/MIGRACION_TARJETA.md para orientación, parámetros y comprobaciones.'''
