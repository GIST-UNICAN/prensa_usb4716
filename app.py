from __future__ import annotations

import argparse
from xml.sax.saxutils import escape
import csv
import json
import queue
import statistics
from stable_zero import stable_channels
from force_processing import ForceFilter, force_series
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
from trial_detection import detect_test_interval
from plot_cleaning import clean_rows, compression_deformation
from signal_processing import time_average, detect_rupture, displayed_peak
from legacy_processing import legacy_plot_rows, legacy_tare
from noise_analysis import summarize_noise, rapid_voltage_changes
from denoising import voltage_filters, train_stable_filter, hardware_signature
from units import available_units, from_kp, is_pressure, unit_title
from exports import csv_text, CHARTS, moving_average, median_filter
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
    "enable_extra_exports": False,
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
        try:
            self.iconbitmap(default=str(BASE / 'assets' / 'prensa_marshall_uc.ico'))
        except tk.TclError:
            # macOS y algunos escritorios Linux no admiten iconos .ico en Tk.
            pass
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
        self.view_settings=self.cfg.get("view_settings",{})
        self.live_charts = {kind: tk.BooleanVar(value=self.view_settings.get("charts",{}).get(kind,kind in ("fd","dt"))) for kind in CHARTS}
        self.join_fd = tk.BooleanVar(value=True)
        self.hide_negative = tk.BooleanVar(value=True)
        self.plot_interval = tk.BooleanVar(value=True)
        self.interval_status = tk.StringVar(value="Esperando tramo de carga")
        self.rupture_status = tk.StringVar(value="Sin rotura detectada")
        self.extra_exports=tk.BooleanVar(value=self.cfg.get("enable_extra_exports",False))
        self.stable_zero=tk.BooleanVar(value=self.cfg.get("view_settings",{}).get("stable_zero",False))
        self.display_mode = tk.StringVar(value=self.view_settings.get("mode","Media de 10 lecturas"))
        self.display_buffer = []
        self.display_started = None
        self.debug_history = deque(maxlen=2000)
        self.filtered_history = deque(maxlen=2000)
        self.kalman_strength = tk.StringVar(value=self.view_settings.get("strength","Alto"))
        self.kalman_profile = None
        self.kalman_status = tk.StringVar(value="Kalman: ajuste inicial")
        self.training_seconds = tk.StringVar(value="30")
        self.voltage_filters = voltage_filters(strength=self.kalman_strength.get())
        self._load_kalman_profile()
        self.signal_alert = ""
        self.last_signal_check = None
        self.debug_last = 0.0
        self.noise_training = False
        self.noise_duration = 10
        self.noise_capture = None
        self.noise_result = None
        self.noise_rows = []
        self.display_seconds = tk.StringVar(value="1")
        self.samples: list[Sample] = []
        self.t0 = None
        self.max_force = 0.0
        self.max_deformation = 0.0

        self.test_name = tk.StringVar(value=self.cfg.get("draft_trial_reference") or datetime.now().strftime("ensayo_%Y%m%d_%H%M%S"))
        self.name_saved=tk.StringVar(value="Nombre guardado" if self.cfg.get("draft_trial_reference") else "Nombre sin guardar")
        self.test_name.trace_add("write",lambda *_:self.name_saved.set("Nombre sin guardar"))
        self.connection_state=tk.StringVar(value="Tarjeta desconectada")
        self.operator = tk.StringVar(value="")
        self.sample_id = tk.StringVar(value="")
        self.notes = tk.StringVar(value="")
        self.status = tk.StringVar(value="Desconectado")
        self.current_force = tk.StringVar(value="0")
        self.current_kn = tk.StringVar(value="0.0")
        self.current_def = tk.StringVar(value="0.00")
        self.max_force_var = tk.StringVar(value="0")
        self.max_def_var = tk.StringVar(value="0.00")
        self.volts_var = tk.StringVar(value="AI fuerza: -- V | AI deformacion: -- V")
        self.display_unit = tk.StringVar(value=self.cfg.get("display_unit", "kp"))

        self._build_ui()
        self.build_workbench()
        self.build_analysis()
        self._redraw_plots()
        self.after(20, self._poll_queue)
        if not self.demo:self.after(250,lambda:self.connect(automatic=True))

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
        style.configure("Config.TNotebook.Tab",padding=(7,6))
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
        self.nb.add(self.tab_test, text="Directo")
        self.nb.add(self.tab_data, text="Exportar")
        self.nb.add(self.tab_config, text="Configuración")

        self._build_config_tab()
        self.tab_help=ttk.Frame(self.config_notebook)
        self.config_notebook.add(self.tab_help,text="Ayuda")
        self._build_test_tab()
        self._build_data_tab()
        self._build_help_tab()
        self._build_debug_tab()

    def _info_button(self, parent, title, text):
        return ttk.Button(parent, text="i", width=3, command=lambda: messagebox.showinfo(title, text))

    def save_trial_name(self):
        name=self.test_name.get().strip()
        if not name:
            messagebox.showerror('Nombre del ensayo','Escriba un nombre para el ensayo.');return
        self.test_name.set(name)
        try:
            if self.samples and not self.recording:
                if not self.archive_current():return
            else:
                cfg={**self.cfg,'draft_trial_reference':name}
                tmp=self.cfg_path.with_suffix('.tmp')
                tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(self.cfg_path)
                self.cfg=cfg
            self.name_saved.set('Nombre guardado' if not self.recording else 'Nombre confirmado; se archiva al finalizar')
            self.status.set('Nombre del ensayo guardado: '+name)
        except OSError as exc:messagebox.showerror('Guardar nombre',str(exc))

    def operator_tare(self):
        if not self.connected:self.connect()
        if self.connected:self.tare()

    def operator_trial_action(self):
        if self.recording:
            self.stop_recording();return
        if not self.connected:self.connect()
        if not self.connected:return
        if getattr(self,"tare_valid",False):
            self.start_recording();return
        self.operator_start_pending=True
        self.tare()
        self.btn_start.configure(state='disabled',text='Tarando…')

    def save_view_preferences(self):
        cfg=json.loads(json.dumps(self.cfg))
        cfg['enable_extra_exports']=self.extra_exports.get()
        cfg['view_settings']={'mode':self.display_mode.get(),'stable_zero':self.stable_zero.get(),'charts':{k:v.get() for k,v in self.live_charts.items()},'strength':self.kalman_strength.get()}
        try:
            tmp=self.cfg_path.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(self.cfg_path)
            self.cfg=cfg;self.status.set('Preferencias guardadas')
        except OSError as exc:messagebox.showerror('Preferencias',str(exc))

    def _update_extra_exports(self):
        self.cfg['enable_extra_exports']=self.extra_exports.get()
        if hasattr(self,'extra_export_bar'):
            if self.extra_exports.get():self.extra_export_bar.pack(fill='x',before=self.history_host)
            else:self.extra_export_bar.pack_forget()

    def _build_test_tab(self):
        actions=ttk.Frame(self.tab_test,padding=10);actions.pack(fill='x')
        self.btn_start=ttk.Button(actions,text='Iniciar ensayo',command=self.operator_trial_action)
        self.btn_start.pack(side='left',padx=3)
        self.btn_tare=ttk.Button(actions,text='Tarar',command=self.operator_tare);self.btn_tare.pack(side='left',before=self.btn_start,padx=3)
        self.btn_reset=ttk.Button(actions,text='Reiniciar',command=self.reset_test);self.btn_reset.pack(side='left',padx=3)
        self.specimen_height=tk.StringVar();self.specimen_volume=tk.StringVar()
        self.geometry_controls(actions)
        self.btn_connect=ttk.Button(actions,text='Conectar',command=self.connect);self.btn_connect.pack(side='left',before=self.btn_tare,padx=3)
        ttk.Label(actions,textvariable=self.connection_state).pack(side='right',padx=5)
        identity=ttk.Frame(self.tab_test,padding=(10,0,10,8));identity.pack(fill='x',after=actions)
        ttk.Label(identity,text='Nombre del ensayo').pack(side='left',padx=(0,5))
        ttk.Entry(identity,textvariable=self.test_name,width=34).pack(side='left')
        ttk.Button(identity,text='Guardar nombre',command=self.save_trial_name).pack(side='left',padx=5)
        ttk.Label(identity,textvariable=self.name_saved).pack(side='left',padx=5)
        controls=ttk.Frame(self.tab_view_config);controls.pack(fill='x',pady=(0,8))
        ttk.Button(controls,text='Desconectar tarjeta',command=self.disconnect).pack(side='left',padx=3)
        self.btn_stop=ttk.Button(controls,text='Parar ensayo',command=self.stop_recording,state='disabled');self.btn_stop.pack(side='left',padx=3)
        ttk.Button(controls,text='Reiniciar',command=self.reset_test).pack(side='left',padx=3)
        ttk.Button(controls,text='Guardar vista',command=self.save_view_preferences).pack(side='left',padx=3)
        meta = ttk.LabelFrame(self.tab_view_config, text="Identificacion del ensayo", padding=8)
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

        displaybar = ttk.Frame(self.tab_view_config, padding=(10, 0, 10, 6))
        displaybar.pack(fill="x")
        ttk.Label(displaybar, text="Indicadores:").pack(side="left")
        mode_box=ttk.Combobox(displaybar,textvariable=self.display_mode,values=('Media de 10 lecturas','Mediana','Antiguo (10 lecturas)','Directa','Suavizada','Kalman'),state='readonly',width=22)
        mode_box.pack(side='left',padx=6);mode_box.bind('<<ComboboxSelected>>',lambda _:self._display_controls_changed())
        ttk.Label(displaybar, text="Ventana media:").pack(side="left")
        interval = ttk.Combobox(displaybar, textvariable=self.display_seconds, values=("0.25", "0.5", "1", "2"), state="readonly", width=5)
        interval.pack(side="left")
        interval.bind("<<ComboboxSelected>>", lambda _: self._reset_display())
        ttk.Label(displaybar, text="s").pack(side="left", padx=(2,8))
        ttk.Label(displaybar, text="Kalman:").pack(side="left", padx=(8,3))
        strength = ttk.Combobox(displaybar, textvariable=self.kalman_strength, values=("Normal", "Alto", "Muy alto"), state="readonly", width=9)
        strength.pack(side="left")
        strength.bind("<<ComboboxSelected>>", lambda _: self._display_controls_changed())

        self._info_button(displaybar, "Limpieza de ruido", "Antiguo: media de bloques de 10 lecturas; tara de 100. Directa: última muestra. Suavizada: promedio de la ventana elegida. Kalman: estimación continua por canal, mostrada cada 0,1 s; la ventana media no se aplica. Ajuste inicial con una captura estable; puede atenuar picos rápidos. Kalman suaviza indicadores y curvas de esta pestaña; los máximos, alarmas, tara y archivos conservan los datos originales. Más suavizado añade retardo.").pack(side="right")

        ttk.Checkbutton(self.tab_view_config,text="Kalman con cero estable tras tarar (5 × ruido; confirma cambios durante 0,3 s)",variable=self.stable_zero,command=self._stable_zero_changed).pack(anchor="w",padx=12)
        choices = ttk.Frame(self.tab_view_config)
        choices.pack(fill="x")
        for kind,title in CHARTS.items():
            ttk.Checkbutton(choices, text=title, variable=self.live_charts[kind], command=self._redraw_plots).pack(side="left", padx=4)
        options = ttk.Frame(self.tab_view_config)
        options.pack(fill="x")
        ttk.Checkbutton(options, text="Ocultar negativos (vista)", variable=self.hide_negative, command=self._redraw_plots).pack(side="left", padx=4)
        ttk.Checkbutton(options, text="Unir puntos F-d", variable=self.join_fd, command=self._redraw_plots).pack(side="left")
        intervalbar = ttk.Frame(self.tab_view_config)
        intervalbar.pack(fill="x")
        ttk.Checkbutton(intervalbar, text="Solo ensayo detectado", variable=self.plot_interval,
                        command=self._redraw_plots).pack(side="left")
        ttk.Label(intervalbar, textvariable=self.interval_status).pack(side="left", padx=8)
        self._info_button(intervalbar, "Tramo automático", "Registre al menos 1 s sin carga antes de empezar. Detecta carga sostenida y final tras 0,5 s de retorno al nivel inicial. No detiene la adquisición. Desmarque para revisar todo el registro.").pack(side="right")
        bottom = ttk.Frame(self.tab_view_config, padding=(10,0,10,10))
        bottom.pack(fill="x")
        ttk.Label(bottom,text="Mostrar en").pack(side="left",padx=(0,4))
        units=ttk.Combobox(bottom,textvariable=self.display_unit,values=available_units(self.cfg.get('specimen_area_mm2')),state='readonly',width=10)
        units.pack(side="left"); units.bind("<<ComboboxSelected>>",lambda _:self._display_unit_changed())
        ttk.Label(bottom, textvariable=self.volts_var).pack(side="left")
        ttk.Label(bottom, text=f"Saturacion configurada: +/-{self.cfg['saturation_voltage']} V").pack(side="right")
        values = ttk.Frame(self.tab_test, padding=(10,0,10,8))
        values.pack(fill="x")
        self._value_box(values, "LECTURA ACTUAL", self.current_force, self.display_unit.get(), 0,
                        "Fuerza calculada a partir del voltaje de fuerza, la tara y la calibracion activa.")
        self._value_box(values, "FUERZA SI", self.current_kn, "kN", 1,
                        "Conversión SI usando 1 kp = 9,80665 N.")
        self._value_box(values, "DEFORMACION", self.current_def, "mm", 2,
                        "Deformacion calculada a partir del segundo canal analogico.")
        raw_values=ttk.Frame(self.tab_view_config);raw_values.pack(fill='x',pady=8)
        self._value_box(raw_values, "PICO BRUTO", self.max_force_var, "kp", 0,
                        "Mayor lectura bruta: puede incluir interferencias. El pico de rotura estimado usa una media temporal de 1 s.")
        self._value_box(raw_values, "DEF. MÁX. BRUTA", self.max_def_var, "mm", 1,
                        "Mayor deformacion registrada desde el inicio del ensayo.")

        self.rupture_banner=tk.Label(self.tab_test, textvariable=self.rupture_status, fg="#a51f27", bg="#fff0ed", font=("Segoe UI",13,"bold"), pady=5)
        self.rupture_banner.pack(fill="x",padx=10)
        self.rupture_banner.bind('<Configure>',lambda event:self.rupture_banner.configure(wraplength=max(200,event.width-20)))
        chartbox = ttk.LabelFrame(self.tab_test, text="Graficas en tiempo real", padding=6)
        chartbox.pack(fill="both", expand=True, padx=10, pady=(0,8))
        if MPL_OK:
            self.fig = Figure(figsize=(10, 4.8), dpi=100, constrained_layout=True)
            self.ax_fd = self.fig.add_subplot(121)
            self.ax_ft = self.fig.add_subplot(122)
            self._format_axes()
            self.canvas = FigureCanvasTkAgg(self.fig, master=chartbox)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            ttk.Label(chartbox, text="Instale matplotlib para ver y exportar graficas: pip install matplotlib").pack(pady=50)


    def _value_box(self, parent, title, variable, unit, col, info):
        f = ttk.LabelFrame(parent, text=title, padding=6, width=185, height=108)
        f.grid(row=0, column=col, padx=4, sticky="nsew")
        f.grid_propagate(False)
        parent.columnconfigure(col, weight=1, uniform="indicators")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(0, weight=1)
        label = ttk.Label(f, textvariable=variable, anchor="center", font=("Consolas", 21, "bold"))
        label.grid(row=0, column=0, columnspan=2, sticky="nsew")
        from tkinter.font import Font
        fonts = {size: Font(family="Consolas", size=size, weight="bold") for size in range(8, 22)}
        def fit(_event=None):
            width = max(20, label.winfo_width()-8)
            size = 21
            while size > 8 and fonts[size].measure(variable.get()) > width:
                size -= 1
            label.configure(font=fonts[size])
        label.bind("<Configure>", fit)
        variable.trace_add("write", lambda *_: fit())
        ttk.Label(f, textvariable=self.display_unit if col in (0, 3) else None,
                  text=unit).grid(row=1, column=0)
        if parent.master!=self.tab_test:self._info_button(f, title, info).grid(row=1, column=1)

    def _stable_zero_changed(self):
        if self.stable_zero.get(): self.display_mode.set('Kalman')
        self._display_controls_changed()
        if self.stable_zero.get() and not getattr(self,'last_tare',None):
            self.status.set('Kalman activo; tare para medir el ruido y activar el cero estable')

    def _reset_display(self):
        self.display_buffer.clear()
        self.live_force_filter=ForceFilter(self.display_mode.get(),seconds=float(self.display_seconds.get()),gain=self.cfg["force_factor_kp_per_v"],profile=self.kalman_profile,strength=self.kalman_strength.get())
        self.zero_holds=stable_channels(self.cfg,getattr(self,"last_tare",None))
        self.compression_history=[]
        self.compression_maximum=0.
        self.display_started = None
        for filt in self.voltage_filters:
            filt.reset()
        self.filtered_history.clear()

    def _display_controls_changed(self):
        self.voltage_filters = voltage_filters(self.kalman_profile, self.kalman_strength.get())
        self._reset_display()
        self._redraw_plots()

    def _kalman_profile_path(self):
        return self.cfg_path.with_name("kalman_profile.demo.json" if self.demo else "kalman_profile.json")

    def _load_kalman_profile(self):
        self.kalman_profile = None
        self.voltage_filters = voltage_filters(strength=self.kalman_strength.get())
        self.kalman_status.set("Kalman: ajuste inicial; sin entrenamiento compatible")
        path = self._kalman_profile_path()
        if not path.exists():
            return
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
            if profile.get('demo') != self.demo or profile.get('hardware') != hardware_signature(self.cfg):
                self.kalman_status.set("Kalman: ajuste inicial; el perfil guardado corresponde a otra configuración")
                return
            filters = voltage_filters(profile, self.kalman_strength.get())
            self.kalman_profile = profile
            self.voltage_filters = filters
            self.kalman_status.set(f"Kalman entrenado {'(SIMULACIÓN) ' if self.demo else ''}— {profile['acquired_at']}")
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self.kalman_status.set("Kalman: perfil guardado inválido; se usa el ajuste inicial")

    def start_kalman_training(self):
        try:
            duration = number(self.training_seconds.get())
            if not 10 <= duration <= 120:
                raise ValueError("El entrenamiento debe durar entre 10 y 120 segundos.")
        except ValueError as exc:
            messagebox.showerror("Entrenamiento", str(exc))
            return
        self.start_noise_capture(training=True, duration=duration)

    def _finish_kalman_training(self):
        try:
            if self.noise_context != self.cfg:
                raise ValueError("La configuración cambió durante la captura; repita el entrenamiento.")
            profile = train_stable_filter(self.noise_rows, self.noise_context['saturation_voltage'])
            profile.update(demo=self.noise_demo, acquired_at=self.noise_started_at,
                           hardware=hardware_signature(self.noise_context), raw_samples=self.noise_rows)
            filters = voltage_filters(profile, self.kalman_strength.get())
            path = self._kalman_profile_path()
            tmp = path.with_suffix('.tmp')
            tmp.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
            tmp.replace(path)
        except (ValueError, OSError) as exc:
            self.noise_status.set(f"Entrenamiento no aplicado: {exc} Se conserva el filtro anterior.")
            return
        self.kalman_profile = profile
        self.voltage_filters = filters
        self.display_mode.set('Kalman')
        self._display_controls_changed()
        self.kalman_status.set(f"Kalman entrenado {'(SIMULACIÓN) ' if self.demo else ''}— {self.noise_started_at}")
        self.noise_status.set("Entrenamiento guardado y Kalman activado. Los datos originales y la calibración se conservan.")

    def _build_debug_tab(self):
        self.tab_debug = ttk.Frame(self.config_notebook, padding=8)
        self.config_notebook.add(self.tab_debug, text="Debug")
        self.tab_debug.columnconfigure(0, weight=1)
        self.tab_debug.rowconfigure(1, weight=1, minsize=240)
        self.debug_controls = ttk.Frame(self.tab_debug)
        self.debug_controls.grid(row=0, column=0, sticky="ew")
        self.debug_info = tk.StringVar()
        self.debug_values = tk.StringVar(value="Sin lecturas")
        ttk.Label(self.debug_controls, textvariable=self.debug_values, font=("Consolas", 12), wraplength=980).pack(anchor="w", pady=(0,4))
        toggles = ttk.Frame(self.debug_controls)
        toggles.pack(fill="x")
        self.kalman_toggle = ttk.Button(toggles, text="▶ Kalman / Captura", command=self.toggle_kalman_panel)
        self.kalman_toggle.pack(side="left")
        self.connection_toggle = ttk.Button(toggles, text="▶ Conexión", command=self.toggle_connection_panel)
        self.connection_toggle.pack(side="left", padx=6)
        self.connection_panel = ttk.Frame(self.debug_controls, padding=5)
        ttk.Label(self.connection_panel, textvariable=self.debug_info, wraplength=940).pack(anchor="w")
        self.kalman_panel = ttk.LabelFrame(self.debug_controls, text="Filtro y entrenamiento", padding=6)
        row = ttk.Frame(self.kalman_panel)
        row.pack(fill="x")
        ttk.Checkbutton(row, text="Activar Kalman", variable=self.display_mode, onvalue="Kalman", offvalue="Directa",
                        command=self._display_controls_changed).pack(side="left")
        strength = ttk.Combobox(row, textvariable=self.kalman_strength, values=("Normal", "Alto", "Muy alto"), state="readonly", width=9)
        strength.pack(side="left", padx=6)
        strength.bind("<<ComboboxSelected>>", lambda _: self._display_controls_changed())
        ttk.Label(row, text="Entrenar (s):").pack(side="left")
        ttk.Spinbox(row, from_=10, to=120, textvariable=self.training_seconds, width=5).pack(side="left", padx=5)
        ttk.Button(row, text="Entrenar", command=self.start_kalman_training).pack(side="left")
        bar = ttk.Frame(self.kalman_panel)
        bar.pack(fill="x", pady=3)
        ttk.Button(bar, text="Medir ruido (10 s)", command=self.start_noise_capture).pack(side="left")
        ttk.Button(bar, text="Cancelar", command=self.cancel_noise_capture).pack(side="left", padx=6)
        ttk.Button(bar, text="Guardar CSV + resumen", command=self.save_noise_capture).pack(side="left")
        ttk.Label(self.kalman_panel, textvariable=self.kalman_status, wraplength=940).pack(anchor="w")
        self.noise_status = tk.StringVar(value="")
        ttk.Label(self.debug_controls, textvariable=self.noise_status, wraplength=940).pack(anchor="w", pady=2)
        curves = ttk.Frame(self.debug_controls)
        curves.pack(fill="x", pady=4)
        self.debug_visible = {}
        for key, title in (("raw_force", "Fuerza original"), ("filtered_force", "Fuerza corregida"),
                           ("raw_deformation", "Deformación original"), ("filtered_deformation", "Deformación corregida")):
            variable = tk.BooleanVar(value=True)
            self.debug_visible[key] = variable
            ttk.Checkbutton(curves, text=title, variable=variable, command=self._refresh_debug).pack(side="left", padx=5)
        if MPL_OK:
            self.debug_fig = Figure(figsize=(10, 4), dpi=100, constrained_layout=True)
            self.debug_ax = self.debug_fig.add_subplot(111)
            self.debug_canvas = FigureCanvasTkAgg(self.debug_fig, master=self.tab_debug)
            self.debug_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

    def toggle_connection_panel(self):
        if self.connection_panel.winfo_manager():
            self.connection_panel.pack_forget()
            self.connection_toggle.configure(text="▶ Conexión")
        else:
            self.connection_panel.pack(fill="x", before=self.debug_controls.winfo_children()[-2])
            self.connection_toggle.configure(text="▼ Conexión")

    def toggle_kalman_panel(self):
        if self.kalman_panel.winfo_manager():
            self.kalman_panel.pack_forget()
            self.kalman_toggle.configure(text="▶ Kalman / Captura")
        else:
            self.kalman_panel.pack(fill="x", before=self.debug_controls.winfo_children()[-2], pady=(3,0))
            self.kalman_toggle.configure(text="▼ Kalman / Captura")

    def start_noise_capture(self, training=False, duration=10):
        if not self.connected or self.recording or self.tare_pending:
            messagebox.showinfo("Captura", "Conecte la tarjeta y detenga el ensayo y la tara antes de medir la fluctuación.")
            return
        if self.noise_capture is not None:
            messagebox.showinfo("Captura", "Ya hay una captura en curso. Espere o pulse Cancelar captura.")
            return
        self.noise_training = training
        self.noise_duration = duration
        self.noise_capture = []
        self.noise_result = None
        self.noise_rows = []
        self.noise_context = json.loads(json.dumps(self.cfg))
        self.noise_started_at = timestamp()
        self.noise_demo = self.demo
        self.noise_status.set(f"{'Entrenando' if training else 'Capturando'} {duration:g} s: mantenga la carga estable.")

    def cancel_noise_capture(self):
        if self.noise_capture is not None:
            self.noise_capture = None
            self.noise_status.set("Captura cancelada; no se ha calculado un resumen parcial.")

    def _capture_noise_sample(self, now, vf, vd):
        if self.noise_capture is None:
            return
        self.noise_capture.append((now, vf, vd))
        elapsed = now-self.noise_capture[0][0]
        self.noise_status.set(f"Capturando: {min(elapsed,self.noise_duration):.1f} / {self.noise_duration:g} s ({len(self.noise_capture)} muestras)")
        if elapsed < self.noise_duration:
            return
        rows, self.noise_capture = self.noise_capture, None
        self.noise_rows = [(t-rows[0][0], f, d) for t, f, d in rows]
        try:
            self.noise_result = summarize_noise(self.noise_rows, self.noise_context['saturation_voltage'])
        except ValueError as exc:
            self.noise_status.set(str(exc))
            return
        r = self.noise_result
        self.noise_status.set(f"{'SIMULACIÓN · ' if self.noise_demo else ''}Captura completa: {r['samples']} muestras, {r['duration_s']:.1f} s. Resumen disponible al guardar CSV.")
        if self.noise_training:
            self._finish_kalman_training()

    def save_noise_capture(self):
        if self.noise_result is None:
            messagebox.showinfo("Captura", "Complete primero una captura de fluctuación.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="fluctuacion.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(("tiempo_s", "fuerza_V", "deformacion_V"))
                writer.writerows(self.noise_rows)
            Path(path).with_suffix(".metadata.json").write_text(json.dumps(dict(
                kind="noise_capture", demo=self.noise_demo, acquired_at=self.noise_started_at,
                configuration=self.noise_context, summary=self.noise_result), indent=2, ensure_ascii=False), encoding="utf-8")
            self.noise_status.set(f"Guardados CSV y resumen: {path}")
        except OSError as exc:
            messagebox.showerror("Captura", str(exc))

    def _refresh_debug(self):
        fc, dc = self.cfg['force_channel'], self.cfg['deformation_channel']
        self.debug_info.set(f"{'SIMULACIÓN' if self.demo else self.cfg['device_description']} | "
                            f"{'Conectado' if self.connected else 'Desconectado'} | Diferencial ±5 V | "
                            f"Fuerza AI{fc}−AI{fc+1}; deformación AI{dc}−AI{dc+1} | "
                            f"Frecuencia solicitada: {self.cfg['sample_hz']} Hz")
        if not self.debug_history:
            self.debug_values.set("Sin lecturas actuales")
            if MPL_OK:
                self.debug_ax.clear()
                self.debug_canvas.draw_idle()
            return
        now, vf, vd = self.debug_history[-1]
        history = [x for x in self.debug_history if now-x[0] <= 10]
        elapsed = history[-1][0]-history[0][0]
        hz = (len(history)-1)/elapsed if elapsed > 0 else 0
        self.debug_values.set(f"Fuerza: {vf:+.6f} V     Deformación: {vd:+.6f} V\n"
                              f"Frecuencia observada: {hz:.1f} Hz | "
                              f"{'SATURACIÓN' if max(abs(vf),abs(vd)) >= self.cfg['saturation_voltage'] else 'Dentro del umbral'}")
        if self.signal_alert:
            self.debug_values.set(self.debug_values.get()+"\n"+self.signal_alert)
        if MPL_OK:
            ax = self.debug_ax
            ax.clear()
            clean = [x for x in self.filtered_history if now-x[0] <= 10]
            for key, source, index, label, color, style in (
                ("raw_force", history, 1, "Fuerza original", "#2479ad", ":"),
                ("filtered_force", clean, 1, "Fuerza corregida (Kalman)", "#14466b", "-"),
                ("raw_deformation", history, 2, "Deformación original", "#e7a04b", ":"),
                ("filtered_deformation", clean, 2, "Deformación corregida (Kalman)", "#ad561c", "-")):
                if self.debug_visible[key].get() and source:
                    ax.plot([x[0]-now for x in source], [x[index] for x in source], label=label,
                            color=color, linestyle=style, linewidth=1.8 if "filtered" in key else .9)
            ax.set(xlabel="Tiempo relativo (s)", ylabel="Voltaje (V)", xlim=(-10, 0))
            ax.grid(alpha=.25)
            if ax.lines:
                ax.legend(loc="upper left")
            self.debug_canvas.draw_idle()

    def _display_unit_changed(self):
        """La selección es de presentación; la adquisición continúa en kp."""
        self._reset_display()
        self.cfg['display_unit']=self.display_unit.get()
        self._update_table_headers(); self._rebuild_table()
        if self.samples:
            peak=max(self.samples,key=lambda s:s.force_kp)
            self.max_force_var.set(f"{max(0.,from_kp(peak.force_kp,self.display_unit.get(),self.cfg.get('specimen_area_mm2'))):.{1 if self.display_unit.get()=='kN' else 0}f}")
        self._redraw_plots()

    def _update_table_headers(self):
        if not hasattr(self,'tree'): return
        unit=self.display_unit.get()
        self.tree.heading('force',text=unit_title(unit)+f' ({unit})')

    def _build_data_tab(self):
        bar=ttk.Frame(self.tab_data,padding=(10,8));bar.pack(fill='x')
        ttk.Label(bar,text='Historial y resultados',font=('Segoe UI',15,'bold')).pack(side='left')
        ttk.Button(bar,text='Exportar Excel',command=lambda:self.export_extended('xlsx')).pack(side='right')
        self.geometry_controls(bar)
        self.extra_export_bar=ttk.Frame(self.tab_data,padding=(10,2))
        for title,command in [('CSV',self.save_csv),('PDF',self.save_pdf),('TXT antiguo',self.save_legacy),('JSON',lambda:self.export_extended('json')),('HTML',lambda:self.export_extended('html')),('ZIP',lambda:self.export_extended('zip'))]:
            ttk.Button(self.extra_export_bar,text=title,command=command).pack(side='left',padx=3)
        self.history_host=ttk.Frame(self.tab_data,padding=(10,0));self.history_host.pack(fill='x')
        self._update_extra_exports()
        cols = ("t", "vf", "vd", "force", "kn", "def")
        frame = ttk.Frame(self.tab_data, padding=(10,0,10,10)); frame.pack(fill="both", expand=True)
        self.data_frame = frame
        results=ttk.Frame(frame,padding=8);results.pack(fill='both',expand=True)
        raw=ttk.Frame(self.config_notebook);self.config_notebook.add(raw,text='Brutos')
        self.marshall_text=tk.StringVar(value='Detenga o abra un ensayo para calcular resultados.')
        ttk.Label(results,text='Resultados Marshall',font=('Segoe UI',17,'bold')).pack(anchor='w')
        self.marshall_processing=tk.StringVar()
        ttk.Label(results,textvariable=self.marshall_processing,wraplength=1000).pack(anchor='w',pady=(2,8))
        from marshall_results import LABELS
        result_body=ttk.Frame(results);result_body.pack(fill='both',expand=True)
        cards=ttk.Frame(result_body);cards.pack(side='right',fill='y',padx=(12,0))
        self.marshall_cards=cards
        self.marshall_values={}
        for key,label in LABELS:
            card=tk.Frame(cards,background='white',padx=8,pady=2)
            card.pack(fill='x',pady=1)
            tk.Label(card,text=label,background='white',anchor='w',font=('Segoe UI',9),wraplength=225,justify='left').pack(side='left')
            value=tk.StringVar(value='—');self.marshall_values[key]=value
            tk.Label(card,textvariable=value,background='white',foreground=UC_DEEP,anchor='e',width=9,font=('Segoe UI',11,'bold')).pack(side='right')
        self.marshall_canvas=None
        if MPL_OK:
            figure=Figure(figsize=(9,4),constrained_layout=True)
            self.marshall_ax=figure.add_subplot(111)
            self.marshall_canvas=FigureCanvasTkAgg(figure,master=result_body)
            self.marshall_canvas.get_tk_widget().pack(side='left',fill='both',expand=True)
        frame=raw
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
        sub = ttk.Notebook(self.tab_config,style="Config.TNotebook")
        self.config_notebook=sub
        self.tab_view_config=ttk.Frame(sub,padding=10)
        sub.add(self.tab_view_config,text="Vista")
        self.advanced_controls=ttk.Frame(sub,padding=10)
        sub.add(self.advanced_controls,text="Archivos")
        ttk.Checkbutton(self.advanced_controls,text="Habilitar formatos adicionales a Excel",variable=self.extra_exports,command=self._update_extra_exports).pack(anchor="w",pady=8)
        ttk.Button(self.advanced_controls,text="Guardar preferencias",command=self.save_view_preferences).pack(anchor="w")
        sub.pack(fill="both", expand=True, padx=10, pady=10)
        gen = ttk.Frame(sub); pin = ttk.Frame(sub); cal = ttk.Frame(sub)
        sub.add(gen, text="DAQ")
        sub.add(pin, text="Pinout")
        sub.add(cal, text="Calibracion")
        self.build_branding_config(sub)
        wiring=ttk.Frame(sub,padding=14); sub.add(wiring,text="Migración")
        ttk.Label(wiring,text=WIRING_HELP,wraplength=900,justify="left").pack(anchor="nw")

        self.cfg_vars = {}
        fields = [
            ("device_description", "Dispositivo DAQNavi", str, "Nombre exacto mostrado por Advantech Navigator, por ejemplo USB-4716,BID#0."),
            ("sample_hz", "Frecuencia de muestreo (Hz)", float, "Numero de lecturas por segundo solicitadas por la aplicacion."),
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
        self.calibration_notebook=ttk.Notebook(cal)
        self.calibration_notebook.pack(fill="both",expand=True)
        manual=ttk.Frame(self.calibration_notebook)
        self.calibration_notebook.add(manual,text="Coeficientes / dos puntos")
        self._calibration_block(manual,0,"Fuerza","kp", "force")
        self._calibration_block(manual,1,"Deformacion","mm", "def")
        ttk.Button(manual,text="Guardar calibracion",command=self.save_configuration).grid(row=2,column=0,columnspan=2,pady=16)

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
        helptext="""INSTRUCCIONES DE USO

1. Directo
La aplicación intenta conectar con la USB-4716 al abrirse. Si no la encuentra, use Conectar. En modo simulación no conecta automáticamente.
Escriba el nombre del ensayo y pulse Guardar nombre; la etiqueta confirma el guardado.
Con la máquina estable y descargada pulse Tarar: se validan y promedian 100 lecturas. Iniciar ensayo usa esa tara; si falta una tara válida, la realiza antes de registrar.
Tarar, Iniciar/Finalizar ensayo y Reiniciar permanecen visibles. Reiniciar limpia el ensayo de la pantalla, con confirmación si hay datos pendientes.
Por defecto, indicadores y gráficas usan bloques de diez lecturas. Se muestran fuerza–deformación y deformación acumulada–tiempo. El historial conserva las lecturas originales.
Altura (mm) y volumen (mm³) son opcionales y pertenecen al ensayo, no a la calibración.

2. Exportar
El historial marca el último ensayo por fecha de adquisición. Haga doble clic para cargar sus resultados.
La gráfica aparece a la izquierda y los valores a la derecha. Excel usa exactamente esos puntos promediados, incluido el último bloque parcial.
El libro contiene una gráfica XY con ejes numéricos, resultados y referencia UNE-EN 12697-34:2022 (§3, §7 y anexo A).
Introduzca altura o volumen en la aplicación o en las celdas amarillas del Excel. Si introduce ambos, se usa altura. Sin dimensiones la estabilidad corregida y S/F quedan pendientes.
La tangente automática requiere revisión visual; los resultados individuales no acreditan por sí solos las condiciones ni la validación del grupo.
Para borrar un ensayo: clic derecho, Borrar ensayo y Confirmar borrado. El borrado del historial es permanente.

3. Configuración
Vista permite elegir gráficas, unidades y procesamiento (media de diez, mediana, Kalman, etc.). Guarde las preferencias para conservarlas.
Archivos permite habilitar otros formatos; todos los que salen de Exportar usan los mismos puntos procesados.
La calibración, adquisición, lecturas brutas, análisis y depuración de voltajes se encuentran aquí.

4. Conexiones
Instale DAQNavi/XNavi y el puente USB-4716. Configure el nombre exacto del dispositivo en DAQ.
Use el pinout configurado y verifique entradas diferenciales y rango ±5 V.
La aplicación adquiere datos; no controla el movimiento de la prensa.
"""
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
            candidate["enable_extra_exports"]=self.extra_exports.get()
            candidate["view_settings"]={"mode":self.display_mode.get(),"stable_zero":self.stable_zero.get(),"charts":{k:v.get() for k,v in self.live_charts.items()},"strength":self.kalman_strength.get()}
            candidate["sample_hz"]=float(self.cfg_vars["sample_hz"].get())
            candidate["tare_samples"]=100
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
            self._load_kalman_profile()
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

    def _visible_plot_samples(self):
        raw=[vars(s) for s in self.samples]
        source = [Sample(**r) for r in (raw if self.display_mode.get()=="Antiguo (10 lecturas)" else clean_rows(raw))]
        visible = list(source)
        if self.display_mode.get() == "Media de 10 lecturas":
            from marshall_results import calculation_rows
            rows=raw[:len(raw)//10*10] if self.recording else raw
            visible=[Sample(**{k:(float('nan') if r[k] is None else r[k]) for k in ('t','vf','vd','force_kp','deformation_mm')}) for r in calculation_rows({'samples':rows})]
            source=visible
        elif self.display_mode.get() == "Antiguo (10 lecturas)":
            visible=[Sample(**r) for r in legacy_plot_rows(raw)]
            source=visible
        elif self.display_mode.get() == "Mediana":
            columns=[median_filter([getattr(s,key) for s in visible],10) for key in ('vf','vd','force_kp','deformation_mm')]
            visible=[Sample(s.t,*values) for s,values in zip(visible,zip(*columns))]
        elif self.display_mode.get() == "Kalman":
            filters = voltage_filters(self.kalman_profile, self.kalman_strength.get())
            context = self.test_context or self.cfg
            visible = []
            for sample in source:
                vf, vd = (f.update(sample.t, v) for f, v in zip(filters, (sample.vf, sample.vd)))
                visible.append(Sample(sample.t, vf, vd,
                    sample.force_kp+(vf-sample.vf)*context['force_factor_kp_per_v'],
                    sample.deformation_mm+(vd-sample.vd)*context['deformation_factor_mm_per_v']))
        elif self.display_mode.get() == "Suavizada" and visible:
            duration = visible[-1].t-visible[0].t
            hz = (len(visible)-1)/duration if duration>0 else self.cfg['sample_hz']
            window = max(1,round(float(self.display_seconds.get())*hz))
            columns=[time_average([s.t for s in visible],[getattr(s,key) for s in visible],float(self.display_seconds.get())) for key in ('vf','vd','force_kp','deformation_mm')]
            visible=[Sample(s.t,*values) for s,values in zip(visible,zip(*columns))]
        if self.display_mode.get() not in ('Antiguo (10 lecturas)','Media de 10 lecturas'):
            context=self.test_context or self.cfg
            forces=force_series([s.t for s in self.samples],[s.force_kp if o.force_kp>=0 else float('nan') for s,o in zip(source,self.samples)],method=self.display_mode.get(),seconds=float(self.display_seconds.get()),gain=context['force_factor_kp_per_v'],profile=self.kalman_profile,strength=self.kalman_strength.get())
            visible=[Sample(s.t,s.vf,s.vd,f,s.deformation_mm) for s,f in zip(visible,forces)]
        if self.stable_zero.get() and self.display_mode.get()=='Kalman':
            context=self.test_context or self.cfg
            holds=stable_channels(context,context.get('tare_statistics') if self.test_context else getattr(self,'last_tare',None))
            if holds:
                visible=[Sample(s.t,s.vf,s.vd,holds[0].update(s.t,s.force_kp),holds[1].update(s.t,s.deformation_mm)) for s in visible]
        projected=compression_deformation([s.deformation_mm for s in visible])
        visible=[Sample(s.t,s.vf,s.vd,s.force_kp,d) for s,d in zip(visible,projected)]
        self.processed_current=visible[-1] if visible else None
        if self.plot_interval.get() and visible:
            span=detect_test_interval([dict(t=s.t,force_kp=s.force_kp) for s in source])
            if span is None:
                self.interval_status.set("Sin tramo claro; desmarque para revisar todo")
                return []
            end=span['end'] if span['end'] is not None else len(visible)-1
            visible=visible[span['start']:end+1]
            end_text=f"{source[end].t:.2f} s" if span['end'] is not None else "en curso"
            self.interval_status.set(f"Inicio estimado {visible[0].t:.2f} s · Final {end_text}")
        else:
            self.interval_status.set("Registro completo" if visible else "Esperando tramo de carga")
        return visible

    def _redraw_plots(self):
        if not MPL_OK: return
        selected=[kind for kind,enabled in self.live_charts.items() if enabled.get()]
        self.fig.clear()
        columns=1 if len(selected)==1 else 2
        rows=(len(selected)+columns-1)//columns
        axes=[self.fig.add_subplot(rows,columns,i+1) for i in range(len(selected))]
        if axes:
            self.ax_fd=axes[0]; self.ax_ft=axes[-1]
        else:
            self.fig.text(.5,.5,'Seleccione al menos una gráfica',ha='center')
        visible=self._visible_plot_samples()
        unit=self.display_unit.get(); area=self.cfg.get('specimen_area_mm2')
        forces=[from_kp(s.force_kp,unit,area) for s in visible]
        deform=[s.deformation_mm for s in visible]; times=[s.t for s in visible]
        confirmation=detect_rupture([vars(s) for s in self.samples])
        peak=displayed_peak([vars(s) for s in visible])
        rupture=peak if peak and (confirmation or (not self.recording and peak['index']<len(visible)-1)) else None
        if rupture:
            span=detect_test_interval([vars(s) for s in self.samples])
            elapsed=f"{rupture['t']-self.samples[span['start']].t:.2f} s desde inicio detectado" if span and self.samples[span['start']].t<=rupture['t'] else 'inicio no detectado'
            deformation=f"{rupture['deformation_mm']:.2f} mm"
            self.rupture_status.set(f"PROBETA ROTA · pico estimado {rupture['force_kp']:.0f} kp · {elapsed} · {deformation}")
        else:self.rupture_status.set('Sin rotura detectada')
        if self.recording and getattr(self,"processed_current",None) is not None:
            value=self.processed_current
            self.current_force.set(f"{from_kp(value.force_kp,unit,area):.{1 if unit=='kN' else 0 if unit in ('kp','kgf') else 3}f}")
            self.current_kn.set(f"{from_kp(value.force_kp,'kN'):.1f}")
            self.current_def.set(f"{value.deformation_mm:.2f}")
        mode=self.display_mode.get()
        suffix=f" · {mode}"+(f" {self.kalman_strength.get().lower()}" if mode=='Kalman' else '')+("" if mode in ("Antiguo (10 lecturas)","Media de 10 lecturas") else " · sin picos aislados")
        for kind,ax in zip(selected,axes):
            ax.set_title(CHARTS[kind]); ax.grid(alpha=.25)
            if kind=='fd': series=[(deform,forces,'Carga')]; xlabel='Deformación (mm)'; ylabel=f'Fuerza ({unit})'
            elif kind=='ft': series=[(times,forces,'Carga')]; xlabel='Tiempo (s)'; ylabel=f'Fuerza ({unit})'
            elif kind=='dt': series=[(times,deform,'Deformación')]; xlabel='Tiempo (s)'; ylabel='Deformación (mm)'
            elif kind=='volts':
                series=[(times,[s.vf for s in visible],'Fuerza'),(times,[s.vd for s in visible],'Deformación')]
                xlabel='Tiempo (s)'; ylabel='Voltaje (V)'
            else:
                xs=[]; ys=[]; j=0
                for i in range(1,len(visible)):
                    while j+1<i and times[i]-times[j+1]>=.5: j+=1
                    dt=times[i]-times[j]
                    if dt>=.5: xs.append(times[i]); ys.append((deform[i]-deform[j])*60/dt)
                series=[(xs,ys,'Velocidad')]; xlabel='Tiempo (s)'; ylabel='Velocidad (mm/min)'
            ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
            for xs,ys,label in series:
                drawn=[float('nan') if self.hide_negative.get() and kind in ('fd','ft','dt') and (y<0 or (kind=='fd' and x<0)) else y for x,y in zip(xs,ys)]
                ax.plot(xs,drawn,linewidth=1.5,label=label, linestyle="None" if kind=="fd" and not self.join_fd.get() else "-", marker="." if kind=="fd" and not self.join_fd.get() else None, markersize=3)
            if rupture and kind in ('fd','ft','dt'):
                for xs,ys,label in series:
                    red=[y if t>=rupture['t'] and not (self.hide_negative.get() and (y<0 or (kind=='fd' and x<0))) else float('nan') for t,x,y in zip(times,xs,ys)]
                    ax.plot(xs,red,color='#c62828',linewidth=1.8,linestyle='None' if kind=='fd' and not self.join_fd.get() else '-',marker='.' if kind=='fd' and not self.join_fd.get() else None,markersize=3,label='Después del pico de rotura estimado')
            if not visible: ax.text(.5,.5,'Sin tramo de ensayo visible',ha='center',transform=ax.transAxes)
            elif kind=='volts': ax.legend()
        self.canvas.draw_idle()
        self.last_plot=time.perf_counter()

    def connect(self,automatic=False):
        if self.connected:
            if not automatic:self.disconnect()
            return
        try:
            if self.demo:
                self.daq=MockDAQ()
            else:
                validate_hardware(self.cfg)
                self.daq=AdvantechDAQ(self.cfg["device_description"],self.cfg["force_channel"],self.cfg["deformation_channel"])
            self.daq.connect()
        except Exception as exc:
            self.connection_state.set('Tarjeta no disponible · pulse Conectar')
            self.status.set('No se pudo conectar con la tarjeta: '+str(exc))
            if self.daq:
                try:self.daq.close()
                except Exception:pass
            if not automatic:messagebox.showerror("Conexion",str(exc))
            return
        self._reset_display()
        self.debug_history.clear()
        self.connected=True
        self.tare_valid=False
        self.status.set("Conectado"+(" (SIMULACION)" if self.demo else ""))
        self.connection_state.set("SIMULACIÓN" if self.demo else "USB-4716 conectada")
        self.btn_connect.pack_forget(); self.btn_tare.configure(state="normal"); self.btn_start.configure(state="normal")
        self.stop_evt.clear(); self.worker=threading.Thread(target=self._acquisition_loop,daemon=True); self.worker.start()

    def disconnect(self):
        self.operator_start_pending=False
        self.tare_valid=False
        self.ring_zero = self.ring_one = None
        self.cancel_noise_capture()
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
        self.signal_alert = ""; self.last_signal_check = None
        self._reset_display(); self.debug_history.clear(); self.volts_var.set("Sin lecturas actuales")
        self.connected=False; self.recording=False; self.status.set("Desconectado")
        self.connection_state.set("Tarjeta desconectada")
        self.btn_connect.configure(text="Conectar");self.btn_connect.pack(side="left",before=self.btn_tare,padx=3)
        self.btn_tare.configure(state="normal"); self.btn_start.configure(state="normal",text="Iniciar ensayo"); self.btn_stop.configure(state="disabled")

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
        debug_key=(self.debug_history[-1][0] if self.debug_history else None,self.connected)
        if self.nb.select() == str(self.tab_config) and self.config_notebook.select()==str(self.tab_debug) and time.perf_counter()-self.debug_last >= .1 and debug_key!=getattr(self,'last_debug_drawn',None):
            self.last_debug_drawn=debug_key
            self.debug_last = time.perf_counter(); self._refresh_debug()
        self.after(20,self._poll_queue)

    def _process_sample(self,now,vf,vd):
        self._capture_noise_sample(now,vf,vd)
        self.debug_history.append((now,vf,vd))
        self.recent_volts.append((now,vf,vd))
        self.recent_volts = [s for s in self.recent_volts if now-s[0] <= 1.2]
        if self.last_signal_check is None or now-self.last_signal_check >= .1:
            self.last_signal_check = now
            self.signal_alert = " | ".join(rapid_voltage_changes(self.recent_volts))
        self.volts_var.set(f"AI fuerza: {vf:+.4f} V | AI deformacion: {vd:+.4f} V")
        if abs(vf)>=float(self.cfg["saturation_voltage"]) or abs(vd)>=float(self.cfg["saturation_voltage"]):
            self.status.set("ATENCION: entrada proxima a saturacion")
        elif self.signal_alert:
            self.status.set("ATENCIÓN: oscilación rápida. Ver Depuración.")
        elif self.connected and not self.tare_pending:
            self.status.set("Ensayo en curso" if self.recording else "Conectado"+(" (SIMULACION)" if self.demo else ""))
        if self.tare_pending:
            self.tare_buffer.append((now,vf,vd))
            if len(self.tare_buffer)>=100:
                try:
                    stats=legacy_tare(self.tare_buffer,self.cfg['saturation_voltage'])
                    self.zero_force_v=stats['channels'][0]['mean_v']+self.cfg.get('force_offset_kp',0)/self.cfg['force_factor_kp_per_v']
                    self.zero_deform_v=stats['channels'][1]['mean_v']+self.cfg.get('deformation_offset_mm',0)/self.cfg['deformation_factor_mm_per_v']
                    self.last_tare=stats
                    self.tare_valid=True
                    self._reset_display()
                    self.current_force.set('0'); self.current_kn.set('0.0'); self.current_def.set('0.00')
                    self.status.set('Tara aplicada: media de 100 lecturas; indicadores a cero')
                except ValueError as exc:
                    self.status.set('Tara rechazada; cero anterior conservado: '+str(exc))
                self.tare_pending=False; self.tare_buffer.clear(); self.force_window.clear(); self.deform_window.clear()
                if getattr(self,'operator_start_pending',False):
                    self.operator_start_pending=False
                    if 'stats' in locals():self.after(0,self.start_recording)
                    else:self.btn_start.configure(state='normal',text='Iniciar ensayo')
            return
        if self.display_started is None:
            self.display_started = now
        mode = self.display_mode.get()
        if not hasattr(self,'live_force_filter'):
            self._reset_display(); self.display_started=now
        measured_force=(vf-self.zero_force_v)*self.cfg['force_factor_kp_per_v']+self.cfg.get('force_offset_kp',0)
        processed_force=self.live_force_filter.update(now,measured_force)
        avf, avd = (filt.update(now, v) for filt, v in zip(self.voltage_filters, (vf, vd)))
        self.filtered_history.append((now, avf, avd))
        if mode != "Kalman":
            self.display_buffer.append((vf, vd))
        if mode=="Mediana": self.display_buffer[:]=self.display_buffer[-10:]
        interval = .1 if mode in ("Kalman","Mediana") else float(self.display_seconds.get())
        ready=(len(self.display_buffer)>=10) if mode in ("Antiguo (10 lecturas)","Media de 10 lecturas") else (mode=="Directa" or now-self.display_started >= interval)
        if ready:
            if mode != "Kalman":
                avf = sum(x[0] for x in self.display_buffer)/len(self.display_buffer)
                avd = sum(x[1] for x in self.display_buffer)/len(self.display_buffer)
            if mode=="Mediana":
                avf=median_filter([r[0] for r in self.display_buffer],10)[-1]
                avd=median_filter([r[1] for r in self.display_buffer],10)[-1]
            force=(avf-self.zero_force_v)*float(self.cfg["force_factor_kp_per_v"])+float(self.cfg.get("force_offset_kp",0.0))
            deform=(avd-self.zero_deform_v)*float(self.cfg["deformation_factor_mm_per_v"])+float(self.cfg.get("deformation_offset_mm",0.0))
            if mode=="Mediana":
                force=median_filter([(v[0]-self.zero_force_v)*self.cfg['force_factor_kp_per_v']+self.cfg.get('force_offset_kp',0) for v in self.display_buffer],10)[-1]
                deform=median_filter([(v[1]-self.zero_deform_v)*self.cfg['deformation_factor_mm_per_v']+self.cfg.get('deformation_offset_mm',0) for v in self.display_buffer],10)[-1]
            if mode in ('Antiguo (10 lecturas)','Media de 10 lecturas'):
                accepted=[(v[0]-self.zero_force_v)*self.cfg['force_factor_kp_per_v']+self.cfg.get('force_offset_kp',0) for v in self.display_buffer]
                accepted=[v for v in accepted if v>=0]
                force=sum(accepted)/len(accepted) if accepted else 0.
            else: force=processed_force
            if self.stable_zero.get() and mode=='Kalman'  and getattr(self,'zero_holds',None):
                force=self.zero_holds[0].update(now,force); deform=self.zero_holds[1].update(now,deform)
            if not hasattr(self,'compression_history'): self.compression_history=[]; self.compression_maximum=0.
            candidate=deform
            if candidate>self.compression_maximum+.02: self.compression_maximum=candidate
            deform=self.compression_maximum
            shown=from_kp(force,self.display_unit.get(),self.cfg.get('specimen_area_mm2'))
            if not self.recording:
                self.current_force.set(f"{shown:.{1 if self.display_unit.get()=='kN' else 0 if self.display_unit.get() in ('kp','kgf') else 3}f}")
                self.current_kn.set(f"{from_kp(force, 'kN'):.1f}")
                self.current_def.set(f"{deform:.2f}")
            if mode!="Mediana": self.display_buffer.clear()
            self.display_started = now
        if self.recording:
            if self.t0 is None:self.t0=now
            # Archivo sin suavizado: cada lectura conserva su voltaje y conversión.
            raw_force=(vf-self.zero_force_v)*self.cfg["force_factor_kp_per_v"]+self.cfg.get("force_offset_kp",0)
            raw_def=(vd-self.zero_deform_v)*self.cfg["deformation_factor_mm_per_v"]+self.cfg.get("deformation_offset_mm",0)
            sample=Sample(now-self.t0,vf,vd,raw_force,raw_def)
            self.samples.append(sample); self.dirty=True
            if len(self.samples)==1 or raw_force>self.max_force:
                self.max_force=raw_force; self.max_force_var.set(f"{max(0.,from_kp(raw_force,self.display_unit.get(),self.cfg.get('specimen_area_mm2'))):.{1 if self.display_unit.get()=='kN' else 0}f}")
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
        self.cancel_noise_capture()
        self.tare_valid=False
        self._reset_display(); self.tare_buffer.clear(); self.tare_pending=True; self.status.set("Tarando: media de 100 lecturas, como en el programa antiguo...")

    def start_recording(self):
        if not self.connected or self.tare_pending:return
        if not self.confirm_discard():return
        try:self.specimen_geometry(strict=True)
        except ValueError as exc:
            messagebox.showerror("Probeta",str(exc));return
        self.cancel_noise_capture()
        self.session_id=None; self.acquired_at=timestamp(); self.session_demo=self.demo; self.session_source="Adquisición"; self.comparisons=[]
        self.test_context=json.loads(json.dumps(self.cfg))
        self.test_context["stable_zero"]={"enabled":self.stable_zero.get(),"noise_sigma_multiplier":5,"confirmation_seconds":.3}
        self.test_context["display_processing"]=self.display_mode.get()
        self.test_context["deformation_processing"]="filtered_running_max_deadband_0.02mm_fixed_tare"
        self.test_context["legacy_processing"]={"block_samples":10,"tare_samples":100,"export_held_samples":10,"truncation":"floor"}
        self.test_context["tare_statistics"]=getattr(self,"last_tare",None)
        self.test_context["zero_force_v"]=self.zero_force_v
        self.test_context["zero_deform_v"]=self.zero_deform_v
        self._reset_display()
        self.force_window.clear(); self.deform_window.clear()
        self.btn_tare.configure(state="disabled")
        self.samples.clear(); self._clear_table(); self.max_force=self.max_deformation=0.0
        self.max_force_var.set("0"); self.max_def_var.set("0.00"); self.t0=None; self.recording=True
        self.btn_start.configure(state="normal",text="Finalizar ensayo"); self.btn_stop.configure(state="normal"); self.status.set("Ensayo en curso"); self._redraw_plots()

    def stop_recording(self):
        was_recording=self.recording
        self.recording=False
        self.btn_tare.configure(state="normal")
        self.update_summary()
        self.recording=False; self.btn_start.configure(state="normal",text="Iniciar ensayo"); self.btn_stop.configure(state="disabled")
        self.status.set(f"Ensayo detenido - {len(self.samples)} puntos"); self._redraw_plots(); self._rebuild_table()
        if was_recording and self.samples:
            if self.test_context is not None: self.test_context["rupture_estimate"]=detect_rupture([vars(s) for s in self.samples])
            self.archive_current(automatic=True)
        self.refresh_analysis()

    def reset_test(self):
        if not self.confirm_discard():return
        self.operator_start_pending=False;self.tare_pending=False;self.tare_buffer.clear()
        self.dirty=False; self.test_context=None
        self.session_id=None; self.acquired_at=None; self.comparisons=[]
        self.btn_tare.configure(state="normal")
        self.recording=False; self.samples.clear(); self._clear_table(); self.max_force=self.max_deformation=0.0
        self.max_force_var.set("0"); self.max_def_var.set("0.00"); self.btn_stop.configure(state="disabled")
        self.btn_start.configure(state="normal",text="Iniciar ensayo")
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
                f.write(csv_text(self.current_export_session()))
            metadata=dict(configuration=self.current_export_session()["configuration"], reference=self.test_name.get(), operator=self.operator.get(), sample_id=self.sample_id.get(), notes=self.notes.get(), demo=self.session_demo, acquired_at=self.acquired_at)
            Path(path).with_suffix(".metadata.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding="utf-8")
            self.dirty=False
            self.status.set(f"Guardado: {Path(path).name} + metadatos")
        except OSError as exc:
            messagebox.showerror("Guardar",str(exc))

    def _save_plot_file(self,path,kind):
        if not MPL_OK: raise RuntimeError("Matplotlib no esta instalado")
        fig=Figure(figsize=(8.5,5.2),dpi=150,constrained_layout=True); ax=fig.add_subplot(111)
        visible=[Sample(**r) for r in self.current_export_session()['samples']]
        unit=self.display_unit.get(); area=self.cfg.get('specimen_area_mm2')
        xs=[s.deformation_mm if kind=='fd' else s.t for s in visible]
        ys=[from_kp(s.force_kp,unit,area) for s in visible]
        ys=[float('nan') if self.hide_negative.get() and (y<0 or (kind=='fd' and x<0)) else y for x,y in zip(xs,ys)]
        ax.plot(xs,ys,linewidth=1.7,linestyle='None' if kind=='fd' and not self.join_fd.get() else '-',marker='.' if kind=='fd' and not self.join_fd.get() else None,markersize=3)
        rupture=displayed_peak([vars(s) for s in visible])
        if rupture:
            ax.plot(xs,[y if s.t>=rupture['t'] else float('nan') for s,y in zip(visible,ys)],color='#c62828',linewidth=1.8,linestyle='None' if kind=='fd' and not self.join_fd.get() else '-',marker='.' if kind=='fd' and not self.join_fd.get() else None,markersize=3)
        ax.set_title(CHARTS[kind])
        ax.set_xlabel('Deformación (mm)' if kind=='fd' else 'Tiempo (s)'); ax.set_ylabel(f'Fuerza ({unit})')
        if not visible: ax.text(.5,.5,'Sin tramo de ensayo visible',ha='center',transform=ax.transAxes)
        ax.grid(True,alpha=.25); fig.savefig(path,dpi=180,bbox_inches='tight')

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
        processed=self.current_export_session()
        samples=[Sample(**r) for r in processed['samples']]
        cfg=processed['configuration']
        peak_force=max(r.force_kp for r in samples);peak_def=max(r.deformation_mm for r in samples)
        doc=SimpleDocTemplate(str(path),pagesize=landscape(A4),rightMargin=14*mm,leftMargin=14*mm,topMargin=33*mm,bottomMargin=16*mm)
        styles=getSampleStyleSheet(); title=ParagraphStyle("Title2",parent=styles["Title"],alignment=TA_CENTER,fontSize=18,leading=22,spaceAfter=10)
        story=[Paragraph("Informe de ensayo - Prensa Marshall",title),Paragraph("UNE-EN 12697-34:2022. Resultados individuales; apartados 3, 7 y anexo A.",styles["Normal"])]
        meta=[
            ["Referencia",self.test_name.get() or "-","Probeta",self.sample_id.get() or "-"],
            ["Operador",self.operator.get() or "-","Adquisición",self.acquired_at or "No disponible"],
            ["Origen", "SIMULACIÓN" if self.session_demo is True else "REAL" if self.session_demo is False else "No verificado", "Informe",datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["Fuerza máxima",f"{peak_force:.3f} kp / {from_kp(peak_force,'kgf'):.3f} kgf / {from_kp(peak_force,'N'):.2f} N / {from_kp(peak_force,'kN'):.4f} kN","Deformación máxima",f"{peak_def:.4f} mm"],
            ["Duracion",f"{samples[-1].t:.2f} s","Puntos",str(len(samples))],
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
        for s in samples:
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
