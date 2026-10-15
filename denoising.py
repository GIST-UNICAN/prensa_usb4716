"""Kalman escalar causal: señal en paseo aleatorio, observación en voltios.

R estimado en los primeros 5 s de captura_20261008_132520.csv, tras quitar
una tendencia lineal. Q elegido para respuesta nominal de 0,15 s a 100 Hz.
El entrenamiento estable posterior ajusta R manteniendo Q independiente.
No es un modelo supervisado ni una corrección de calibración.
"""
import math
import statistics

NOISE_VARIANCES = (0.0003091841523165094, 6.6660806787839095e-06)
RESPONSE_SECONDS = .15


class VoltageKalman:
    def __init__(self, measurement_variance, response_seconds=RESPONSE_SECONDS, process_variance_per_second=None):
        if not math.isfinite(measurement_variance) or measurement_variance <= 0:
            raise ValueError('La varianza debe ser finita y positiva.')
        if not math.isfinite(response_seconds) or response_seconds <= 0:
            raise ValueError('La respuesta debe ser finita y positiva.')
        self.r = measurement_variance
        gain = -math.expm1(-.01/response_seconds)
        self.q_per_second = self.r*gain*gain/(1-gain)/.01
        if process_variance_per_second is not None:
            if not math.isfinite(process_variance_per_second) or process_variance_per_second <= 0:
                raise ValueError('La varianza de proceso debe ser finita y positiva.')
            self.q_per_second = process_variance_per_second
        self.reset()

    def reset(self):
        self.value = None
        self.time = None
        self.variance = self.r

    def update(self, now, voltage):
        if not math.isfinite(now) or not math.isfinite(voltage):
            raise ValueError('Tiempo y voltaje deben ser finitos.')
        # Una pausa larga o un reloj reiniciado inicia un tramo independiente.
        if self.time is None or now <= self.time or now-self.time > 1.:
            self.value, self.time, self.variance = voltage, now, self.r
            return voltage
        predicted = self.variance + self.q_per_second*(now-self.time)
        gain = predicted/(predicted+self.r)
        self.value += gain*(voltage-self.value)
        self.variance = (1-gain)*predicted
        self.time = now
        return self.value


def voltage_filters(profile=None, strength="Normal"):
    scales = {"Normal": 1., "Alto": .09, "Muy alto": .01}
    if strength not in scales:
        raise ValueError('Nivel de suavizado desconocido.')
    if profile is None:
        filters = tuple(VoltageKalman(r) for r in NOISE_VARIANCES)
    else:
        if profile.get('version') != 1 or len(profile.get('channels', [])) != 2:
            raise ValueError('Perfil de Kalman no compatible.')
        filters = tuple(VoltageKalman(c['measurement_variance'], process_variance_per_second=c['process_variance_per_second'])
                        for c in profile['channels'])
    for filt in filters:
        filt.q_per_second *= scales[strength]
    return filters


def hardware_signature(cfg):
    return {key: cfg[key] for key in ('device_description', 'force_channel', 'deformation_channel',
                                     'input_mode', 'input_range', 'sample_hz')}


def train_stable_filter(rows, saturation=4.95):
    """Estima R en el primer 70%; comprueba estabilidad en toda la captura.

    Q se conserva como hipótesis dinámica: no se puede aprender la respuesta a
    cargas cambiantes a partir de una señal constante. Evita escalar Q con R,
    que dejaría la ganancia del filtro invariable al entrenar.
    """
    from noise_analysis import summarize_noise
    summary = summarize_noise(rows, saturation)
    if summary['duration_s'] < 9.99 or len(rows) < 200 or summary['observed_hz'] < 20:
        raise ValueError('Capture al menos 10 s y 200 muestras, a 20 Hz o más.')
    gaps = [b[0]-a[0] for a, b in zip(rows, rows[1:])]
    if max(gaps) > max(.25, 5*statistics.median(gaps)):
        raise ValueError('Hay interrupciones de adquisición; repita la captura.')
    cut = rows[0][0] + summary['duration_s']*.7
    fit_rows = [row for row in rows if row[0] < cut]
    channels = []
    # Suelo de cuantización del rango de 10 V y 16 bits del perfil actual.
    floor = (10/65536)**2/12
    for index, name in ((1, 'force'), (2, 'deformation')):
        label = 'Fuerza' if index == 1 else 'Deformación'
        c = summary['channels'][name]
        if c['saturated_samples']:
            raise ValueError(f'{label}: hay saturación; entrenamiento rechazado.')
        # El rango de ±5 V puede contener una interferencia enorme sin saturar.
        # No normalizarla como ruido entrenable aunque la media sea estable.
        if c['std_v'] > .1 or c['peak_to_peak_v'] > .5:
            raise ValueError(f'{label}: fluctuación excesiva (σ={c["std_v"]:.3f} V; '
                             f'pico a pico={c["peak_to_peak_v"]:.3f} V). '
                             'Revise sensor, acondicionador y cableado antes de entrenar.')
        sigma = max(c['std_v'], math.sqrt(floor))
        if abs(c['drift_v_per_s'])*summary['duration_s'] > 2*sigma:
            raise ValueError(f'{label}: deriva excesiva; mantenga la carga estable y repita.')
        bins = [[] for _ in range(10)]
        for row in rows:
            bins[min(9, int((row[0]-rows[0][0])/summary['duration_s']*10))].append(row[index])
        means = [statistics.mean(b) for b in bins if b]
        if max(means)-min(means) > 2*sigma:
            raise ValueError(f'{label}: cambios de nivel; mantenga la carga estable y repita.')
        tm = statistics.mean(row[0] for row in fit_rows)
        vm = statistics.mean(row[index] for row in fit_rows)
        slope = sum((row[0]-tm)*(row[index]-vm) for row in fit_rows)/sum((row[0]-tm)**2 for row in fit_rows)
        r = max(floor, sum((row[index]-vm-slope*(row[0]-tm))**2 for row in fit_rows)/(len(fit_rows)-2))
        q = VoltageKalman(NOISE_VARIANCES[index-1]).q_per_second
        filt = VoltageKalman(r, process_variance_per_second=q)
        raw, clean = [], []
        for row in rows:
            value = filt.update(row[0], row[index])
            if row[0] >= cut:
                raw.append(row[index]); clean.append(value)
        # Respuesta de referencia a 100 Hz, en régimen estacionario.
        ratio = q*.01/r
        gain = (math.sqrt(ratio*ratio+4*ratio)-ratio)/2
        t90 = .01*math.log(.1)/math.log1p(-min(gain, 1-1e-12))
        channels.append(dict(measurement_variance=r, process_variance_per_second=q,
                             validation_raw_std_v=statistics.stdev(raw),
                             validation_filtered_std_v=statistics.stdev(clean),
                             nominal_t90_s=t90))
    return dict(version=1, channels=channels, summary=summary, fit_fraction=.7,
                stability_rule='drift and ten-block mean spread <= 2 raw standard deviations')
