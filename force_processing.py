"""Fuerza de compresión: los negativos no participan en los filtros."""
from collections import deque
import math
from denoising import voltage_filters

class ForceFilter:
    def __init__(self,method='Sin filtro',window=10,seconds=1.,gain=1.,profile=None,strength='Alto'):
        self.method=method; self.window=max(1,int(window)); self.seconds=seconds
        self.rows=deque(); self.gain=max(abs(gain),1e-12)
        self.kalman=voltage_filters(profile,strength)[0]
    def update(self,t,value):
        valid=math.isfinite(value) and value>=0
        self.rows.append((t,value if valid else None))
        if self.method in ('Suavizada','Media temporal 1 s'):
            while self.rows and t-self.rows[0][0]>=self.seconds: self.rows.popleft()
        else:
            while len(self.rows)>self.window: self.rows.popleft()
        values=[v for _,v in self.rows if v is not None]
        if self.method=='Kalman':
            if not valid: return 0. if self.kalman.value is None else max(0.,self.kalman.value*self.gain)
            return max(0.,self.kalman.update(t,value/self.gain)*self.gain)
        if self.method=='Mediana': return sorted(values)[len(values)//2] if values else 0.
        if self.method in ('Suavizada','Media temporal 1 s','Media móvil'): return sum(values)/len(values) if values else 0.
        return value if valid else 0.


def force_series(times,values,**kwargs):
    filt=ForceFilter(**kwargs)
    return [filt.update(t,v) for t,v in zip(times,values)]
