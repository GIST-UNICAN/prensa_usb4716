"""Promedios por bloques y truncado equivalentes al formulario VB antiguo."""
import math
from plot_cleaning import correct_transient_reversals
from taring import stable_tare


def legacy_rows(rows):
    original=rows
    rows=correct_transient_reversals(rows)
    rows=[{**r,"force_kp":r["force_kp"] if o["force_kp"]>=0 else float("nan")} for r,o in zip(rows,original)]
    result=[]; block=[]
    held=dict(vf=float('nan'),vd=float('nan'),force_kp=0.,deformation_mm=0.)
    for row in rows:
        block.append(row)
        if len(block)==10:
            held={k:sum(r[k] for r in block)/10 for k in held}
            accepted=[r['force_kp'] for r in block if math.isfinite(r['force_kp']) and r['force_kp']>=0]
            held['force_kp']=sum(accepted)/len(accepted) if accepted else 0.
            block=[]
        result.append({**row,**held})
    return result


def legacy_plot_rows(rows):
    visible=legacy_rows(rows); result=[]
    for end in range(10,len(visible)+1,10):
        block=visible[end-10:end]
        result.append(dict(t=block[-1]['t'],
            vf=sum(r['vf'] for r in block)/10,vd=sum(r['vd'] for r in block)/10,
            force_kp=math.floor(sum(r['force_kp'] for r in block)/10),
            deformation_mm=math.floor(100*sum(r['deformation_mm'] for r in block)/10)/100))
    return result


def legacy_text(rows):
    # VB Int redondea hacia menos infinito, incluso con valores negativos.
    return ''.join(f"{round(r['deformation_mm']*100)} * {r['force_kp']} * {r['t']:.6f}\n" for r in legacy_plot_rows(rows))


def legacy_tare(rows,saturation=4.95):
    if len(rows)!=100: raise ValueError('La tara requiere 100 lecturas.')
    if any(not math.isfinite(v) or abs(v)>=saturation for r in rows for v in r[1:]):
        raise ValueError('Saturación o lectura inválida; tara anterior conservada.')
    validation=stable_tare(rows,saturation)
    return dict(stability=validation,method='legacy_mean_100',samples=100,duration_s=rows[-1][0]-rows[0][0],channels=[dict(mean_v=sum(r[i] for r in rows)/100) for i in (1,2)])
