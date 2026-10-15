"""Historial, comparación de ensayos y exportaciones ampliadas."""
from datetime import datetime
from pathlib import Path
import json
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from sessions import SessionStore, make_session, timestamp, load_session, session_summary, validate_session
from exports import CHARTS, draw_chart, export_session, filtered_csv_text
from units import available_units,from_kp


class AnalysisUI:
    def build_analysis(self):
        self.session_id=None
        self.acquired_at=None
        self.session_demo=self.demo
        self.session_source='Adquisición'
        self.comparisons=[]
        self.history_search=tk.StringVar()
        self.history_mode=tk.StringVar(value='Todos')
        self.history_info=tk.StringVar(value='Los ensayos se archivan automáticamente al detener la adquisición.')
        self.chart_kind=tk.StringVar(value=CHARTS['fd'])
        self.chart_unit=tk.StringVar(value='kp')
        self.chart_average=tk.StringVar(value='10')
        self.chart_filter=tk.StringVar(value='Mediana')
        self.chart_range=tk.StringVar(value='Ensayo detectado')
        self.chart_positive=tk.BooleanVar(value=True)
        self.chart_info=tk.StringVar(value='Seleccione un ensayo o compare varios desde el historial.')
        self.tab_history=self.history_host
        self.tab_analysis=ttk.Frame(self.config_notebook,padding=12)
        self.config_notebook.add(self.tab_analysis,text='Análisis')
        self._build_history();self._build_analysis_charts()
        ttk.Button(self.advanced_controls,text='Guardar ensayo actual en historial',command=self.archive_current).pack(anchor='w',pady=3)
        ttk.Button(self.advanced_controls,text='Importar ensayo JSON',command=self.import_session).pack(anchor='w',pady=3)
        # Cambiar identificación de un ensayo guardado requiere volver a guardarlo.
        for var in (self.test_name,self.operator,self.sample_id,self.notes,self.specimen_height,self.specimen_volume):
            var.trace_add('write',self._metadata_changed)
        self.refresh_history()

    def _metadata_changed(self,*_):
        if self.samples: self.dirty=True

    def session_store(self):
        return SessionStore(self._outdir()/'historial.sqlite3')

    def geometry_controls(self,parent):
        for label,var in (('Altura (mm)',self.specimen_height),('Volumen (mm³)',self.specimen_volume)):
            ttk.Label(parent,text=label).pack(side='left',padx=(12,3))
            entry=ttk.Entry(parent,textvariable=var,width=10);entry.pack(side='left')
            entry.bind('<FocusOut>',lambda _:self.update_summary())
            entry.bind('<Return>',lambda _:self.update_summary())

    def specimen_geometry(self,strict=False):
        import math
        result={}
        for key,label,var in (('specimen_height_mm','altura',self.specimen_height),('specimen_volume_mm3','volumen',self.specimen_volume)):
            text=var.get().strip()
            if not text:continue
            try:
                value=float(text.replace(',','.'))
                if not math.isfinite(value) or value<=0:raise ValueError()
                result[key]=value
            except ValueError:
                if strict:raise ValueError(f'La {label} debe ser un número positivo o quedar vacía.')
        return result

    def current_session(self):
        context=dict(self.test_context or {})
        for key in ('specimen_height_mm','specimen_volume_mm3'):context.pop(key,None)
        context.update(self.specimen_geometry())
        return make_session(self.samples,
            dict(reference=self.test_name.get(),operator=self.operator.get(),sample_id=self.sample_id.get(),
                 notes=self.notes.get(),demo=self.session_demo,source=self.session_source),
            configuration=context or None,session_id=self.session_id,acquired_at=self.acquired_at)

    def current_export_session(self):
        from copy import deepcopy
        from marshall_results import calculation_rows
        source=self.current_session();result=deepcopy(source);points=calculation_rows(source)
        result['samples']=[{key:r.get(key) for key in ('t','vf','vd','force_kp','deformation_mm')} for r in points]
        result['configuration']={**(result.get('configuration') or {}),'export_processed':True,'export_block_counts':[r.get('samples_count',1) for r in points],'export_method':'Media de bloques de diez; mismos puntos que Exportar','standard_reference':'UNE-EN 12697-34:2022'}
        return result

    def archive_current(self, automatic=False):
        if self.recording:
            if not automatic: messagebox.showinfo('Historial','Detenga el ensayo antes de archivarlo.')
            return False
        if not self.samples:
            if not automatic: messagebox.showinfo('Historial','No hay muestras que guardar.')
            return False
        try:
            session=self.current_session(); self.session_store().save(session)
            self.session_id=session['id']; self.dirty=False
            self.name_saved.set('Nombre guardado')
            self.refresh_history(); self.status.set('Ensayo guardado en el historial')
            return True
        except (OSError,ValueError,sqlite3.Error) as exc:
            self.dirty=True
            messagebox.showerror('Historial',f'No se pudo archivar. Los datos siguen en memoria; expórtelos antes de cerrar.\n{exc}')
            return False

    def _build_history(self):
        tab=self.tab_history
        bar=ttk.Frame(tab);bar.pack(fill='x')
        ttk.Label(bar,text='Ensayos guardados · doble clic para cargar',font=('Segoe UI',10,'bold')).pack(side='left')
        search=ttk.Entry(bar,textvariable=self.history_search,width=24);search.pack(side='left',padx=6)
        search.bind('<Return>',lambda _:self.refresh_history())
        mode=ttk.Combobox(bar,textvariable=self.history_mode,values=['Todos','Real','Simulación','Importado / desconocido'],state='readonly',width=13)
        mode.pack(side='left');mode.bind('<<ComboboxSelected>>',lambda _:self.refresh_history())
        ttk.Button(bar,text='Actualizar',command=self.refresh_history).pack(side='right')
        container=ttk.Frame(tab);container.pack(fill='x',pady=(3,0))
        columns=('latest','date','reference','sample','operator','mode','peak','def','points')
        self.history_tree=ttk.Treeview(container,columns=columns,show='headings',selectmode='extended',height=3)
        for col,title,width in zip(columns,['','Fecha','Referencia','Probeta','Operador','Origen','Pico bruto kN','Def. pico mm','Muestras'],[55,125,160,70,80,65,90,85,75]):
            self.history_tree.heading(col,text=title);self.history_tree.column(col,width=width,minwidth=45,stretch=True)
        sy=ttk.Scrollbar(container,orient='vertical',command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=sy.set)
        self.history_tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns')
        container.columnconfigure(0,weight=1)
        self.history_tree.tag_configure('latest',foreground='#14505B',font=('Segoe UI',9,'bold'))
        self.history_tree.bind('<Double-1>',lambda _:self.open_history())
        self.history_menu=tk.Menu(self.history_tree,tearoff=False)
        self.history_menu.add_command(label='Borrar ensayo…',command=self.confirm_delete_history)
        self.history_tree.bind('<Button-3>',self.history_context_menu)
        self.history_tree.bind('<<TreeviewSelect>>',self.history_selected)
        ttk.Label(tab,textvariable=self.history_info,wraplength=1000).pack(anchor='w')

    def history_context_menu(self,event):
        item=self.history_tree.identify_row(event.y)
        if not item:return
        self.history_tree.selection_set(item);self.history_tree.focus(item)
        self.history_menu.tk_popup(event.x_root,event.y_root)

    def confirm_delete_history(self):
        ids=self.history_tree.selection()
        if len(ids)!=1:return
        session_id=ids[0]
        try:session=self.session_store().get(session_id)
        except (ValueError,OSError,sqlite3.Error) as exc:
            messagebox.showerror('Borrar ensayo',str(exc));return
        dialog=tk.Toplevel(self);dialog.title('Confirmar borrado');dialog.transient(self);dialog.resizable(False,False)
        body=ttk.Frame(dialog,padding=20);body.pack(fill='both',expand=True)
        reference=session['metadata'].get('reference') or session_id
        ttk.Label(body,text=f'¿Borrar el ensayo «{reference}» del historial?',wraplength=430).pack(anchor='w')
        ttk.Label(body,text='Este borrado es permanente.',padding=(0,8)).pack(anchor='w')
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons,text='Cancelar',command=dialog.destroy).pack(side='right',padx=4)
        def confirm():
            if self.delete_history_session(session_id):dialog.destroy()
        ttk.Button(buttons,text='Confirmar borrado',command=confirm).pack(side='right',padx=4)
        dialog.bind('<Escape>',lambda _:dialog.destroy());dialog.grab_set()

    def delete_history_session(self,session_id):
        try:
            self.session_store().delete(session_id)
            self.comparisons=[s for s in self.comparisons if s['id']!=session_id]
            if self.session_id==session_id:
                self.dirty=False;self.reset_test()
            self.refresh_history();self.status.set('Ensayo borrado del historial')
            return True
        except (ValueError,OSError,sqlite3.Error) as exc:
            messagebox.showerror('Borrar ensayo',str(exc));return False

    def refresh_history(self):
        try:
            selected=self.history_tree.selection()
            items=self.session_store().list(self.history_search.get().strip(),self.history_mode.get())
            def order(item):
                try:return datetime.fromisoformat(item.get('acquired_at') or item['saved_at']).timestamp()
                except (ValueError,TypeError):return 0.
            all_items=self.session_store().list()
            latest=max(all_items,key=order)['id'] if all_items else None
            items.sort(key=order,reverse=True)
            self.history_tree.delete(*self.history_tree.get_children())
            for item in items:
                m=item['metadata']; r=item['summary']
                date=item.get('acquired_at') or item['saved_at']
                try: date=datetime.fromisoformat(date).astimezone().strftime('%d/%m/%Y %H:%M')
                except ValueError: pass
                mode='Simulación' if m.get('demo') is True else 'Real' if m.get('demo') is False else 'Desconocido'
                self.history_tree.insert('','end',iid=item['id'],tags=('latest',) if item['id']==latest else (),values=('Último' if item['id']==latest else '',date,m.get('reference',''),m.get('sample_id',''),m.get('operator',''),mode,f"{r['peak_kn']:.3f}",f"{r['deformation_at_peak_mm']:.3f}",r['points']))
            self.history_tree.selection_set([iid for iid in selected if self.history_tree.exists(iid)])
            self.history_info.set(f'{len(items)} ensayos · El último está marcado. Doble clic para cargar resultados y exportar Excel.')
        except (OSError,ValueError,sqlite3.Error) as exc:
            self.history_info.set(f'No se pudo leer el historial: {exc}')

    def history_selected(self,event=None):
        ids=self.history_tree.selection()
        if len(ids)!=1:return
        try:
            session=self.session_store().get(ids[0]); summary=session_summary(session)
            self.history_info.set(f"{summary['points']} muestras · {summary['duration_s']:.2f} s · {session['metadata'].get('notes','')} · Doble clic para abrir")
        except (ValueError,sqlite3.Error,OSError) as exc: self.history_info.set(str(exc))

    def restore_session(self, session, archived=False):
        validate_session(session)
        from app import Sample
        samples=[Sample(**{key:(float('nan') if value is None else value) for key,value in row.items() if key in ('t','vf','vd','force_kp','deformation_mm')}) for row in session['samples']]
        self.samples=samples; self.test_context=session.get('configuration')
        cfg=self.test_context or {}
        self.specimen_height.set(str(cfg.get('specimen_height_mm','')))
        self.specimen_volume.set(str(cfg.get('specimen_volume_mm3','')))
        # Los archivos externos se guardan como un registro nuevo, nunca sobrescriben un UUID local.
        self.session_id=session['id'] if archived else None
        self.acquired_at=session.get('acquired_at'); meta=session['metadata']
        self.session_demo=meta.get('demo'); self.session_source=meta.get('source','Importado JSON')
        for variable,key in [(self.test_name,'reference'),(self.sample_id,'sample_id'),(self.operator,'operator'),(self.notes,'notes')]:
            variable.set(meta.get(key,''))
        self.dirty=False
        self.name_saved.set("Nombre guardado")
        summary=session_summary(session)
        self.max_force=summary['peak_kp']; self.max_deformation=summary['max_deformation_mm']
        self.max_force_var.set(f'{self.max_force:.2f}'); self.max_def_var.set(f'{self.max_deformation:.3f}')
        self.comparisons=[]; self._rebuild_table(); self._redraw_plots(); self.update_summary(); self.refresh_analysis()
        if getattr(self,'processed_current',None):
            value=self.processed_current
            self.current_force.set(f"{from_kp(value.force_kp,self.display_unit.get(),self.cfg.get('specimen_area_mm2')):.0f}")
            self.current_kn.set(f"{from_kp(value.force_kp,'kN'):.1f}")
            self.current_def.set(f"{value.deformation_mm:.2f}")
        self.status.set('Ensayo recuperado con su configuración original')

    def open_history(self):
        if self.recording:
            messagebox.showinfo('Historial','Detenga el ensayo antes de abrir otro.'); return
        ids=self.history_tree.selection()
        if len(ids)!=1:
            messagebox.showinfo('Historial','Seleccione un ensayo para abrir.'); return
        if not self.confirm_discard():return
        try:
            self.restore_session(self.session_store().get(ids[0]),archived=True)
            self.nb.select(self.tab_data)
        except (OSError,ValueError,sqlite3.Error,TypeError) as exc: messagebox.showerror('Historial',str(exc))

    def import_session(self):
        if self.recording:
            messagebox.showinfo('Importar','Detenga el ensayo antes de abrir otro.'); return
        if not self.confirm_discard():return
        path=filedialog.askopenfilename(filetypes=[('Ensayo Marshall JSON','*.json')])
        if not path:return
        try:
            self.restore_session(load_session(path))
            self.archive_current(); self.nb.select(self.tab_data)
        except (OSError,ValueError,TypeError) as exc: messagebox.showerror('Importar',str(exc))

    def _build_analysis_charts(self):
        tab=self.tab_analysis
        ttk.Label(tab,text='Explorar resultados',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(tab,text='Cinco vistas, unidades seleccionables, filtros y comparación. La señal bruta nunca se modifica.').pack(anchor='w',pady=(3,10))
        bar=ttk.Frame(tab); bar.pack(fill='x')
        for var,values,width in [(self.chart_kind,list(CHARTS.values()),25),(self.chart_unit,available_units(self.cfg.get('specimen_area_mm2')),10),(self.chart_filter,['Antiguo (10 lecturas)','Sin filtro','Media temporal 1 s','Media móvil','Mediana'],14),(self.chart_range,['Todo','Ensayo detectado','Desde 5 %','Ascenso 5–95 %'],18)]:
            box=ttk.Combobox(bar,textvariable=var,values=values,state='readonly',width=width)
            box.pack(side='left',padx=(0,8)); box.bind('<<ComboboxSelected>>',lambda _:self.refresh_analysis())
        ttk.Label(bar,text='Media (muestras)').pack(side='left')
        smooth=ttk.Combobox(bar,textvariable=self.chart_average,values=['1','5','10','25','50'],width=6,state='readonly')
        smooth.pack(side='left',padx=8); smooth.bind('<<ComboboxSelected>>',lambda _:self.refresh_analysis())
        ttk.Button(bar,text='Ver ensayo actual',command=self.show_current_analysis).pack(side='left')

        ttk.Checkbutton(tab,text='Ocultar negativos en fuerza/deformación (solo gráfica)',variable=self.chart_positive,command=self.refresh_analysis).pack(anchor='w')

        self.analysis_canvas=None
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            self.analysis_figure=Figure(figsize=(10,4.8),constrained_layout=True)
            self.analysis_ax=self.analysis_figure.add_subplot(111)
            frame=ttk.Frame(tab); frame.pack(fill='both',expand=True,pady=8)
            self.analysis_canvas=FigureCanvasTkAgg(self.analysis_figure,master=frame)
            toolbar=NavigationToolbar2Tk(self.analysis_canvas,frame,pack_toolbar=False); toolbar.pack(side='bottom',fill='x')
            self.analysis_canvas.get_tk_widget().pack(fill='both',expand=True)
            draw_chart(self.analysis_ax,[],'fd')
        except ImportError:
            ttk.Label(tab,text='Instale matplotlib para activar las gráficas.').pack(pady=30)
        ttk.Label(tab,textvariable=self.chart_info,wraplength=1050).pack(anchor='w',pady=4)
        self.nb.bind('<<NotebookTabChanged>>',self.analysis_tab_changed,add='+')
        self.config_notebook.bind('<<NotebookTabChanged>>',self.analysis_tab_changed,add='+')

    def analysis_tab_changed(self,event=None):
        if self.nb.select()==str(self.tab_data):self.refresh_marshall_results()
        if self.nb.select()==str(self.tab_config) and self.config_notebook.select()==str(self.tab_analysis):self.refresh_analysis()

    def show_current_analysis(self):
        self.comparisons=[]; self.refresh_analysis()

    def refresh_analysis(self):
        if self.analysis_canvas is None:return
        sessions=self.comparisons or ([self.current_session()] if self.samples else [])
        kind=next(k for k,v in CHARTS.items() if v==self.chart_kind.get())
        draw_chart(self.analysis_ax,sessions,kind,self.chart_unit.get(),int(self.chart_average.get()),self.chart_filter.get(),self.chart_range.get(),self.chart_positive.get())
        self.analysis_canvas.draw_idle()
        if self.comparisons:
            self.chart_info.set('Comparación · '+ ' | '.join(f"{s['metadata'].get('reference','Ensayo')}: {session_summary(s)['peak_kn']:.3f} kN" for s in sessions)+' · Tiempos relativos al inicio de cada ensayo.')
        else:
            self.chart_info.set(f"Vista del ensayo actual · {self.chart_filter.get()} · tramo {self.chart_range.get()}. Pulse «Ver ensayo actual» para actualizar durante la adquisición. Los filtros no modifican el archivo bruto.")

    def compare_history(self):
        ids=self.history_tree.selection()
        if not 2<=len(ids)<=6:
            messagebox.showinfo('Comparar','Seleccione entre dos y seis ensayos con Ctrl/Cmd + clic.'); return
        try:
            self.comparisons=[self.session_store().get(iid) for iid in ids]
            self.refresh_analysis(); self.nb.select(self.tab_config);self.config_notebook.select(self.tab_analysis)
        except (OSError,ValueError,sqlite3.Error) as exc: messagebox.showerror('Comparar',str(exc))

    def export_analysis_chart(self):
        if self.recording:
            messagebox.showinfo('Exportación','Detenga el ensayo antes de exportar.'); return
        if self.analysis_canvas is None or not (self.samples or self.comparisons):return
        path=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG','*.png'),('SVG vectorial','*.svg')])
        if not path:return
        try:
            self.refresh_analysis(); self.analysis_figure.savefig(path,dpi=180,bbox_inches='tight')
            self.status.set('Gráfica exportada: '+Path(path).name)
        except (OSError,ValueError) as exc: messagebox.showerror('Gráfica',str(exc))

    def export_extended(self, kind):
        if self.recording:
            messagebox.showinfo('Exportación','Detenga el ensayo antes de exportar.'); return
        if not self.samples:
            messagebox.showinfo('Exportación','No hay muestras que exportar.'); return
        try:self.specimen_geometry(strict=True)
        except ValueError as exc:
            messagebox.showerror('Probeta',str(exc));return
        path=filedialog.asksaveasfilename(initialdir=str(self._outdir()),initialfile='ensayo.'+kind,defaultextension='.'+kind,filetypes=[(kind.upper(),'*.'+kind)])
        if not path:return
        self.configure(cursor='watch'); self.update_idletasks()
        try:
            session=self.current_export_session(); export_session(session,path,kind)
            if self.session_id:
                self.session_store().save(self.current_session());self.refresh_history();self.dirty=False
            if kind in ('json','zip'):self.dirty=False
            self.status.set(f'{kind.upper()} exportado: {Path(path).name}')
        except Exception as exc: messagebox.showerror('Exportación',f'No se pudo exportar: {exc}')
        finally: self.configure(cursor='')

    def export_filtered_csv(self):
        if self.recording:
            messagebox.showinfo('Exportación','Detenga el ensayo antes de exportar.'); return
        if not self.samples:
            messagebox.showinfo('Exportación','No hay muestras que exportar.'); return
        path=filedialog.asksaveasfilename(initialdir=str(self._outdir()),initialfile='vista_filtrada.csv',defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        try:
            Path(path).write_text('\ufeff'+filtered_csv_text(self.current_session(),self.chart_filter.get(),int(self.chart_average.get()),self.chart_range.get()),encoding='utf-8')
            self.status.set('CSV de análisis exportado: '+Path(path).name)
        except (OSError,ValueError) as exc: messagebox.showerror('Exportación',str(exc))

    def export_history_batch(self):
        import zipfile
        import tempfile
        from sessions import dumps_session
        from exports import csv_text
        ids=self.history_tree.selection()
        if not ids:
            messagebox.showinfo('Exportación','Seleccione los ensayos que desea exportar.'); return
        path=filedialog.asksaveasfilename(defaultextension='.zip',filetypes=[('Archivo de ensayos ZIP','*.zip')])
        if not path:return
        try:
            # UUIDs y nombres controlados: referencias del usuario no se convierten en rutas.
            with tempfile.TemporaryDirectory(dir=Path(path).parent) as tmp:
                target=Path(tmp)/'historial.zip'
                with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
                    index=[]
                    for i,iid in enumerate(ids,1):
                        session=self.session_store().get(iid); folder=f'ensayo_{i:03d}'
                        archive.writestr(folder+'/ensayo.json',dumps_session(session))
                        archive.writestr(folder+'/datos.csv','\ufeff'+csv_text(session))
                        index.append(dict(folder=folder,reference=session['metadata'].get('reference',''),**session_summary(session)))
                    archive.writestr('indice.json',json.dumps(index,ensure_ascii=False,indent=2))
                target.replace(path)
            self.status.set(f'{len(ids)} ensayos exportados a ZIP (JSON + CSV + índice)')
        except (OSError,ValueError,sqlite3.Error) as exc: messagebox.showerror('Exportación',str(exc))
