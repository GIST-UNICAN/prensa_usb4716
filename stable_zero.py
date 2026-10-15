"""Retención visible por banda de ruido; nunca modifica tara ni voltajes."""
import math

class StableValue:
    def __init__(self, threshold, seconds=.3):
        self.threshold=threshold; self.seconds=seconds; self.value=0.; self.since=None; self.direction=0
    def update(self,t,value):
        if not math.isfinite(value): self.since=None; return value
        delta=value-self.value
        if abs(delta)<=self.threshold:
            self.since=None; self.direction=0; return self.value
        direction=1 if delta>0 else -1
        if self.since is None or direction!=self.direction or t<self.since:
            self.since=t; self.direction=direction
        if t-self.since>=self.seconds:
            self.value=value; self.since=None; self.direction=0
        return self.value


def stable_channels(cfg, tare):
    channels=(tare or {}).get('stability',{}).get('channels',[])
    if len(channels)!=2: return None
    thresholds=[max(1.,5*channels[0]['std_v']*abs(cfg['force_factor_kp_per_v'])),
                max(.02,5*channels[1]['std_v']*abs(cfg['deformation_factor_mm_per_v']))]
    return tuple(StableValue(v) for v in thresholds)
