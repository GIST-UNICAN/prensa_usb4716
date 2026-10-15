"""Recalcula copias de los dos últimos ensayos reales; no escribe en el historial."""
import sys,json,sqlite3,html
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calibration_comparison import recalibrate,INITIAL_CALIBRATION
from marshall_results import session_results,draw_results
from exports import export_session
from matplotlib.figure import Figure

out=Path('output/comparacion_dos_ultimos');out.mkdir(parents=True,exist_ok=True)
con=sqlite3.connect('file:ensayos/historial.sqlite3?mode=ro',uri=True)
sessions=[]
for payload, in con.execute('select payload from sessions order by saved_at desc'):
    session=json.loads(payload)
    if session['metadata'].get('demo') is False and session.get('configuration'):
        sessions.append(session)
        if len(sessions)==2:break
con.close()
comparison=[]
fig=Figure(figsize=(12,5),layout='constrained')
for i,session in enumerate(sessions):
    cfg=session['configuration']
    calibration=next(r for r in cfg['calibration_history'] if r.get('method')=='ring_zero_and_1mm')
    ring={**INITIAL_CALIBRATION,'force_factor_kp_per_v':cfg['force_factor_kp_per_v'],'force_offset_kp':cfg.get('force_offset_kp',0),
          'deformation_factor_mm_per_v':calibration['deformation_fit']['factor'],'deformation_offset_mm':calibration['deformation_fit']['offset']}
    initial=recalibrate(session)
    ring_session=recalibrate(session,ring)
    item=dict(id=session['id'],reference=session['metadata']['reference'],acquired_at=session.get('acquired_at'),scenarios={})
    ax=fig.add_subplot(1,2,i+1)
    for label,copy in [('Registrada',session),('Inicial',initial),('Anillo: hipótesis de recorrido',ring_session)]:
        result=session_results(copy)
        item['scenarios'][label]={k:result[k] for k in ('peak_kp','peak_mm','corrected_mm','slope_kp_mm')}
        rows=result['rows']
        ax.plot([r['deformation_mm'] for r in rows],[r['force_kp'] for r in rows],label=label)
    ax.set_title(session['metadata']['reference']+'\n'+session.get('acquired_at',''));ax.set_xlabel('Recorrido estimado (mm)');ax.set_ylabel('Fuerza (kp)');ax.grid(alpha=.2);ax.legend(fontsize=8)
    initial['metadata']['notes']+='\nRecalculado con calibración inicial conservando la misma tara física. No es una nueva adquisición.'
    export_session(initial,out/f'ensayo_{i+1}_calibracion_inicial.xlsx','xlsx')
    item['xlsx']=f'ensayo_{i+1}_calibracion_inicial.xlsx';comparison.append(item)
fig.savefig(out/'comparacion.png',dpi=140)
(out/'comparacion.json').write_text(json.dumps(comparison,indent=2,ensure_ascii=False),encoding='utf-8')
rows=[]
for index,item in enumerate(comparison):
    for name,result in item['scenarios'].items():
        rows.append('<tr><td>'+html.escape(item['reference'])+'</td><td>'+html.escape(name)+'</td>'+''.join(f'<td>{result[k]:.2f}</td>' if result[k] is not None else '<td>No disponible</td>' for k in ('peak_kp','peak_mm','corrected_mm'))+'</tr>')
body="""<!doctype html><meta charset="utf-8"><title>Comparación de calibraciones</title><style>body{font:17px Arial;max-width:1150px;margin:30px auto;color:#173f49}table{border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #ccc;text-align:left}img{max-width:100%}p{line-height:1.5}</style><h1>Dos últimos ensayos: calibración registrada, inicial y del anillo</h1><p>Comparación sobre los mismos voltajes y el mismo cero físico. Media por bloques de 10 lecturas, exclusión de fuerza negativa y recorrido estimado sin retrocesos en los tres casos. No se modifica la configuración activa ni los ensayos archivados.</p><table><tr><th>Ensayo</th><th>Calibración</th><th>Pico (kp)</th><th>Deformación en pico (mm)</th><th>Corregida por tangente (mm)</th></tr>"""
body+=''.join(rows)+'</table><p>Los factores iniciales son −1970,57 kp/V y 2,643095 mm/V, con offsets cero. El anillo guardado proporciona 1,282755921 mm/V: su intervalo de referencia de 1 mm se convertiría en 2,06048 mm con el factor actual. El usuario aclara que el anillo se deformó: este ajuste NO valida el recorrido de prensa ni la deformación de probeta. La columna del anillo es una hipótesis numérica, no una calibración aplicable del recorrido.</p><img src="comparacion.png" alt="Curvas con las tres calibraciones"><p>Los Excel siguientes contienen el escenario inicial ya calculado, lecturas brutas y gráfica editable:</p><ul>'
body+=''.join('<li><a href="'+r['xlsx']+'">'+html.escape(r['reference'])+' · calibración inicial</a></li>' for r in comparison)+'</ul>'
(out/'informe.html').write_text(body,encoding='utf-8')
print(json.dumps(comparison,indent=2,ensure_ascii=True))
