"""Resumen descriptivo de una captura estable, sin modificar las muestras."""
import math
import statistics


def rapid_voltage_changes(samples):
    """Aviso descriptivo de saltos repetidos; no diagnostica su origen eléctrico."""
    if len(samples) < 20 or samples[-1][0]-samples[0][0] < .2:
        return []
    pairs = [(a, b) for a, b in zip(samples, samples[1:]) if 0 < b[0]-a[0] <= .05]
    if len(pairs) < 15:
        return []
    warnings = []
    for index, name in ((1, 'Fuerza'), (2, 'Deformación')):
        values = [row[index] for row in samples]
        jumps = sum(abs(b[index]-a[index]) >= .25 for a, b in pairs)
        if jumps/len(pairs) >= .2 and max(values)-min(values) >= .5:
            warnings.append(f'{name}: saltos repetidos ({min(values):+.3f} a {max(values):+.3f} V)')
    return warnings


def summarize_noise(samples, saturation=4.95):
    if len(samples) < 3:
        raise ValueError('Se necesitan al menos tres muestras.')
    if any(not all(math.isfinite(v) for v in row) for row in samples):
        raise ValueError('La captura contiene valores no finitos.')
    times = [row[0]-samples[0][0] for row in samples]
    gaps = [b-a for a, b in zip(times, times[1:])]
    if min(gaps) <= 0:
        raise ValueError('Los tiempos deben ser crecientes.')
    result = dict(samples=len(samples), duration_s=times[-1], observed_hz=(len(samples)-1)/times[-1],
                  max_gap_s=max(gaps), channels={})
    for index, name in ((1, 'force'), (2, 'deformation')):
        values = [row[index] for row in samples]
        mean = statistics.mean(values)
        tm = statistics.mean(times)
        slope = sum((t-tm)*(v-mean) for t, v in zip(times, values))/sum((t-tm)**2 for t in times)
        windows = {}
        for seconds in (.25, .5, 1., 2.):
            blocks = {}
            for t, v in zip(times, values):
                block = int(t/seconds)
                if (block+1)*seconds <= times[-1]:
                    blocks.setdefault(block, []).append(v)
            means = [statistics.mean(v) for v in blocks.values()]
            windows[str(seconds)] = dict(blocks=len(means), std_v=statistics.stdev(means) if len(means)>1 else None)
        result['channels'][name] = dict(mean_v=mean, std_v=statistics.stdev(values),
            peak_to_peak_v=max(values)-min(values), min_v=min(values), max_v=max(values),
            drift_v_per_s=slope, saturated_samples=sum(abs(v)>=saturation for v in values), windows=windows)
    return result
