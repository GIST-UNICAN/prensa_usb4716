"""Comparación reproducible, solo lectura de originales e historial."""
import sys,json,sqlite3,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from measurement import read_legacy
from signal_processing import time_average,detect_rupture
out=Path('output/comparacion_antiguo'); out.mkdir(parents=True,exist_ok=True)
con=sqlite3.connect('file:ensayos/historial.sqlite3?mode=ro',uri=True)
s=json.loads(con.execute('select payload from sessions order by saved_at desc limit 1').fetchone()[0])
a=s['samples']; c=s['configuration']; t=[r['t'] for r in a]
f=time_average(t,[r['force_kp'] for r in a]); d=time_average(t,[r['deformation_mm'] for r in a])
# Conservar la misma tara física. El cero almacenado incorpora offset/factor.
physical_f=c['zero_force_v']-c.get('force_offset_kp',0)/c['force_factor_kp_per_v']
physical_d=c['zero_deform_v']-c.get('deformation_offset_mm',0)/c['deformation_factor_mm_per_v']
initial_f=time_average(t,[(r['vf']-physical_f)*-1970.57 for r in a])
initial_d=time_average(t,[(r['vd']-physical_d)*2.643095 for r in a])
i=max(range(len(f)),key=f.__getitem__)
metrics={'session_id':s['id'] if 'id' in s else s.get('session_id'),'reference':s['metadata']['reference'],'raw_peak_kp':max(r['force_kp'] for r in a),'mean_1s_peak_kp':f[i],'deformation_at_mean_peak_mm':d[i],'initial_calibration_peak_kp':max(initial_f),'initial_calibration_deformation_at_peak_mm':initial_d[i],'force_gain_change_percent':(-1970.57/c['force_factor_kp_per_v']-1)*100,'rupture':detect_rupture(a),'old_files':{}}
fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
axes[0,0].plot(t,[r['force_kp'] for r in a],alpha=.25,label='Bruta');axes[0,0].plot(t,f,label='Media temporal 1 s');axes[0,0].set(title='Última rotura: ruido y señal media',xlabel='Tiempo (s)',ylabel='Fuerza (kp)')
axes[0,1].plot(d,f,label='Última rotura · calibración registrada');axes[0,1].plot(initial_d,initial_f,'--',label='Última rotura · calibración inicial')
for name in ['prueba programa-1.txt','prueba comparativa con 3 del otro pc-1.txt']:
 rows=read_legacy(Path('C:/Users/andre/Desktop/andres')/name);peak=max(rows,key=lambda r:r[1]);metrics['old_files'][name]={'peak_kp':peak[1],'deformation_at_peak_mm':peak[2],'samples':len(rows)}
 axes[0,1].plot([r[2] for r in rows],[r[1] for r in rows],label=name)
axes[0,1].set(title='Mismas unidades; sin ajustar curvas entre probetas',xlabel='Deformación (mm)',ylabel='Fuerza (kp)')
axes[1,0].plot(t,d,label='Registrada / inicial (coinciden)');axes[1,0].plot(t,[x*1.28275592092386/2.643095 for x in d],label='Alternativa del anillo, misma tara');axes[1,0].set(xlabel='Tiempo (s)',ylabel='Deformación (mm)',title='Sensibilidad a calibración de deformación')
axes[1,1].plot(t,[r['vf'] for r in a],alpha=.4,label='Voltaje bruto fuerza');axes[1,1].plot(t,time_average(t,[r['vf'] for r in a]),label='Media 1 s');axes[1,1].set(xlabel='Tiempo (s)',ylabel='Voltaje (V)',title='La oscilación ya está en los voltajes')
for ax in axes.flat: ax.grid(alpha=.2);ax.legend(fontsize=7)
fig.savefig(out/'comparacion.png',dpi=150)
(out/'metricas.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(metrics,ensure_ascii=True,indent=2))
