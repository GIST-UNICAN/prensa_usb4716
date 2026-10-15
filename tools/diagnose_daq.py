"""Diagnóstico de lectura desde CMD: py tools/diagnose_daq.py [--demo]."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daq_api import AdvantechDAQ, MockDAQ
from paths import config_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--seconds', type=float, default=5)
    args = parser.parse_args()
    cfg = json.loads(config_file().read_text(encoding='utf-8')) if config_file().exists() else {}
    device = cfg.get('device_description', 'USB-4716,BID#0')
    fc, dc = cfg.get('force_channel', 0), cfg.get('deformation_channel', 2)
    print('SIMULACION' if args.demo else f'Dispositivo solicitado: {device}')
    print(f'Configuracion: diferencial +/-5 V; fuerza AI{fc}-AI{fc+1}; deformacion AI{dc}-AI{dc+1}')
    daq = MockDAQ() if args.demo else AdvantechDAQ(device, fc, dc)
    try:
        daq.connect()
        start = time.perf_counter()
        print('tiempo_s,fuerza_V,deformacion_V')
        while time.perf_counter()-start < args.seconds:
            vf, vd = daq.read_voltages()
            print(f'{time.perf_counter()-start:.3f},{vf:+.6f},{vd:+.6f}', flush=True)
            time.sleep(.1)
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    finally:
        daq.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
