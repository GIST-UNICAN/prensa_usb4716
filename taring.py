"""Tara temporal con media recortada y comprobación de estabilidad."""
import math
import statistics


def stable_tare(rows, saturation=4.95):
    if len(rows)<20:
        raise ValueError('Muestras insuficientes para tarar.')
    if not all(math.isfinite(v) for row in rows for v in row):
        raise ValueError('Lecturas no finitas durante la tara.')
    if any(b[0]<=a[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('Tiempos inválidos durante la tara.')
    def trimmed(values):
        values=sorted(values); trim=int(len(values)*.1)
        return statistics.mean(values[trim:len(values)-trim] if trim else values)
    result=[]
    for index,label in ((1,'Fuerza'),(2,'Deformación')):
        values=[r[index] for r in rows]
        if max(abs(v) for v in values)>=saturation:
            raise ValueError(f'{label}: saturación; tara anterior conservada.')
        sigma=statistics.stdev(values)
        if sigma>.1 or max(values)-min(values)>.5:
            raise ValueError(f'{label}: oscilación excesiva; tara anterior conservada.')
        quarter=max(5,len(values)//4)
        drift=abs(trimmed(values[-quarter:])-trimmed(values[:quarter]))
        if drift>max(.003,5*sigma/math.sqrt(quarter)):
            raise ValueError(f'{label}: señal cambiante; mantenga la máquina descargada y estable.')
        result.append(dict(mean_v=trimmed(values), std_v=sigma, drift_v=drift))
    return dict(method='trimmed_mean_10_percent_each_tail', samples=len(rows),
                duration_s=rows[-1][0]-rows[0][0], channels=result)
