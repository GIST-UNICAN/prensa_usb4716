"""Promedio temporal reproducible y rotura estimada por descenso sostenido."""
import math
import statistics
from collections import deque
from plot_cleaning import correct_transient_reversals
from force_processing import force_series


def time_average(times, values, seconds=1.):
    queue=deque(); total=0.; result=[]
    for t,v in zip(times,values):
        if math.isfinite(v): queue.append((t,v)); total+=v
        while queue and t-queue[0][0]>=seconds:
            total-=queue.popleft()[1]
        result.append(total/len(queue) if queue else float('nan'))
    return result


def detect_rupture(rows):
    """Confirma caída >=1 % del incremento, >=6 sigma y >=5 kp durante 0,3 s.

    Trabaja con medias temporales de 0,15 s; requiere 1 s inicial sin carga.
    La confirmación breve permite actualizar el rojo en aproximadamente 1 s.
    Una descarga voluntaria puede producir la misma señal: es una estimación.
    """
    if len(rows)<20 or rows[-1]['t']-rows[0]['t']<2: return None
    rows=correct_transient_reversals(rows)
    times=[r['t'] for r in rows]
    force=force_series(times,[r['force_kp'] for r in rows],method='Suavizada',seconds=.15)
    baseline_values=[f for t,f in zip(times,force) if .5<=t-times[0]<=1 and math.isfinite(f)]
    if len(baseline_values)<3: return None
    baseline=statistics.median(baseline_values)
    sigma=1.4826*statistics.median(abs(v-baseline) for v in baseline_values)
    peak=None; below=None
    for i,(t,f) in enumerate(zip(times,force)):
        if t-times[0]<1 or not math.isfinite(f): continue
        if peak is None or f>force[peak]: peak=i; below=None
        gain=force[peak]-baseline
        if gain<max(25.,10*sigma): continue
        threshold=max(5.,6*sigma,.01*gain)
        if force[peak]-f>=threshold:
            if below is None: below=i
            if t-times[below]>=.3:
                return dict(index=peak,t=times[peak],confirmed_at=t,force_kp=force[peak],drop_kp=threshold,method='mean_0.15s_drop_1pct_6sigma_0.3s')
        else: below=None
    return None


def displayed_peak(rows):
    """Máximo del dato ya procesado que se dibuja; primer punto de una meseta."""
    valid=[i for i,r in enumerate(rows) if math.isfinite(r['force_kp'])]
    if not valid:return None
    i=max(valid,key=lambda j:rows[j]['force_kp'])
    if rows[i]['force_kp']<=0:return None
    return dict(index=i,t=rows[i]['t'],force_kp=rows[i]['force_kp'],deformation_mm=rows[i].get('deformation_mm'))
