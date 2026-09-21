"""Genera un ensayo Marshall reproducible para probar la interfaz sin hardware."""
from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exports import csv_text
from sessions import dumps_session, make_session, session_summary


@dataclass
class Sample:
    t: float
    vf: float
    vd: float
    force_kp: float
    deformation_mm: float


def build_demo_session():
    randomizer = random.Random(4716)
    samples = []
    for index in range(401):
        t = index / 20
        if t <= 12:
            fraction = t / 12
            force = 1275 * math.sin(fraction * math.pi / 2) ** 1.12
            deformation = 5.15 * fraction ** 1.08
        else:
            fraction = (t - 12) / 8
            force = 1275 * (1 - .34 * fraction) + 9 * math.sin(5 * fraction)
            deformation = 5.15 + 1.72 * fraction
        force += randomizer.gauss(0, 4.0)
        deformation += randomizer.gauss(0, .012)
        vf = force / -1970.57 + randomizer.gauss(0, .0008)
        vd = deformation / 2.643095 + randomizer.gauss(0, .0005)
        samples.append(Sample(t, vf, vd, max(0, force), max(0, deformation)))
    config = {
        'device_description': 'USB-4716,BID#0', 'input_mode': 'Differential',
        'input_range': 'V_Neg5To5', 'force_factor_kp_per_v': -1970.57,
        'deformation_factor_mm_per_v': 2.643095, 'sample_hz': 20,
        'specimen_area_mm2': 1000.0, 'display_unit': 'kN',
        'zero_force_v': 0.0, 'zero_deform_v': 0.0,
    }
    return make_session(
        samples,
        metadata={
            'reference': 'DEMO-MARSHALL-USB4716', 'sample_id': 'DEMO-001',
            'operator': 'Simulación integrada', 'demo': True, 'source': 'Datos de prueba',
            'notes': 'Curva sintética: subida hasta 12 s, pico y descenso controlado.',
        },
        configuration=config,
        session_id='demo-marshall-usb4716-001',
        acquired_at=datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc).isoformat(),
    )


def main():
    root = ROOT / 'sample_data'
    root.mkdir(exist_ok=True)
    session = build_demo_session()
    (root / 'ensayo_marshall_simulado.json').write_text(dumps_session(session), encoding='utf-8')
    (root / 'ensayo_marshall_simulado.csv').write_text('\ufeff' + csv_text(session), encoding='utf-8')
    summary = session_summary(session)
    print(f"{summary['points']} muestras · pico {summary['peak_kp']:.2f} kp · {summary['peak_kn']:.3f} kN")
    print(root)


if __name__ == '__main__':
    main()
