"""Conversión de unidades. La fuerza se conserva internamente en kp sin redondear."""
from __future__ import annotations

G0 = 9.80665  # m/s², gravedad convencional

FORCE_UNITS = {
    'kp': ('kp', 1.0),
    'kgf': ('kgf', 1.0),
    'N': ('N', G0),
    'kN': ('kN', G0 / 1000.0),
}
PRESSURE_UNITS = ('Pa', 'kPa', 'MPa', 'kgf/cm²')


def is_pressure(unit: str) -> bool:
    return unit in PRESSURE_UNITS


def available_units(area_mm2: float | None = None) -> list[str]:
    units = list(FORCE_UNITS)
    if area_mm2 and area_mm2 > 0:
        units.extend(PRESSURE_UNITS)
    return units


def unit_label(unit: str) -> str:
    return unit


def from_kp(force_kp: float, unit: str, area_mm2: float | None = None) -> float:
    """Convierte kp a fuerza o presión; para presión se exige área de probeta."""
    if unit in FORCE_UNITS:
        return force_kp * FORCE_UNITS[unit][1]
    if not area_mm2 or area_mm2 <= 0:
        raise ValueError('Indique un área de probeta positiva para trabajar en presión.')
    # N/mm² equivale a MPa.
    mpa = force_kp * G0 / area_mm2
    factors = {'Pa': 1_000_000.0, 'kPa': 1_000.0, 'MPa': 1.0, 'kgf/cm²': 100.0 / area_mm2}
    if unit == 'kgf/cm²':
        return force_kp * factors[unit]
    return mpa * factors[unit]


def unit_title(unit: str) -> str:
    return 'Presión' if is_pressure(unit) else 'Fuerza'
