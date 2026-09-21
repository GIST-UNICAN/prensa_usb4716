from __future__ import annotations

import argparse
from xml.sax.saxutils import escape
import csv
import json
import queue
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from daq_api import AdvantechDAQ, MockDAQ
from workbench import Workbench
from analysis_ui import AnalysisUI
from sessions import timestamp
from branding import BrandingUI, DEFAULT_LOGO, pdf_page_branding
from hardware import validate_hardware, WIRING_HELP
from measurement import number, fit_calibration
from units import available_units, from_kp, is_pressure, unit_title
from exports import csv_text
from theme import UC_BACKGROUND, UC_DEEP, UC_INK, UC_MID, UC_PALE, UC_PRIMARY, UC_SOFT
from paths import config_file, output_dir

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    MPL_OK = True
except Exception:
    MPL_OK = False

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    PDF_OK = True
except Exception:
    PDF_OK = False

BASE = Path(__file__).resolve().parent


@dataclass
class Sample:
    t: float
    vf: float
    vd: float
    force_kp: float
    deformation_mm: float


DEFAULT_CONFIG = {
    "device_description": "USB-4716,BID#0",
    "logo_path": DEFAULT_LOGO,
    "input_mode": "Differential",
    "input_range": "V_Neg5To5",
    "force_channel": 0,
    "deformation_channel": 2,
    "force_factor_kp_per_v": -1970.57,
    "force_offset_kp": 0.0,
    "deformation_factor_mm_per_v": 2.643095,
    "deformation_offset_mm": 0.0,
    "sample_hz": 100,
    "display_average_samples": 10,
    "tare_samples": 100,
    "saturation_voltage": 4.95,
    "output_directory": "ensayos",
    "display_unit": "kp",
    "specimen_area_mm2": 0.0,
    "pinout": {
        "legacy_force_high": 1,
        "legacy_force_low": 20,
        "legacy_deformation_high": 2,
        "legacy_deformation_low": 21,
        "usb_force_plus": 0,
        "usb_force_minus": 1,
        "usb_deformation_plus": 2,
        "usb_deformation_minus": 3
    }
}


class App(BrandingUI, AnalysisUI, Workbench, tk.Tk):
    def __init__(self, demo=False):
        super().__init__()
        self.title("Prensa Marshall - Advantech USB-4716")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.cfg_path = config_file()
        self.cfg = self._load_config()
        self.demo = demo
        self.daq = None
        self.q: queue.Queue = queue.Queue()
        self.stop_evt = threading.Event()
        self.worker = None
        self.connected = False
        self.recording = False
        self.tare_pending = False
        self.tare_buffer: list[tuple[float, float]] = []
        self.zero_force_v = 0.0
        self.zero_deform_v = 0.0
        self.force_window = deque(maxlen=int(self.cfg["display_average_samples"]))
        self.deform_window = deque(maxlen=int(self.cfg["display_average_samples"]))
        self.samples: list[Sample] = []
        self.t0 = None
        self.max_force = 0.0
        self.max_deformation = 0.0

        self.test_name = tk.StringVar(value=datetime.now().strftime("ensayo_%Y%m%d_%H%M%S"))
        self.operator = tk.StringVar(value="")
        self.sample_id = tk.StringVar(value="")
        self.notes = tk.StringVar(value="")
        self.status = tk.StringVar(value="Desconectado")
        self.current_force = tk.StringVar(value="0")
        self.current_kn = tk.StringVar(value="0.000")
        self.current_def = tk.StringVar(value="0.00")
        self.max_force_var = tk.StringVar(value="0")
        self.max_def_var = tk.StringVar(value="0.00")
        self.volts_var = tk.StringVar(value="AI fuerza: -- V | AI deformacion: -- V")
        self.display_unit = tk.StringVar(value=self.cfg.get("display_unit", "kp"))

        self._build_ui()
        self.build_workbench()
        self.build_analysis()
        self.after(20, self._poll_queue)

    def _load_config(self):
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        if self.cfg_path.exists():
            try:
                old = json.loads(self.cfg_path.read_text(encoding="utf-8"))
                cfg.update({k: v for k, v in old.items() if k != "pinout"})
                cfg["pinout"].update(old.get("pinout", {}))
            except Exception:
                pass
        return cfg

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=UC_BACKGROUND)
        style.configure("TLabel", background=UC_BACKGROUND, foreground=UC_INK)
        style.configure("TButton", padding=(10, 7), background=UC_PALE, foreground=UC_DEEP, borderwidth=0)
        style.map("TButton", background=[("active", UC_SOFT), ("disabled", "#e7eeee")])
        style.configure("TLabelframe", background="#ffffff", bordercolor=UC_PALE)
        style.configure("TLabelframe.Label", background="#ffffff", foreground=UC_DEEP)
        style.configure("TNotebook", background=UC_BACKGROUND, borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", UC_DEEP)])
        style.configure("TNotebook.Tab", padding=(16, 9))
        style.configure("Treeview", rowheight=27)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        header = ttk.Frame(self, padding=(12, 9))
        header.pack(fill="x")
        self.build_logo_header(header)
        ttk.Label(header, text="Prensa Marshall · Laboratorio", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, textvariable=self.status, font=("Segoe UI", 10, "bold")).pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tab_test = ttk.Frame(self.nb)
        self.tab_data = ttk.Frame(self.nb)
        self.tab_config = ttk.Frame(self.nb)
        self.tab_help = ttk.Frame(self.nb)
        self.nb.add(self.tab_test, text="Ensayo")
        self.nb.add(self.tab_data, text="Datos / Exportacion")
        self.nb.add(self.tab_config, text="Configuracion")
        self.nb.add(self.tab_help, text="Instrucciones")

        self._build_test_tab()
        self._build_data_tab()
        self._build_config_tab()
        self._build_help_tab()

    def _info_button(self, parent, title, text):
        return ttk.Button(parent, text="i", width=3, command=lambda: messagebox.showinfo(title, text))

    def _build_test_tab(self):
        controls = ttk.Frame(self.tab_test, padding=10)
        controls.pack(fill="x")
        self.btn_connect = ttk.Button(controls, text="Conectar", command=self.connect)
        self.btn_connect.pack(side="left", padx=3)
        self._info_button(controls, "Conexion", "Abre la USB-4716 mediante el modulo daq_api.py y la DLL puente DAQNavi. Use modo demo para probar sin hardware.").pack(side="left")
        self.btn_tare = ttk.Button(controls, text="Tarar", command=self.tare, state="disabled")
        self.btn_tare.pack(side="left", padx=(12,3))
        self._info_button(controls, "Tara", "Promedia el numero de lecturas configurado y guarda ese voltaje como cero para fuerza y deformacion.").pack(side="left")
        self.btn_start = ttk.Button(controls, text="Iniciar ensayo", command=self.start_recording, state="disabled")
        self.btn_start.pack(side="left", padx=(12,3))
        self.btn_stop = ttk.Button(controls, text="Parar", command=self.stop_recording, state="disabled")
        self.btn_stop.pack(side="left", padx=3)
        ttk.Button(controls, text="Reiniciar", command=self.reset_test).pack(side="left", padx=12)

        meta = ttk.LabelFrame(self.tab_test, text="Identificacion del ensayo", padding=8)
        meta.pack(fill="x", padx=10, pady=(0,8))
        for c in range(8): meta.columnconfigure(c, weight=1 if c in (1,3,5,7) else 0)
        ttk.Label(meta, text="Referencia").grid(row=0, column=0, sticky="w")
        ttk.Entry(meta, textvariable=self.test_name).grid(row=0, column=1, sticky="ew", padx=(5,12))
        ttk.Label(meta, text="Probeta").grid(row=0, column=2, sticky="w")
        ttk.Entry(meta, textvariable=self.sample_id).grid(row=0, column=3, sticky="ew", padx=(5,12))
        ttk.Label(meta, text="Operador").grid(row=0, column=4, sticky="w")
        ttk.Entry(meta, textvariable=self.operator).grid(row=0, column=5, sticky="ew", padx=(5,12))
        ttk.Label(meta, text="Notas").grid(row=0, column=6, sticky="w")
        ttk.Entry(meta, textvariable=self.notes).grid(row=0, column=7, sticky="ew", padx=(5,0))

        values = ttk.Frame(self.tab_test, padding=(10,0,10,8))
        values.pack(fill="x")
        self._value_box(values, "LECTURA ACTUAL", self.current_force, self.display_unit.get(), 0,
                        "Fuerza calculada a partir del voltaje de fuerza, la tara y la calibracion activa.")
        self._value_box(values, "FUERZA SI", self.current_kn, "kN", 1,
                        "Conversión SI usando 1 kp = 9,80665 N.")
        self._value_box(values, "DEFORMACION", self.current_def, "mm", 2,
                        "Deformacion calculada a partir del segundo canal analogico.")
        self._value_box(values, "FUERZA MAXIMA", self.max_force_var, "kp", 3,
                        "Mayor valor de fuerza registrado desde el inicio del ensayo.")
        self._value_box(values, "DEFORMACION MAX.", self.max_def_var, "mm", 4,
                        "Mayor deformacion registrada desde el inicio del ensayo.")

        chartbox = ttk.LabelFrame(self.tab_test, text="Graficas en tiempo real", padding=6)
        chartbox.pack(fill="both", expand=True, padx=10, pady=(0,8))
        chartbar = ttk.Frame(chartbox)
        chartbar.pack(fill="x")
        ttk.Button(chartbar, text="Exportar curva F-d PNG", command=lambda: self.export_png("fd")).pack(side="left", padx=3)
        ttk.Button(chartbar, text="Exportar fuerza-tiempo PNG", command=lambda: self.export_png("ft")).pack(side="left", padx=3)
        self._info_button(chartbar, "Graficas", "La izquierda representa fuerza frente a deformacion. La derecha representa fuerza frente al tiempo. Ambas se pueden guardar como PNG.").pack(side="left", padx=6)

        if MPL_OK:
            self.fig = Figure(figsize=(10, 4.8), dpi=100, constrained_layout=True)
            self.ax_fd = self.fig.add_subplot(121)
            self.ax_ft = self.fig.add_subplot(122)
            self._format_axes()
            self.canvas = FigureCanvasTkAgg(self.fig, master=chartbox)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            toolbar = NavigationToolbar2Tk(self.canvas, chartbox, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(fill="x")
        else:
            ttk.Label(chartbox, text="Instale matplotlib para ver y exportar graficas: pip install matplotlib").pack(pady=50)

        bottom = ttk.Frame(self.tab_test, padding=(10,0,10,10))
        bottom.pack(fill="x")
        ttk.Label(bottom,text="Mostrar en").pack(side="left",padx=(0,4))
        units=ttk.Combobox(bottom,textvariable=self.display_unit,values=available_units(self.cfg.get('specimen_area_mm2')),state='readonly',width=10)
        units.pack(side="left"); units.bind("<<ComboboxSelected>>",lambda _:self._display_unit_changed())
        ttk.Label(bottom, textvariable=self.volts_var).pack(side="left")
        ttk.Label(bottom, text=f"Saturacion configurada: +/-{self.cfg['saturation_voltage']} V").pack(side="right")

    def _value_box(self, parent, title, variable, unit, col, info):
        f = ttk.LabelFrame(parent, text=title, padding=8)
        f.grid(row=0, column=col, padx=4, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        line = ttk.Frame(f); line.pack(fill="x")
        ttk.Label(line, textvariable=variable, font=("Consolas", 24, "bold")).pack(side="left", expand=True)
        self._info_button(line, title, info).pack(side="right")
        ttk.Label(f, text=unit).pack()

    def _display_unit_changed(self):
        """La selección es de presentación; la adquisición continúa en kp."""
        self.cfg['display_unit']=self.display_unit.get()
        self._update_table_headers(); self._rebuild_table()
        if self.samples:
            peak=max(self.samples,key=lambda s:s.force_kp)
            self.max_force_var.set(f"{from_kp(peak.force_kp,self.display_unit.get(),self.cfg.get('specimen_area_mm2')):.3f}")
        self._redraw_plots()

    def _update_table_headers(self):
        if not hasattr(self,'tree'): return
        unit=self.display_unit.get()
        self.tree.heading('force',text=unit_title(unit)+f' ({unit})')

    def _build_data_tab(self):
        bar = ttk.Frame(self.tab_data, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="Guardar CSV", command=self.save_csv).pack(side="left", padx=3)
        ttk.Button(bar, text="Generar informe PDF", command=self.save_pdf).pack(side="left", padx=3)
        ttk.Button(bar, text="PNG curva F-d", command=lambda: self.export_png("fd")).pack(side="left", padx=3)
        ttk.Button(bar, text="PNG fuerza-tiempo", command=lambda: self.export_png("ft")).pack(side="left", padx=3)
        self._info_button(bar, "Exportacion", "CSV guarda todos los puntos. PDF genera resumen, calibracion, pinout, graficas y tabla completa. PNG exporta la grafica elegida.").pack(side="left", padx=7)

        cols = ("t", "vf", "vd", "force", "kn", "def")
        frame = ttk.Frame(self.tab_data, padding=(10,0,10,10)); frame.pack(fill="both", expand=True)
        self.data_frame = frame
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        headers = {"t":"Tiempo (s)","vf":"V fuerza","vd":"V deform.","force":unit_title(self.display_unit.get())+f" ({self.display_unit.get()})","kn":"Fuerza (kN)","def":"Deform. (mm)"}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=125, anchor="center")
        sy = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0,column=0,sticky="nsew"); sy.grid(row=0,column=1,sticky="ns"); sx.grid(row=1,column=0,sticky="ew")
        frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)

    def _build_config_tab(self):
        sub = ttk.Notebook(self.tab_config)
        sub.pack(fill="both", expand=True, padx=10, pady=10)
        gen = ttk.Frame(sub); pin = ttk.Frame(sub); cal = ttk.Frame(sub)
        sub.add(gen, text="Adquisicion")
        sub.add(pin, text="Pinout")
        sub.add(cal, text="Calibracion")
        self.build_branding_config(sub)
        wiring=ttk.Frame(sub,padding=14); sub.add(wiring,text="Migración PCL-816")
        ttk.Label(wiring,text=WIRING_HELP,wraplength=900,justify="left").pack(anchor="nw")

        self.cfg_vars = {}
        fields = [
            ("device_description", "Dispositivo DAQNavi", str, "Nombre exacto mostrado por Advantech Navigator, por ejemplo USB-4716,BID#0."),
            ("sample_hz", "Frecuencia de muestreo (Hz)", float, "Numero de lecturas por segundo solicitadas por la aplicacion."),
            ("display_average_samples", "Promedio del indicador (muestras)", int, "Media móvil de los indicadores. El registro y las gráficas conservan las lecturas sin suavizar."),
            ("tare_samples", "Muestras para tara", int, "Numero de lecturas utilizadas para calcular el cero."),
            ("saturation_voltage", "Aviso saturacion (V)", float, "Umbral absoluto de voltaje a partir del cual se muestra aviso de proximidad al limite."),
            ("specimen_area_mm2", "Área de probeta (mm²; 0 desactiva presión)", float, "Necesaria para ver y exportar Pa, kPa, MPa y kgf/cm². La fuerza interna no cambia."),
        ]
        for r,(key,label,_,helptext) in enumerate(fields):
            ttk.Label(gen,text=label).grid(row=r,column=0,sticky="w",padx=10,pady=8)
            v=tk.StringVar(value=str(self.cfg[key])); self.cfg_vars[key]=v
            ttk.Entry(gen,textvariable=v,width=34).grid(row=r,column=1,sticky="ew",padx=6,pady=8)
            self._info_button(gen,label,helptext).grid(row=r,column=2,padx=5)
        gen.columnconfigure(1,weight=1)
        ttk.Button(gen,text="Guardar configuracion",command=self.save_configuration).grid(row=len(fields),column=0,columnspan=3,pady=18)

        p = self.cfg["pinout"]
        self.pin_vars = {}
        pin_fields = [
            ("legacy_force_high", "DB37 fuerza H/+", "Pin del DB37 antiguo correspondiente a H0/+ de fuerza."),
            ("legacy_force_low", "DB37 fuerza L/-", "Pin del DB37 antiguo correspondiente a L0/- de fuerza."),
            ("legacy_deformation_high", "DB37 deformacion H/+", "Pin del DB37 antiguo correspondiente a H1/+ de deformacion."),
            ("legacy_deformation_low", "DB37 deformacion L/-", "Pin del DB37 antiguo correspondiente a L1/- de deformacion."),
            ("usb_force_plus", "USB-4716 fuerza AI+", "Entrada AI positiva del par diferencial de fuerza."),
            ("usb_force_minus", "USB-4716 fuerza AI-", "Entrada AI negativa del par diferencial de fuerza."),
            ("usb_deformation_plus", "USB-4716 deformacion AI+", "Entrada AI positiva del par diferencial de deformacion."),
            ("usb_deformation_minus", "USB-4716 deformacion AI-", "Entrada AI negativa del par diferencial de deformacion."),
        ]
        for r,(key,label,helptext) in enumerate(pin_fields):
            ttk.Label(pin,text=label).grid(row=r,column=0,sticky="w",padx=10,pady=7)
            v=tk.StringVar(value=str(p[key])); self.pin_vars[key]=v
            ttk.Spinbox(pin,from_=0,to=37,textvariable=v,width=10).grid(row=r,column=1,sticky="w",padx=6)
            self._info_button(pin,label,helptext).grid(row=r,column=2,padx=4)
        self.pin_preview = tk.StringVar()
        ttk.Separator(pin).grid(row=8,column=0,columnspan=3,sticky="ew",pady=10)
        ttk.Label(pin,text="Esquema resultante",font=("Segoe UI",10,"bold")).grid(row=9,column=0,sticky="nw",padx=10)
        ttk.Label(pin,textvariable=self.pin_preview,justify="left",font=("Consolas",10)).grid(row=9,column=1,columnspan=2,sticky="w",padx=6)
        ttk.Button(pin,text="Guardar pinout",command=self.save_configuration).grid(row=10,column=0,columnspan=3,pady=15)
        for v in self.pin_vars.values(): v.trace_add("write",lambda *_: self._update_pin_preview())
        self._update_pin_preview()

        self.cal_vars = {
            "force_factor": tk.StringVar(value=str(self.cfg["force_factor_kp_per_v"])),
            "force_offset": tk.StringVar(value=str(self.cfg.get("force_offset_kp",0.0))),
            "def_factor": tk.StringVar(value=str(self.cfg["deformation_factor_mm_per_v"])),
            "def_offset": tk.StringVar(value=str(self.cfg.get("deformation_offset_mm",0.0))),
        }
        self._calibration_block(cal,0,"Fuerza","kp", "force")
        self._calibration_block(cal,1,"Deformacion","mm", "def")
        ttk.Button(cal,text="Guardar calibracion",command=self.save_configuration).grid(row=2,column=0,columnspan=2,pady=16)

    def _calibration_block(self,parent,col,title,unit,prefix):
        box=ttk.LabelFrame(parent,text=f"Calibracion de {title.lower()}",padding=12)
        box.grid(row=0,column=col,sticky="nsew",padx=8,pady=8)
        parent.columnconfigure(col,weight=1)
        factor_key = "force_factor" if prefix=="force" else "def_factor"
        offset_key = "force_offset" if prefix=="force" else "def_offset"
        ttk.Label(box,text=f"Factor ({unit}/V)").grid(row=0,column=0,sticky="w",pady=4)
        ttk.Entry(box,textvariable=self.cal_vars[factor_key]).grid(row=0,column=1,sticky="ew",padx=5)
        self._info_button(box,"Factor de calibracion",f"Pendiente de la relacion {unit} = factor * (V - tara) + offset.").grid(row=0,column=2)
        ttk.Label(box,text=f"Offset ({unit})").grid(row=1,column=0,sticky="w",pady=4)
        ttk.Entry(box,textvariable=self.cal_vars[offset_key]).grid(row=1,column=1,sticky="ew",padx=5)
        self._info_button(box,"Offset","Termino independiente de la ecuacion de calibracion despues de aplicar la tara.").grid(row=1,column=2)
        ttk.Separator(box).grid(row=2,column=0,columnspan=3,sticky="ew",pady=8)
        ttk.Label(box,text="Calibracion a 2 puntos",font=("Segoe UI",9,"bold")).grid(row=3,column=0,columnspan=3,sticky="w")
        v1=tk.StringVar(); y1=tk.StringVar(); v2=tk.StringVar(); y2=tk.StringVar()
        setattr(self,f"_{prefix}_cal2",(v1,y1,v2,y2))
        for rr,(lab,var) in enumerate((("Voltaje 1 (V)",v1),(f"Valor 1 ({unit})",y1),("Voltaje 2 (V)",v2),(f"Valor 2 ({unit})",y2)),start=4):
            ttk.Label(box,text=lab).grid(row=rr,column=0,sticky="w",pady=3)
            ttk.Entry(box,textvariable=var,width=16).grid(row=rr,column=1,sticky="ew",padx=5)
        ttk.Button(box,text="Calcular factor y offset",command=lambda p=prefix,u=unit:self.calculate_two_point(p,u)).grid(row=8,column=0,columnspan=3,pady=8)
        box.columnconfigure(1,weight=1)

    def _build_help_tab(self):
        outer=ttk.Frame(self.tab_help,padding=12); outer.pack(fill="both",expand=True)
        txt=tk.Text(outer,wrap="word",font=("Segoe UI",10),padx=12,pady=12)
        sy=ttk.Scrollbar(outer,orient="vertical",command=txt.yview); txt.configure(yscrollcommand=sy.set)
        txt.pack(side="left",fill="both",expand=True); sy.pack(side="right",fill="y")
        helptext="""INSTRUCCIONES DE USO\n\n1. Conexiones\n- Con la prensa apagada, conecte el DB37 de la instalacion al breakout y desde este a la USB-4716 segun el pinout configurado.\n- Configuracion inicial propuesta: DB37 fuerza 1/20 -> USB AI0/AI1; DB37 deformacion 2/21 -> USB AI2/AI3.\n- La aplicacion espera entradas diferenciales y rango +/-5 V.\n\n2. Antes del primer uso\n- Instale Advantech DAQNavi/XNavi y compruebe la USB-4716 en Navigator.\n- Compile bridge\\usb4716_bridge.dll con build_bridge.bat.\n- En Configuracion > Adquisicion indique el nombre exacto del dispositivo.\n\n3. Puesta a cero\n- Con la prensa descargada y en la posicion de referencia pulse Conectar.\n- Compruebe que los voltajes son razonables y no estan cerca de +/-5 V.\n- Pulse Tarar. La aplicacion promedia las muestras configuradas y establece el cero.\n\n4. Calibracion\n- Puede introducir directamente factor y offset.\n- Tambien puede introducir dos puntos conocidos de voltaje y magnitud; la aplicacion calcula la recta y guarda los coeficientes.\n- Ecuacion: magnitud = factor * (voltaje - tara) + offset.\n\n5. Ensayo\n- Identifique referencia, probeta, operador y notas.\n- Pulse Iniciar ensayo.\n- Las graficas fuerza-deformacion y fuerza-tiempo se actualizan en tiempo real.\n- Pulse Parar al finalizar.\n\n6. Resultados\n- Datos / Exportacion permite revisar la tabla completa.\n- CSV conserva voltajes brutos y magnitudes calculadas.\n- PNG exporta cada grafica a alta resolucion.\n- PDF genera un informe con resumen, pinout, calibracion, graficas y tabla de datos.\n\n7. Seguridad y calidad de dato\n- La aplicacion es un sistema de adquisicion, no controla la prensa.\n- Si aparece aviso de saturacion, detenga el ensayo y revise el rango/senal antes de continuar.\n- Conserve los voltajes brutos para permitir recalibraciones futuras.\n"""
        txt.insert("1.0",helptext); txt.configure(state="disabled")

    def _update_pin_preview(self):
        try:
            p={k:int(v.get()) for k,v in self.pin_vars.items()}
            self.pin_preview.set(
                f"FUERZA:      DB37 pin {p['legacy_force_high']} (H/+) -> USB AI{p['usb_force_plus']} (+)\n"
                f"             DB37 pin {p['legacy_force_low']} (L/-) -> USB AI{p['usb_force_minus']} (-)\n\n"
                f"DEFORMACION: DB37 pin {p['legacy_deformation_high']} (H/+) -> USB AI{p['usb_deformation_plus']} (+)\n"
                f"             DB37 pin {p['legacy_deformation_low']} (L/-) -> USB AI{p['usb_deformation_minus']} (-)"
            )
        except Exception:
            self.pin_preview.set("Revise los valores del pinout.")

    def calculate_two_point(self,prefix,unit):
        try:
            v1,y1,v2,y2=getattr(self,f"_{prefix}_cal2")
            a=number(v1.get()); b=number(y1.get()); c=number(v2.get()); d=number(y2.get())
            if c==a: raise ValueError("Los dos voltajes deben ser diferentes")
            fit=fit_calibration([(a,b),(c,d)]); factor=fit["factor"]; offset=fit["offset"]
            if prefix=="force":
                self.cal_vars["force_factor"].set(f"{factor:.9g}"); self.cal_vars["force_offset"].set(f"{offset:.9g}")
            else:
                self.cal_vars["def_factor"].set(f"{factor:.9g}"); self.cal_vars["def_offset"].set(f"{offset:.9g}")
            messagebox.showinfo("Calibracion",f"Recta calculada: {unit} = {factor:.9g} * V + {offset:.9g}\n\nNota: durante el ensayo la tara se resta antes de aplicar esta ecuacion.")
        except Exception as exc:
            messagebox.showerror("Calibracion",str(exc))

    def save_configuration(self):
        if self.connected:
            messagebox.showwarning("Configuracion","Desconecte la DAQ antes de cambiar pinout/canales.")
            return
        try:
            candidate=json.loads(json.dumps(self.cfg))
            candidate["device_description"]=self.cfg_vars["device_description"].get().strip()
            candidate["sample_hz"]=float(self.cfg_vars["sample_hz"].get())
            candidate["display_average_samples"]=int(self.cfg_vars["display_average_samples"].get())
            candidate["tare_samples"]=int(self.cfg_vars["tare_samples"].get())
            candidate["saturation_voltage"]=float(self.cfg_vars["saturation_voltage"].get())
            candidate["specimen_area_mm2"]=float(self.cfg_vars["specimen_area_mm2"].get())
            candidate["display_unit"]=self.display_unit.get()
            p={k:int(v.get()) for k,v in self.pin_vars.items()}
            if p["usb_force_minus"] != p["usb_force_plus"]+1 or p["usb_deformation_minus"] != p["usb_deformation_plus"]+1:
                raise ValueError("En modo diferencial, cada AI- debe ser el canal consecutivo a su AI+ (0/1, 2/3, 4/5...).")
            if p["usb_force_plus"]%2 or p["usb_deformation_plus"]%2:
                raise ValueError("Los canales positivos diferenciales deben comenzar en un canal par: AI0, AI2, AI4...")
            if not all(0 <= p[k] <= 15 for k in p if k.startswith("usb_")):
                raise ValueError("Canales USB fuera de rango 0–15.")
            if p["usb_force_plus"] == p["usb_deformation_plus"]:
                raise ValueError("Fuerza y deformación deben usar pares distintos.")
            if not all(1 <= p[k] <= 37 for k in p if k.startswith("legacy_")):
                raise ValueError("Pines DB37 fuera de rango 1–37.")
            candidate["pinout"].update(p)
            candidate["force_channel"]=p["usb_force_plus"]
            candidate["deformation_channel"]=p["usb_deformation_plus"]
            candidate["force_factor_kp_per_v"]=float(self.cal_vars["force_factor"].get())
            candidate["force_offset_kp"]=float(self.cal_vars["force_offset"].get())
            candidate["deformation_factor_mm_per_v"]=float(self.cal_vars["def_factor"].get())
            candidate["deformation_offset_mm"]=float(self.cal_vars["def_offset"].get())
            for key in ("sample_hz", "saturation_voltage", "specimen_area_mm2", "force_factor_kp_per_v", "deformation_factor_mm_per_v", "force_offset_kp", "deformation_offset_mm"):
                number(candidate[key])
            if not 1 <= candidate["sample_hz"] <= 1000:
                raise ValueError("Frecuencia permitida: 1–1000 Hz.")
            if not 1 <= candidate["display_average_samples"] <= 10000 or not 1 <= candidate["tare_samples"] <= 100000:
                raise ValueError("El número de muestras debe ser positivo y estar dentro de los límites.")
            if not 0 < candidate["saturation_voltage"] <= 5:
                raise ValueError("Saturación permitida: mayor que 0 y hasta 5 V.")
            if candidate['specimen_area_mm2'] < 0:
                raise ValueError('El área de probeta debe ser 0 o positiva.')
            if candidate['display_unit'] not in available_units(candidate['specimen_area_mm2']):
                raise ValueError('La unidad elegida requiere un área de probeta positiva.')
            if not candidate["force_factor_kp_per_v"] or not candidate["deformation_factor_mm_per_v"]:
                raise ValueError("Los factores no pueden ser cero.")
            validate_hardware(candidate)
            tmp=self.cfg_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(candidate,indent=2,ensure_ascii=False),encoding="utf-8")
            tmp.replace(self.cfg_path)
            self.cfg=candidate
            self._display_unit_changed()
            self.zero_force_v=self.zero_deform_v=0.0
            self.force_window=deque(maxlen=int(candidate["display_average_samples"]))
            self.deform_window=deque(maxlen=int(candidate["display_average_samples"]))
            messagebox.showinfo("Configuracion","Configuracion guardada correctamente.")
        except Exception as exc:
            messagebox.showerror("Configuracion",f"No se pudo guardar:\n{exc}")

    def _format_axes(self):
        if not MPL_OK: return
        self.ax_fd.clear(); self.ax_ft.clear()
        self.ax_fd.set_title("Fuerza - deformacion")
        unit=self.display_unit.get(); label=unit_title(unit)
        self.ax_fd.set_xlabel("Deformacion (mm)"); self.ax_fd.set_ylabel(f"{label} ({unit})"); self.ax_fd.grid(True,alpha=.25)
        self.ax_ft.set_title("Fuerza - tiempo")
        self.ax_ft.set_xlabel("Tiempo (s)"); self.ax_ft.set_ylabel(f"{label} ({unit})"); self.ax_ft.grid(True,alpha=.25)

    def _redraw_plots(self):
        if not MPL_OK: return
        self._format_axes()
        if self.samples:
            unit=self.display_unit.get(); area=self.cfg.get('specimen_area_mm2')
            shown=[from_kp(s.force_kp,unit,area) for s in self.samples]
            self.ax_fd.plot([s.deformation_mm for s in self.samples],shown,linewidth=1.5)
            self.ax_ft.plot([s.t for s in self.samples],shown,linewidth=1.5,color=UC_PRIMARY)
            peak=max(self.samples,key=lambda s:s.force_kp)
            peak_value=from_kp(peak.force_kp,unit,area)
            self.ax_fd.scatter([peak.deformation_mm],[peak_value],color=UC_DEEP,zorder=4)
            self.ax_fd.annotate(f"Pico {peak_value:.2f} {unit}",(peak.deformation_mm,peak_value),xytext=(0,10),textcoords="offset points",ha="center")
        self.canvas.draw()
        self.last_plot=time.perf_counter()

    def connect(self):
        if self.connected:
            self.disconnect(); return
        try:
            if self.demo:
                self.daq=MockDAQ()
            else:
                validate_hardware(self.cfg)
                self.daq=AdvantechDAQ(self.cfg["device_description"],self.cfg["force_channel"],self.cfg["deformation_channel"])
            self.daq.connect()
        except Exception as exc:
            messagebox.showerror("Conexion",str(exc)); return
        self.connected=True
        self.status.set("Conectado"+(" (SIMULACION)" if self.demo else ""))
        self.btn_connect.configure(text="Desconectar"); self.btn_tare.configure(state="normal"); self.btn_start.configure(state="normal")
        self.stop_evt.clear(); self.worker=threading.Thread(target=self._acquisition_loop,daemon=True); self.worker.start()

    def disconnect(self):
        self.stop_evt.set()
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=2)
            if self.worker.is_alive():
                self.status.set("Esperando a que termine la lectura de la DAQ"); return False
        if self.recording: self.stop_recording()
        self.tare_pending=False; self.tare_buffer.clear(); self.force_window.clear(); self.deform_window.clear(); self.recent_volts.clear()
        while not self.q.empty():
            try: self.q.get_nowait()
            except queue.Empty: break
        if self.daq:
            try:self.daq.close()
            except Exception:pass
        self.connected=False; self.recording=False; self.status.set("Desconectado")
        self.btn_connect.configure(text="Conectar"); self.btn_tare.configure(state="disabled"); self.btn_start.configure(state="disabled"); self.btn_stop.configure(state="disabled")

    def _acquisition_loop(self):
        period=1.0/max(1.0,float(self.cfg["sample_hz"])); next_t=time.perf_counter()
        while not self.stop_evt.is_set():
            try:
                vf,vd=self.daq.read_voltages(); self.q.put(("sample",time.perf_counter(),vf,vd))
            except Exception as exc:
                self.q.put(("error",str(exc))); return
            next_t+=period; delay=next_t-time.perf_counter()
            if delay>0: self.stop_evt.wait(delay)
            else: next_t=time.perf_counter()

    def _poll_queue(self):
        try:
            deadline=time.perf_counter()+0.015
            while time.perf_counter()<deadline:
                msg=self.q.get_nowait()
                if msg[0]=="error":
                    messagebox.showerror("Adquisicion",msg[1]); self.disconnect(); break
                _,now,vf,vd=msg; self._process_sample(now,vf,vd)
        except queue.Empty: pass
        if self.recording and time.perf_counter()-self.last_plot >= .25:
            self.last_plot=time.perf_counter(); self._redraw_plots(); self.update_summary()
        self.after(20,self._poll_queue)

    def _process_sample(self,now,vf,vd):
        self.recent_volts.append((now,vf,vd))
        self.recent_volts = [s for s in self.recent_volts if now-s[0] <= 1.2]
        self.volts_var.set(f"AI fuerza: {vf:+.4f} V | AI deformacion: {vd:+.4f} V")
        if abs(vf)>=float(self.cfg["saturation_voltage"]) or abs(vd)>=float(self.cfg["saturation_voltage"]):
            self.status.set("ATENCION: entrada proxima a saturacion")
        elif self.connected and not self.tare_pending and not self.recording:
            self.status.set("Conectado"+(" (SIMULACION)" if self.demo else ""))
        if self.tare_pending:
            self.tare_buffer.append((vf,vd))
            if len(self.tare_buffer)>=int(self.cfg["tare_samples"]):
                self.zero_force_v=sum(x[0] for x in self.tare_buffer)/len(self.tare_buffer)+self.cfg.get("force_offset_kp",0)/self.cfg["force_factor_kp_per_v"]
                self.zero_deform_v=sum(x[1] for x in self.tare_buffer)/len(self.tare_buffer)+self.cfg.get("deformation_offset_mm",0)/self.cfg["deformation_factor_mm_per_v"]
                self.tare_pending=False; self.tare_buffer.clear(); self.force_window.clear(); self.deform_window.clear()
                self.status.set(f"Tara aplicada: {self.zero_force_v:+.4f} V / {self.zero_deform_v:+.4f} V")
            return
        self.force_window.append(vf); self.deform_window.append(vd)
        avf=sum(self.force_window)/len(self.force_window); avd=sum(self.deform_window)/len(self.deform_window)
        force=(avf-self.zero_force_v)*float(self.cfg["force_factor_kp_per_v"])+float(self.cfg.get("force_offset_kp",0.0))
        deform=(avd-self.zero_deform_v)*float(self.cfg["deformation_factor_mm_per_v"])+float(self.cfg.get("deformation_offset_mm",0.0))
        kn=from_kp(force,'kN')
        try: shown=from_kp(force,self.display_unit.get(),self.cfg.get('specimen_area_mm2'))
        except ValueError: shown=force
        self.current_force.set(f"{shown:.3f}"); self.current_kn.set(f"{kn:.3f}"); self.current_def.set(f"{deform:.2f}")
        if self.recording:
            if self.t0 is None:self.t0=now
            # Archivo sin suavizado: cada lectura conserva su voltaje y conversión.
            raw_force=(vf-self.zero_force_v)*self.cfg["force_factor_kp_per_v"]+self.cfg.get("force_offset_kp",0)
            raw_def=(vd-self.zero_deform_v)*self.cfg["deformation_factor_mm_per_v"]+self.cfg.get("deformation_offset_mm",0)
            sample=Sample(now-self.t0,vf,vd,raw_force,raw_def)
            self.samples.append(sample); self.dirty=True
            if len(self.samples)==1 or raw_force>self.max_force:
                self.max_force=raw_force; self.max_force_var.set(f"{from_kp(raw_force,self.display_unit.get(),self.cfg.get('specimen_area_mm2')):.3f}")
            if len(self.samples)==1 or raw_def>self.max_deformation:
                self.max_deformation=raw_def; self.max_def_var.set(f"{raw_def:.3f}")
            if len(self.samples)%10==0:self._refresh_table_tail()

    def _refresh_table_tail(self):
        # Mantiene la tabla responsiva mostrando como maximo los ultimos 5000 puntos.
        items=self.tree.get_children()
        if len(items)>5000:
            for iid in items[:1000]:self.tree.delete(iid)
        for s in self.samples[max(0,len(self.samples)-10):]:
            tag=f"{s.t:.5f}"
            if self.tree.exists(tag):continue
            self.tree.insert("", "end", iid=tag, values=(f"{s.t:.3f}",f"{s.vf:.5f}",f"{s.vd:.5f}",f"{from_kp(s.force_kp,self.display_unit.get(),self.cfg.get('specimen_area_mm2')):.3f}",f"{from_kp(s.force_kp,'kN'):.4f}",f"{s.deformation_mm:.4f}"))

    def tare(self):
        if not self.connected or self.recording:return
        self.tare_buffer.clear(); self.tare_pending=True; self.status.set(f"Tarando ({self.cfg['tare_samples']} lecturas)...")

    def start_recording(self):
        if not self.connected or self.tare_pending:return
        if not self.confirm_discard():return
        self.session_id=None; self.acquired_at=timestamp(); self.session_demo=self.demo; self.session_source="Adquisición"; self.comparisons=[]
        self.test_context=json.loads(json.dumps(self.cfg))
        self.test_context["zero_force_v"]=self.zero_force_v
        self.test_context["zero_deform_v"]=self.zero_deform_v
        self.force_window.clear(); self.deform_window.clear()
        self.btn_tare.configure(state="disabled")
        self.samples.clear(); self._clear_table(); self.max_force=self.max_deformation=0.0
        self.max_force_var.set("0"); self.max_def_var.set("0.00"); self.t0=None; self.recording=True
        self.btn_start.configure(state="disabled"); self.btn_stop.configure(state="normal"); self.status.set("Ensayo en curso"); self._redraw_plots()

    def stop_recording(self):
        was_recording=self.recording
        self.btn_tare.configure(state="normal" if self.connected else "disabled")
        self.update_summary()
        self.recording=False; self.btn_start.configure(state="normal" if self.connected else "disabled"); self.btn_stop.configure(state="disabled")
        self.status.set(f"Ensayo detenido - {len(self.samples)} puntos"); self._redraw_plots(); self._rebuild_table()
        if was_recording and self.samples:self.archive_current(automatic=True)
        self.refresh_analysis()

    def reset_test(self):
        if not self.confirm_discard():return
        self.dirty=False; self.test_context=None
        self.session_id=None; self.acquired_at=None; self.comparisons=[]
        self.btn_tare.configure(state="normal" if self.connected else "disabled")
        self.recording=False; self.samples.clear(); self._clear_table(); self.max_force=self.max_deformation=0.0
        self.max_force_var.set("0"); self.max_def_var.set("0.00"); self.btn_stop.configure(state="disabled")
        if self.connected:self.btn_start.configure(state="normal")
        self._redraw_plots(); self.update_summary(); self.refresh_analysis()

    def _clear_table(self):
        for iid in self.tree.get_children():self.tree.delete(iid)

    def _rebuild_table(self):
        self._clear_table()
        for i,s in enumerate(self.samples):
            self.tree.insert("","end",iid=f"row{i}",values=(f"{s.t:.3f}",f"{s.vf:.5f}",f"{s.vd:.5f}",f"{from_kp(s.force_kp,self.display_unit.get(),self.cfg.get('specimen_area_mm2')):.3f}",f"{from_kp(s.force_kp,'kN'):.4f}",f"{s.deformation_mm:.4f}"))

    def _outdir(self):
        return output_dir(self.cfg.get("output_directory","ensayos"))

    def save_csv(self):
        if self.recording:
            messagebox.showinfo("Exportación", "Detenga el ensayo antes de exportar."); return
        if not self.samples:messagebox.showinfo("Guardar","No hay datos de ensayo para guardar."); return
        default=self._outdir()/f"{self.test_name.get().strip() or 'ensayo'}.csv"
        path=filedialog.asksaveasfilename(initialfile=default.name,initialdir=str(default.parent),defaultextension=".csv",filetypes=[("CSV","*.csv")])
        if not path:return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                f.write(csv_text(self.current_session()))
            metadata=dict(configuration=self.test_context, reference=self.test_name.get(), operator=self.operator.get(), sample_id=self.sample_id.get(), notes=self.notes.get(), demo=self.session_demo, acquired_at=self.acquired_at)
            Path(path).with_suffix(".metadata.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding="utf-8")
            self.dirty=False
            self.status.set(f"Guardado: {Path(path).name} + metadatos")
        except OSError as exc:
            messagebox.showerror("Guardar",str(exc))

    def _save_plot_file(self,path,kind):
        if not MPL_OK: raise RuntimeError("Matplotlib no esta instalado")
        fig=Figure(figsize=(8.5,5.2),dpi=150,constrained_layout=True); ax=fig.add_subplot(111)
        unit=self.display_unit.get(); area=self.cfg.get('specimen_area_mm2'); label=unit_title(unit)
        shown=[from_kp(s.force_kp,unit,area) for s in self.samples]
        if kind=="fd":
            ax.set_title(f"Curva {label.lower()} - deformacion"); ax.set_xlabel("Deformacion (mm)"); ax.set_ylabel(f"{label} ({unit})")
            ax.plot([s.deformation_mm for s in self.samples],shown,linewidth=1.7)
        else:
            ax.set_title(f"{label} - tiempo"); ax.set_xlabel("Tiempo (s)"); ax.set_ylabel(f"{label} ({unit})")
            ax.plot([s.t for s in self.samples],shown,linewidth=1.7)
        ax.grid(True,alpha=.25); fig.savefig(path,dpi=180,bbox_inches="tight")

    def export_png(self,kind):
        if self.recording:
            messagebox.showinfo("Exportación", "Detenga el ensayo antes de exportar."); return
        if not self.samples:messagebox.showinfo("PNG","No hay datos de ensayo para exportar."); return
        suffix="fuerza_deformacion" if kind=="fd" else "fuerza_tiempo"
        default=self._outdir()/f"{self.test_name.get().strip() or 'ensayo'}_{suffix}.png"
        path=filedialog.asksaveasfilename(initialfile=default.name,initialdir=str(default.parent),defaultextension=".png",filetypes=[("PNG","*.png")])
        if not path:return
        try:self._save_plot_file(path,kind); self.status.set(f"PNG guardado: {Path(path).name}")
        except Exception as exc:messagebox.showerror("PNG",str(exc))

    def save_pdf(self):
        if self.recording:
            messagebox.showinfo("Exportación", "Detenga el ensayo antes de exportar."); return
        if not self.samples:messagebox.showinfo("PDF","No hay datos de ensayo para generar el informe."); return
        if not PDF_OK:messagebox.showerror("PDF","Falta reportlab. Instale: pip install reportlab"); return
        if not MPL_OK:messagebox.showerror("PDF","Falta matplotlib. Instale: pip install matplotlib"); return
        default=self._outdir()/f"{self.test_name.get().strip() or 'ensayo'}.pdf"
        path=filedialog.asksaveasfilename(initialfile=default.name,initialdir=str(default.parent),defaultextension=".pdf",filetypes=[("PDF","*.pdf")])
        if not path:return
        try:
            with tempfile.TemporaryDirectory() as td:
                pfd=Path(td)/"fd.png"; pft=Path(td)/"ft.png"
                self._save_plot_file(pfd,"fd"); self._save_plot_file(pft,"ft")
                self._build_pdf(path,pfd,pft)
            self.status.set(f"PDF guardado: {Path(path).name}")
        except Exception as exc:messagebox.showerror("PDF",f"No se pudo generar el informe:\n{exc}")

    def _build_pdf(self,path,pfd,pft):
        if self.test_context is None:
            raise ValueError("Este archivo no contiene la configuración de adquisición original. Exporte sus datos a CSV o PNG.")
        cfg=self.test_context
        doc=SimpleDocTemplate(str(path),pagesize=landscape(A4),rightMargin=14*mm,leftMargin=14*mm,topMargin=33*mm,bottomMargin=16*mm)
        styles=getSampleStyleSheet(); title=ParagraphStyle("Title2",parent=styles["Title"],alignment=TA_CENTER,fontSize=18,leading=22,spaceAfter=10)
        story=[Paragraph("Informe de ensayo - Prensa Marshall",title)]
        meta=[
            ["Referencia",self.test_name.get() or "-","Probeta",self.sample_id.get() or "-"],
            ["Operador",self.operator.get() or "-","Adquisición",self.acquired_at or "No disponible"],
            ["Origen", "SIMULACIÓN" if self.session_demo is True else "REAL" if self.session_demo is False else "No verificado", "Informe",datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["Fuerza máxima",f"{self.max_force:.3f} kp / {from_kp(self.max_force,'kgf'):.3f} kgf / {from_kp(self.max_force,'N'):.2f} N / {from_kp(self.max_force,'kN'):.4f} kN","Deformación máxima",f"{self.max_deformation:.4f} mm"],
            ["Duracion",f"{self.samples[-1].t:.2f} s","Puntos",str(len(self.samples))],
            ["Notas",self.notes.get() or "-","Dispositivo",cfg["device_description"]],
        ]
        cell_style=ParagraphStyle("MetaCell",parent=styles["Normal"],fontSize=9,leading=11)
        meta=[[Paragraph(escape(str(value)),cell_style) for value in row] for row in meta]
        t=Table(meta,colWidths=[30*mm,75*mm,38*mm,100*mm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor(UC_PALE)),("BACKGROUND",(2,0),(2,-1),colors.HexColor(UC_PALE)),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),.35,colors.HexColor(UC_SOFT)),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story += [t,Spacer(1,7*mm)]
        p=cfg["pinout"]
        conf=[
            ["Parametro","Fuerza","Deformacion"],
            ["DB37 antiguo",f"{p['legacy_force_high']} (+) / {p['legacy_force_low']} (-)",f"{p['legacy_deformation_high']} (+) / {p['legacy_deformation_low']} (-)"],
            ["USB-4716",f"AI{p['usb_force_plus']} (+) / AI{p['usb_force_minus']} (-)",f"AI{p['usb_deformation_plus']} (+) / AI{p['usb_deformation_minus']} (-)"],
            ["Entrada", "Diferencial / +/-5 V", "Diferencial / +/-5 V"],
            ["Factor",f"{cfg['force_factor_kp_per_v']:.8g} kp/V",f"{cfg['deformation_factor_mm_per_v']:.8g} mm/V"],
            ["Offset",f"{cfg.get('force_offset_kp',0):.8g} kp",f"{cfg.get('deformation_offset_mm',0):.8g} mm"],
            ["Tara",f"{cfg['zero_force_v']:+.6f} V",f"{cfg['zero_deform_v']:+.6f} V"],
        ]
        ct=Table(conf,colWidths=[45*mm,80*mm,80*mm],repeatRows=1)
        ct.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(UC_PALE)),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.35,colors.HexColor(UC_SOFT)),("ALIGN",(1,1),(-1,-1),"CENTER"),("FONTSIZE",(0,0),(-1,-1),9),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story += [Paragraph("Configuracion y calibracion",styles["Heading2"]),ct,PageBreak(),Paragraph("Graficas",styles["Heading2"]),Table([[Image(str(pfd),width=122*mm,height=74*mm),Image(str(pft),width=122*mm,height=74*mm)]],colWidths=[130*mm,130*mm]),PageBreak(),Paragraph("Tabla de datos",styles["Heading2"])]
        area=cfg.get('specimen_area_mm2')
        data=[["t (s)","V fuerza","V deform.","kp","kgf","N","kN","MPa","kgf/cm²","Def. (mm)"]]
        for s in self.samples:
            try: pressure=[f"{from_kp(s.force_kp,u,area):.5g}" for u in ('MPa','kgf/cm²')]
            except ValueError: pressure=['—','—']
            data.append([f"{s.t:.3f}",f"{s.vf:.6f}",f"{s.vd:.6f}",f"{s.force_kp:.3f}",f"{from_kp(s.force_kp,'kgf'):.3f}",f"{from_kp(s.force_kp,'N'):.2f}",f"{from_kp(s.force_kp,'kN'):.5f}",*pressure,f"{s.deformation_mm:.5f}"])
        dt=Table(data,colWidths=[22*mm,27*mm,27*mm,22*mm,22*mm,25*mm,23*mm,22*mm,24*mm,25*mm],repeatRows=1)
        dt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(UC_PALE)),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.25,colors.HexColor(UC_SOFT)),("ALIGN",(0,0),(-1,-1),"CENTER"),("FONTSIZE",(0,0),(-1,-1),7.5),("LEADING",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
        story.append(dt)
        branding=pdf_page_branding(self.cfg)
        doc.build(story,onFirstPage=branding,onLaterPages=branding)

    def on_close(self):
        if not self.confirm_discard():return
        if self.disconnect() is not False:self.destroy()


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--demo",action="store_true",help="Arranca sin hardware con senales simuladas")
    args=p.parse_args(); App(demo=args.demo).mainloop()
