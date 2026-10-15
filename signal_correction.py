"""Estimación causal de señal lenta frente a interferencia de red y picos.

Frecuencia estimada sobre los primeros 8 s del ensayo real identificado abajo.
No constituye una referencia metrológica ni recupera la exactitud del sensor.
"""
from collections import deque
import math
import numpy as np

PROFILE = dict(frequency_hz=49.98, window_s=.6, update_s=.1,
               source_session='1183a84f-6dcf-4565-bd25-f3c1a0ce131b', fit_interval_s=[0,8],
               method='causal_huber_linear_plus_mains_v1')


class RealtimeCorrection:
    def __init__(self, frequency_hz=PROFILE['frequency_hz']):
        self.frequency=frequency_hz
        self.reset()

    def reset(self):
        self.rows=deque(maxlen=2000)
        self.value=None
        self.last_fit=None
        self.state='Estabilizando corrección'
        self.downweighted=0

    def update(self, now, vf, vd):
        if not all(math.isfinite(v) for v in (now,vf,vd)):
            self.reset(); self.state='Lectura no finita'; return None
        if self.rows and (now<=self.rows[-1][0] or now-self.rows[-1][0]>.25): self.reset()
        self.rows.append((now,vf,vd))
        while self.rows and now-self.rows[0][0]>PROFILE['window_s']: self.rows.popleft()
        if max(abs(vf),abs(vd))>=4.95:
            self.value=None; self.state='Saturación: estimación suspendida'; return None
        if self.last_fit is not None and now-self.last_fit<PROFILE['update_s']: return self.value
        self.last_fit=now
        if len(self.rows)<24 or now-self.rows[0][0]<.35:
            self.value=None; self.state='Estabilizando corrección'; return None
        a=np.asarray(self.rows,dtype=float)
        if np.any(np.abs(a[:,1:])>=4.95):
            self.value=None; self.state='Saturación reciente'; return None
        t=a[:,0]-now
        hz=(len(a)-1)/(t[-1]-t[0])
        if hz<80:
            self.value=None; self.state='Corrección requiere al menos 80 lecturas/s'; return None
        phase=2*np.pi*self.frequency*t
        x=np.column_stack((np.ones(len(t)),t/PROFILE['window_s'],np.sin(phase),np.cos(phase)))
        _,singular,vh=np.linalg.svd(x,full_matrices=False)
        # A 100 Hz exactos puede faltar una cuadratura de 50 Hz. Solo se admite
        # si el componente lento sigue siendo identificable.
        rank=int(np.sum(singular>singular[0]*1e-5))
        if rank<2 or (rank<4 and np.linalg.norm(vh[rank:,0])>.01):
            self.value=None; self.state='Fases insuficientes para separar interferencia'; return None
        estimates=[]; count=0
        for values in a[:,1:].T:
            weights=np.ones(len(t))
            for _ in range(4):
                root=np.sqrt(weights)
                coeff=np.linalg.lstsq(x*root[:,None],values*root,rcond=1e-5)[0]
                residual=values-x@coeff
                scale=max(1.4826*np.median(np.abs(residual-np.median(residual))),10/65536)
                weights=np.minimum(1.,1.5*scale/np.maximum(np.abs(residual),1e-12))
            estimates.append(float(np.clip(coeff[0],values.min(),values.max())))
            count+=int(np.sum(weights<.5))
        self.value=tuple(estimates)
        self.downweighted=count
        self.state=f'Estimación 50 Hz · {count} observaciones atenuadas en la ventana'
        return self.value
