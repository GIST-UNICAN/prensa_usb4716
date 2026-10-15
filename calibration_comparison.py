"""Recalcular voltajes archivados conservando el cero físico de la tara."""
from copy import deepcopy
import math

INITIAL_CALIBRATION=dict(force_factor_kp_per_v=-1970.57,force_offset_kp=0.,
                         deformation_factor_mm_per_v=2.643095,deformation_offset_mm=0.)


def recalibrate(session,calibration=None):
    calibration=calibration or INITIAL_CALIBRATION
    result=deepcopy(session)
    old=session.get('configuration') or {}
    cfg=result['configuration']
    if not cfg: raise ValueError('El ensayo no contiene la configuración de adquisición.')
    for value,voltage,factor,offset,zero in (
        ('force_kp','vf','force_factor_kp_per_v','force_offset_kp','zero_force_v'),
        ('deformation_mm','vd','deformation_factor_mm_per_v','deformation_offset_mm','zero_deform_v')):
        if zero not in old or not old.get(factor):raise ValueError('Falta la tara o el factor original del ensayo.')
        # El cero archivado incluye offset/factor: quitarlo antes de cambiar la recta.
        physical_zero=old[zero]-old.get(offset,0)/old[factor]
        new_factor=calibration[factor];new_offset=calibration.get(offset,0.)
        cfg.update({factor:new_factor,offset:new_offset,zero:physical_zero+new_offset/new_factor})
        for row in result['samples']:
            if row.get(voltage) is None or not math.isfinite(row[voltage]):
                raise ValueError('No se puede recalcular un ensayo sin voltajes brutos.')
            row[value]=(row[voltage]-physical_zero)*new_factor
    cfg['calibration_comparison']=dict(method='same_physical_tare',source_session_id=session['id'],scenario='Calibración inicial')
    return result
