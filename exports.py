"""Exportaciones reproducibles a partir de una instantánea de ensayo."""
import csv
import html
import io
import json
import math
import os
import tempfile
import zipfile
from pathlib import Path
from trial_detection import detect_test_interval
from plot_cleaning import clean_rows, compression_deformation
from legacy_processing import legacy_plot_rows
from force_processing import force_series
from signal_processing import detect_rupture, time_average
from sessions import dumps_session, session_summary
from units import from_kp
from theme import UC_BACKGROUND, UC_CHART_COLORS, UC_DEEP, UC_INK, UC_PALE, UC_PRIMARY

CHARTS = {
    'fd': 'Fuerza · deformación', 'ft': 'Fuerza · tiempo',
    'dt': 'Deformación · tiempo', 'volts': 'Voltajes · tiempo',
    'speed': 'Velocidad · tiempo',
}
COLORS = UC_CHART_COLORS
HEADERS = ['tiempo_s','voltaje_fuerza_V','voltaje_deformacion_V','fuerza_kp','fuerza_kN','deformacion_mm',
           'fuerza_kgf','fuerza_N','presion_Pa','presion_kPa','presion_MPa','presion_kgf_cm2']


def data_rows(session):
    area=(session.get('configuration') or {}).get('specimen_area_mm2')
    for row in session['samples']:
        force=row['force_kp']
        try: pressure=[from_kp(force,u,area) for u in ('Pa','kPa','MPa','kgf/cm²')]
        except ValueError: pressure=['','','','']
        yield [row['t'], row['vf'], row['vd'], force, from_kp(force,'kN'), row['deformation_mm'],
               from_kp(force,'kgf'), from_kp(force,'N'), *pressure]


def csv_text(session):
    out=io.StringIO(newline=''); writer=csv.writer(out,delimiter=';')
    writer.writerow(HEADERS); writer.writerows(data_rows(session)); return out.getvalue()


def moving_average(values, window):
    result=[]; total=0.; count=0
    for i,value in enumerate(values):
        if value is not None: total+=value; count+=1
        if i>=window and values[i-window] is not None:
            total-=values[i-window]; count-=1
        result.append(total/count if count else None)
    return result


def median_filter(values, window):
    """Mediana causal: elimina picos aislados sin mirar datos futuros."""
    result=[]
    for index,value in enumerate(values):
        sample=[v for v in values[max(0,index-window+1):index+1] if v is not None]
        result.append(sorted(sample)[len(sample)//2] if sample else value)
    return result


def filter_values(values, method='Sin filtro', window=1):
    window=max(1,int(window))
    if method == 'Media móvil': return moving_average(values,window)
    if method == 'Mediana': return median_filter(values,window)
    return list(values)


def selected_indices(rows, range_filter='Todo'):
    if range_filter == 'Ensayo detectado':
        span = detect_test_interval(rows)
        if span is None: return []
        return list(range(span['start'], (span['end'] if span['end'] is not None else len(rows)-1)+1))
    """El tramo histórico 5–95 % se limita al ascenso anterior al primer pico."""
    if range_filter == 'Todo' or not rows: return list(range(len(rows)))
    peak_index=max(range(len(rows)),key=lambda i: rows[i]['force_kp'])
    peak=rows[peak_index]['force_kp']; lower=.05*peak
    if range_filter == 'Ascenso 5–95 %':
        return [i for i in range(peak_index+1) if lower <= rows[i]['force_kp'] <= .95*peak]
    if range_filter == 'Desde 5 %':
        return [i for i,row in enumerate(rows) if row['force_kp'] >= lower]
    return list(range(len(rows)))


def chart_series(session, kind, unit='kp', window=1, method='Sin filtro', range_filter='Todo'):
    original=session['samples'] if (session.get('configuration') or {}).get('export_processed') else legacy_plot_rows(session['samples']) if method=='Antiguo (10 lecturas)' else clean_rows(session['samples'])
    indices=selected_indices(original,range_filter)
    rows=[original[i] for i in indices]
    if not rows: return [([],[],'Sin puntos en el tramo elegido')], 'Tiempo (s)', unit
    area=(session.get('configuration') or {}).get('specimen_area_mm2')
    times=[r['t']-rows[0]['t'] for r in rows]
    filter_series=lambda values: time_average([r['t'] for r in original],values,1.) if method=='Media temporal 1 s' else filter_values(values,method,window)
    force_input=original if method=='Antiguo (10 lecturas)' else [{**r,'force_kp':r['force_kp'] if o['force_kp']>=0 else float('nan')} for r,o in zip(original,session['samples'])]
    force_all=[from_kp(v,unit,area) for v in force_series([r['t'] for r in force_input],[r['force_kp'] for r in force_input],method=method,window=window)]
    deform_all=compression_deformation(filter_series([r['deformation_mm'] for r in original]))
    force=[force_all[i] for i in indices]
    deform=[deform_all[i] for i in indices]
    if kind=='fd': return [(deform,force,'Carga')], 'Deformación (mm)', f'Fuerza ({unit})'
    if kind=='ft': return [(times,force,'Carga')], 'Tiempo (s)', f'Fuerza ({unit})'
    if kind=='dt': return [(times,deform,'Deformación')], 'Tiempo (s)', 'Deformación (mm)'
    if kind=='volts':
        vf=filter_series([r['vf'] for r in original])
        vd=filter_series([r['vd'] for r in original])
        return [(times,[vf[i] for i in indices],'Fuerza'),
                (times,[vd[i] for i in indices],'Deformación')], 'Tiempo (s)', 'Voltaje (V)'
    if kind=='speed':
        # Diferencias sobre una ventana de al menos 0,5 s para reducir ruido.
        x=[]; y=[]; j=0
        for i in range(1,len(rows)):
            while j+1<i and times[i]-times[j+1]>=.5: j+=1
            dt=times[i]-times[j]
            if dt>=.5:
                x.append(times[i]); y.append((deform[i]-deform[j])*60/dt)
        return [(x,y,'Velocidad (ventana ≥0,5 s)')], 'Tiempo (s)', 'Velocidad (mm/min)'
    raise ValueError('Gráfica desconocida.')


def draw_chart(ax, sessions, kind, unit='kp', window=1, method='Sin filtro', range_filter='Todo', positive_only=False):
    ax.clear(); ax.set_facecolor(UC_BACKGROUND); ax.grid(alpha=.18,color=UC_PRIMARY)
    ax.set_title(CHARTS[kind],loc='left',fontweight='bold',pad=14)
    visible=False
    for n,session in enumerate(sessions):
        series,xlabel,ylabel=chart_series(session,kind,unit,window,method,range_filter)
        for j,(xs,ys,label) in enumerate(series):
            if positive_only and kind in ('fd','ft','dt'):
                ys=[float('nan') if y is not None and (y<0 or (kind=='fd' and x<0)) else y for x,y in zip(xs,ys)]
            if not any(y is not None and math.isfinite(y) for y in ys): continue
            visible=True
            # Limita solamente la representación; los archivos conservan todos los datos.
            indices=list(range(0,len(xs),max(1,len(xs)//4000)))
            if xs:
                indices=sorted(set(indices+[len(xs)-1]+[max(range(len(ys)),key=lambda i:ys[i] if ys[i] is not None else -math.inf)]))
            name=session['metadata'].get('reference','Ensayo')
            ax.plot([xs[i] for i in indices],[ys[i] if ys[i] is not None else float('nan') for i in indices],
                    color=COLORS[n%len(COLORS)] if len(sessions)>1 else COLORS[j],
                    linestyle='--' if j else '-',marker=None,markersize=3,linewidth=1.6,label=f'{name} · {label}')
        if kind in ('fd','ft','dt'):
            force_series_for_peak,_,_=chart_series(session,'ft',unit,window,method,range_filter)
            force_values=force_series_for_peak[0][1]
            finite=[i for i,v in enumerate(force_values) if v is not None and math.isfinite(v)]
            peak_index=max(finite,key=lambda i:force_values[i]) if finite else None
            if peak_index is not None and force_values[peak_index]>0:
                for xs,ys,label in series:
                    red=[y if i>=peak_index and y is not None and not (positive_only and (y<0 or (kind=='fd' and x<0))) else float('nan') for i,(x,y) in enumerate(zip(xs,ys))]
                    ax.plot(xs,red,color='#c62828',linestyle='-',marker=None,markersize=3,label='Desde carga máxima · '+session['metadata'].get('reference','Ensayo'))
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    if visible: ax.legend(fontsize=8,loc='best')
    else: ax.text(.5,.5,'Sin datos disponibles para esta gráfica',ha='center',va='center',transform=ax.transAxes,color=UC_PRIMARY)


def figure_for(session, kind):
    from matplotlib.figure import Figure
    fig=Figure(figsize=(8,4.5),dpi=120,constrained_layout=True)
    rows=session['samples']; duration=rows[-1]['t']-rows[0]['t'] if rows else 0
    window=max(1,round((len(rows)-1)/duration)) if duration>0 else 1
    ax=fig.add_subplot(111)
    processed=(session.get('configuration') or {}).get('export_processed',False)
    draw_chart(ax,[session],kind,method='Sin filtro' if processed else 'Mediana',window=1 if processed else 10,range_filter='Todo' if processed else 'Ensayo detectado',positive_only=True)
    ax.set_title(CHARTS[kind],loc='left',fontsize=11,fontweight='bold')
    return fig


def filtered_csv_text(session, method='Sin filtro', window=1, range_filter='Todo'):
    """CSV de análisis: contiene sólo la selección y los valores mostrados."""
    rows=legacy_plot_rows(session['samples']) if method=='Antiguo (10 lecturas)' else session['samples']
    indices=selected_indices(rows,range_filter)
    area=(session.get('configuration') or {}).get('specimen_area_mm2')
    filt=lambda values: time_average([r['t'] for r in rows],values,1.) if method=='Media temporal 1 s' else filter_values(values,method,window)
    all_forces=force_series([r['t'] for r in rows],[r['force_kp'] for r in rows],method=method,window=window)
    all_deformations=compression_deformation(filt([r['deformation_mm'] for r in rows]))
    forces=[all_forces[i] for i in indices]
    deformations=[all_deformations[i] for i in indices]
    out=io.StringIO(newline=''); writer=csv.writer(out,delimiter=';')
    writer.writerow(['tiempo_s','fuerza_kp_filtrada','fuerza_kgf_filtrada','fuerza_N_filtrada','fuerza_kN_filtrada','deformacion_mm_filtrada','presion_MPa_filtrada','presion_kgf_cm2_filtrada'])
    for index,force,deformation in zip(indices,forces,deformations):
        row=rows[index]
        try: pressure=[from_kp(force,u,area) for u in ('MPa','kgf/cm²')]
        except ValueError: pressure=['','']
        writer.writerow([row['t'],force,from_kp(force,'kgf'),from_kp(force,'N'),from_kp(force,'kN'),deformation,*pressure])
    return out.getvalue()


def html_report(session):
    summary=session_summary(session); meta=session['metadata']; esc=lambda v:html.escape(str(v))
    metrics=[('Carga máxima',f"{summary['peak_kp']:.2f} kp"),('Carga máxima',f"{summary['peak_kn']:.3f} kN"),
             ('Deformación al pico',f"{summary['deformation_at_peak_mm']:.3f} mm"),('Duración',f"{summary['duration_s']:.2f} s")]
    cards=''.join(f'<div class="card"><small>{esc(k)}</small><strong>{esc(v)}</strong></div>' for k,v in metrics)
    plots=[]
    for kind in CHARTS:
        buf=io.StringIO(); figure_for(session,kind).savefig(buf,format='svg')
        plots.append('<section>'+buf.getvalue()[buf.getvalue().index('<svg'):]+'</section>')
    mode='SIMULACIÓN' if meta.get('demo') is True else 'REAL' if meta.get('demo') is False else 'ORIGEN NO VERIFICADO'
    config=esc(json.dumps(session.get('configuration'),ensure_ascii=False,indent=2)) if session.get('configuration') else 'Configuración original no disponible.'
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta.get('reference','Ensayo'))} · Marshall</title>
<style>body{{font:15px system-ui,sans-serif;color:{UC_INK};background:{UC_BACKGROUND};margin:0}}main{{max-width:1100px;margin:auto;padding:32px}}h1{{font-size:32px}}.badge{{color:{UC_DEEP};font-weight:700}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card,section{{background:white;border-radius:14px;padding:18px;margin-bottom:18px;border-top:3px solid {UC_PALE}}}small,strong{{display:block}}strong{{font-size:24px;margin-top:8px}}svg{{width:100%;height:auto}}.plots{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}@media(max-width:700px){{.cards,.plots{{grid-template-columns:1fr}}}}@media print{{body{{background:white}}section{{break-inside:avoid}}main{{padding:0}}}}</style>
<main><div class="badge">MARSHALL / {mode}</div><h1>{esc(meta.get('reference','Ensayo'))}</h1>
<p>Probeta: {esc(meta.get('sample_id',''))} · Operador: {esc(meta.get('operator',''))}</p>
<p>Adquisición: {esc(session.get('acquired_at') or 'No disponible')} · Archivo: {esc(session['saved_at'])} · {summary['points']} puntos</p>
<p>{esc(meta.get('notes',''))}</p><div class="cards">{cards}</div><div class="plots">{''.join(plots)}</div>
<p>Referencia de cálculo: UNE-EN 12697-34:2022, apartados 3, 7 y anexo A. Los archivos generados desde Exportar utilizan la misma media por bloques de diez y los mismos puntos de la curva. El historial conserva los originales. Resultados individuales: no certifican por sí solos las condiciones del ensayo ni el grupo de probetas.</p>
<details><summary>Configuración y calibración originales</summary><pre>{config}</pre></details>
<p>Informe autónomo: las gráficas están incluidas y no requiere conexión a Internet. Use Imprimir en su navegador para obtener una copia.</p></main></html>'''


def write_xlsx(session,path):
    """Excel calculado con exactamente los puntos del panel de resultados."""
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill
    from marshall_results import add_excel_results
    wb=Workbook();wb.remove(wb.active)
    add_excel_results(wb,session)
    config=wb.create_sheet('Configuración')
    config.append(['Campo','Valor'])
    for key,value in {**session['metadata'],'Fecha adquisición':session.get('acquired_at'),'ID ensayo':session['id'],**(session.get('configuration') or {})}.items():
        config.append([key,json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value) if value is not None else 'No disponible'])
        config.cell(config.max_row,2).data_type='s'
    config.column_dimensions['A'].width=40;config.column_dimensions['B'].width=90;config.freeze_panes='A2'
    for cell in config[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor=UC_DEEP[1:])
    wb.active=1
    wb.save(path)


def export_session(session, path, kind):
    """Escribe a temporal en el mismo disco; un fallo no deja un archivo final parcial."""
    path=Path(path); dumps_session(session)
    fd,tmp=tempfile.mkstemp(prefix='.marshall-',suffix=path.suffix,dir=path.parent); os.close(fd)
    try:
        if kind=='json': Path(tmp).write_text(dumps_session(session),encoding='utf-8')
        elif kind=='html': Path(tmp).write_text(html_report(session),encoding='utf-8')
        elif kind=='xlsx': write_xlsx(session,tmp)
        elif kind=='zip':
            with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('ensayo.json',dumps_session(session))
                archive.writestr('datos.csv','\ufeff'+csv_text(session))
                archive.writestr('informe.html',html_report(session))
                for chart in CHARTS:
                    buffer=io.BytesIO(); figure_for(session,chart).savefig(buffer,format='png',dpi=160)
                    archive.writestr('graficas/'+chart+'.png',buffer.getvalue())
                archive.writestr('LEEME.txt','Abra ensayo.json en Marshall para recuperar todos los datos y metadatos. Los voltajes no disponibles son null en JSON y celdas vacías en CSV. El HTML funciona sin conexión.\n')
        else: raise ValueError('Formato no compatible.')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
