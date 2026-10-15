"""Limpieza de picos aislados para representación; nunca modifica el registro."""
import math
import statistics


def clean_rows(rows):
    rows=correct_transient_reversals(rows)
    result=[dict(r) for r in rows]
    # Ventana local centrada: al llegar nuevas muestras se confirma el pico.
    for key in ('vf','vd','force_kp','deformation_mm'):
        values=[r[key] for r in rows]
        for i,v in enumerate(values):
            neighbors=[values[j] for j in range(max(0,i-5),min(len(rows),i+6)) if j!=i and math.isfinite(values[j])]
            if len(neighbors)<5: continue
            median=statistics.median(neighbors)
            mad=statistics.median(abs(x-median) for x in neighbors)
            floor=max(1e-8,abs(median)*1e-6)
            support=sum(abs(x-median)<=max(3*1.4826*mad,floor) for x in neighbors)/len(neighbors)
            if support>=.8 and (not math.isfinite(v) or abs(v-median)>max(6*1.4826*mad,floor)):
                # No sustituir un escalón sostenido: deben existir vecinos a ambos lados.
                if 0<i<len(values)-1 and abs(values[i-1]-median)<=max(3*1.4826*mad,floor) and abs(values[i+1]-median)<=max(3*1.4826*mad,floor):
                    result[i][key]=median
    return result


def _correct_dips(rows, value_key, voltage_key, minimum_drop, relative_drop, max_duration=.12):
    """Corrige solo caídas breves con subida previa y recuperación confirmada.

    Necesita dos muestras posteriores: nunca fuerza una curva creciente ni
    sustituye una bajada sostenida. Conserva el registro de entrada.
    """
    result=[dict(r) for r in rows]
    if any(value_key not in r for r in rows): return result
    i=5
    while i<len(rows)-2:
        before=rows[i-5:i]
        f=[r[value_key] for r in before]
        increments=[b-a for a,b in zip(f,f[1:])]
        if not all(math.isfinite(v) for v in f+increments) or min(increments)<0 or f[-1]<=f[0]:
            i+=1; continue
        typical=statistics.median(increments)
        threshold=max(minimum_drop,6*typical,relative_drop*abs(f[-1]))
        if f[-1]-rows[i][value_key]<threshold:
            i+=1; continue
        j=i+1
        while j<len(rows)-1 and rows[j]['t']-rows[i-1]['t']<=max_duration:
            if rows[j][value_key]>=f[-1]-typical and rows[j+1][value_key]>=f[-1]-typical:
                dt=rows[j]['t']-rows[i-1]['t']
                if dt<=0: break
                for k in range(i,j):
                    fraction=(rows[k]['t']-rows[i-1]['t'])/dt
                    for key in (value_key,voltage_key):
                        if key not in rows[i-1] or key not in rows[j]: continue
                        result[k][key]=rows[i-1][key]+fraction*(rows[j][key]-rows[i-1][key])
                i=j
                break
            j+=1
        i+=1
    return result


def correct_force_dips(rows, max_duration=.12):
    return _correct_dips(rows,'force_kp','vf',10.,.15,max_duration)


def correct_transient_reversals(rows):
    force=correct_force_dips(rows)
    return _correct_dips(force,'deformation_mm','vd',.02,0.)


def compression_deformation(values):
    """Recorrido estimado unidireccional de la señal ya filtrada, cero fijo."""
    result=[]; maximum=0.
    for value in values:
        if not math.isfinite(value): result.append(float('nan')); continue
        if value>maximum+.02: maximum=value
        result.append(maximum)
    return result
