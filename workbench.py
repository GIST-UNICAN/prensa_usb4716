"""Herramientas de calibración y revisión integradas en la aplicación."""
import csv
import json
import time
import math
import statistics
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from measurement import number, fit_calibration, read_legacy
from legacy_processing import legacy_text
from theme import UC_DEEP, UC_PRIMARY


class Workbench:
    def build_workbench(self):
        self.ring_zero = None
        self.ring_one = None
        self.ring_force = tk.StringVar()
        self.ring_channels = tk.StringVar(value='Solo deformación')
        self.active_calibration = tk.StringVar()
        self.ring_status = tk.StringVar(value='Sin carga: capture cero. Después sitúe el anillo en 1 mm y capture ambos canales.')
        self.cal_points = []
        self.recent_volts = []
        self.dirty = False
        self.test_context = None
        self.last_plot = 0
        self.cal_channel = tk.StringVar(value='Fuerza (kp)')
        self.cal_voltage = tk.StringVar()
        self.cal_reference = tk.StringVar()
        self.cal_result = tk.StringVar(value='1. Seleccione el sensor   →   2. Añada patrones   →   3. Revise y aplique')
        laboratory=ttk.Frame(self.calibration_notebook)
        self.calibration_notebook.add(laboratory,text='Patrones / anillo / versiones')
        scroll=tk.Canvas(laboratory,highlightthickness=0)
        scrollbar=ttk.Scrollbar(laboratory,orient='vertical',command=scroll.yview)
        scrollbar.pack(side='right',fill='y'); scroll.pack(side='left',fill='both',expand=True)
        scroll.configure(yscrollcommand=scrollbar.set)
        tab=ttk.Frame(scroll,padding=14)
        self.calibration_laboratory=tab
        window=scroll.create_window((0,0),window=tab,anchor='nw')
        tab.bind('<Configure>',lambda _:scroll.configure(scrollregion=scroll.bbox('all')))
        scroll.bind('<Configure>',lambda event:scroll.itemconfigure(window,width=event.width))
        scroll.bind('<MouseWheel>',lambda event:scroll.yview_scroll(-int(event.delta/120),'units'))
        ttk.Label(tab, text='Calibración multipunto', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(tab, text='Voltajes brutos, sin tara. Ajuste lineal por mínimos cuadrados; patrones en kp o mm.').pack(anchor='w', pady=(4,12))
        ring = ttk.LabelFrame(tab, text='Calibración de 0 a 1 mm', padding=8)
        ring.pack(fill='x', pady=(0,10))
        ttk.Label(ring, textvariable=self.active_calibration, wraplength=940).pack(anchor='w')
        ttk.Combobox(ring, textvariable=self.ring_channels, values=['Solo deformación', 'Ambas'], state='readonly', width=24).pack(anchor='w', pady=4)
        controls = ttk.Frame(ring); controls.pack(fill='x')
        ttk.Label(controls, text='Fuerza conocida a 1 mm (kp):').pack(side='left')
        ttk.Entry(controls, textvariable=self.ring_force, width=10).pack(side='left', padx=5)
        ttk.Button(controls, text='1. Capturar cero', command=lambda: self.capture_ring_point(False)).pack(side='left', padx=4)
        ttk.Button(controls, text='2. Capturar a 1 mm', command=lambda: self.capture_ring_point(True)).pack(side='left', padx=4)
        ttk.Button(controls, text='3. Aplicar y guardar', command=self.save_ring_calibration).pack(side='left', padx=4)
        ttk.Label(ring, textvariable=self.ring_status, wraplength=940).pack(anchor='w', pady=(5,0))
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
        resultbar = ttk.Frame(self.advanced_controls, padding=10)
        resultbar.pack(fill='x')
        ttk.Label(resultbar, textvariable=self.summary, wraplength=1100, font=('Segoe UI',11,'bold')).pack(anchor='w')
        actions = ttk.Frame(self.advanced_controls, padding=(10,4))
        actions.pack(fill='x', before=resultbar)
        ttk.Button(actions, text='Abrir CSV / TXT antiguo', command=self.open_test).pack(side='left')
        ttk.Button(actions, text='Exportar TXT antiguo', command=self.save_legacy).pack(side='left', padx=8)
        self.refresh_calibration()
        self.refresh_active_calibration()
        compare=ttk.LabelFrame(tab,text='Comparar calibraciones guardadas',padding=6)
        compare.pack(fill='x')
        self.cal_version=tk.StringVar(value='Actual')
        self.cal_versions={'Actual':dict(self.cfg)}
        for i,record in enumerate(self.cfg.get('calibration_history',[])):
            previous=record.get('previous_calibration')
            if previous:
                self.cal_versions[f"Anterior al ajuste {i+1}"]={**self.cfg,**previous}
            fitted=dict(self.cfg)
            found=False
            for name,factor,offset in [('force_fit','force_factor_kp_per_v','force_offset_kp'),('deformation_fit','deformation_factor_mm_per_v','deformation_offset_mm')]:
                fit=record.get(name)
                if fit:
                    fitted.update({factor:fit['factor'],offset:fit['offset']}); found=True
            if found: self.cal_versions[f"Ajuste {i+1} · {record.get('date','')}"]=fitted
        picker=ttk.Combobox(compare,textvariable=self.cal_version,values=list(self.cal_versions),state='readonly',width=48)
        picker.pack(side='left'); picker.bind('<<ComboboxSelected>>',lambda _:self.preview_calibration_version())
        ttk.Button(compare,text='Aplicar al sensor seleccionado',command=self.apply_calibration_version).pack(side='left',padx=6)
        self.cal_comparison=tk.StringVar()
        ttk.Label(tab,textvariable=self.cal_comparison,wraplength=950).pack(anchor='w')
        self.preview_calibration_version()

    def preview_calibration_version(self):
        selected=self.cfg if self.cal_version.get()=='Actual' else self.cal_versions[self.cal_version.get()]
        lines=[]
        for label,factor,offset,index in [('Fuerza','force_factor_kp_per_v','force_offset_kp',1),('Deformación','deformation_factor_mm_per_v','deformation_offset_mm',2)]:
            voltage=self.recent_volts[-1][index] if self.recent_volts else 1.
            old=self.cfg[factor]*voltage+self.cfg.get(offset,0)
            new=selected[factor]*voltage+selected.get(offset,0)
            lines.append(f"{label}: factor {self.cfg[factor]:.8g} → {selected[factor]:.8g}; offset {self.cfg.get(offset,0):.8g} → {selected.get(offset,0):.8g}. A {voltage:.5g} V, sin tara: {old:.6g} → {new:.6g} (diferencia {new-old:+.6g}).")
        self.cal_comparison.set('\n'.join(lines))

    def apply_calibration_version(self):
        if self.recording or self.tare_pending:
            messagebox.showinfo('Calibración','Detenga ensayo y tara antes de cambiar la calibración.'); return
        force=self.cal_channel.get().startswith('Fuerza')
        keys=('force_factor_kp_per_v','force_offset_kp') if force else ('deformation_factor_mm_per_v','deformation_offset_mm')
        selected=self.cfg if self.cal_version.get()=='Actual' else self.cal_versions[self.cal_version.get()]
        cfg=json.loads(json.dumps(self.cfg))
        previous={k:cfg.get(k,0) for k in keys}
        cfg.update({k:selected.get(k,0) for k in keys})
        cfg.setdefault('calibration_history',[]).append(dict(date=datetime.now().isoformat(),method='select_saved_calibration',sensor=self.cal_channel.get(),previous_calibration=previous,restored_calibration={k:cfg[k] for k in keys}))
        try:
            tmp=self.cfg_path.with_suffix('.tmp'); tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(self.cfg_path)
        except OSError as exc:
            messagebox.showerror('Calibración',str(exc)); return
        self.cfg=cfg
        prefix='force' if force else 'def'
        self.cal_vars[prefix+'_factor'].set(str(cfg[keys[0]])); self.cal_vars[prefix+'_offset'].set(str(cfg[keys[1]]))
        if force: self.zero_force_v=0.
        else: self.zero_deform_v=0.
        self._reset_display(); self.refresh_active_calibration(); self.preview_calibration_version()
        self.status.set('Calibración seleccionada guardada; tara del sensor reiniciada')

    def refresh_active_calibration(self):
        c=self.cfg
        history=c.get("calibration_history", [])
        date=history[-1].get("date", "sin fecha") if history else "sin patrones guardados"
        self.active_calibration.set(f"Activa · Fuerza: {c['force_factor_kp_per_v']:.9g} × V + {c.get('force_offset_kp',0):.9g} kp\n"
            f"Deformación: {c['deformation_factor_mm_per_v']:.9g} × V + {c.get('deformation_offset_mm',0):.9g} mm\n"
            f"Último ajuste: {date} · Archivo: {self.cfg_path.resolve()}")

    def capture_ring_point(self, at_one_mm):
        if not self.connected or self.recording or self.tare_pending:
            messagebox.showinfo('Anillo', 'Conecte la DAQ y detenga el ensayo y la tara antes de capturar.'); return
        try:
            now = time.perf_counter()
            recent = [r for r in self.recent_volts if 0 <= now-r[0] <= .25]
            if len(recent)<3 or recent[-1][0]-recent[0][0]<.1 or now-recent[-1][0]>.1:
                raise ValueError('Espere lecturas recientes antes de capturar.')
            if self.signal_alert:
                raise ValueError('La señal tiene saltos repetidos. Estabilice la señal antes de calibrar.')
            if any(not math.isfinite(v) or abs(v)>=self.cfg['saturation_voltage'] for r in recent for v in r[1:]):
                raise ValueError('Voltajes inválidos o próximos a saturación.')
            if at_one_mm and self.ring_zero is None:
                raise ValueError('Capture primero el cero sin carga.')
            point = dict(t=recent[-1][0], vf=statistics.mean(r[1] for r in recent), vd=statistics.mean(r[2] for r in recent),
                         samples=len(recent), averaging_seconds=recent[-1][0]-recent[0][0],
                         sigma_f=statistics.stdev(r[1] for r in recent),
                         sigma_d=statistics.stdev(r[2] for r in recent),
                         configuration=json.loads(json.dumps(self.cfg)), demo=self.demo,
                         captured_at=datetime.now().isoformat())
            if at_one_mm:
                self.ring_one=point
            else:
                self.ring_zero=point; self.ring_one=None
            self.ring_status.set(f"{'1 mm' if at_one_mm else 'Cero'} capturado: fuerza {point['vf']:+.6f} V · deformación {point['vd']:+.6f} V. "
                                 + ('Capturas pendientes de aplicar. Seleccione el canal y pulse Aplicar y guardar.' if at_one_mm else 'Sitúe el anillo en 1 mm y capture el segundo punto.'))
        except ValueError as exc:
            messagebox.showerror('Anillo',str(exc))

    def save_ring_calibration(self):
        if not self.connected or self.recording or self.tare_pending:
            messagebox.showinfo('Anillo','Conecte la DAQ y detenga ensayo y tara antes de guardar.'); return
        try:
            if self.ring_zero is None or self.ring_one is None:
                raise ValueError('Capture cero y 1 mm antes de guardar.')
            zero, one = self.ring_zero, self.ring_one
            if any(p['configuration'] != self.cfg or p['demo'] != self.demo for p in (zero,one)):
                raise ValueError('La configuración cambió; repita las dos capturas.')
            both = self.ring_channels.get() == 'Ambas'
            force = number(self.ring_force.get()) if both else None
            if both and force<=0: raise ValueError('Introduzca la fuerza positiva del certificado, expresada en kp.')
            fits = {}
            targets=[('vd','sigma_d',1.)]
            if both: targets.append(('vf','sigma_f',force))
            for key, sigma, target in targets:
                uncertainty=math.hypot(zero[sigma],one[sigma])
                if abs(one[key]-zero[key]) <= max(5*uncertainty,3*10/65536):
                    raise ValueError('La separación entre puntos es insuficiente frente al ruido. Mantenga los puntos estables y repita.')
                fits[key]=fit_calibration([(zero[key],0.),(one[key],target)])
            cfg=json.loads(json.dumps(self.cfg))
            cfg.update(deformation_factor_mm_per_v=fits['vd']['factor'],deformation_offset_mm=fits['vd']['offset'])
            if both: cfg.update(force_factor_kp_per_v=fits['vf']['factor'],force_offset_kp=fits['vf']['offset'])
            cfg.setdefault('calibration_history',[]).append(dict(date=datetime.now().isoformat(), method='ring_zero_and_1mm',
                demo=self.demo, force_at_1mm_kp=force, deformation_reference_mm=1.,
                zero={k:v for k,v in zero.items() if k!='configuration'}, one_mm={k:v for k,v in one.items() if k!='configuration'},
                channels=self.ring_channels.get(), previous_calibration={k:self.cfg.get(k,0) for k in ('force_factor_kp_per_v','force_offset_kp','deformation_factor_mm_per_v','deformation_offset_mm')},
                force_fit=fits.get('vf'), deformation_fit=fits['vd']))
            tmp=self.cfg_path.with_suffix('.tmp')
            tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(self.cfg_path)
            self.cfg=cfg
            for prefix,key in (('force','vf'),('def','vd')):
                if key not in fits: continue
                self.cal_vars[prefix+'_factor'].set(str(fits[key]['factor']))
                self.cal_vars[prefix+'_offset'].set(str(fits[key]['offset']))
            self.zero_deform_v=0.
            if both: self.zero_force_v=0.
            self._reset_display()
            self.ring_zero=self.ring_one=None
            self.refresh_active_calibration()
            self.ring_status.set(('Ambos canales guardados.' if both else 'Deformación guardada; calibración y tara de fuerza conservadas.') + ' Se recuperará al abrir el programa. Archivo: '+str(self.cfg_path.resolve()))
            self.status.set('Calibración aplicada y guardada')
        except (ValueError,OSError) as exc:
            messagebox.showerror('Anillo',str(exc))

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
            self._reset_display()
            self.refresh_active_calibration()
            self.cal_result.set('Calibración guardada con patrones, fecha y errores. Tara del sensor reiniciada.'); self.status.set('Calibración aplicada')
        except (ValueError,OSError) as exc: messagebox.showerror('Calibración', str(exc))

    def confirm_discard(self):
        return not self.dirty or messagebox.askyesno('Datos sin guardar', 'Hay datos sin guardar. ¿Desea descartarlos?')

    def refresh_marshall_results(self):
        if not hasattr(self,'marshall_text'):return
        from marshall_results import session_results,draw_results,LABELS
        result=session_results(self.current_session()) if self.samples else __import__("marshall_results").calculate([])
        self.marshall_text.set(result.get('processing','')+'\n'+'   |   '.join(f"{label}: {result[key]:.2f}" if result[key] is not None else f"{label}: no disponible" for key,label in LABELS))
        if hasattr(self,'marshall_values'):
            self.marshall_processing.set('UNE-EN 12697-34:2022')
            for key,_ in LABELS:
                value=result[key]
                self.marshall_values[key].set(('%.0f' if key=='peak_kp' else '%.4f' if key=='correction_factor' else '%.2f' if key=='zero_mm' else '%.1f') % value if value is not None else 'Pendiente h/v' if key in ('stability_kn','quotient_kn_mm','correction_factor') else 'No disponible')
        if self.marshall_canvas:
            draw_results(self.marshall_ax,result);self.marshall_canvas.draw_idle()

    def update_summary(self):
        if not self.recording or self.nb.select()==str(self.tab_data):self.refresh_marshall_results()
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
                for r in self.current_export_session()['samples']:f.write(f"{r['deformation_mm']*100:.6f} * {r['force_kp']:.6f} * {r['t']:.6f}\n")
            self.status.set('TXT procesado: mismos puntos que Exportar, centésimas de mm / kp / segundos')
        except OSError as exc: messagebox.showerror('Exportación',str(exc))
