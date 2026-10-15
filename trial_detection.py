"""Detección conservadora del tramo de carga para visualización, sin borrar datos."""
import math
import statistics


def detect_test_interval(rows):
    """Retorna índices [inicio, fin] inclusivos; fin=None mientras sigue activo.

    Requiere un reposo inicial de 1 s. Medias de bloques de 0,25 s,
    umbral de inicio 5 sigma/5 % del pico y retorno sostenido de 0,5 s.
    """
    if len(rows)<5:
        return None
    times=[float(r['t']) for r in rows]
    forces=[float(r['force_kp']) for r in rows]
    if not all(math.isfinite(x) for x in times+forces) or any(b<=a for a,b in zip(times,times[1:])):
        return None
    if times[-1]-times[0]<1.5:
        return None
    bins={}
    for i,t in enumerate(times): bins.setdefault(int((t-times[0])/.25),[]).append(i)
    averaged=[(ids[0],ids[-1],statistics.mean(forces[i] for i in ids)) for ids in bins.values()]
    baseline=[v for first,last,v in averaged if times[first]-times[0]<1.]
    if len(baseline)<3: return None
    base=statistics.median(baseline)
    sigma=1.4826*statistics.median(abs(v-base) for v in baseline)
    direction = 1 if max(v-base for _,_,v in averaged) >= max(base-v for _,_,v in averaged) else -1
    blocks=[(first,last,direction*(v-base)) for first,last,v in averaged]
    peak=max(v for _,_,v in blocks)
    onset=max(1.,5*sigma,.05*peak)
    release=max(.5,3*sigma,.02*peak)
    if peak<=onset:
        return None
    peak_block=max(range(len(blocks)),key=lambda i:blocks[i][2])
    boundary=0; below=None
    for i in range(peak_block,-1,-1):
        first,last,value=blocks[i]
        if value<onset:
            if below is None: below=last
            if times[below]-times[first]>=.5:
                boundary=i+1
                while boundary<peak_block and blocks[boundary][2]<onset: boundary+=1
                break
        else: below=None
    candidate=None; start=None
    for first,last,value in blocks[boundary:peak_block+1]:
        if times[first]-times[0]<1.: continue
        if value>onset:
            if candidate is None: candidate=first
            if times[last]-times[candidate]>=.35:
                start=candidate; break
        else: candidate=None
    if start is None: return None
    below=None
    for first,last,value in blocks[peak_block+1:]:
        if value<release:
            if below is None: below=first
            if times[last]-times[below]>=.5:
                return {'start':start,'end':below,'baseline_kp':base,'threshold_kp':onset}
        else: below=None
    return {'start':start,'end':None,'baseline_kp':base,'threshold_kp':onset}
