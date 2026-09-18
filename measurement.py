"""Cálculos independientes de la interfaz y lectura del formato Marshall antiguo."""
import math
from pathlib import Path


def number(value):
    result = float(str(value).strip().replace(',', '.'))
    if not math.isfinite(result):
        raise ValueError('Introduzca números finitos.')
    return result


def fit_calibration(points):
    if len(points) < 2:
        raise ValueError('Añada al menos dos patrones distintos.')
    points = [(number(x), number(y)) for x, y in points]
    xs, ys = zip(*points)
    xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
    xx = sum((x-xm)**2 for x in xs)
    if xx < 1e-18:
        raise ValueError('Los voltajes deben ser distintos.')
    slope = sum((x-xm)*(y-ym) for x,y in points)/xx
    if abs(slope) < 1e-12:
        raise ValueError('Los patrones deben cubrir valores físicos distintos.')
    offset = ym-slope*xm
    residuals = [y-(slope*x+offset) for x,y in points]
    total = sum((y-ym)**2 for y in ys)
    return dict(factor=slope, offset=offset, r2=1-sum(r*r for r in residuals)/total,
                max_error=max(abs(r) for r in residuals), residuals=residuals)


def read_legacy(path):
    """TXT: centésimas de mm * kp * segundos desde medianoche (VB Timer)."""
    result = []
    first = previous = None
    day = 0
    for line_no, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            d, f, t = map(number, line.split('*'))
            if previous is not None and t < previous:
                if previous > 86000 and t < 400:
                    day += 86400
                else:
                    raise ValueError('Tiempo no ordenado')
            previous = t
            t += day
            if first is None:
                first = t
            result.append((t-first, f, d/100))
        except ValueError as exc:
            raise ValueError(f'Línea {line_no}: {exc}') from exc
    if not result:
        raise ValueError('El archivo no contiene lecturas.')
    return result
