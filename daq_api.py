"""Capa de conexion de la aplicacion con la USB-4716.

La GUI no conoce detalles de Advantech. Solo usa la interfaz BaseDAQ.
AdvantechDAQ usa una DLL puente muy pequena compilada contra DAQNavi.
MockDAQ permite probar toda la aplicacion sin hardware.
"""
from __future__ import annotations

import ctypes
import math
import os
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from hardware import validate_channels


class DAQError(RuntimeError):
    pass


class BaseDAQ(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def read_voltages(self) -> tuple[float, float]: ...

    @abstractmethod
    def close(self) -> None: ...


class AdvantechDAQ(BaseDAQ):
    """Conexion real mediante usb4716_bridge.dll.

    La DLL puente usa la API C++ oficial Automation::BDaq de DAQNavi.
    """

    def __init__(self, device_description: str, force_channel: int = 0,
                 deformation_channel: int = 2,
                 dll_path: str | os.PathLike | None = None):
        self.device_description = device_description
        self.force_channel = int(force_channel)
        self.deformation_channel = int(deformation_channel)
        if dll_path is None:
            dll_path = Path(__file__).resolve().parent / "bridge" / "usb4716_bridge.dll"
        self.dll_path = Path(dll_path)
        self._dll = None
        self._connected = False

    def connect(self) -> None:
        try: validate_channels(self.force_channel,self.deformation_channel)
        except ValueError as exc: raise DAQError(str(exc)) from exc
        if os.name != "nt": raise DAQError("La adquisición real requiere Windows, DAQNavi y la DLL x64. Use --demo en este equipo.")
        if not self.dll_path.exists():
            raise DAQError(
                f"No se encuentra {self.dll_path.name}. Compile la DLL puente con bridge\\build_bridge.bat "
                "despues de instalar DAQNavi SDK."
            )
        try:
            self._dll = ctypes.CDLL(str(self.dll_path))
        except OSError as exc:
            raise DAQError(f"No se pudo cargar la DLL puente: {exc}") from exc

        self._dll.daq_open.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int]
        self._dll.daq_open.restype = ctypes.c_int
        self._dll.daq_read_two.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
        self._dll.daq_read_two.restype = ctypes.c_int
        self._dll.daq_close.argtypes = []
        self._dll.daq_close.restype = None

        rc = self._dll.daq_open(self.device_description, self.force_channel, self.deformation_channel)
        if rc != 0:
            self._dll = None
            raise DAQError(
                f"DAQNavi devolvio el codigo 0x{rc & 0xFFFFFFFF:08X} al abrir {self.device_description}. "
                "Compruebe el nombre del dispositivo en Advantech Navigator."
            )
        self._connected = True

    def read_voltages(self) -> tuple[float, float]:
        if not self._connected or self._dll is None:
            raise DAQError("La DAQ no esta conectada")
        vf = ctypes.c_double()
        vd = ctypes.c_double()
        rc = self._dll.daq_read_two(ctypes.byref(vf), ctypes.byref(vd))
        if rc != 0:
            raise DAQError(f"Error de lectura DAQNavi: 0x{rc & 0xFFFFFFFF:08X}")
        return vf.value, vd.value

    def close(self) -> None:
        if self._dll is not None and self._connected:
            try:
                self._dll.daq_close()
            finally:
                self._connected = False
                self._dll = None


class MockDAQ(BaseDAQ):
    """Simulador para desarrollar/probar la interfaz sin la tarjeta."""

    def __init__(self):
        self.t0 = 0.0
        self.connected = False

    def connect(self) -> None:
        self.t0 = time.perf_counter()
        self.connected = True

    def read_voltages(self) -> tuple[float, float]:
        if not self.connected:
            raise DAQError("Simulador no conectado")
        t = time.perf_counter() - self.t0
        # Ciclo de carga triangular suave para demostrar la GUI.
        phase = (t % 18.0) / 18.0
        load = 2 * phase if phase < 0.5 else 2 * (1 - phase)
        force_v = -2.2 * max(0.0, load) + random.gauss(0, 0.003)
        deform_v = 1.15 * max(0.0, load) + 0.03 * math.sin(t * 2) + random.gauss(0, 0.002)
        return force_v, deform_v

    def close(self) -> None:
        self.connected = False
