"""Herramientas de calibración y revisión integradas en la aplicación."""
import csv
import json
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from measurement import number, fit_calibration, read_legacy
from theme import UC_DEEP, UC_PRIMARY


class Workbench:
    def build_workbench(self):
        self.cal_points = []
        self.recent_volts = []
        self.dirty = False
        self.test_context = None
        self.last_plot = 0
        self.cal_channel = tk.StringVar(value='Fuerza (kp)')
        self.cal_voltage = tk.StringVar()
        self.cal_reference = tk.StringVar()
        self.cal_result = tk.StringVar(value='1. Seleccione el sensor   →   2. Añada patrones   →   3. Revise y aplique')
        tab = ttk.Frame(self.nb, padding=14)
        self.nb.insert(2, tab, text='Calibración · laboratorio')
        ttk.Label(tab, text='Calibración multipunto', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(tab, text='Voltajes brutos, sin tara. Ajuste lineal por mínimos cuadrados; patrones en kp o mm.').pack(anchor='w', pady=(4,12))
        bar = ttk.Frame(tab); bar.pack(fill='x')
        selector = ttk.Combobox(bar, textvariable=self.cal_channel, values=['Fuerza (kp)', 'Deformación (mm)'], state='readonly', width=20)
        selector.pack(side='left'); selector.bind('<<ComboboxSelected>>', self.clear_calibration)
        for label, var in [('Voltaje (V)', self.cal_voltage), ('Patrón conocido', self.cal_reference)]:
            ttk.Label(bar, text=label).pack(side='left', padx=(12,4))
            ttk.Entry(bar, textvariable=var, width=12).pack(side='left')
        ttk.Button(bar, text='Capturar 1 s', command=self.capture_calibration).pack(side='left', padx=8)
        ttk.Button(bar, text='Añadir punto', command=self.add_calibration).pack(side='left')
        body = ttk.Frame(tab); body.pack(fill='both', expand=True, pady=12)
        self.cal_table = ttk.Treeview(body, columns=('v','y','error'), show='headings', height=8)
        for c, title in [('v','Voltaje (V)'),('y','Patrón'),('error','Residuo')]:
            self.cal_table.heading(c, text=title); self.cal_table.column(c, width=105, stretch=True)
        self.cal_table.pack(side='left', fill='both', expand=True)
        self.cal_canvas = None
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            fig = Figure(figsize=(5,3), constrained_layout=True)
            self.cal_ax = fig.add_subplot(111)
            self.cal_canvas = FigureCanvasTkAgg(fig, master=body)
            self.cal_canvas.get_tk_widget().pack(side='left', fill='both', expand=True)
        except ImportError:
            pass
        ttk.Label(tab, textvariable=self.cal_result, wraplength=950).pack(anchor='w', pady=8)
        buttons = ttk.Frame(tab); buttons.pack(fill='x')
        ttk.Button(buttons, text='Eliminar seleccionado', command=self.remove_calibration).pack(side='left')
        ttk.Button(buttons, text='Vaciar patrones', command=self.clear_calibration).pack(side='left', padx=8)
        ttk.Button(buttons, text='Aplicar y guardar calibración', command=self.apply_calibration).pack(side='left')
        ttk.Label(tab, text='Al aplicar se reinicia la tara del sensor. Dos puntos definen una recta exacta; use más patrones para evaluar el ajuste.').pack(anchor='w', pady=12)
        self.summary = tk.StringVar(value='Inicie un ensayo o abra un archivo para consultar resultados.')
        resultbar = ttk.Frame(self.tab_data, padding=10)
        resultbar.pack(fill='x', before=self.data_frame)
        ttk.Label(resultbar, textvariable=self.summary, wraplength=1100, font=('Segoe UI',11,'bold')).pack(anchor='w')
        actions = ttk.Frame(self.tab_data, padding=(10,4))
        actions.pack(fill='x', before=resultbar)
        ttk.Button(actions, text='Abrir CSV / TXT antiguo', command=self.open_test).pack(side='left')
        ttk.Button(actions, text='Exportar TXT antiguo', command=self.save_legacy).pack(side='left', padx=8)
        self.refresh_calibration()

    def clear_calibration(self, event=None):
        self.cal_points.clear(); self.refresh_calibration()

    def capture_calibration(self):
        if not self.connected or self.recording or self.tare_pending:
            messagebox.showinfo('Captura', 'Conecte la DAQ y detenga el ensayo y la tara antes de capturar.'); return
        recent = [s for s in self.recent_volts if time.perf_counter()-s[0] <= 1]
        if len(recent)<2 or recent[-1][0]-recent[0][0]<0.8:
            messagebox.showinfo('Captura', 'Espere un segundo de señal estable.'); return
        idx = 1 if self.cal_channel.get().startswith('Fuerza') else 2
        values = [s[idx] for s in recent]
        self.cal_voltage.set(f'{sum(values)/len(values):.9g}')
        self.cal_result.set(f'Captura: {len(values)} muestras · variación pico a pico {max(values)-min(values):.6f} V. Añada el valor del patrón y pulse Añadir punto.')

    def add_calibration(self):
        try:
            point = number(self.cal_voltage.get()), number(self.cal_reference.get())
            if abs(point[0])>=5: raise ValueError('Voltaje fuera del rango ±5 V.')
            self.cal_points.append(point); self.refresh_calibration()
        except ValueError as exc: messagebox.showerror('Calibración', str(exc))

    def remove_calibration(self):
        for iid in sorted(self.cal_table.selection(), key=int, reverse=True): self.cal_points.pop(int(iid))
        self.refresh_calibration()

    def refresh_calibration(self):
        fit = None
        try:
            fit = fit_calibration(self.cal_points)
            self.cal_result.set(f"Factor {fit['factor']:.8g} · Offset {fit['offset']:.8g} · R² {fit['r2']:.6f} · Error máximo {fit['max_error']:.6g}")
        except ValueError as exc: self.cal_result.set(str(exc))
        self.cal_table.delete(*self.cal_table.get_children())
        for i,(v,y) in enumerate(self.cal_points):
            self.cal_table.insert('', 'end', iid=str(i), values=(f'{v:.6f}',f'{y:.6g}', f"{fit['residuals'][i]:+.6g}" if fit else '—'))
        if self.cal_canvas:
            ax=self.cal_ax; ax.clear(); ax.set_xlabel('Voltaje bruto (V)'); ax.set_ylabel(self.cal_channel.get()); ax.grid(alpha=.2)
            if self.cal_points:
                x,y=zip(*self.cal_points); ax.scatter(x,y,color=UC_PRIMARY,label='Patrones')
                if fit:
                    ends=[min(x),max(x)]; ax.plot(ends,[fit['factor']*v+fit['offset'] for v in ends],color=UC_DEEP,label='Ajuste')
                ax.legend()
            self.cal_canvas.draw_idle()

    def apply_calibration(self):
        if self.recording or self.tare_pending:
            messagebox.showinfo('Calibración', 'Detenga el ensayo y espere a terminar la tara.'); return
        try:
            fit=fit_calibration(self.cal_points)
            force=self.cal_channel.get().startswith('Fuerza')
            factor_key='force_factor_kp_per_v' if force else 'deformation_factor_mm_per_v'
            offset_key='force_offset_kp' if force else 'deformation_offset_mm'
            cfg=json.loads(json.dumps(self.cfg)); cfg[factor_key]=fit['factor']; cfg[offset_key]=fit['offset']
            record=dict(date=datetime.now().isoformat(), sensor=self.cal_channel.get(), points=self.cal_points[:], demo=self.demo, **fit)
            cfg.setdefault('calibration_history',[]).append(record)
            tmp=self.cfg_path.with_suffix('.tmp'); tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(self.cfg_path)
            self.cfg=cfg
            prefix='force' if force else 'def'
            self.cal_vars[prefix+'_factor'].set(str(fit['factor'])); self.cal_vars[prefix+'_offset'].set(str(fit['offset']))
            if force: self.zero_force_v=0
            else: self.zero_deform_v=0
            self.force_window.clear(); self.deform_window.clear()
            self.cal_result.set('Calibración guardada con patrones, fecha y errores. Tara del sensor reiniciada.'); self.status.set('Calibración aplicada')
        except (ValueError,OSError) as exc: messagebox.showerror('Calibración', str(exc))

    def confirm_discard(self):
        return not self.dirty or messagebox.askyesno('Datos sin guardar', 'Hay datos sin guardar. ¿Desea descartarlos?')

    def update_summary(self):
        if not self.samples:
            self.summary.set('Sin datos de ensayo.'); return
        peak=max(self.samples,key=lambda s:s.force_kp)
        duration=self.samples[-1].t-self.samples[0].t
        speed=(self.samples[-1].deformation_mm-self.samples[0].deformation_mm)*60/duration if duration else 0
        self.summary.set(f'{len(self.samples):,} puntos · {duration:.1f} s · Pico {peak.force_kp:.2f} kp / {peak.force_kp*0.00980665:.3f} kN · Deformación al pico {peak.deformation_mm:.3f} mm · Velocidad media {speed:.2f} mm/min')

    def open_test(self):
        if self.recording:
            messagebox.showinfo('Abrir', 'Detenga el ensayo antes de abrir otro.'); return
        if not self.confirm_discard(): return
        path=filedialog.askopenfilename(filetypes=[('Ensayos CSV / TXT','*.csv *.txt')])
        if not path:return
        try:
            from app import Sample
            if Path(path).suffix.lower()=='.txt':
                samples=[Sample(t,float('nan'),float('nan'),f,d) for t,f,d in read_legacy(path)]
            else:
                with open(path,encoding='utf-8-sig',newline='') as f:
                    samples=[]
                    for row in csv.DictReader(f,delimiter=';'):
                        vf=float(row['voltaje_fuerza_V'] or 'nan'); vd=float(row['voltaje_deformacion_V'] or 'nan')
                        samples.append(Sample(number(row['tiempo_s']),vf,vd,number(row['fuerza_kp']),number(row['deformacion_mm'])))
                if not samples: raise ValueError('No hay lecturas.')
                if any(b.t<a.t for a,b in zip(samples,samples[1:])): raise ValueError('Tiempos desordenados.')
            metadata={}
            sidecar=Path(path).with_suffix('.metadata.json')
            if Path(path).suffix.lower()=='.csv' and sidecar.exists():
                metadata=json.loads(sidecar.read_text(encoding='utf-8'))
                if not isinstance(metadata,dict):raise ValueError('Metadatos inválidos.')
            from sessions import make_session
            session=make_session(samples,dict(reference=metadata.get('reference',Path(path).stem),
                operator=metadata.get('operator',''),sample_id=metadata.get('sample_id',''),
                notes=metadata.get('notes','Importado: '+Path(path).name),demo=metadata.get('demo'),source=Path(path).name),
                configuration=metadata.get('configuration'),acquired_at=metadata.get('acquired_at'))
            self.restore_session(session)
            self.status.set('Archivo cargado · use Guardar en historial para archivarlo')
        except (ValueError,KeyError,OSError,TypeError) as exc: messagebox.showerror('Abrir ensayo',str(exc))

    def save_legacy(self):
        if self.recording:
            messagebox.showinfo('Exportación','Detenga el ensayo antes de exportar.'); return
        if not self.samples:return
        path=filedialog.asksaveasfilename(defaultextension='.txt',filetypes=[('Marshall antiguo','*.txt')])
        if not path:return
        try:
            with open(path,'w',encoding='utf-8') as f:
                for s in self.samples:f.write(f'{s.deformation_mm*100:.6f} * {s.force_kp:.6f} * {s.t:.6f}\n')
            self.status.set('TXT exportado (centésimas de mm, kp, segundos)')
        except OSError as exc: messagebox.showerror('Exportación',str(exc))
